"""
非同期画像生成管理モジュール
"""

from typing import Dict, List, Optional, Any
import logging
import time
from app.tasks.utils import (
    create_image_chunks, validate_menu_data, generate_job_id,
    save_job_info, get_job_info, calculate_job_progress, cleanup_job_data
)
from app.tasks.image_tasks import advanced_image_chunk_task, real_image_chunk_task
from app.core.config import settings

logger = logging.getLogger(__name__)

class AsyncImageManager:
    """非同期画像生成の管理クラス"""
    
    def __init__(self):
        self.manager_name = "AsyncImageManager"
        logger.info(f"{self.manager_name} initialized")
    
    def validate_request(self, final_menu: Dict[str, List[Dict]]) -> tuple[bool, str]:
        """
        リクエストデータの妥当性をチェック
        
        Args:
            final_menu: 検証対象のメニューデータ
            
        Returns:
            (妥当性フラグ, エラーメッセージ)
        """
        if not isinstance(final_menu, dict):
            return False, "Menu data must be a dictionary"
        
        if not final_menu:
            return False, "Menu data cannot be empty"
        
        # 基本的な妥当性チェック
        if not validate_menu_data(final_menu):
            return False, "Invalid menu data structure or missing required fields"
        
        # アイテム数チェック
        total_items = sum(len(items) for items in final_menu.values())
        if total_items == 0:
            return False, "No menu items found"
        
        if total_items > settings.MAX_IMAGE_WORKERS * 10:  # 適度な制限
            return False, f"Too many items ({total_items}). Maximum allowed: {settings.MAX_IMAGE_WORKERS * 10}"
        
        return True, "Valid"
    
    def create_job_chunks(self, final_menu: Dict[str, List[Dict]]) -> List[Dict]:
        """
        メニューデータからジョブ用チャンクを作成
        
        Args:
            final_menu: メニューデータ
            
        Returns:
            チャンクリスト
        """
        chunks = create_image_chunks(
            final_menu, 
            chunk_size=settings.IMAGE_PROCESSING_CHUNK_SIZE
        )
        
        logger.info(f"Created {len(chunks)} chunks for processing")
        return chunks
    
    def start_async_generation(
        self, 
        final_menu: Dict[str, List[Dict]], 
        session_id: Optional[str] = None
    ) -> tuple[bool, str, Optional[str]]:
        """
        非同期画像生成を開始
        
        Args:
            final_menu: メニューデータ
            session_id: セッションID
            
        Returns:
            (成功フラグ, メッセージ, ジョブID)
        """
        try:
            # リクエスト妥当性チェック
            is_valid, error_message = self.validate_request(final_menu)
            if not is_valid:
                logger.error(f"Request validation failed: {error_message}")
                return False, error_message, None
            
            # ジョブID生成
            job_id = generate_job_id()
            logger.info(f"Starting async image generation: job_id={job_id}")
            
            # チャンク作成
            chunks = self.create_job_chunks(final_menu)
            
            if not chunks:
                return False, "No chunks created from menu data", None
            
            # ジョブ情報を作成・保存
            job_data = {
                "job_id": job_id,
                "status": "starting",
                "total_chunks": len(chunks),
                "session_id": session_id,
                "created_at": time.time(),
                "menu_data": final_menu,
                "chunk_size": settings.IMAGE_PROCESSING_CHUNK_SIZE,
                "estimated_time": sum(len(items) for items in final_menu.values()) * 2,  # 2秒/アイテム
                "total_items": sum(len(items) for items in final_menu.values())
            }
            
            if not save_job_info(job_id, job_data):
                return False, "Failed to save job information", None
            
            # 各チャンクをタスクキューに送信
            task_ids = []
            
            # 実際の画像生成を行うかモック処理にするかを設定で制御
            use_real_image_generation = getattr(settings, 'USE_REAL_IMAGE_GENERATION', True)
            selected_task = real_image_chunk_task if use_real_image_generation else advanced_image_chunk_task
            task_type = "real_image" if use_real_image_generation else "mock_image"
            
            logger.info(f"Using {task_type} generation for job {job_id}")
            
            for chunk in chunks:
                chunk_info = {
                    "chunk_id": chunk["chunk_id"],
                    "total_chunks": chunk["total_chunks"],
                    "category": chunk["category"]
                }
                
                try:
                    task = selected_task.delay(
                        chunk["items"], 
                        chunk_info, 
                        job_id
                    )
                    task_ids.append(task.id)
                    logger.info(f"Queued {task_type} chunk {chunk['chunk_id']}: task_id={task.id}")
                    
                except Exception as e:
                    logger.error(f"Failed to queue chunk {chunk['chunk_id']}: {e}")
                    continue
            
            if not task_ids:
                cleanup_job_data(job_id)
                return False, "Failed to queue any tasks", None
            
            # ジョブ情報にタスクIDを追加
            job_data["task_ids"] = task_ids
            job_data["status"] = "queued"
            job_data["queued_at"] = time.time()
            
            if not save_job_info(job_id, job_data):
                logger.warning(f"Failed to update job info with task IDs: {job_id}")
            
            logger.info(f"Async image generation started: job_id={job_id}, chunks={len(chunks)}, tasks={len(task_ids)}")
            return True, f"Image generation started with {len(chunks)} chunks", job_id
            
        except Exception as e:
            logger.error(f"Failed to start async image generation: {e}")
            return False, f"Internal error: {str(e)}", None
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        ジョブの現在ステータスを取得
        
        Args:
            job_id: ジョブID
            
        Returns:
            ジョブステータス情報
        """
        try:
            # 基本ジョブ情報を取得
            job_info = get_job_info(job_id)
            if not job_info:
                return {
                    "found": False,
                    "error": "Job not found",
                    "job_id": job_id
                }
            
            # 進行状況を計算
            progress_info = calculate_job_progress(job_id)
            
            # レスポンスを構築
            response = {
                "found": True,
                "job_id": job_id,
                "status": progress_info.get("status", "unknown"),
                "progress_percent": progress_info.get("progress_percent", 0),
                "total_chunks": job_info.get("total_chunks", 0),
                "completed_chunks": progress_info.get("completed_chunks", 0),
                "failed_chunks": progress_info.get("failed_chunks", 0),
                "created_at": job_info.get("created_at", 0),
                "session_id": job_info.get("session_id"),
                "total_items": job_info.get("total_items", 0),
                "estimated_time": job_info.get("estimated_time", 0)
            }
            
            # 完了時は結果も含める
            if response["status"] in ["completed", "partial_completed"]:
                chunk_results = progress_info.get("chunk_results", {})
                
                # 結果を統合
                final_images = {}
                total_successful_images = 0
                
                for chunk_id, chunk_result in chunk_results.items():
                    if chunk_result.get("status") == "completed":
                        category = chunk_result.get("category", "Unknown")
                        results = chunk_result.get("results", [])
                        
                        if category not in final_images:
                            final_images[category] = []
                        
                        final_images[category].extend(results)
                        total_successful_images += len([r for r in results if r.get("generation_success")])
                
                response.update({
                    "images_generated": final_images,
                    "total_images": total_successful_images,
                    "completed_at": max(
                        (chunk.get("completed_at", 0) for chunk in chunk_results.values() 
                         if chunk.get("status") == "completed"), 
                        default=time.time()
                    )
                })
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to get job status: {e}")
            return {
                "found": False,
                "error": f"Status retrieval error: {str(e)}",
                "job_id": job_id
            }
    
    def cancel_job(self, job_id: str) -> tuple[bool, str]:
        """
        ジョブをキャンセル
        
        Args:
            job_id: ジョブID
            
        Returns:
            (成功フラグ, メッセージ)
        """
        try:
            job_info = get_job_info(job_id)
            if not job_info:
                return False, "Job not found"
            
            # ジョブ状態を確認
            current_status = job_info.get("status", "unknown")
            if current_status in ["completed", "failed", "cancelled"]:
                return False, f"Cannot cancel job in {current_status} state"
            
            # タスクをキャンセル（Celeryタスクの停止）
            task_ids = job_info.get("task_ids", [])
            cancelled_tasks = 0
            
            for task_id in task_ids:
                try:
                    # Celeryタスクを取り消し
                    from app.tasks.celery_app import celery_app
                    celery_app.control.revoke(task_id, terminate=True)
                    cancelled_tasks += 1
                except Exception as e:
                    logger.warning(f"Failed to cancel task {task_id}: {e}")
            
            # ジョブステータスを更新
            job_info["status"] = "cancelled"
            job_info["cancelled_at"] = time.time()
            job_info["cancelled_tasks"] = cancelled_tasks
            
            save_job_info(job_id, job_info)
            
            logger.info(f"Job cancelled: job_id={job_id}, cancelled_tasks={cancelled_tasks}")
            return True, f"Job cancelled successfully ({cancelled_tasks} tasks stopped)"
            
        except Exception as e:
            logger.error(f"Failed to cancel job: {e}")
            return False, f"Cancellation error: {str(e)}"
    
    def cleanup_old_jobs(self, max_age_hours: int = 24) -> tuple[int, int]:
        """
        古いジョブデータをクリーンアップ
        
        Args:
            max_age_hours: 最大保持時間（時間）
            
        Returns:
            (削除件数, エラー件数)
        """
        try:
            # 実装は簡略化（実際にはRedisのキーを列挙して古いものを削除）
            logger.info(f"Cleanup requested for jobs older than {max_age_hours} hours")
            # ここでは実装を省略
            return 0, 0
            
        except Exception as e:
            logger.error(f"Failed to cleanup old jobs: {e}")
            return 0, 1
    
    def get_manager_stats(self) -> Dict[str, Any]:
        """
        マネージャーの統計情報を取得
        
        Returns:
            統計情報
        """
        return {
            "manager_name": self.manager_name,
            "config": {
                "chunk_size": settings.IMAGE_PROCESSING_CHUNK_SIZE,
                "max_workers": settings.MAX_IMAGE_WORKERS,
                "job_timeout": settings.IMAGE_JOB_TIMEOUT,
                "async_enabled": settings.ASYNC_IMAGE_ENABLED
            },
            "features": [
                "async_image_generation",
                "chunk_based_processing", 
                "redis_progress_tracking",
                "job_cancellation",
                "real_time_status"
            ]
        }

# シングルトンインスタンス
_async_manager_instance = None

def get_async_manager() -> AsyncImageManager:
    """AsyncImageManagerのシングルトンインスタンスを取得"""
    global _async_manager_instance
    if _async_manager_instance is None:
        _async_manager_instance = AsyncImageManager()
    return _async_manager_instance

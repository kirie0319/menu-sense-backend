"""
🎯 MenuProcessingService - メニュー処理統合サービス

このサービスはメニュー処理の統合管理を担当します。
セッション管理、タスク調整、SSE通知を統合し、エンドポイントから
ビジネスロジックを完全に分離します。
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from .session_manager import SessionManager, ProcessingSession
from .task_coordinator import TaskCoordinator, TaskBatch, QueueMode
from .file_handler import FileHandler

# Import status function
from app.tasks.pure_menu_tasks import pure_get_real_status


@dataclass
class MenuItemsRequest:
    """メニューアイテム処理リクエスト"""
    menu_items: List[str]
    test_mode: bool = False


@dataclass
class ProcessingResult:
    """処理結果"""
    success: bool
    session: ProcessingSession
    task_batch: TaskBatch
    message: str
    streaming_url: str
    status_url: str
    error: Optional[str] = None


class MenuProcessingService:
    """
    メニュー処理統合サービス
    
    責任:
    - メニュー処理の統合管理
    - セッション・タスク・SSEの調整
    - ビジネスロジック実装
    - エラーハンドリング
    """

    def __init__(
        self,
        session_manager: SessionManager,
        task_coordinator: TaskCoordinator,
        file_handler: FileHandler
    ):
        self.session_manager = session_manager
        self.task_coordinator = task_coordinator
        self.file_handler = file_handler

    async def start_menu_processing(
        self, 
        request: MenuItemsRequest
    ) -> ProcessingResult:
        """
        メニュー処理を開始
        
        Args:
            request: 処理リクエスト
            
        Returns:
            ProcessingResult: 処理結果
        """
        try:
            # 1. セッション作成・管理
            session = await self.session_manager.create_session(
                menu_items=request.menu_items,
                test_mode=request.test_mode
            )
            
            # 2. バリデーション
            self._validate_processing_request(request)
            
            # 3. タスク投入調整
            task_batch = await self.task_coordinator.queue_processing_tasks(session)
            
            # 4. レスポンス構築
            result = ProcessingResult(
                success=True,
                session=session,
                task_batch=task_batch,
                message=self._build_success_message(session, task_batch),
                streaming_url=f"/api/v1/menu-parallel/stream/{session.session_id}",
                status_url=f"/api/v1/menu-parallel/status/{session.session_id}"
            )
            
            return result
            
        except Exception as e:
            return ProcessingResult(
                success=False,
                session=None,
                task_batch=None,
                message="Processing failed",
                streaming_url="",
                status_url="",
                error=str(e)
            )

    async def start_categorized_processing(
        self, 
        categories: Dict[str, List[str]], 
        test_mode: bool = False
    ) -> ProcessingResult:
        """
        カテゴリ分類済みメニューの処理を開始
        
        Args:
            categories: カテゴリ分類されたメニューアイテム
            test_mode: テストモード
            
        Returns:
            ProcessingResult: 処理結果
        """
        try:
            # メニューアイテムリストを展開
            menu_items = []
            for category_items in categories.values():
                for item in category_items:
                    item_text = item if isinstance(item, str) else item.get('name', str(item))
                    menu_items.append(item_text)
            
            # セッション作成
            session = await self.session_manager.create_session(
                menu_items=menu_items,
                test_mode=test_mode
            )
            
            # カテゴリ情報をメタデータに保存
            session.metadata["categories"] = categories
            session.metadata["processing_type"] = "categorized"
            
            # タスク投入（カテゴリ付き）
            task_batch = await self.task_coordinator.queue_processing_tasks(
                session, categories
            )
            
            result = ProcessingResult(
                success=True,
                session=session,
                task_batch=task_batch,
                message=self._build_categorized_success_message(session, categories, task_batch),
                streaming_url=f"/api/v1/menu-parallel/stream/{session.session_id}",
                status_url=f"/api/v1/menu-parallel/status/{session.session_id}"
            )
            
            return result
            
        except Exception as e:
            return ProcessingResult(
                success=False,
                session=None,
                task_batch=None,
                message="Categorized processing failed",
                streaming_url="",
                status_url="",
                error=str(e)
            )

    async def get_item_status(
        self, 
        session_id: str, 
        item_id: int
    ) -> Dict[str, Any]:
        """
        アイテム状況を取得
        
        Args:
            session_id: セッションID
            item_id: アイテムID
            
        Returns:
            Dict: アイテム状況
        """
        try:
            # セッション確認
            session = await self.session_manager.get_session(session_id)
            if session is None:
                raise ValueError(f"Session not found: {session_id}")
            
            # アイテムIDバリデーション
            if item_id < 0 or item_id >= session.total_items:
                raise ValueError(f"Invalid item_id: {item_id}")
            
            # タスク状況取得（Redis経由）
            status = pure_get_real_status(session_id, item_id)
            
            if "error" in status:
                raise ValueError(status["error"])
            
            return {
                "success": True,
                "session_id": session_id,
                "item_id": item_id,
                "translation": status.get("translation", {"completed": False, "data": None}),
                "description": status.get("description", {"completed": False, "data": None}),
                "image": status.get("image", {"completed": False, "data": None}),
                "session_info": session.to_response_dict()
            }
            
        except Exception as e:
            return {
                "success": False,
                "session_id": session_id,
                "item_id": item_id,
                "error": str(e)
            }

    async def get_session_status(
        self, 
        session_id: str, 
        total_items: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        セッション全体の状況を取得
        
        Args:
            session_id: セッションID
            total_items: 合計アイテム数（後方互換性）
            
        Returns:
            Dict: セッション状況
        """
        try:
            # セッション確認
            session = await self.session_manager.get_session(session_id)
            if session is None:
                raise ValueError(f"Session not found: {session_id}")
            
            # total_itemsが指定されている場合は使用（後方互換性）
            items_count = total_items if total_items is not None else session.total_items
            
            # 各アイテムの状況を収集
            items_status = []
            completed_count = 0
            
            for item_id in range(items_count):
                try:
                    status = pure_get_real_status(session_id, item_id)
                    
                    if "error" not in status:
                        item_status = self._build_item_status(item_id, status)
                        items_status.append(item_status)
                        
                        if item_status["overall_completed"]:
                            completed_count += 1
                    else:
                        items_status.append(self._build_error_item_status(item_id, status.get("error", "Unknown error")))
                        
                except Exception as item_error:
                    items_status.append(self._build_error_item_status(item_id, f"Status check failed: {str(item_error)}"))
            
            # セッション進行状況更新
            await self.session_manager.update_session_progress(session_id, completed_count)
            
            # 進行率計算
            progress_percentage = (completed_count / items_count * 100) if items_count > 0 else 0
            
            return {
                "success": True,
                "session_id": session_id,
                "total_items": items_count,
                "completed_items": completed_count,
                "progress_percentage": progress_percentage,
                "items_status": items_status,
                "api_integration": session.api_mode,
                "session_info": session.to_response_dict()
            }
            
        except Exception as e:
            return {
                "success": False,
                "session_id": session_id,
                "error": str(e)
            }

    def get_processing_statistics(self) -> Dict[str, Any]:
        """
        処理統計を取得
        
        Returns:
            Dict: 統計情報
        """
        session_stats = self.session_manager.get_session_statistics()
        task_stats = self.task_coordinator.get_task_statistics()
        file_stats = self.file_handler.get_file_statistics()
        
        return {
            "service_status": "active",
            "session_statistics": session_stats,
            "task_statistics": task_stats,
            "file_statistics": file_stats,
            "integration_apis": [
                "Google Translate",
                "OpenAI GPT-4",
                "Google Imagen 3",
                "Gemini OCR",
                "Redis Queue"
            ]
        }

    async def cleanup_processing_session(self, session_id: str) -> Dict[str, Any]:
        """
        処理セッションをクリーンアップ
        
        Args:
            session_id: セッションID
            
        Returns:
            Dict: クリーンアップ結果
        """
        cleanup_results = {}
        
        # セッションクリーンアップ
        session_cleaned = await self.session_manager.cleanup_session(session_id)
        cleanup_results["session_cleaned"] = session_cleaned
        
        # タスクバッチクリーンアップ
        task_batch_cleaned = await self.task_coordinator.cleanup_batch(session_id)
        cleanup_results["task_batch_cleaned"] = task_batch_cleaned
        
        # ファイルクリーンアップ
        files_cleaned = await self.file_handler.cleanup_session_files(session_id)
        cleanup_results["files_cleaned"] = files_cleaned
        
        return {
            "success": True,
            "session_id": session_id,
            "cleanup_results": cleanup_results,
            "message": f"Session {session_id} cleaned up successfully"
        }

    def _validate_processing_request(self, request: MenuItemsRequest) -> None:
        """処理リクエストのバリデーション"""
        if not request.menu_items:
            raise ValueError("Menu items cannot be empty")
        
        if len(request.menu_items) > 100:
            raise ValueError("Too many menu items (max: 100)")

    def _build_success_message(self, session: ProcessingSession, task_batch: TaskBatch) -> str:
        """成功メッセージを構築"""
        api_integration = "real API integration" if session.api_mode == "real_api_integration" else "test mode"
        return (
            f"Started {api_integration} processing for {session.total_items} menu items. "
            f"Google Translate + OpenAI GPT-4 + Google Imagen 3. "
            f"Queued {task_batch.total_tasks} tasks. "
            f"Use /stream/{session.session_id} for real-time progress."
        )

    def _build_categorized_success_message(
        self, 
        session: ProcessingSession, 
        categories: Dict[str, List[str]], 
        task_batch: TaskBatch
    ) -> str:
        """カテゴリ分類成功メッセージを構築"""
        api_integration = "real API integration" if session.api_mode == "real_api_integration" else "test mode"
        category_count = len(categories)
        return (
            f"🎉 Complete OCR → Categorization → Parallel Processing pipeline started! "
            f"{session.total_items} items in {category_count} categories queued with {api_integration}. "
            f"APIs: Gemini OCR + OpenAI Categorization + Google Translate + OpenAI Description + Google Imagen 3"
        )

    def _build_item_status(self, item_id: int, status: Dict[str, Any]) -> Dict[str, Any]:
        """アイテム状況を構築"""
        translation_data = status.get("translation", {})
        description_data = status.get("description", {})
        image_data = status.get("image", {})
        
        t_completed = translation_data.get("completed", False)
        d_completed = description_data.get("completed", False)
        i_completed = image_data.get("completed", False)
        
        item_status = {
            "item_id": item_id,
            "translation_completed": t_completed,
            "description_completed": d_completed,
            "image_completed": i_completed,
            "overall_completed": t_completed and d_completed and i_completed
        }
        
        # 実際のデータを追加
        if t_completed and translation_data.get("data"):
            t_data = translation_data["data"]
            item_status.update({
                "japanese_text": t_data.get("japanese_text", ""),
                "english_text": t_data.get("english_text", ""),
                "translation_provider": t_data.get("provider", "")
            })
        
        if d_completed and description_data.get("data"):
            d_data = description_data["data"]
            item_status.update({
                "description": d_data.get("description", ""),
                "description_provider": d_data.get("provider", "")
            })
        
        if i_completed and image_data.get("data"):
            i_data = image_data["data"]
            item_status.update({
                "image_url": i_data.get("image_url", ""),
                "image_provider": i_data.get("provider", ""),
                "fallback_used": i_data.get("fallback_used", False)
            })
        
        return item_status

    def _build_error_item_status(self, item_id: int, error: str) -> Dict[str, Any]:
        """エラーアイテム状況を構築"""
        return {
            "item_id": item_id,
            "translation_completed": False,
            "description_completed": False,
            "image_completed": False,
            "overall_completed": False,
            "error": error
        }
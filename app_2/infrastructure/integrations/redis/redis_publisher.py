"""
Redis Publisher - Infrastructure Layer
Simple message publisher for SSE communication (MVP Simplified)
"""

import json
from typing import Dict, Any, Optional, List
from datetime import datetime

from app_2.infrastructure.integrations.redis.redis_client import RedisClient
from app_2.core.config import settings
from app_2.utils.logger import get_logger

logger = get_logger("redis_publisher")


class RedisPublisher:
    """
    Redis メッセージ配信クライアント（MVP版）
    
    SSE用メッセージ配信の基本機能を提供
    """
    
    def __init__(self, redis_client: Optional[RedisClient] = None):
        """
        Redis Publisher を初期化
        
        Args:
            redis_client: Redis クライアント（オプション）
        """
        self.redis_client = redis_client or RedisClient()

    async def publish_session_message(
        self, 
        session_id: str, 
        message_type: str, 
        data: Dict[str, Any]
    ) -> bool:
        """
        セッション用メッセージを配信
        
        Args:
            session_id: セッションID
            message_type: メッセージタイプ
            data: メッセージデータ
            
        Returns:
            bool: 配信が成功したか
        """
        try:
            # チャンネル名を生成
            channel = settings.celery.get_sse_channel(session_id)
            
            # メッセージを構築
            message = {
                "type": message_type,
                "session_id": session_id,
                "data": data,
                "timestamp": self._get_timestamp()
            }
            
            # JSON文字列に変換
            message_json = json.dumps(message, ensure_ascii=False)
            
            # Redis に配信
            subscriber_count = await self.redis_client.publish(channel, message_json)
            
            logger.info(f"📢 Published {message_type} to session {session_id} -> {subscriber_count} subscribers")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to publish session message {session_id}/{message_type}: {e}")
            return False

    async def publish_stage_completion(
        self, 
        session_id: str, 
        stage: str, 
        data: Dict[str, Any]
    ) -> bool:
        """
        各段階完了時のSSE配信
        
        Args:
            session_id: セッションID
            stage: 完了した段階名 (ocr, mapping, categorize等)
            data: 段階完了データ
            
        Returns:
            bool: 配信が成功したか
        """
        return await self.publish_session_message(
            session_id=session_id,
            message_type="stage_completed",
            data={
                "stage": stage,
                "completion_data": data,
                "timestamp": self._get_timestamp(),
                "ui_action": f"update_{stage}_display"  # フロントエンド向けアクション指示
            }
        )

    async def publish_stage_completion_enhanced(
        self, 
        session_id: str, 
        stage: str,
        stage_results: Any,
        next_stage_info: Optional[Dict] = None,
        **kwargs
    ) -> bool:
        """
        段階完了時の拡張SSE配信（OCR、Mapping、Categorize共通）
        
        Args:
            session_id: セッションID
            stage: 段階名 ("ocr", "mapping", "categorize")
            stage_results: 各段階の処理結果
            next_stage_info: 次段階の情報
            **kwargs: 段階固有の追加データ
            
        Returns:
            bool: 配信が成功したか
        """
        try:
            # 段階ごとのデータ構築
            if stage == "ocr":
                stage_data = self._build_ocr_stage_data(stage_results, **kwargs)
            elif stage == "mapping":
                stage_data = self._build_mapping_stage_data(stage_results, **kwargs)
            elif stage == "categorize":
                stage_data = self._build_categorize_stage_data(stage_results, **kwargs)
            else:
                # 汎用段階データ
                stage_data = {
                    "stage_name": stage,
                    "results": stage_results,
                    "processing_successful": True
                }
            
            # 次段階情報を追加
            if next_stage_info:
                stage_data.update(next_stage_info)
            
            # DB保存状況を追加
            stage_data["db_saved"] = kwargs.get("db_saved", False)
            
            logger.info(f"📝 Publishing {stage} completion: session {session_id}")
            
            return await self.publish_stage_completion(
                session_id=session_id,
                stage=stage,
                data=stage_data
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to publish {stage} completion: {e}")
            return False

    def _build_ocr_stage_data(self, ocr_results: List[Dict], **kwargs) -> Dict[str, Any]:
        """OCR段階の専用データ構築"""
        # OCR結果のプレビュー作成
        preview_elements = []
        for i, element in enumerate(ocr_results[:5]):  # 最初の5個
            preview_elements.append({
                "index": i + 1,
                "text": element.get("text", ""),
                "position": {
                    "x": round(element.get("x_center", 0), 1),
                    "y": round(element.get("y_center", 0), 1)
                }
            })
        
        return {
            "elements_extracted": len(ocr_results),
            "preview_elements": preview_elements,
            "ocr_summary": {
                "total_elements": len(ocr_results),
                "text_density": "high" if len(ocr_results) > 20 else "medium" if len(ocr_results) > 10 else "low",
                "processing_successful": True
            },
            "next_stage": "mapping",
            "estimated_next_duration": 15
        }

    def _build_mapping_stage_data(self, mapping_data: str, **kwargs) -> Dict[str, Any]:
        """Mapping段階の専用データ構築"""
        # データプレビューを作成
        preview_length = min(200, len(mapping_data))
        preview_data = mapping_data[:preview_length]
        if len(mapping_data) > preview_length:
            preview_data += "..."
        
        return {
            "data_formatted": True,
            "formatted_data_length": len(mapping_data),
            "data_preview": preview_data,
            "mapping_summary": {
                "total_data_size": len(mapping_data),
                "preview_available": True,
                "processing_successful": True
            },
            "next_stage": "categorization",
            "estimated_next_duration": 20
        }

    def _build_categorize_stage_data(self, categorize_results: Dict, **kwargs) -> Dict[str, Any]:
        """Categorize段階の専用データ構築"""
        # カテゴリ情報を抽出
        categories = []
        menu_items_count = 0
        
        if "menu" in categorize_results and "categories" in categorize_results["menu"]:
            categories_data = categorize_results["menu"]["categories"]
            for cat in categories_data:
                category_info = {
                    "name": cat.get("name", "unknown"),
                    "japanese_name": cat.get("japanese_name", ""),
                    "items_count": len(cat.get("items", []))
                }
                categories.append(category_info)
                menu_items_count += category_info["items_count"]
        
        # 保存されたメニューアイテム情報（kwargsから取得）
        saved_menu_items = kwargs.get("saved_menu_items", [])
        
        return {
            "menu_structure_analyzed": True,
            "categories_found": categories,
            "total_categories": len(categories),
            "total_menu_items": menu_items_count,
            "saved_items_count": len(saved_menu_items),
            "menu_items": saved_menu_items[:10],  # 最初の10個をプレビュー
            "categorization_summary": {
                "categories_detected": len(categories),
                "items_categorized": menu_items_count,
                "processing_successful": True
            },
            "next_stage": "parallel_enhancements",
            "estimated_next_duration": 60,
            "parallel_tasks_starting": True
        }

    # 段階別の便利メソッド
    async def publish_ocr_completion(
        self, 
        session_id: str, 
        ocr_results: list,
        next_stage_info: Optional[Dict] = None,
        **kwargs
    ) -> bool:
        """OCR完了時の配信（後方互換性）"""
        return await self.publish_stage_completion_enhanced(
            session_id=session_id,
            stage="ocr",
            stage_results=ocr_results,
            next_stage_info=next_stage_info,
            **kwargs
        )

    async def publish_mapping_completion(
        self, 
        session_id: str, 
        mapping_data: str,
        next_stage_info: Optional[Dict] = None,
        **kwargs
    ) -> bool:
        """Mapping完了時の配信"""
        return await self.publish_stage_completion_enhanced(
            session_id=session_id,
            stage="mapping",
            stage_results=mapping_data,
            next_stage_info=next_stage_info,
            **kwargs
        )

    async def publish_categorize_completion(
        self, 
        session_id: str, 
        categorize_results: Dict,
        saved_menu_items: Optional[List] = None,
        next_stage_info: Optional[Dict] = None,
        **kwargs
    ) -> bool:
        """Categorize完了時の配信"""
        if saved_menu_items:
            kwargs["saved_menu_items"] = saved_menu_items
            
        return await self.publish_stage_completion_enhanced(
            session_id=session_id,
            stage="categorize",
            stage_results=categorize_results,
            next_stage_info=next_stage_info,
            **kwargs
        )

    async def publish_progress_update(
        self, 
        session_id: str, 
        task_name: str, 
        status: str, 
        progress_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        進捗更新メッセージを配信
        
        Args:
            session_id: セッションID
            task_name: タスク名
            status: タスクステータス
            progress_data: 進捗データ（オプション）
            
        Returns:
            bool: 配信が成功したか
        """
        data = {
            "task_name": task_name,
            "status": status
        }
        
        if progress_data:
            data.update(progress_data)
        
        return await self.publish_session_message(
            session_id=session_id,
            message_type="progress_update",
            data=data
        )

    async def publish_menu_update(
        self, 
        session_id: str, 
        menu_id: str, 
        menu_data: Dict[str, Any]
    ) -> bool:
        """
        メニュー更新メッセージを配信
        
        Args:
            session_id: セッションID
            menu_id: メニューID
            menu_data: メニューデータ
            
        Returns:
            bool: 配信が成功したか
        """
        data = {
            "menu_id": menu_id,
            "menu_data": menu_data
        }
        
        return await self.publish_session_message(
            session_id=session_id,
            message_type="menu_update",
            data=data
        )

    async def publish_error_message(
        self, 
        session_id: str, 
        error_type: str, 
        error_message: str, 
        task_name: Optional[str] = None
    ) -> bool:
        """
        エラーメッセージを配信
        
        Args:
            session_id: セッションID
            error_type: エラータイプ
            error_message: エラーメッセージ
            task_name: タスク名（オプション）
            
        Returns:
            bool: 配信が成功したか
        """
        data = {
            "error_type": error_type,
            "error_message": error_message
        }
        
        if task_name:
            data["task_name"] = task_name
        
        return await self.publish_session_message(
            session_id=session_id,
            message_type="error",
            data=data
        )

    async def publish_completion_message(
        self, 
        session_id: str, 
        completion_data: Dict[str, Any]
    ) -> bool:
        """
        完了メッセージを配信
        
        Args:
            session_id: セッションID
            completion_data: 完了データ
            
        Returns:
            bool: 配信が成功したか
        """
        return await self.publish_session_message(
            session_id=session_id,
            message_type="completion",
            data=completion_data
        )

    def _get_timestamp(self) -> str:
        """現在のタイムスタンプを取得"""
        return datetime.utcnow().isoformat()

    async def cleanup(self) -> None:
        """リソースクリーンアップ"""
        if self.redis_client:
            await self.redis_client.cleanup() 
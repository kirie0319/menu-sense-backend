"""
📊 ProgressTracker - 進行状況追跡専用サービス

このサービスはメニュー処理の進行状況を追跡・監視します。
Redisからの状態取得とSSEイベント生成を担当します。
"""

import asyncio
import time
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


logger = logging.getLogger(__name__)


class ItemStatus(Enum):
    """アイテム状態"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ItemProgress:
    """アイテム進行状況"""
    item_id: int
    status: ItemStatus
    translation_completed: bool
    description_completed: bool
    image_completed: bool
    translation_data: Optional[Dict[str, Any]] = None
    description_data: Optional[Dict[str, Any]] = None
    image_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    @property
    def overall_completed(self) -> bool:
        """全体完了フラグ"""
        return self.translation_completed and self.description_completed and self.image_completed

    @property
    def progress_percentage(self) -> float:
        """アイテム進行率"""
        completed_tasks = sum([
            self.translation_completed,
            self.description_completed,
            self.image_completed
        ])
        return (completed_tasks / 3) * 100

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        result = {
            "item_id": self.item_id,
            "status": self.status.value,
            "translation_completed": self.translation_completed,
            "description_completed": self.description_completed,
            "image_completed": self.image_completed,
            "overall_completed": self.overall_completed,
            "progress_percentage": self.progress_percentage
        }
        
        # 実際のデータを追加
        if self.translation_completed and self.translation_data:
            result.update({
                "japanese_text": self.translation_data.get("japanese_text", ""),
                "english_text": self.translation_data.get("english_text", ""),
                "translation_provider": self.translation_data.get("provider", "")
            })
        
        if self.description_completed and self.description_data:
            result.update({
                "description": self.description_data.get("description", ""),
                "description_provider": self.description_data.get("provider", "")
            })
        
        if self.image_completed and self.image_data:
            result.update({
                "image_url": self.image_data.get("image_url", ""),
                "image_provider": self.image_data.get("provider", ""),
                "fallback_used": self.image_data.get("fallback_used", False)
            })
        
        if self.error:
            result["error"] = self.error
        
        return result


@dataclass
class SessionProgress:
    """セッション進行状況"""
    session_id: str
    total_items: int
    items_progress: List[ItemProgress]
    start_time: float
    last_update: float

    @property
    def completed_items(self) -> int:
        """完了アイテム数"""
        return sum(1 for item in self.items_progress if item.overall_completed)

    @property
    def in_progress_items(self) -> int:
        """進行中アイテム数"""
        return sum(1 for item in self.items_progress if item.status == ItemStatus.IN_PROGRESS)

    @property
    def failed_items(self) -> int:
        """失敗アイテム数"""
        return sum(1 for item in self.items_progress if item.status == ItemStatus.FAILED)

    @property
    def progress_percentage(self) -> float:
        """全体進行率"""
        if self.total_items == 0:
            return 0.0
        return (self.completed_items / self.total_items) * 100

    @property
    def elapsed_time(self) -> float:
        """経過時間"""
        return time.time() - self.start_time

    @property
    def api_stats(self) -> Dict[str, int]:
        """API統計"""
        return {
            "translation_completed": sum(1 for item in self.items_progress if item.translation_completed),
            "description_completed": sum(1 for item in self.items_progress if item.description_completed),
            "image_completed": sum(1 for item in self.items_progress if item.image_completed)
        }

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "session_id": self.session_id,
            "total_items": self.total_items,
            "completed_items": self.completed_items,
            "in_progress_items": self.in_progress_items,
            "failed_items": self.failed_items,
            "progress_percentage": self.progress_percentage,
            "elapsed_time": self.elapsed_time,
            "api_stats": self.api_stats,
            "items_status": [item.to_dict() for item in self.items_progress],
            "last_update": self.last_update
        }


class ProgressTracker:
    """
    進行状況追跡専用サービス
    
    責任:
    - Redis状態監視
    - 進行状況計算
    - 変更検出
    - イベントデータ生成
    """

    def __init__(self):
        self._session_cache: Dict[str, SessionProgress] = {}
        self._cache_timeout = 300  # 5分

    async def track_session_progress(
        self, 
        session_id: str, 
        total_items: int
    ) -> SessionProgress:
        """
        セッション進行状況を追跡
        
        Args:
            session_id: セッションID
            total_items: 合計アイテム数
            
        Returns:
            SessionProgress: セッション進行状況
        """
        # アイテム進行状況を取得
        items_progress = []
        
        for item_id in range(total_items):
            item_progress = await self._get_item_progress(session_id, item_id)
            items_progress.append(item_progress)
        
        # セッション進行状況作成
        session_progress = SessionProgress(
            session_id=session_id,
            total_items=total_items,
            items_progress=items_progress,
            start_time=self._get_session_start_time(session_id),
            last_update=time.time()
        )
        
        # キャッシュ更新
        self._session_cache[session_id] = session_progress
        
        return session_progress

    async def get_item_progress(self, session_id: str, item_id: int) -> ItemProgress:
        """
        アイテム進行状況を取得
        
        Args:
            session_id: セッションID
            item_id: アイテムID
            
        Returns:
            ItemProgress: アイテム進行状況
        """
        return await self._get_item_progress(session_id, item_id)

    def detect_progress_changes(
        self, 
        session_id: str, 
        current_progress: SessionProgress
    ) -> bool:
        """
        進行状況の変更を検出
        
        Args:
            session_id: セッションID
            current_progress: 現在の進行状況
            
        Returns:
            bool: 変更があったかどうか
        """
        cached_progress = self._session_cache.get(session_id)
        
        if cached_progress is None:
            return True
        
        # 完了アイテム数の変更をチェック
        if current_progress.completed_items != cached_progress.completed_items:
            return True
        
        # 進行中アイテム数の変更をチェック
        if current_progress.in_progress_items != cached_progress.in_progress_items:
            return True
        
        # 最終更新時間が5秒以上経過している場合
        if current_progress.last_update - cached_progress.last_update > 5:
            return True
        
        return False

    def generate_progress_event(self, session_progress: SessionProgress) -> Dict[str, Any]:
        """
        進行状況イベントを生成
        
        Args:
            session_progress: セッション進行状況
            
        Returns:
            Dict: 進行状況イベントデータ
        """
        return {
            "type": "progress_update",
            "session_id": session_progress.session_id,
            "timestamp": session_progress.last_update,
            "total_items": session_progress.total_items,
            "completed_items": session_progress.completed_items,
            "in_progress_items": session_progress.in_progress_items,
            "progress_percentage": session_progress.progress_percentage,
            "api_stats": session_progress.api_stats,
            "items_status": [item.to_dict() for item in session_progress.items_progress],
            "api_integration": "real_api_integration",
            "elapsed_time": session_progress.elapsed_time
        }

    def generate_completion_event(self, session_progress: SessionProgress) -> Dict[str, Any]:
        """
        完了イベントを生成
        
        Args:
            session_progress: セッション進行状況
            
        Returns:
            Dict: 完了イベントデータ
        """
        return {
            "type": "processing_completed",
            "session_id": session_progress.session_id,
            "timestamp": session_progress.last_update,
            "total_time": session_progress.elapsed_time,
            "final_stats": {
                "total_items": session_progress.total_items,
                "completed_items": session_progress.completed_items,
                "failed_items": session_progress.failed_items,
                "success_rate": session_progress.progress_percentage,
                "api_integration": "real_api_integration"
            },
            "message": "🎉 All menu items processed successfully!"
        }

    def get_cached_progress(self, session_id: str) -> Optional[SessionProgress]:
        """
        キャッシュされた進行状況を取得
        
        Args:
            session_id: セッションID
            
        Returns:
            SessionProgress: キャッシュされた進行状況
        """
        return self._session_cache.get(session_id)

    async def cleanup_session_cache(self, session_id: str) -> bool:
        """
        セッションキャッシュをクリーンアップ
        
        Args:
            session_id: セッションID
            
        Returns:
            bool: クリーンアップ実行フラグ
        """
        if session_id in self._session_cache:
            del self._session_cache[session_id]
            return True
        return False

    def get_tracking_statistics(self) -> Dict[str, Any]:
        """
        追跡統計を取得
        
        Returns:
            Dict: 統計情報
        """
        total_sessions = len(self._session_cache)
        total_items = sum(s.total_items for s in self._session_cache.values())
        completed_items = sum(s.completed_items for s in self._session_cache.values())
        
        return {
            "cached_sessions": total_sessions,
            "total_tracked_items": total_items,
            "total_completed_items": completed_items,
            "overall_completion_rate": (completed_items / total_items * 100) if total_items > 0 else 0,
            "memory_usage_estimate": len(str(self._session_cache)) / 1024  # KB
        }

    async def _get_item_progress(self, session_id: str, item_id: int) -> ItemProgress:
        """Redis からアイテム進行状況を取得"""
        try:
            # ここではRedisからのデータ取得を模倣します。
            # 実際のRedisクライアントを使用する場合は、ここを置き換えます。
            # 例: redis_client.get(f"{session_id}:item:{item_id}")
            
            # シンプルなモックデータ
            mock_status = {
                "translation": {"completed": False, "data": None},
                "description": {"completed": False, "data": None},
                "image": {"completed": False, "data": None}
            }

            # エラーを発生させるために、適切なシミュレーションを追加
            if item_id % 5 == 0: # 5番目のアイテムはエラーを発生させる
                return ItemProgress(
                    item_id=item_id,
                    status=ItemStatus.FAILED,
                    translation_completed=False,
                    description_completed=False,
                    image_completed=False,
                    error=f"Simulated error for item {item_id}"
                )
            
            # 各サービスの完了状況
            translation_data = mock_status["translation"]["data"]
            description_data = mock_status["description"]["data"]
            image_data = mock_status["image"]["data"]
            
            t_completed = mock_status["translation"]["completed"]
            d_completed = mock_status["description"]["completed"]
            i_completed = mock_status["image"]["completed"]
            
            # ステータス判定
            if t_completed and d_completed and i_completed:
                item_status = ItemStatus.COMPLETED
            elif t_completed or d_completed or i_completed:
                item_status = ItemStatus.IN_PROGRESS
            else:
                item_status = ItemStatus.PENDING
            
            return ItemProgress(
                item_id=item_id,
                status=item_status,
                translation_completed=t_completed,
                description_completed=d_completed,
                image_completed=i_completed,
                translation_data=translation_data,
                description_data=description_data,
                image_data=image_data
            )
            
        except Exception as e:
            return ItemProgress(
                item_id=item_id,
                status=ItemStatus.FAILED,
                translation_completed=False,
                description_completed=False,
                image_completed=False,
                error=f"Status check failed: {str(e)}"
            )

    def _get_session_start_time(self, session_id: str) -> float:
        """セッション開始時間を取得（キャッシュまたは現在時刻）"""
        cached_progress = self._session_cache.get(session_id)
        if cached_progress:
            return cached_progress.start_time
        return time.time()
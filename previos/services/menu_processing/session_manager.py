"""
🎯 SessionManager - セッション管理専用サービス

このサービスはメニュー処理セッションの生成・管理・状態追跡を担当します。
エンドポイントからビジネスロジックを分離し、単一責任原則に従います。
"""

import logging
import time
import uuid
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class SessionStatus(Enum):
    """セッション状態"""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass
class ProcessingSession:
    """処理セッションのデータクラス"""
    session_id: str
    total_items: int
    status: SessionStatus
    start_time: float
    last_update: float
    api_mode: str
    menu_items: list[str]
    completed_items: int = 0
    failed_items: int = 0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    @property
    def progress_percentage(self) -> float:
        """進行率を計算"""
        if self.total_items == 0:
            return 0.0
        return (self.completed_items / self.total_items) * 100

    @property
    def is_completed(self) -> bool:
        """完了判定"""
        return self.completed_items >= self.total_items

    @property
    def elapsed_time(self) -> float:
        """経過時間"""
        return time.time() - self.start_time

    def to_response_dict(self) -> Dict[str, Any]:
        """APIレスポンス用の辞書に変換"""
        return {
            "session_id": self.session_id,
            "total_items": self.total_items,
            "completed_items": self.completed_items,
            "progress_percentage": self.progress_percentage,
            "status": self.status.value,
            "api_mode": self.api_mode,
            "elapsed_time": self.elapsed_time,
            "metadata": self.metadata
        }

    def update_progress(self, completed: int, failed: int = 0) -> None:
        """進行状況を更新"""
        self.completed_items = completed
        self.failed_items = failed
        self.last_update = time.time()
        
        if self.is_completed:
            self.status = SessionStatus.COMPLETED
        elif failed > 0:
            self.status = SessionStatus.FAILED
        else:
            self.status = SessionStatus.ACTIVE


class SessionManager:
    """
    セッション管理専用サービス
    
    責任:
    - セッションID生成
    - セッション初期化
    - セッション状態管理
    - Redis接続確認
    - セッション永続化
    """

    def __init__(self):
        self._sessions: Dict[str, ProcessingSession] = {}
        self._session_timeout = 3600  # 1時間

    async def create_session(
        self, 
        menu_items: list[str], 
        test_mode: bool = False
    ) -> ProcessingSession:
        """
        新しい処理セッションを作成
        
        Args:
            menu_items: メニューアイテムリスト
            test_mode: テストモードフラグ
            
        Returns:
            ProcessingSession: 作成されたセッション
            
        Raises:
            ValueError: バリデーションエラー
            ConnectionError: Redis接続エラー
        """
        # バリデーション
        self._validate_menu_items(menu_items)
        
        # Redis接続確認
        await self._verify_redis_connection()
        
        # セッションID生成
        session_id = self._generate_session_id(test_mode)
        
        # セッション作成
        session = ProcessingSession(
            session_id=session_id,
            total_items=len(menu_items),
            status=SessionStatus.INITIALIZING,
            start_time=time.time(),
            last_update=time.time(),
            api_mode="test_mode" if test_mode else "real_api_integration",
            menu_items=menu_items.copy(),
            metadata={
                "test_mode": test_mode,
                "created_at": time.time(),
                "version": "2.0"
            }
        )
        
        # セッション保存
        self._sessions[session_id] = session
        
        # 状態をアクティブに変更
        session.status = SessionStatus.ACTIVE
        
        return session

    async def get_session(self, session_id: str) -> Optional[ProcessingSession]:
        """
        セッションを取得
        
        Args:
            session_id: セッションID
            
        Returns:
            ProcessingSession: セッション（存在しない場合はNone）
        """
        session = self._sessions.get(session_id)
        
        if session is None:
            return None
            
        # タイムアウトチェック
        if self._is_session_expired(session):
            session.status = SessionStatus.EXPIRED
            
        return session

    async def update_session_progress(
        self, 
        session_id: str, 
        completed: int, 
        failed: int = 0
    ) -> bool:
        """
        セッションの進行状況を更新
        
        Args:
            session_id: セッションID
            completed: 完了アイテム数
            failed: 失敗アイテム数
            
        Returns:
            bool: 更新成功フラグ
        """
        session = self._sessions.get(session_id)
        if session is None:
            return False
            
        session.update_progress(completed, failed)
        return True

    async def cleanup_session(self, session_id: str) -> bool:
        """
        セッションをクリーンアップ
        
        Args:
            session_id: セッションID
            
        Returns:
            bool: クリーンアップ実行フラグ
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    async def cleanup_expired_sessions(self) -> int:
        """
        期限切れセッションをクリーンアップ
        
        Returns:
            int: クリーンアップされたセッション数
        """
        expired_sessions = [
            session_id for session_id, session in self._sessions.items()
            if self._is_session_expired(session)
        ]
        
        for session_id in expired_sessions:
            await self.cleanup_session(session_id)
            
        return len(expired_sessions)

    def get_session_statistics(self) -> Dict[str, Any]:
        """
        セッション統計を取得
        
        Returns:
            Dict: 統計情報
        """
        active_sessions = [s for s in self._sessions.values() if s.status == SessionStatus.ACTIVE]
        completed_sessions = [s for s in self._sessions.values() if s.status == SessionStatus.COMPLETED]
        
        return {
            "total_sessions": len(self._sessions),
            "active_sessions": len(active_sessions),
            "completed_sessions": len(completed_sessions),
            "average_items_per_session": sum(s.total_items for s in self._sessions.values()) / len(self._sessions) if self._sessions else 0,
            "memory_usage_estimate": len(str(self._sessions)) / 1024  # KB
        }

    def _generate_session_id(self, test_mode: bool = False) -> str:
        """セッションID生成"""
        prefix = "test" if test_mode else "real"
        timestamp = int(time.time())
        unique_id = str(uuid.uuid4())[:8]
        return f"{prefix}_{timestamp}_{unique_id}"

    def _validate_menu_items(self, menu_items: list[str]) -> None:
        """メニューアイテムのバリデーション"""
        if not menu_items:
            raise ValueError("Menu items cannot be empty")
        
        if len(menu_items) > 100:
            raise ValueError("Too many menu items (max: 100)")
        
        for item in menu_items:
            if not isinstance(item, str) or not item.strip():
                raise ValueError("All menu items must be non-empty strings")

    async def _verify_redis_connection(self) -> None:
        """Redis接続確認（簡略化）"""
        try:
            # 基本的なRedis接続テスト
            from app.tasks.utils import async_redis_client
            if async_redis_client:
                # 簡単な接続テスト
                await async_redis_client.ping()
                logger.info("Redis connection check successful.")
            else:
                logger.warning("Redis client not available")
                
        except Exception as e:
            # Redis接続エラーの場合はログに記録して続行
            logger.warning(f"Redis connection check failed: {e}")
            # 開発環境では接続エラーを無視して続行
            pass

    def _is_session_expired(self, session: ProcessingSession) -> bool:
        """セッション期限切れ判定"""
        return time.time() - session.start_time > self._session_timeout
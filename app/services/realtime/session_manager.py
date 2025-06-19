"""
リアルタイム通信のセッション管理サービス
"""
import asyncio
from typing import Dict, List, Any, Optional
from .types import (
    SessionId, ProgressStore, PingPongSessions, 
    ProgressData, PingData, PingPongSession,
    ProgressStatus
)

class SessionManager:
    """セッション状態を管理するシングルトンクラス"""
    
    _instance: Optional['SessionManager'] = None
    
    def __new__(cls) -> 'SessionManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        # 進行状況ストレージ
        self.progress_store: ProgressStore = {}
        
        # Ping/Pongセッション管理
        self.ping_pong_sessions: PingPongSessions = {}
        
        # Ping/Pongスケジュール管理
        self._ping_scheduled: Dict[SessionId, bool] = {}
        
        self._initialized = True
    
    def create_session(self, session_id: SessionId) -> None:
        """新しいセッションを作成"""
        if session_id not in self.progress_store:
            self.progress_store[session_id] = []
            print(f"📂 Session created: {session_id}")
    
    def delete_session(self, session_id: SessionId) -> None:
        """セッションを削除"""
        if session_id in self.progress_store:
            del self.progress_store[session_id]
            print(f"🗑️ Progress store cleaned for session: {session_id}")
        
        if session_id in self.ping_pong_sessions:
            self.ping_pong_sessions[session_id].active = False
            del self.ping_pong_sessions[session_id]
            print(f"🏓 Ping/Pong session cleaned for: {session_id}")
        
        if session_id in self._ping_scheduled:
            del self._ping_scheduled[session_id]
    
    def add_progress(self, session_id: SessionId, progress_data: Dict[str, Any]) -> None:
        """進行状況データを追加"""
        if session_id not in self.progress_store:
            self.create_session(session_id)
        
        self.progress_store[session_id].append(progress_data)
    
    def get_progress(self, session_id: SessionId) -> List[Dict[str, Any]]:
        """進行状況データを取得"""
        return self.progress_store.get(session_id, [])
    
    def pop_progress(self, session_id: SessionId) -> Optional[Dict[str, Any]]:
        """進行状況データを取得して削除"""
        if session_id in self.progress_store and self.progress_store[session_id]:
            return self.progress_store[session_id].pop(0)
        return None
    
    def has_progress(self, session_id: SessionId) -> bool:
        """進行状況データが存在するかチェック"""
        return session_id in self.progress_store and len(self.progress_store[session_id]) > 0
    
    def session_exists(self, session_id: SessionId) -> bool:
        """セッションが存在するかチェック"""
        return session_id in self.progress_store
    
    # Ping/Pong関連メソッド
    def create_ping_pong_session(self, session_id: SessionId) -> None:
        """Ping/Pongセッションを作成"""
        self.ping_pong_sessions[session_id] = PingPongSession()
        print(f"🏓 Ping/Pong session created for: {session_id}")
    
    def update_last_pong(self, session_id: SessionId) -> bool:
        """最後のPong受信時刻を更新"""
        if session_id in self.ping_pong_sessions:
            self.ping_pong_sessions[session_id].last_pong = asyncio.get_event_loop().time()
            return True
        return False
    
    def increment_ping_count(self, session_id: SessionId) -> None:
        """Ping送信回数を増やす"""
        if session_id in self.ping_pong_sessions:
            self.ping_pong_sessions[session_id].ping_count += 1
    
    def get_ping_pong_session(self, session_id: SessionId) -> Optional[PingPongSession]:
        """Ping/Pongセッション情報を取得"""
        return self.ping_pong_sessions.get(session_id)
    
    def is_ping_pong_active(self, session_id: SessionId) -> bool:
        """Ping/Pongが有効かチェック"""
        session = self.ping_pong_sessions.get(session_id)
        return session is not None and session.active
    
    def deactivate_ping_pong(self, session_id: SessionId) -> None:
        """Ping/Pongを無効化"""
        if session_id in self.ping_pong_sessions:
            self.ping_pong_sessions[session_id].active = False
    
    # Ping/Pongスケジュール管理
    def is_ping_scheduled(self, session_id: SessionId) -> bool:
        """Pingがスケジュールされているかチェック"""
        return self._ping_scheduled.get(session_id, False)
    
    def set_ping_scheduled(self, session_id: SessionId, scheduled: bool = True) -> None:
        """Pingスケジュール状態を設定"""
        self._ping_scheduled[session_id] = scheduled
    
    # 統計情報
    def get_stats(self) -> Dict[str, Any]:
        """セッション統計情報を取得"""
        return {
            "total_sessions": len(self.progress_store),
            "active_ping_pong_sessions": len([s for s in self.ping_pong_sessions.values() if s.active]),
            "total_ping_pong_sessions": len(self.ping_pong_sessions),
            "sessions_with_data": len([s for s in self.progress_store.values() if len(s) > 0])
        }

# シングルトンインスタンスを取得する関数
def get_session_manager() -> SessionManager:
    """SessionManagerのシングルトンインスタンスを取得"""
    return SessionManager() 
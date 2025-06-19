"""
リアルタイム通信サービスの型定義
"""
from typing import Dict, List, Any, Optional
from enum import Enum
import time

class ProgressStatus(Enum):
    """進行状況のステータス"""
    ACTIVE = "active"
    COMPLETED = "completed"
    ERROR = "error"
    WARNING = "warning"

class ProgressData:
    """進行状況データのクラス"""
    def __init__(
        self, 
        stage: int, 
        status: ProgressStatus, 
        message: str, 
        data: Optional[Dict[str, Any]] = None
    ):
        self.stage = stage
        self.status = status
        self.message = message
        self.timestamp = time.time()
        self.data = data or {}

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        result = {
            "stage": self.stage,
            "status": self.status.value,
            "message": self.message,
            "timestamp": self.timestamp
        }
        result.update(self.data)
        return result

class PingData:
    """Pingデータのクラス"""
    def __init__(self, session_id: str):
        self.type = "ping"
        self.timestamp = time.time()
        self.session_id = session_id

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "type": self.type,
            "timestamp": self.timestamp,
            "session_id": self.session_id
        }

class PingPongSession:
    """Ping/Pongセッション情報"""
    def __init__(self):
        self.last_pong = time.time()
        self.ping_count = 0
        self.active = True

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "last_pong": self.last_pong,
            "ping_count": self.ping_count,
            "active": self.active
        }

# 型エイリアス
SessionId = str
ProgressStore = Dict[SessionId, List[Dict[str, Any]]]
PingPongSessions = Dict[SessionId, PingPongSession] 
"""
Session Entity - Domain Layer
Business entity definition for processing session management (MVP Simplified)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum


class SessionStatus(Enum):
    """セッション処理状況の列挙型"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SessionEntity:
    """
    セッションエンティティ（MVP版）
    
    メニュー画像処理の1つのセッション（パイプライン実行）を表現
    外部依存なし、純粋なビジネスロジック
    """
    session_id: str
    status: SessionStatus
    menu_ids: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """初期化後の処理"""
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()
    
    def is_processing(self) -> bool:
        """処理中かどうか判定"""
        return self.status == SessionStatus.PROCESSING
    
    def is_completed(self) -> bool:
        """処理完了かどうか判定"""
        return self.status == SessionStatus.COMPLETED
    
    def is_failed(self) -> bool:
        """処理失敗かどうか判定"""
        return self.status == SessionStatus.FAILED
    
    def update_status(self, status: SessionStatus) -> None:
        """
        セッション全体のステータスを更新
        
        Args:
            status: 新しいステータス
        """
        self.status = status
        self.updated_at = datetime.utcnow()
    
    def add_menu_id(self, menu_id: str) -> None:
        """メニューIDを追加"""
        if menu_id not in self.menu_ids:
            self.menu_ids.append(menu_id)
            self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict:
        """辞書形式に変換（外部出力用）"""
        return {
            "session_id": self.session_id,
            "status": self.status.value,
            "menu_ids": self.menu_ids,
            "menu_count": len(self.menu_ids),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        } 
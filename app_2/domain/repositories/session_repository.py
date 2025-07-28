"""
Session Repository Interface - Domain Layer
Abstract interface for session data access (MVP Simplified)
"""

from abc import ABC, abstractmethod
from typing import Optional

from app_2.domain.entities.session_entity import SessionEntity


class SessionRepositoryInterface(ABC):
    """
    セッションリポジトリ抽象インターフェース（MVP版）
    
    ドメイン層での抽象化、実装詳細は隠蔽
    """
    
    @abstractmethod
    async def save(self, session: SessionEntity) -> SessionEntity:
        """
        セッションを保存
        
        Args:
            session: 保存するセッションエンティティ
            
        Returns:
            SessionEntity: 保存されたセッションエンティティ
        """
        pass
    
    @abstractmethod
    async def upsert_session(self, session: SessionEntity) -> SessionEntity:
        """
        セッションを作成または更新（UPSERT）
        
        Args:
            session: 作成/更新するセッションエンティティ
            
        Returns:
            SessionEntity: 作成/更新されたセッションエンティティ
        """
        pass
    
    @abstractmethod
    async def get_by_id(self, session_id: str) -> Optional[SessionEntity]:
        """
        IDでセッションを取得
        
        Args:
            session_id: セッションID
            
        Returns:
            Optional[SessionEntity]: 見つかったセッションエンティティ
        """
        pass
    
    @abstractmethod
    async def update(self, session: SessionEntity) -> SessionEntity:
        """
        セッションを更新
        
        Args:
            session: 更新するセッションエンティティ
            
        Returns:
            SessionEntity: 更新されたセッションエンティティ
        """
        pass
    
    @abstractmethod
    async def delete_by_id(self, session_id: str) -> bool:
        """
        IDでセッションを削除
        
        Args:
            session_id: セッションID
            
        Returns:
            bool: 削除が成功したかどうか
        """
        pass 
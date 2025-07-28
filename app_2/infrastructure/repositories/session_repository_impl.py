"""
Session Repository Implementation - Infrastructure Layer
Concrete implementation of session repository using SQLAlchemy (MVP Simplified)
"""

from typing import Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app_2.domain.entities.session_entity import SessionEntity
from app_2.domain.repositories.session_repository import SessionRepositoryInterface
from app_2.infrastructure.models.session_model import SessionModel
from app_2.utils.logger import get_logger

logger = get_logger("session_repository")


class SessionRepositoryImpl(SessionRepositoryInterface):
    """
    セッションリポジトリ実装（MVP版）
    
    最小限のCRUD操作を実装
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def save(self, session_entity: SessionEntity) -> SessionEntity:
        """
        セッションを保存（新規作成用）
        
        Args:
            session_entity: 保存するセッションエンティティ
            
        Returns:
            SessionEntity: 保存されたセッションエンティティ
        """
        try:
            session_model = SessionModel.from_entity(session_entity)
            
            self.session.add(session_model)
            await self.session.commit()
            await self.session.refresh(session_model)
            
            logger.info(f"Session saved: {session_entity.session_id}")
            return session_model.to_entity()
            
        except IntegrityError as e:
            await self.session.rollback()
            logger.warning(f"Session already exists: {session_entity.session_id}, attempting to update")
            # 重複エラーの場合は更新を試行
            existing_session = await self.get_by_id(session_entity.session_id)
            if existing_session:
                session_entity.created_at = existing_session.created_at  # 作成日時を保持
                return await self.update(session_entity)
            else:
                logger.error(f"Unexpected integrity error for session {session_entity.session_id}: {e}")
                raise
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to save session {session_entity.session_id}: {e}")
            raise

    async def upsert_session(self, session_entity: SessionEntity) -> SessionEntity:
        """
        セッションを作成または更新（UPSERT）
        
        Args:
            session_entity: 作成/更新するセッションエンティティ
            
        Returns:
            SessionEntity: 作成/更新されたセッションエンティティ
        """
        try:
            # 既存のセッションを確認
            existing_session = await self.get_by_id(session_entity.session_id)
            
            if existing_session:
                # 既存の場合は更新
                logger.info(f"Updating existing session: {session_entity.session_id}")
                session_entity.created_at = existing_session.created_at  # 作成日時を保持
                return await self.update(session_entity)
            else:
                # 新規の場合は作成
                logger.info(f"Creating new session: {session_entity.session_id}")
                return await self.save(session_entity)
                
        except Exception as e:
            logger.error(f"Failed to upsert session {session_entity.session_id}: {e}")
            raise
    
    async def get_by_id(self, session_id: str) -> Optional[SessionEntity]:
        """
        IDでセッションを取得
        
        Args:
            session_id: セッションID
            
        Returns:
            Optional[SessionEntity]: 見つかったセッションエンティティ
        """
        try:
            stmt = select(SessionModel).where(SessionModel.session_id == session_id)
            result = await self.session.execute(stmt)
            session_model = result.scalar_one_or_none()
            
            return session_model.to_entity() if session_model else None
            
        except Exception as e:
            logger.error(f"Failed to get session by ID {session_id}: {e}")
            raise
    
    async def update(self, session_entity: SessionEntity) -> SessionEntity:
        """
        セッションを更新
        
        Args:
            session_entity: 更新するセッションエンティティ
            
        Returns:
            SessionEntity: 更新されたセッションエンティティ
        """
        try:
            stmt = select(SessionModel).where(SessionModel.session_id == session_entity.session_id)
            result = await self.session.execute(stmt)
            session_model = result.scalar_one_or_none()
            
            if not session_model:
                raise ValueError(f"Session not found: {session_entity.session_id}")
            
            session_model.update_from_entity(session_entity)
            
            await self.session.commit()
            await self.session.refresh(session_model)
            
            logger.info(f"Session updated: {session_entity.session_id}")
            return session_model.to_entity()
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to update session {session_entity.session_id}: {e}")
            raise

    async def delete_by_id(self, session_id: str) -> bool:
        """
        IDでセッションを削除
        
        Args:
            session_id: セッションID
            
        Returns:
            bool: 削除が成功したかどうか
        """
        try:
            stmt = delete(SessionModel).where(SessionModel.session_id == session_id)
            result = await self.session.execute(stmt)
            await self.session.commit()
            
            deleted_rows = result.rowcount
            if deleted_rows > 0:
                logger.info(f"Session deleted: {session_id}")
                return True
            else:
                logger.warning(f"Session not found for deletion: {session_id}")
                return False
                
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to delete session {session_id}: {e}")
            raise
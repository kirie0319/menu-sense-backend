"""
Menu Translation Repository Implementation

This repository provides data access methods for menu translation operations.
It handles CRUD operations for sessions, menu items, providers, and images.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from app.models.menu_translation import Session, MenuItem, ProcessingProvider, MenuItemImage
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime

@dataclass
class SessionProgress:
    """Data class for session progress information"""
    total_items: int
    translation_completed: int
    description_completed: int
    image_completed: int
    fully_completed: int
    progress_percentage: float

class MenuTranslationRepository:
    """Repository for menu translation database operations"""
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
    
    async def create_session(self, session_data: dict) -> Session:
        """
        Create new session
        
        Args:
            session_data: Dictionary containing session information
            
        Returns:
            Session: Created session object
        """
        session = Session(
            session_id=session_data["session_id"],
            total_items=session_data["total_items"],
            session_metadata=session_data.get("session_metadata", {})
        )
        self.db_session.add(session)
        await self.db_session.commit()
        await self.db_session.refresh(session)
        return session
    
    async def save_translation_result(self, session_id: str, data: dict) -> MenuItem:
        """
        Save translation result to database
        
        Args:
            session_id: Session identifier
            data: Translation data dictionary
            
        Returns:
            MenuItem: Created or updated menu item
        """
        # First, get the session
        session_result = await self.db_session.execute(
            select(Session).where(Session.session_id == session_id)
        )
        session = session_result.scalar_one()
        
        # Check if menu item already exists
        item_result = await self.db_session.execute(
            select(MenuItem).where(
                and_(
                    MenuItem.session_id == session.id,
                    MenuItem.item_id == data["item_id"]
                )
            )
        )
        menu_item = item_result.scalar_one_or_none()
        
        if menu_item is None:
            # Create new menu item
            menu_item = MenuItem(
                session_id=session.id,
                item_id=data["item_id"],
                japanese_text=data["japanese_text"],
                english_text=data.get("english_text"),
                category=data.get("category"),
                translation_status="completed"
            )
            self.db_session.add(menu_item)
        else:
            # Update existing menu item
            menu_item.english_text = data.get("english_text")
            menu_item.category = data.get("category")
            menu_item.translation_status = "completed"
        
        await self.db_session.flush()  # Get menu_item.id
        
        # Create processing provider record
        provider = ProcessingProvider(
            menu_item_id=menu_item.id,
            stage="translation",
            provider=data.get("provider", "Unknown"),
            processing_time_ms=data.get("processing_time_ms"),
            fallback_used=data.get("fallback_used", False),
            provider_metadata={"translation_data": data}
        )
        self.db_session.add(provider)
        
        await self.db_session.commit()
        await self.db_session.refresh(menu_item)
        
        # Load relationships for return
        await self.db_session.refresh(menu_item, ['providers'])
        
        return menu_item
    
    async def save_description_result(self, session_id: str, data: dict) -> MenuItem:
        """
        Save description result to database
        
        Args:
            session_id: Session identifier
            data: Description data dictionary
            
        Returns:
            MenuItem: Updated menu item
        """
        # Get the session and menu item
        session_result = await self.db_session.execute(
            select(Session).where(Session.session_id == session_id)
        )
        session = session_result.scalar_one()
        
        item_result = await self.db_session.execute(
            select(MenuItem).where(
                and_(
                    MenuItem.session_id == session.id,
                    MenuItem.item_id == data["item_id"]
                )
            )
        )
        menu_item = item_result.scalar_one()
        
        # Update description
        menu_item.description = data.get("description")
        menu_item.description_status = "completed"
        
        await self.db_session.flush()
        
        # Create processing provider record
        provider = ProcessingProvider(
            menu_item_id=menu_item.id,
            stage="description",
            provider=data.get("provider", "Unknown"),
            processing_time_ms=data.get("processing_time_ms"),
            fallback_used=data.get("fallback_used", False),
            provider_metadata={"description_data": data}
        )
        self.db_session.add(provider)
        
        await self.db_session.commit()
        await self.db_session.refresh(menu_item)
        
        # Load relationships for return
        await self.db_session.refresh(menu_item, ['providers'])
        
        return menu_item
    
    async def save_image_result(self, session_id: str, data: dict) -> MenuItem:
        """
        Save image result to database
        
        Args:
            session_id: Session identifier
            data: Image data dictionary
            
        Returns:
            MenuItem: Updated menu item with image
        """
        # Get the session and menu item
        session_result = await self.db_session.execute(
            select(Session).where(Session.session_id == session_id)
        )
        session = session_result.scalar_one()
        
        item_result = await self.db_session.execute(
            select(MenuItem).where(
                and_(
                    MenuItem.session_id == session.id,
                    MenuItem.item_id == data["item_id"]
                )
            )
        )
        menu_item = item_result.scalar_one()
        
        # Update image status
        menu_item.image_status = "completed"
        
        await self.db_session.flush()
        
        # Create menu item image record
        image = MenuItemImage(
            menu_item_id=menu_item.id,
            image_url=data.get("image_url"),
            s3_key=data.get("s3_key"),
            prompt=data.get("prompt"),
            provider=data.get("provider", "Unknown"),
            fallback_used=data.get("fallback_used", False),
            image_metadata={"image_data": data}
        )
        self.db_session.add(image)
        
        # Create processing provider record
        provider = ProcessingProvider(
            menu_item_id=menu_item.id,
            stage="image",
            provider=data.get("provider", "Unknown"),
            processing_time_ms=data.get("processing_time_ms"),
            fallback_used=data.get("fallback_used", False),
            provider_metadata={"image_data": data}
        )
        self.db_session.add(provider)
        
        await self.db_session.commit()
        await self.db_session.refresh(menu_item)
        
        # Load relationships for return
        await self.db_session.refresh(menu_item, ['providers', 'images'])
        
        return menu_item
    
    async def get_session_progress(self, session_id: str) -> SessionProgress:
        """
        Get session progress information
        
        Args:
            session_id: Session identifier
            
        Returns:
            SessionProgress: Progress information
        """
        # Get session
        session_result = await self.db_session.execute(
            select(Session).where(Session.session_id == session_id)
        )
        session = session_result.scalar_one()
        
        # Get all menu items for this session
        items_result = await self.db_session.execute(
            select(MenuItem).where(MenuItem.session_id == session.id)
        )
        menu_items = items_result.scalars().all()
        
        # Calculate progress
        total_items = len(menu_items)
        translation_completed = sum(1 for item in menu_items if item.translation_status == "completed")
        description_completed = sum(1 for item in menu_items if item.description_status == "completed")
        image_completed = sum(1 for item in menu_items if item.image_status == "completed")
        
        fully_completed = sum(1 for item in menu_items if all([
            item.translation_status == "completed",
            item.description_status == "completed", 
            item.image_status == "completed"
        ]))
        
        progress_percentage = (fully_completed / total_items * 100) if total_items > 0 else 0
        
        return SessionProgress(
            total_items=total_items,
            translation_completed=translation_completed,
            description_completed=description_completed,
            image_completed=image_completed,
            fully_completed=fully_completed,
            progress_percentage=progress_percentage
        )
    
    async def get_session_by_id(self, session_id: str) -> Optional[Session]:
        """
        Get session by ID with all related data
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session: Session object with relationships loaded
        """
        result = await self.db_session.execute(
            select(Session)
            .options(selectinload(Session.menu_items).selectinload(MenuItem.providers))
            .options(selectinload(Session.menu_items).selectinload(MenuItem.images))
            .where(Session.session_id == session_id)
        )
        return result.scalar_one_or_none()
    
    async def get_menu_item_by_id(self, session_id: str, item_id: int) -> Optional[MenuItem]:
        """
        Get menu item by session and item ID
        
        Args:
            session_id: Session identifier
            item_id: Item identifier within session
            
        Returns:
            MenuItem: Menu item with relationships loaded
        """
        # First get session
        session_result = await self.db_session.execute(
            select(Session).where(Session.session_id == session_id)
        )
        session = session_result.scalar_one_or_none()
        
        if session is None:
            return None
        
        # Get menu item
        result = await self.db_session.execute(
            select(MenuItem)
            .options(selectinload(MenuItem.providers))
            .options(selectinload(MenuItem.images))
            .where(
                and_(
                    MenuItem.session_id == session.id,
                    MenuItem.item_id == item_id
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def search_menu_items(self, query: str, category: Optional[str] = None, limit: int = 100) -> List[MenuItem]:
        """
        Search menu items by text query
        
        Args:
            query: Search query
            category: Optional category filter
            limit: Maximum number of results
            
        Returns:
            List[MenuItem]: Matching menu items
        """
        # Build query
        stmt = select(MenuItem).options(selectinload(MenuItem.providers))
        
        # Add text search (simple LIKE for now, can be enhanced with full-text search)
        if query:
            search_filter = (
                MenuItem.japanese_text.ilike(f"%{query}%") |
                MenuItem.english_text.ilike(f"%{query}%") |
                MenuItem.description.ilike(f"%{query}%")
            )
            stmt = stmt.where(search_filter)
        
        # Add category filter
        if category:
            stmt = stmt.where(MenuItem.category == category)
        
        # Add limit
        stmt = stmt.limit(limit)
        
        result = await self.db_session.execute(stmt)
        return result.scalars().all()
    
    async def update_session_status(self, session_id: str, status: str) -> Session:
        """
        Update session status
        
        Args:
            session_id: Session identifier
            status: New status value
            
        Returns:
            Session: Updated session
        """
        result = await self.db_session.execute(
            select(Session).where(Session.session_id == session_id)
        )
        session = result.scalar_one()
        
        session.status = status
        session.updated_at = datetime.utcnow()
        
        if status == "completed":
            session.completed_at = datetime.utcnow()
        
        await self.db_session.commit()
        await self.db_session.refresh(session)
        
        return session
    
    async def complete_session(self, session_id: str) -> Session:
        """
        Mark session as completed
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session: Updated session
        """
        return await self.update_session_status(session_id, "completed")
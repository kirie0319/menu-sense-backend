"""
Menu Translation Service Layer

This service integrates the repository layer with the existing Celery-based system.
It provides dual storage (Redis + Database) and manages the translation workflow.
"""
from typing import Optional, Dict, Any, List
from app.repositories.menu_translation_repository import MenuTranslationRepository, SessionProgress
from app.models.menu_translation import Session, MenuItem
import json
import time

class MenuTranslationService:
    """Service layer for menu translation operations"""
    
    def __init__(self, repository: MenuTranslationRepository, redis_client=None):
        self.repository = repository
        self.redis_client = redis_client
    
    async def start_translation_session(self, session_id: str, menu_items: List[str], metadata: Optional[Dict] = None) -> Session:
        """
        Start a new translation session
        
        Args:
            session_id: Unique session identifier
            menu_items: List of Japanese menu item texts
            metadata: Optional session metadata
            
        Returns:
            Session: Created session object
        """
        session_data = {
            "session_id": session_id,
            "total_items": len(menu_items),
            "session_metadata": {
                "menu_items": menu_items,
                "start_time": time.time(),
                **(metadata or {})
            }
        }
        
        return await self.repository.create_session(session_data)
    
    async def process_translation_result(self, celery_result: Dict[str, Any]) -> MenuItem:
        """
        Process translation result from Celery task and save to database
        
        Args:
            celery_result: Result from Celery translation task
            
        Returns:
            MenuItem: Created/updated menu item
        """
        translation_data = {
            "item_id": celery_result["item_id"],
            "japanese_text": celery_result["japanese_text"],
            "english_text": celery_result["english_text"],
            "category": celery_result.get("category", "Other"),
            "provider": celery_result.get("provider", "Unknown"),
            "processing_time_ms": int(celery_result.get("processing_time", 0) * 1000),
            "fallback_used": celery_result.get("fallback_used", False)
        }
        
        # Save to database
        menu_item = await self.repository.save_translation_result(
            celery_result["session_id"],
            translation_data
        )
        
        # Also save to Redis for backward compatibility (if Redis client available)
        if self.redis_client:
            await self._save_to_redis(celery_result["session_id"], celery_result["item_id"], "translation", translation_data)
        
        return menu_item
    
    async def process_description_result(self, celery_result: Dict[str, Any]) -> MenuItem:
        """
        Process description result from Celery task and save to database
        
        Args:
            celery_result: Result from Celery description task
            
        Returns:
            MenuItem: Updated menu item
        """
        description_data = {
            "item_id": celery_result["item_id"],
            "description": celery_result["description"],
            "provider": celery_result.get("provider", "Unknown"),
            "processing_time_ms": int(celery_result.get("processing_time", 0) * 1000),
            "fallback_used": celery_result.get("fallback_used", False)
        }
        
        # Save to database
        menu_item = await self.repository.save_description_result(
            celery_result["session_id"],
            description_data
        )
        
        # Also save to Redis for backward compatibility
        if self.redis_client:
            await self._save_to_redis(celery_result["session_id"], celery_result["item_id"], "description", description_data)
        
        return menu_item
    
    async def process_image_result(self, celery_result: Dict[str, Any]) -> MenuItem:
        """
        Process image result from Celery task and save to database
        
        Args:
            celery_result: Result from Celery image task
            
        Returns:
            MenuItem: Updated menu item with image
        """
        image_data = {
            "item_id": celery_result["item_id"],
            "image_url": celery_result["image_url"],
            "s3_key": celery_result.get("s3_key"),
            "prompt": celery_result.get("prompt"),
            "provider": celery_result.get("provider", "Unknown"),
            "processing_time_ms": int(celery_result.get("processing_time", 0) * 1000),
            "fallback_used": celery_result.get("fallback_used", False)
        }
        
        # Save to database
        menu_item = await self.repository.save_image_result(
            celery_result["session_id"],
            image_data
        )
        
        # Also save to Redis for backward compatibility
        if self.redis_client:
            await self._save_to_redis(celery_result["session_id"], celery_result["item_id"], "image", image_data)
        
        return menu_item
    
    async def get_real_time_progress(self, session_id: str) -> SessionProgress:
        """
        Get real-time session progress from database
        
        Args:
            session_id: Session identifier
            
        Returns:
            SessionProgress: Current progress information
        """
        return await self.repository.get_session_progress(session_id)
    
    async def get_session_with_items(self, session_id: str) -> Optional[Session]:
        """
        Get complete session with all menu items and related data
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session: Complete session data or None if not found
        """
        return await self.repository.get_session_by_id(session_id)
    
    async def search_menu_items(self, query: str, category: Optional[str] = None, limit: int = 100) -> List[MenuItem]:
        """
        Search menu items across all sessions
        
        Args:
            query: Search query text
            category: Optional category filter
            limit: Maximum number of results
            
        Returns:
            List[MenuItem]: Matching menu items
        """
        return await self.repository.search_menu_items(query, category, limit)
    
    async def complete_session(self, session_id: str) -> Session:
        """
        Mark session as completed
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session: Updated session
        """
        return await self.repository.update_session_status(session_id, "completed")
    
    async def _save_to_redis(self, session_id: str, item_id: int, stage: str, data: Dict[str, Any]):
        """
        Save data to Redis for backward compatibility
        
        Args:
            session_id: Session identifier
            item_id: Item identifier
            stage: Processing stage (translation, description, image)
            data: Data to save
        """
        if not self.redis_client:
            return
        
        redis_key = f"{session_id}:item{item_id}:{stage}"
        
        # Add timestamp and test_mode flag for compatibility
        redis_data = {
            **data,
            "timestamp": time.time(),
            "test_mode": False
        }
        
        try:
            # Set with 1 hour TTL like the existing system
            self.redis_client.setex(redis_key, 3600, json.dumps(redis_data))
        except Exception as e:
            # Log error but don't fail the operation
            print(f"⚠️ Failed to save to Redis: {e}")
    
    async def migrate_from_redis(self, session_id: str, item_count: int) -> Optional[Session]:
        """
        Migrate existing Redis data to database
        
        Args:
            session_id: Session identifier
            item_count: Number of items in session
            
        Returns:
            Session: Migrated session or None if no Redis data found
        """
        if not self.redis_client:
            return None
        
        # Check if session already exists in database
        existing_session = await self.repository.get_session_by_id(session_id)
        if existing_session:
            return existing_session
        
        # Try to find Redis data
        redis_data_found = False
        
        for item_id in range(item_count):
            for stage in ["translation", "description", "image"]:
                redis_key = f"{session_id}:item{item_id}:{stage}"
                redis_data = self.redis_client.get(redis_key)
                
                if redis_data:
                    redis_data_found = True
                    break
            
            if redis_data_found:
                break
        
        if not redis_data_found:
            return None
        
        # Create session from Redis data
        session = await self.start_translation_session(
            session_id=session_id,
            menu_items=[f"Item {i}" for i in range(item_count)],  # Placeholder
            metadata={"migrated_from_redis": True}
        )
        
        # Migrate each item's data
        for item_id in range(item_count):
            # Migrate translation
            translation_key = f"{session_id}:item{item_id}:translation"
            translation_data = self.redis_client.get(translation_key)
            if translation_data:
                data = json.loads(translation_data)
                await self.repository.save_translation_result(session_id, {
                    "item_id": item_id,
                    "japanese_text": data.get("japanese_text", ""),
                    "english_text": data.get("english_text", ""),
                    "category": data.get("category", "Other"),
                    "provider": data.get("provider", "Unknown"),
                    "processing_time_ms": 0,
                    "fallback_used": False
                })
            
            # Migrate description
            description_key = f"{session_id}:item{item_id}:description"
            description_data = self.redis_client.get(description_key)
            if description_data:
                data = json.loads(description_data)
                await self.repository.save_description_result(session_id, {
                    "item_id": item_id,
                    "description": data.get("description", ""),
                    "provider": data.get("provider", "Unknown"),
                    "processing_time_ms": 0,
                    "fallback_used": False
                })
            
            # Migrate image
            image_key = f"{session_id}:item{item_id}:image"
            image_data = self.redis_client.get(image_key)
            if image_data:
                data = json.loads(image_data)
                await self.repository.save_image_result(session_id, {
                    "item_id": item_id,
                    "image_url": data.get("image_url", ""),
                    "s3_key": data.get("s3_key"),
                    "prompt": data.get("prompt"),
                    "provider": data.get("provider", "Unknown"),
                    "processing_time_ms": 0,
                    "fallback_used": data.get("fallback_used", False)
                })
        
        return session
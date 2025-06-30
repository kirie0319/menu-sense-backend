"""
Database Sync Worker

This worker monitors Redis for Celery task results and syncs them to the database.
It ensures that all menu translation data is persisted to the database.
"""
import asyncio
import json
import logging
import time
from typing import Dict, Any
import redis
from app.core.database import async_session_factory
from app.repositories.menu_translation_repository import MenuTranslationRepository
from app.services.menu_translation_service import MenuTranslationService
from app.core.config import settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Redis client
redis_client = redis.from_url(settings.REDIS_URL)


async def sync_redis_to_database():
    """Sync Redis data to database"""
    logger.info("🔄 Starting Redis to Database sync worker...")
    
    while True:
        try:
            # Get all Redis keys
            keys = redis_client.keys("*:item*:*")
            
            for key in keys:
                key_str = key.decode('utf-8')
                
                # Parse key format: session_id:itemX:stage
                parts = key_str.split(':')
                if len(parts) != 3:
                    continue
                
                session_id = parts[0]
                item_part = parts[1]
                stage = parts[2]
                
                # Extract item_id
                if not item_part.startswith('item'):
                    continue
                    
                try:
                    item_id = int(item_part[4:])
                except ValueError:
                    continue
                
                # Get data from Redis
                redis_data = redis_client.get(key)
                if not redis_data:
                    continue
                
                try:
                    data = json.loads(redis_data)
                except json.JSONDecodeError:
                    continue
                
                # Check if this is new data (not already synced)
                # We can use a marker key or timestamp to track synced data
                sync_key = f"synced:{key_str}"
                if redis_client.exists(sync_key):
                    continue
                
                # Sync to database
                async with async_session_factory() as db_session:
                    repository = MenuTranslationRepository(db_session)
                    service = MenuTranslationService(repository, redis_client)
                    
                    try:
                        # Check if session exists, create if not
                        session = await repository.get_session_by_id(session_id)
                        if not session:
                            # Create session with estimated item count
                            await service.start_translation_session(
                                session_id=session_id,
                                menu_items=[f"Item {i}" for i in range(item_id + 1)],
                                metadata={"source": "redis_sync"}
                            )
                        
                        # Process based on stage
                        if stage == "translation":
                            result = {
                                "session_id": session_id,
                                "item_id": item_id,
                                "japanese_text": data.get("japanese_text", ""),
                                "english_text": data.get("english_text", ""),
                                "category": data.get("category", "Other"),
                                "provider": data.get("provider", "Unknown"),
                                "processing_time": data.get("processing_time", 0),
                                "fallback_used": data.get("fallback_used", False)
                            }
                            await service.process_translation_result(result)
                            logger.info(f"✅ Synced translation: {session_id}:item{item_id}")
                            
                        elif stage == "description":
                            result = {
                                "session_id": session_id,
                                "item_id": item_id,
                                "description": data.get("description", ""),
                                "provider": data.get("provider", "Unknown"),
                                "processing_time": data.get("processing_time", 0),
                                "fallback_used": data.get("fallback_used", False)
                            }
                            await service.process_description_result(result)
                            logger.info(f"✅ Synced description: {session_id}:item{item_id}")
                            
                        elif stage == "image":
                            result = {
                                "session_id": session_id,
                                "item_id": item_id,
                                "image_url": data.get("image_url", ""),
                                "s3_key": data.get("s3_key"),
                                "prompt": data.get("prompt"),
                                "provider": data.get("provider", "Unknown"),
                                "processing_time": data.get("processing_time", 0),
                                "fallback_used": data.get("fallback_used", False)
                            }
                            await service.process_image_result(result)
                            logger.info(f"✅ Synced image: {session_id}:item{item_id}")
                        
                        # Mark as synced
                        redis_client.setex(sync_key, 86400, "1")  # 24 hour TTL
                        
                    except Exception as e:
                        logger.error(f"❌ Failed to sync {key_str}: {e}")
                        await db_session.rollback()
                        
        except Exception as e:
            logger.error(f"❌ Sync worker error: {e}")
        
        # Wait before next sync cycle
        await asyncio.sleep(5)  # Check every 5 seconds


async def main():
    """Main entry point"""
    try:
        await sync_redis_to_database()
    except KeyboardInterrupt:
        logger.info("🛑 Sync worker stopped")


if __name__ == "__main__":
    asyncio.run(main()) 
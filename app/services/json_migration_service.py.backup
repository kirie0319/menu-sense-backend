"""
JSON to Database Migration Service

Migrates existing JSON translation files to the new database structure.
Handles the transformation from the current file-based system to database storage.
"""
import json
import os
import glob
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio
from pathlib import Path

from app.core.database import get_db_session
from app.repositories.menu_translation_repository import MenuTranslationRepository
from app.services.menu_translation_service import MenuTranslationService


class JSONMigrationService:
    """Service for migrating JSON translation files to database"""
    
    def __init__(self, repository: MenuTranslationRepository):
        self.repository = repository
        self.service = MenuTranslationService(repository)
    
    async def migrate_all_json_files(self, json_directory: str = "uploads/menu_translations") -> Dict[str, Any]:
        """
        Migrate all JSON files in the directory to database
        
        Args:
            json_directory: Path to directory containing JSON files
        
        Returns:
            Migration summary with statistics
        """
        print(f"🔄 Starting migration from {json_directory}...")
        
        # Find all JSON files
        json_files = self._find_json_files(json_directory)
        print(f"📁 Found {len(json_files)} JSON files to migrate")
        
        migration_summary = {
            "total_files": len(json_files),
            "migrated_sessions": 0,
            "migrated_items": 0,
            "failed_migrations": [],
            "skipped_sessions": [],
            "start_time": datetime.utcnow(),
            "end_time": None
        }
        
        # Migrate each file
        for json_file in json_files:
            try:
                print(f"📝 Processing {json_file}...")
                result = await self._migrate_single_file(json_file)
                
                if result["success"]:
                    migration_summary["migrated_sessions"] += 1
                    migration_summary["migrated_items"] += result["items_count"]
                    print(f"✅ Migrated session {result['session_id']} with {result['items_count']} items")
                else:
                    if result["reason"] == "already_exists":
                        migration_summary["skipped_sessions"].append({
                            "file": json_file,
                            "session_id": result["session_id"],
                            "reason": "Already exists in database"
                        })
                        print(f"⏭️ Skipped {result['session_id']} - already in database")
                    else:
                        migration_summary["failed_migrations"].append({
                            "file": json_file,
                            "error": result["error"]
                        })
                        print(f"❌ Failed to migrate {json_file}: {result['error']}")
                        
            except Exception as e:
                migration_summary["failed_migrations"].append({
                    "file": json_file,
                    "error": str(e)
                })
                print(f"❌ Unexpected error migrating {json_file}: {e}")
        
        migration_summary["end_time"] = datetime.utcnow()
        migration_summary["duration_seconds"] = (
            migration_summary["end_time"] - migration_summary["start_time"]
        ).total_seconds()
        
        print(f"\n🎉 Migration completed!")
        print(f"✅ Successfully migrated: {migration_summary['migrated_sessions']} sessions")
        print(f"📊 Total menu items: {migration_summary['migrated_items']}")
        print(f"⏭️ Skipped (already exist): {len(migration_summary['skipped_sessions'])}")
        print(f"❌ Failed: {len(migration_summary['failed_migrations'])}")
        print(f"⏱️ Duration: {migration_summary['duration_seconds']:.2f} seconds")
        
        return migration_summary
    
    def _find_json_files(self, directory: str) -> List[str]:
        """Find all JSON files in directory recursively"""
        json_pattern = os.path.join(directory, "**", "*.json")
        return glob.glob(json_pattern, recursive=True)
    
    async def _migrate_single_file(self, file_path: str) -> Dict[str, Any]:
        """
        Migrate a single JSON file to database
        
        Returns:
            Dictionary with migration result
        """
        try:
            # Load JSON data
            with open(file_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            session_id = json_data["session_id"]
            
            # Check if session already exists
            existing_session = await self.repository.get_session_by_id(session_id)
            if existing_session:
                return {
                    "success": False,
                    "reason": "already_exists",
                    "session_id": session_id
                }
            
            # Create session
            session_data = {
                "session_id": session_id,
                "total_items": json_data["total_items"],
                "session_metadata": {
                    "original_timestamp": json_data.get("timestamp"),
                    "last_updated": json_data.get("last_updated"),
                    "status": json_data.get("status", "completed"),
                    "migrated_from": file_path,
                    "migration_timestamp": datetime.utcnow().isoformat()
                }
            }
            
            session = await self.repository.create_session(session_data)
            
            # Migrate menu items
            migrated_items = 0
            for item_data in json_data["menu_items"]:
                await self._migrate_menu_item(session_id, item_data)
                migrated_items += 1
            
            # Update session status if it was completed
            if json_data.get("status") == "completed":
                await self.repository.complete_session(session_id)
            
            return {
                "success": True,
                "session_id": session_id,
                "items_count": migrated_items
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "session_id": json_data.get("session_id", "unknown") if 'json_data' in locals() else "unknown"
            }
    
    async def _migrate_menu_item(self, session_id: str, item_data: Dict[str, Any]):
        """Migrate a single menu item with all its stages"""
        
        # Determine statuses based on available data
        translation_status = "completed" if item_data.get("english_text") else "pending"
        description_status = "completed" if item_data.get("description") else "pending"  
        image_status = "completed" if item_data.get("image_url") else "pending"
        
        # Create base menu item with translation data
        translation_data = {
            "item_id": item_data["item_id"],
            "japanese_text": item_data["japanese_text"],
            "english_text": item_data.get("english_text"),
            "category": item_data.get("category", "Other"),
            "provider": item_data.get("providers", {}).get("translation", "Unknown"),
            "processing_time_ms": 0,  # Not available in JSON
            "fallback_used": False
        }
        
        menu_item = await self.repository.save_translation_result(session_id, translation_data)
        
        # Update with description if available
        if item_data.get("description"):
            description_data = {
                "item_id": item_data["item_id"],
                "description": item_data["description"],
                "provider": item_data.get("providers", {}).get("description", "Unknown"),
                "processing_time_ms": 0,
                "fallback_used": False
            }
            await self.repository.save_description_result(session_id, description_data)
        
        # Add image if available
        if item_data.get("image_url"):
            image_data = {
                "item_id": item_data["item_id"],
                "image_url": item_data["image_url"],
                "s3_key": self._extract_s3_key_from_url(item_data["image_url"]),
                "prompt": f"Food image for {item_data.get('english_text', item_data['japanese_text'])}",
                "provider": item_data.get("providers", {}).get("image", "Unknown"),
                "processing_time_ms": 0,
                "fallback_used": False
            }
            await self.repository.save_image_result(session_id, image_data)
    
    def _extract_s3_key_from_url(self, image_url: str) -> Optional[str]:
        """Extract S3 key from image URL"""
        if not image_url:
            return None
        
        # Extract key from S3 URL pattern
        # https://menu-sense.s3.ap-northeast-1.amazonaws.com/generated-images/2025/06/27/menu_image_blend_20250627_044902.png
        if "amazonaws.com/" in image_url:
            return image_url.split("amazonaws.com/")[1]
        
        return None


async def run_migration():
    """Run the migration process"""
    print("🚀 Starting JSON to Database Migration")
    
    # Get database session
    async with get_db_session() as db_session:
        repository = MenuTranslationRepository(db_session)
        migration_service = JSONMigrationService(repository)
        
        # Run migration
        summary = await migration_service.migrate_all_json_files()
        
        return summary


if __name__ == "__main__":
    summary = asyncio.run(run_migration())
    print(f"\n📋 Final Migration Summary:")
    print(f"Sessions migrated: {summary['migrated_sessions']}")
    print(f"Items migrated: {summary['migrated_items']}")
    print(f"Duration: {summary['duration_seconds']:.2f} seconds")
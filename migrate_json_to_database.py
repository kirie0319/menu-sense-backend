#!/usr/bin/env python3
"""
Migration Script: JSON Files to Database

This script migrates existing JSON translation files to the new database system.
It's part of Phase 6 of the TDD implementation.

Usage:
    python migrate_json_to_database.py

The script will:
1. Find all JSON files in uploads/menu_translations/
2. Parse each file and extract session/menu item data
3. Create corresponding database records
4. Preserve all translation, description, and image data
5. Provide detailed migration summary
"""
import asyncio
import sys
from pathlib import Path
import traceback

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import async_session_factory
from app.repositories.menu_translation_repository import MenuTranslationRepository
from app.services.json_migration_service import JSONMigrationService


async def main():
    """Main migration execution"""
    print("=" * 60)
    print("🚀 JSON to Database Migration Script")
    print("=" * 60)
    print()
    
    try:
        # Create database connection
        print("📡 Connecting to database...")
        
        async with async_session_factory() as db_session:
            print("✅ Database connection established")
            
            # Initialize migration service
            repository = MenuTranslationRepository(db_session)
            migration_service = JSONMigrationService(repository)
            
            # Run migration
            print("🔄 Starting migration process...")
            print()
            
            summary = await migration_service.migrate_all_json_files()
            
            # Display final summary
            print("\n" + "=" * 60)
            print("📊 MIGRATION SUMMARY")
            print("=" * 60)
            print(f"📁 Total files processed: {summary['total_files']}")
            print(f"✅ Sessions migrated: {summary['migrated_sessions']}")
            print(f"📝 Menu items migrated: {summary['migrated_items']}")
            print(f"⏭️ Sessions skipped (already exist): {len(summary['skipped_sessions'])}")
            print(f"❌ Failed migrations: {len(summary['failed_migrations'])}")
            print(f"⏱️ Total duration: {summary['duration_seconds']:.2f} seconds")
            
            if summary['skipped_sessions']:
                print("\n📋 Skipped Sessions:")
                for skip in summary['skipped_sessions']:
                    print(f"  • {skip['session_id']} - {skip['reason']}")
            
            if summary['failed_migrations']:
                print("\n❌ Failed Migrations:")
                for failure in summary['failed_migrations']:
                    print(f"  • {failure['file']}: {failure['error']}")
            
            print("\n🎉 Migration completed successfully!")
            
    except Exception as e:
        print(f"\n💥 Migration failed with error: {e}")
        print("\n🔍 Full error traceback:")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Run the migration
    asyncio.run(main())
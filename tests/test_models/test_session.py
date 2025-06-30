"""
RED PHASE: Session Model Tests

These tests define the expected behavior of the Session model.
Initially, these tests will FAIL because we need to implement proper constraints.
"""
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.models.menu_translation import Session, MenuItem
from tests.factories import SessionFactory, MenuItemFactory

class TestSessionModel:
    """Test Session model behavior and relationships"""
    
    async def test_create_session_with_required_fields(self, db_session):
        """RED: Test session creation with minimal required fields"""
        session = Session(
            session_id="test_session_123",
            total_items=5
        )
        db_session.add(session)
        await db_session.commit()
        
        assert session.id is not None
        assert session.session_id == "test_session_123"
        assert session.total_items == 5
        assert session.status == "processing"  # default value
        assert session.created_at is not None
        assert session.updated_at is not None
        assert session.metadata == {}  # default empty dict
    
    async def test_session_unique_constraint_on_session_id(self, db_session):
        """RED: Test unique constraint on session_id"""
        session1 = Session(session_id="duplicate_id", total_items=1)
        session2 = Session(session_id="duplicate_id", total_items=2)
        
        db_session.add(session1)
        await db_session.commit()
        
        db_session.add(session2)
        with pytest.raises(IntegrityError):  # Should raise integrity error
            await db_session.commit()
    
    async def test_session_menu_items_relationship(self, db_session):
        """RED: Test one-to-many relationship with menu items"""
        session = Session(session_id="rel_test", total_items=2)
        db_session.add(session)
        await db_session.flush()  # Get session.id without committing
        
        # Create related menu items
        item1 = MenuItem(
            session_id=session.id,
            item_id=0,
            japanese_text="アイテム1"
        )
        item2 = MenuItem(
            session_id=session.id, 
            item_id=1,
            japanese_text="アイテム2"
        )
        
        db_session.add_all([item1, item2])
        await db_session.commit()
        
        # Test relationship loading
        result = await db_session.execute(
            select(Session).where(Session.id == session.id)
        )
        loaded_session = result.scalar_one()
        
        # Test relationship access
        assert len(loaded_session.menu_items) == 2
        assert loaded_session.menu_items[0].session_id == session.id
        assert loaded_session.menu_items[1].session_id == session.id
    
    async def test_session_cascade_delete_menu_items(self, db_session):
        """RED: Test cascade delete of menu items when session is deleted"""
        session = Session(session_id="cascade_test", total_items=1)
        db_session.add(session)
        await db_session.flush()
        
        item = MenuItem(
            session_id=session.id,
            item_id=0,
            japanese_text="削除テスト"
        )
        db_session.add(item)
        await db_session.commit()
        
        # Verify item exists
        result = await db_session.execute(
            select(MenuItem).where(MenuItem.session_id == session.id)
        )
        assert result.scalar_one() is not None
        
        # Delete session
        await db_session.delete(session)
        await db_session.commit()
        
        # Verify menu items are also deleted (cascade)
        result = await db_session.execute(
            select(MenuItem).where(MenuItem.session_id == session.id)
        )
        assert result.scalar_one_or_none() is None
    
    async def test_session_status_values(self, db_session):
        """RED: Test valid status transitions"""
        session = Session(session_id="status_test", total_items=1)
        
        # Test default status
        assert session.status == "processing"
        
        # Test status updates
        session.status = "completed"
        db_session.add(session)
        await db_session.commit()
        
        # Reload and verify
        result = await db_session.execute(
            select(Session).where(Session.session_id == "status_test")
        )
        reloaded = result.scalar_one()
        assert reloaded.status == "completed"
    
    async def test_session_metadata_json_field(self, db_session):
        """RED: Test JSON metadata field functionality"""
        metadata = {
            "source": "api_upload",
            "original_filename": "menu.jpg", 
            "user_id": "user_123",
            "settings": {
                "use_fallback": True,
                "quality": "high"
            }
        }
        
        session = Session(
            session_id="metadata_test",
            total_items=1,
            metadata=metadata
        )
        db_session.add(session)
        await db_session.commit()
        
        # Reload and verify JSON data
        result = await db_session.execute(
            select(Session).where(Session.session_id == "metadata_test")
        )
        reloaded = result.scalar_one()
        
        assert reloaded.metadata["source"] == "api_upload"
        assert reloaded.metadata["settings"]["quality"] == "high"
        assert reloaded.metadata["user_id"] == "user_123"
    
    async def test_session_timestamps_auto_update(self, db_session):
        """RED: Test automatic timestamp updates"""
        session = Session(session_id="timestamp_test", total_items=1)
        db_session.add(session)
        await db_session.commit()
        
        original_updated_at = session.updated_at
        
        # Update session
        session.status = "completed"
        await db_session.commit()
        
        # Verify updated_at changed
        await db_session.refresh(session)
        assert session.updated_at > original_updated_at
    
    async def test_session_factory_creates_valid_instance(self, db_session):
        """RED: Test that our factory creates valid Session instances"""
        session = SessionFactory.build()
        
        # Test factory-generated data
        assert session.session_id.startswith("test_")
        assert 1 <= session.total_items <= 20
        assert session.status in ['processing', 'completed', 'failed']
        assert session.metadata.get("source") == "test_factory"
        
        # Test database persistence
        db_session.add(session)
        await db_session.commit()
        
        # Verify it's saved correctly
        result = await db_session.execute(
            select(Session).where(Session.session_id == session.session_id)
        )
        saved_session = result.scalar_one()
        assert saved_session.id == session.id
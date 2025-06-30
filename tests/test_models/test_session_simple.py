"""
RED PHASE: Simple Session Model Tests (Without DB Container)

These tests verify our model structure works correctly.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.models.menu_translation import Session, MenuItem

class TestSessionModelSimple:
    """Test Session model basic functionality"""
    
    @pytest.fixture
    def in_memory_db(self):
        """Create in-memory SQLite database for testing"""
        engine = create_engine("sqlite:///:memory:", echo=True)
        Base.metadata.create_all(engine)
        session_factory = sessionmaker(bind=engine)
        session = session_factory()
        yield session
        session.close()
    
    def test_create_session_with_required_fields(self, in_memory_db):
        """RED: Test session creation with minimal required fields"""
        session = Session(
            session_id="test_session_123",
            total_items=5
        )
        in_memory_db.add(session)
        in_memory_db.commit()
        
        assert session.id is not None
        assert session.session_id == "test_session_123"
        assert session.total_items == 5
        assert session.status == "processing"  # default value
        assert session.created_at is not None
        assert session.updated_at is not None
        assert session.metadata == {}  # default empty dict
        
        print("✅ Session creation test passed!")
    
    def test_session_metadata_json_field(self, in_memory_db):
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
        in_memory_db.add(session)
        in_memory_db.commit()
        
        # Reload and verify JSON data
        reloaded = in_memory_db.query(Session).filter_by(session_id="metadata_test").first()
        
        assert reloaded.metadata["source"] == "api_upload"
        assert reloaded.metadata["settings"]["quality"] == "high"
        assert reloaded.metadata["user_id"] == "user_123"
        
        print("✅ Session metadata test passed!")
    
    def test_session_menu_items_relationship(self, in_memory_db):
        """RED: Test one-to-many relationship with menu items"""
        session = Session(session_id="rel_test", total_items=2)
        in_memory_db.add(session)
        in_memory_db.flush()  # Get session.id without committing
        
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
        
        in_memory_db.add_all([item1, item2])
        in_memory_db.commit()
        
        # Test relationship loading
        loaded_session = in_memory_db.query(Session).filter_by(id=session.id).first()
        
        # Test relationship access
        assert len(loaded_session.menu_items) == 2
        assert loaded_session.menu_items[0].session_id == session.id
        assert loaded_session.menu_items[1].session_id == session.id
        
        print("✅ Session relationship test passed!")
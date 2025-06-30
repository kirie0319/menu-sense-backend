"""
Standalone test to verify our database models work
"""
from sqlalchemy import create_engine, Column, String, Integer, Text, DateTime, Boolean, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
import uuid
from datetime import datetime

# Create declarative base for models
Base = declarative_base()

class Session(Base):
    """Session model for tracking menu translation sessions"""
    __tablename__ = "sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(100), unique=True, nullable=False, index=True)
    total_items = Column(Integer, nullable=False)
    status = Column(String(20), default='processing')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    session_metadata = Column(JSON, default=lambda: {})
    
    # Relationships
    menu_items = relationship("MenuItem", back_populates="session", cascade="all, delete-orphan")

class MenuItem(Base):
    """MenuItem model for individual menu items within a session"""
    __tablename__ = "menu_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey('sessions.id'), nullable=False)
    item_id = Column(Integer, nullable=False)
    japanese_text = Column(Text, nullable=False)
    english_text = Column(Text)
    category = Column(String(100))
    description = Column(Text)
    
    # Status tracking for each processing stage
    translation_status = Column(String(20), default='pending')
    description_status = Column(String(20), default='pending')
    image_status = Column(String(20), default='pending')
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    session = relationship("Session", back_populates="menu_items")
    
    # Composite unique constraint on session_id and item_id
    __table_args__ = (
        UniqueConstraint('session_id', 'item_id', name='uq_session_item'),
    )

def test_models():
    """Test that our models can be created and used"""
    print("🧪 Testing Menu Translation Database Models (Standalone)...")
    
    # Create in-memory SQLite database
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    db_session = session_factory()
    
    try:
        # Test 1: Create a Session
        print("\n1️⃣ Testing Session creation...")
        session = Session(
            session_id="test_session_123",
            total_items=5,
            session_metadata={"source": "test", "user": "tester"}
        )
        db_session.add(session)
        db_session.commit()
        
        assert session.id is not None
        assert session.session_id == "test_session_123"
        assert session.total_items == 5
        assert session.status == "processing"  # default value
        assert session.session_metadata["source"] == "test"
        print("✅ Session creation works!")
        
        # Test 2: Create MenuItem with relationship
        print("\n2️⃣ Testing MenuItem creation with relationship...")
        menu_item = MenuItem(
            session_id=session.id,
            item_id=0,
            japanese_text="カレーライス",
            english_text="Curry Rice",
            category="Main Dishes",
            description="Delicious Japanese curry over rice"
        )
        db_session.add(menu_item)
        db_session.commit()
        
        assert menu_item.id is not None
        assert menu_item.japanese_text == "カレーライス"
        assert menu_item.translation_status == "pending"  # default
        print("✅ MenuItem creation works!")
        
        # Test 3: Test relationship
        print("\n3️⃣ Testing Session-MenuItem relationship...")
        loaded_session = db_session.query(Session).filter_by(id=session.id).first()
        assert len(loaded_session.menu_items) == 1
        assert loaded_session.menu_items[0].japanese_text == "カレーライス"
        print("✅ Relationship works!")
        
        # Test 4: Test unique constraint
        print("\n4️⃣ Testing unique constraint on (session_id, item_id)...")
        try:
            duplicate_item = MenuItem(
                session_id=session.id,
                item_id=0,  # Same item_id - should fail
                japanese_text="重複アイテム"
            )
            db_session.add(duplicate_item)
            db_session.commit()
            print("❌ Unique constraint not working!")
            return False
        except Exception as e:
            print("✅ Unique constraint works! (Expected error)")
            db_session.rollback()
        
        # Test 5: Test cascade delete
        print("\n5️⃣ Testing cascade delete...")
        # First verify item exists
        item_count = db_session.query(MenuItem).filter_by(session_id=session.id).count()
        assert item_count == 1
        
        # Delete session and check cascade
        db_session.delete(session)
        db_session.commit()
        
        item_count_after = db_session.query(MenuItem).filter_by(session_id=session.id).count()
        assert item_count_after == 0
        print("✅ Cascade delete works!")
        
        print("\n🎉 All model tests passed! Database schema is working correctly.")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        db_session.close()

if __name__ == "__main__":
    success = test_models()
    exit(0 if success else 1)
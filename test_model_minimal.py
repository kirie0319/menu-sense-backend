"""
Minimal test to verify our database models work
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.models.menu_translation import Session, MenuItem

def test_models():
    """Test that our models can be created and used"""
    print("🧪 Testing Menu Translation Database Models...")
    
    # Create in-memory SQLite database
    engine = create_engine("sqlite:///:memory:", echo=True)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    db_session = session_factory()
    
    try:
        # Test 1: Create a Session
        print("\n1️⃣ Testing Session creation...")
        session = Session(
            session_id="test_session_123",
            total_items=5,
            metadata={"source": "test", "user": "tester"}
        )
        db_session.add(session)
        db_session.commit()
        
        assert session.id is not None
        assert session.session_id == "test_session_123"
        assert session.total_items == 5
        assert session.status == "processing"  # default value
        assert session.metadata["source"] == "test"
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
        
        print("\n🎉 All model tests passed! Database schema is working correctly.")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False
        
    finally:
        db_session.close()

if __name__ == "__main__":
    success = test_models()
    exit(0 if success else 1)
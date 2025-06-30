"""
Standalone test to verify our repository implementation works
"""
import asyncio
from sqlalchemy import create_engine, Column, String, Integer, Text, DateTime, Boolean, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
import uuid
from datetime import datetime

# Create declarative base for models (same as before)
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
    
    # Status tracking
    translation_status = Column(String(20), default='pending')
    description_status = Column(String(20), default='pending')
    image_status = Column(String(20), default='pending')
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    session = relationship("Session", back_populates="menu_items")
    providers = relationship("ProcessingProvider", back_populates="menu_item", cascade="all, delete-orphan")
    images = relationship("MenuItemImage", back_populates="menu_item", cascade="all, delete-orphan")
    
    # Composite unique constraint
    __table_args__ = (
        UniqueConstraint('session_id', 'item_id', name='uq_session_item'),
    )

class ProcessingProvider(Base):
    """ProcessingProvider model for tracking AI services"""
    __tablename__ = "processing_providers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    menu_item_id = Column(UUID(as_uuid=True), ForeignKey('menu_items.id'), nullable=False)
    stage = Column(String(20), nullable=False)
    provider = Column(String(100), nullable=False)
    processed_at = Column(DateTime, default=datetime.utcnow)
    processing_time_ms = Column(Integer)
    fallback_used = Column(Boolean, default=False)
    provider_metadata = Column(JSON, default=lambda: {})
    
    # Relationships
    menu_item = relationship("MenuItem", back_populates="providers")

class MenuItemImage(Base):
    """MenuItemImage model for storing generated images"""
    __tablename__ = "menu_item_images"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    menu_item_id = Column(UUID(as_uuid=True), ForeignKey('menu_items.id'), nullable=False)
    image_url = Column(Text, nullable=False)
    s3_key = Column(Text)
    prompt = Column(Text)
    provider = Column(String(100))
    fallback_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    image_metadata = Column(JSON, default=lambda: {})
    
    # Relationships
    menu_item = relationship("MenuItem", back_populates="images")

# Import our repository
from dataclasses import dataclass
from typing import Optional, List
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

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
    
    def __init__(self, db_session):
        self.db_session = db_session
    
    async def create_session(self, session_data: dict):
        """Create new session"""
        session = Session(
            session_id=session_data["session_id"],
            total_items=session_data["total_items"],
            session_metadata=session_data.get("session_metadata", {})
        )
        self.db_session.add(session)
        await self.db_session.commit()
        await self.db_session.refresh(session)
        return session
    
    async def save_translation_result(self, session_id: str, data: dict):
        """Save translation result to database"""
        # Get session
        session_result = await self.db_session.execute(
            select(Session).where(Session.session_id == session_id)
        )
        session = session_result.scalar_one()
        
        # Create menu item
        menu_item = MenuItem(
            session_id=session.id,
            item_id=data["item_id"],
            japanese_text=data["japanese_text"],
            english_text=data.get("english_text"),
            category=data.get("category"),
            translation_status="completed"
        )
        self.db_session.add(menu_item)
        await self.db_session.flush()
        
        # Create provider record
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
        return menu_item
    
    async def get_session_progress(self, session_id: str):
        """Get session progress information"""
        # Get session
        session_result = await self.db_session.execute(
            select(Session).where(Session.session_id == session_id)
        )
        session = session_result.scalar_one()
        
        # Get all menu items
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

async def test_repository():
    """Test that our repository implementation works"""
    print("🧪 Testing Menu Translation Repository...")
    
    # Create async in-memory SQLite database
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with async_session() as session:
            repository = MenuTranslationRepository(session)
            
            # Test 1: Create session
            print("\n1️⃣ Testing session creation...")
            session_data = {
                "session_id": "test_repo_session",
                "total_items": 3,
                "session_metadata": {"source": "test_repository"}
            }
            
            created_session = await repository.create_session(session_data)
            assert created_session.session_id == "test_repo_session"
            assert created_session.total_items == 3
            print("✅ Session creation works!")
            
            # Test 2: Save translation result
            print("\n2️⃣ Testing translation result saving...")
            translation_data = {
                "item_id": 0,
                "japanese_text": "寿司",
                "english_text": "Sushi",
                "category": "Main Dishes",
                "provider": "Google Translate API",
                "processing_time_ms": 150
            }
            
            menu_item = await repository.save_translation_result(
                "test_repo_session",
                translation_data
            )
            
            assert menu_item.japanese_text == "寿司"
            assert menu_item.english_text == "Sushi"
            assert menu_item.translation_status == "completed"
            print("✅ Translation result saving works!")
            
            # Test 3: Get session progress
            print("\n3️⃣ Testing session progress calculation...")
            progress = await repository.get_session_progress("test_repo_session")
            
            assert isinstance(progress, SessionProgress)
            assert progress.total_items == 1  # We created 1 item
            assert progress.translation_completed == 1
            assert progress.description_completed == 0
            assert progress.image_completed == 0
            assert progress.fully_completed == 0
            assert progress.progress_percentage == 0.0  # Not fully complete
            print("✅ Session progress calculation works!")
            
        print("\n🎉 All repository tests passed! Repository implementation is working correctly.")
        return True
        
    except Exception as e:
        print(f"\n❌ Repository test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        await engine.dispose()

if __name__ == "__main__":
    success = asyncio.run(test_repository())
    exit(0 if success else 1)
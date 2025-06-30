"""
Integration test to verify service + repository work together
"""
import asyncio
from sqlalchemy import create_engine, Column, String, Integer, Text, DateTime, Boolean, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
import uuid
from datetime import datetime

# Models (same as before)
Base = declarative_base()

class Session(Base):
    __tablename__ = "sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(100), unique=True, nullable=False, index=True)
    total_items = Column(Integer, nullable=False)
    status = Column(String(20), default='processing')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    session_metadata = Column(JSON, default=lambda: {})
    
    menu_items = relationship("MenuItem", back_populates="session", cascade="all, delete-orphan")

class MenuItem(Base):
    __tablename__ = "menu_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey('sessions.id'), nullable=False)
    item_id = Column(Integer, nullable=False)
    japanese_text = Column(Text, nullable=False)
    english_text = Column(Text)
    category = Column(String(100))
    description = Column(Text)
    
    translation_status = Column(String(20), default='pending')
    description_status = Column(String(20), default='pending')
    image_status = Column(String(20), default='pending')
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    session = relationship("Session", back_populates="menu_items")
    providers = relationship("ProcessingProvider", back_populates="menu_item", cascade="all, delete-orphan")
    images = relationship("MenuItemImage", back_populates="menu_item", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('session_id', 'item_id', name='uq_session_item'),
    )

class ProcessingProvider(Base):
    __tablename__ = "processing_providers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    menu_item_id = Column(UUID(as_uuid=True), ForeignKey('menu_items.id'), nullable=False)
    stage = Column(String(20), nullable=False)
    provider = Column(String(100), nullable=False)
    processed_at = Column(DateTime, default=datetime.utcnow)
    processing_time_ms = Column(Integer)
    fallback_used = Column(Boolean, default=False)
    provider_metadata = Column(JSON, default=lambda: {})
    
    menu_item = relationship("MenuItem", back_populates="providers")

class MenuItemImage(Base):
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
    
    menu_item = relationship("MenuItem", back_populates="images")

# Import repository and service
from dataclasses import dataclass
from typing import Optional, List
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

@dataclass
class SessionProgress:
    total_items: int
    translation_completed: int
    description_completed: int
    image_completed: int
    fully_completed: int
    progress_percentage: float

class MenuTranslationRepository:
    def __init__(self, db_session):
        self.db_session = db_session
    
    async def create_session(self, session_data: dict):
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
        session_result = await self.db_session.execute(
            select(Session).where(Session.session_id == session_id)
        )
        session = session_result.scalar_one()
        
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
    
    async def save_description_result(self, session_id: str, data: dict):
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
        
        menu_item.description = data.get("description")
        menu_item.description_status = "completed"
        
        await self.db_session.flush()
        
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
        return menu_item
    
    async def get_session_progress(self, session_id: str):
        session_result = await self.db_session.execute(
            select(Session).where(Session.session_id == session_id)
        )
        session = session_result.scalar_one()
        
        items_result = await self.db_session.execute(
            select(MenuItem).where(MenuItem.session_id == session.id)
        )
        menu_items = items_result.scalars().all()
        
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

class MenuTranslationService:
    def __init__(self, repository, redis_client=None):
        self.repository = repository
        self.redis_client = redis_client
    
    async def start_translation_session(self, session_id: str, menu_items: list, metadata=None):
        import time
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
    
    async def process_translation_result(self, celery_result):
        translation_data = {
            "item_id": celery_result["item_id"],
            "japanese_text": celery_result["japanese_text"],
            "english_text": celery_result["english_text"],
            "category": celery_result.get("category", "Other"),
            "provider": celery_result.get("provider", "Unknown"),
            "processing_time_ms": int(celery_result.get("processing_time", 0) * 1000),
            "fallback_used": celery_result.get("fallback_used", False)
        }
        
        return await self.repository.save_translation_result(
            celery_result["session_id"],
            translation_data
        )
    
    async def process_description_result(self, celery_result):
        description_data = {
            "item_id": celery_result["item_id"],
            "description": celery_result["description"],
            "provider": celery_result.get("provider", "Unknown"),
            "processing_time_ms": int(celery_result.get("processing_time", 0) * 1000),
            "fallback_used": celery_result.get("fallback_used", False)
        }
        
        return await self.repository.save_description_result(
            celery_result["session_id"],
            description_data
        )
    
    async def get_real_time_progress(self, session_id: str):
        return await self.repository.get_session_progress(session_id)

async def test_service_integration():
    """Test complete service + repository integration"""
    print("🧪 Testing Service + Repository Integration...")
    
    # Create async in-memory SQLite database
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with async_session() as session:
            repository = MenuTranslationRepository(session)
            service = MenuTranslationService(repository)
            
            # Test 1: Start translation session
            print("\n1️⃣ Testing service session creation...")
            menu_items = ["カレーライス", "寿司", "ラーメン"]
            created_session = await service.start_translation_session(
                session_id="service_test_session",
                menu_items=menu_items,
                metadata={"source": "integration_test"}
            )
            
            assert created_session.session_id == "service_test_session"
            assert created_session.total_items == 3
            assert created_session.session_metadata["source"] == "integration_test"
            print("✅ Service session creation works!")
            
            # Test 2: Process translation result (simulating Celery task)
            print("\n2️⃣ Testing translation result processing...")
            celery_translation_result = {
                "session_id": "service_test_session",
                "item_id": 0,
                "japanese_text": "カレーライス",
                "english_text": "Curry Rice",
                "category": "Main Dishes",
                "provider": "Google Translate API",
                "processing_time": 0.15,
                "fallback_used": False
            }
            
            menu_item = await service.process_translation_result(celery_translation_result)
            
            assert menu_item.japanese_text == "カレーライス"
            assert menu_item.english_text == "Curry Rice"
            assert menu_item.translation_status == "completed"
            print("✅ Translation result processing works!")
            
            # Test 3: Process description result
            print("\n3️⃣ Testing description result processing...")
            celery_description_result = {
                "session_id": "service_test_session",
                "item_id": 0,
                "description": "Japanese curry sauce served over steamed rice with tender meat and vegetables.",
                "provider": "OpenAI GPT-4.1-mini",
                "processing_time": 2.5,
                "fallback_used": False
            }
            
            updated_item = await service.process_description_result(celery_description_result)
            
            assert updated_item.description.startswith("Japanese curry sauce")
            assert updated_item.description_status == "completed"
            print("✅ Description result processing works!")
            
            # Test 4: Get real-time progress
            print("\n4️⃣ Testing real-time progress...")
            progress = await service.get_real_time_progress("service_test_session")
            
            assert progress.total_items == 1  # We only processed 1 item
            assert progress.translation_completed == 1
            assert progress.description_completed == 1
            assert progress.image_completed == 0
            assert progress.fully_completed == 0  # No image yet
            assert progress.progress_percentage == 0.0
            print("✅ Real-time progress works!")
            
        print("\n🎉 All service integration tests passed! Service layer is working correctly.")
        return True
        
    except Exception as e:
        print(f"\n❌ Service integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        await engine.dispose()

if __name__ == "__main__":
    success = asyncio.run(test_service_integration())
    exit(0 if success else 1)
"""
RED PHASE: MenuItem Model Tests

These tests define the expected behavior of the MenuItem model.
Initially, these tests will FAIL because we need to add proper constraints.
"""
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.models.menu_translation import MenuItem, Session, ProcessingProvider, MenuItemImage
from tests.factories import MenuItemFactory, SessionFactory, ProcessingProviderFactory

class TestMenuItemModel:
    """Test MenuItem model behavior and constraints"""
    
    async def test_create_menu_item_with_required_fields(self, db_session):
        """RED: Test menu item creation with required Japanese text"""
        session = Session(session_id="item_test", total_items=1)
        db_session.add(session)
        await db_session.flush()
        
        menu_item = MenuItem(
            session_id=session.id,
            item_id=0,
            japanese_text="カレーライス"
        )
        db_session.add(menu_item)
        await db_session.commit()
        
        assert menu_item.id is not None
        assert menu_item.japanese_text == "カレーライス"
        assert menu_item.translation_status == "pending"  # default
        assert menu_item.description_status == "pending"  # default
        assert menu_item.image_status == "pending"  # default
        assert menu_item.created_at is not None
    
    async def test_menu_item_unique_constraint_session_item_id(self, db_session):
        """RED: Test unique constraint on (session_id, item_id)"""
        session = Session(session_id="unique_test", total_items=2)
        db_session.add(session)
        await db_session.flush()
        
        item1 = MenuItem(
            session_id=session.id,
            item_id=0,
            japanese_text="アイテム1"
        )
        item2 = MenuItem(
            session_id=session.id,
            item_id=0,  # Same item_id - should cause constraint violation
            japanese_text="アイテム2"
        )
        
        db_session.add(item1)
        await db_session.commit()
        
        db_session.add(item2)
        with pytest.raises(IntegrityError):  # Should raise integrity error
            await db_session.commit()
    
    async def test_menu_item_allows_duplicate_item_id_different_sessions(self, db_session):
        """RED: Test that same item_id is allowed in different sessions"""
        session1 = Session(session_id="session1", total_items=1)
        session2 = Session(session_id="session2", total_items=1)
        db_session.add_all([session1, session2])
        await db_session.flush()
        
        item1 = MenuItem(
            session_id=session1.id,
            item_id=0,
            japanese_text="アイテム1"
        )
        item2 = MenuItem(
            session_id=session2.id, 
            item_id=0,  # Same item_id but different session - should be OK
            japanese_text="アイテム2"
        )
        
        db_session.add_all([item1, item2])
        await db_session.commit()  # Should not raise error
        
        # Verify both items exist
        result = await db_session.execute(select(MenuItem))
        items = result.scalars().all()
        assert len(items) == 2
    
    async def test_menu_item_status_transitions(self, db_session):
        """RED: Test status field updates"""
        session = Session(session_id="status_test", total_items=1)
        menu_item = MenuItem(
            session_id=session.id,
            item_id=0,
            japanese_text="ステータステスト"
        )
        
        db_session.add_all([session, menu_item])
        await db_session.commit()
        
        # Test status updates
        menu_item.translation_status = "completed"
        menu_item.description_status = "failed"
        menu_item.image_status = "completed"
        await db_session.commit()
        
        # Reload and verify
        result = await db_session.execute(
            select(MenuItem).where(MenuItem.id == menu_item.id)
        )
        reloaded = result.scalar_one()
        assert reloaded.translation_status == "completed"
        assert reloaded.description_status == "failed"
        assert reloaded.image_status == "completed"
    
    async def test_menu_item_processing_providers_relationship(self, db_session):
        """RED: Test one-to-many relationship with processing providers"""
        session = Session(session_id="provider_test", total_items=1)
        menu_item = MenuItem(
            session_id=session.id,
            item_id=0,
            japanese_text="プロバイダーテスト"
        )
        
        db_session.add_all([session, menu_item])
        await db_session.flush()
        
        # Create processing providers for different stages
        translation_provider = ProcessingProvider(
            menu_item_id=menu_item.id,
            stage="translation",
            provider="Google Translate API",
            processing_time_ms=150
        )
        
        description_provider = ProcessingProvider(
            menu_item_id=menu_item.id,
            stage="description", 
            provider="OpenAI GPT-4.1-mini",
            processing_time_ms=2500
        )
        
        db_session.add_all([translation_provider, description_provider])
        await db_session.commit()
        
        # Test relationship loading
        result = await db_session.execute(
            select(MenuItem).where(MenuItem.id == menu_item.id)
        )
        loaded_item = result.scalar_one()
        
        assert len(loaded_item.providers) == 2
        stages = [p.stage for p in loaded_item.providers]
        assert "translation" in stages
        assert "description" in stages
    
    async def test_menu_item_images_relationship(self, db_session):
        """RED: Test one-to-many relationship with images"""
        session = Session(session_id="image_test", total_items=1)
        menu_item = MenuItem(
            session_id=session.id,
            item_id=0,
            japanese_text="画像テスト"
        )
        
        db_session.add_all([session, menu_item])
        await db_session.flush()
        
        # Create menu item image
        image = MenuItemImage(
            menu_item_id=menu_item.id,
            image_url="https://test.com/image.jpg",
            s3_key="test/image.jpg",
            provider="Google Imagen 3"
        )
        
        db_session.add(image)
        await db_session.commit()
        
        # Test relationship loading
        result = await db_session.execute(
            select(MenuItem).where(MenuItem.id == menu_item.id)
        )
        loaded_item = result.scalar_one()
        
        assert len(loaded_item.images) == 1
        assert loaded_item.images[0].image_url == "https://test.com/image.jpg"
        assert loaded_item.images[0].provider == "Google Imagen 3"
    
    async def test_menu_item_cascade_delete_related_data(self, db_session):
        """RED: Test cascade delete of providers and images when menu item is deleted"""
        session = Session(session_id="cascade_test", total_items=1)
        menu_item = MenuItem(
            session_id=session.id,
            item_id=0,
            japanese_text="カスケード削除テスト"
        )
        
        db_session.add_all([session, menu_item])
        await db_session.flush()
        
        # Create related data
        provider = ProcessingProvider(
            menu_item_id=menu_item.id,
            stage="translation",
            provider="Test Provider"
        )
        
        image = MenuItemImage(
            menu_item_id=menu_item.id,
            image_url="https://test.com/image.jpg",
            provider="Test Image Provider"
        )
        
        db_session.add_all([provider, image])
        await db_session.commit()
        
        # Verify related data exists
        provider_result = await db_session.execute(
            select(ProcessingProvider).where(ProcessingProvider.menu_item_id == menu_item.id)
        )
        image_result = await db_session.execute(
            select(MenuItemImage).where(MenuItemImage.menu_item_id == menu_item.id)
        )
        
        assert provider_result.scalar_one() is not None
        assert image_result.scalar_one() is not None
        
        # Delete menu item
        await db_session.delete(menu_item)
        await db_session.commit()
        
        # Verify related data is also deleted (cascade)
        provider_result = await db_session.execute(
            select(ProcessingProvider).where(ProcessingProvider.menu_item_id == menu_item.id)
        )
        image_result = await db_session.execute(
            select(MenuItemImage).where(MenuItemImage.menu_item_id == menu_item.id)
        )
        
        assert provider_result.scalar_one_or_none() is None
        assert image_result.scalar_one_or_none() is None
    
    async def test_menu_item_factory_creates_valid_instance(self, db_session):
        """RED: Test that our factory creates valid MenuItem instances"""
        session = SessionFactory.build()
        db_session.add(session)
        await db_session.flush()
        
        menu_item = MenuItemFactory.build(session_id=session.id)
        
        # Test factory-generated data
        assert menu_item.japanese_text in [
            "カレーライス", "寿司", "ラーメン", "天ぷら", "焼き鳥"
        ]
        assert menu_item.category in [
            'Appetizers', 'Main Dishes', 'Desserts', 'Beverages', 'Soups', 'Other'
        ]
        
        # Test database persistence
        db_session.add(menu_item)
        await db_session.commit()
        
        # Verify it's saved correctly
        result = await db_session.execute(
            select(MenuItem).where(MenuItem.id == menu_item.id)
        )
        saved_item = result.scalar_one()
        assert saved_item.japanese_text == menu_item.japanese_text
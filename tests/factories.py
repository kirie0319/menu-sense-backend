"""
Test data factories for Menu Translation Database TDD

Factory classes using factory_boy to generate test data for database models.
These factories create realistic test instances with proper relationships.
"""
import factory
from factory import fuzzy
from datetime import datetime, timedelta
import uuid
from app.models.menu_translation import Session, MenuItem, ProcessingProvider, MenuItemImage, Category

class SessionFactory(factory.Factory):
    """Factory for creating Session test instances"""
    class Meta:
        model = Session
    
    session_id = factory.LazyFunction(lambda: f"test_{str(uuid.uuid4())[:8]}")
    total_items = fuzzy.FuzzyInteger(1, 20)
    status = fuzzy.FuzzyChoice(['processing', 'completed', 'failed'])
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)
    completed_at = None
    metadata = factory.Dict({
        "source": "test_factory",
        "test_mode": True
    })

class MenuItemFactory(factory.Factory):
    """Factory for creating MenuItem test instances"""
    class Meta:
        model = MenuItem
    
    item_id = factory.Sequence(lambda n: n)
    japanese_text = fuzzy.FuzzyChoice([
        "カレーライス", "寿司", "ラーメン", "天ぷら", "焼き鳥", 
        "そば", "うどん", "丼物", "味噌汁", "刺身"
    ])
    english_text = fuzzy.FuzzyChoice([
        "Curry Rice", "Sushi", "Ramen", "Tempura", "Yakitori",
        "Soba", "Udon", "Rice Bowl", "Miso Soup", "Sashimi"
    ])
    category = fuzzy.FuzzyChoice(['Appetizers', 'Main Dishes', 'Desserts', 'Beverages', 'Soups', 'Other'])
    description = factory.Faker('paragraph', nb_sentences=3)
    
    # Status fields
    translation_status = 'pending'
    description_status = 'pending'
    image_status = 'pending'
    
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)

class CompletedMenuItemFactory(MenuItemFactory):
    """Factory for creating fully completed menu items"""
    translation_status = 'completed'
    description_status = 'completed'
    image_status = 'completed'

class ProcessingProviderFactory(factory.Factory):
    """Factory for creating ProcessingProvider test instances"""
    class Meta:
        model = ProcessingProvider
    
    stage = fuzzy.FuzzyChoice(['translation', 'description', 'image'])
    provider = fuzzy.FuzzyChoice([
        'Google Translate API', 
        'OpenAI GPT-4.1-mini', 
        'Google Imagen 3',
        'Fallback Translation Service',
        'Fallback Description Service'
    ])
    processed_at = factory.LazyFunction(datetime.utcnow)
    processing_time_ms = fuzzy.FuzzyInteger(100, 5000)
    fallback_used = False
    metadata = factory.Dict({
        "confidence": factory.Faker('pyfloat', left_digits=0, right_digits=2, positive=True, max_value=1.0),
        "model_version": "test-v1.0"
    })

class FallbackProcessingProviderFactory(ProcessingProviderFactory):
    """Factory for creating fallback provider instances"""
    provider = fuzzy.FuzzyChoice([
        'Fallback Translation Service',
        'Fallback Description Service', 
        'Fallback Image Service'
    ])
    fallback_used = True

class MenuItemImageFactory(factory.Factory):
    """Factory for creating MenuItemImage test instances"""
    class Meta:
        model = MenuItemImage
    
    image_url = factory.LazyFunction(
        lambda: f"https://test-bucket.s3.amazonaws.com/test-images/{uuid.uuid4()}.jpg"
    )
    s3_key = factory.LazyFunction(
        lambda: f"test-images/{uuid.uuid4()}.jpg"
    )
    prompt = factory.Faker('sentence', nb_words=10)
    provider = 'Google Imagen 3'
    fallback_used = False
    created_at = factory.LazyFunction(datetime.utcnow)
    metadata = factory.Dict({
        "generation_time_ms": factory.Faker('pyint', min_value=1000, max_value=10000),
        "image_size": "1024x1024",
        "format": "jpg"
    })

class FallbackMenuItemImageFactory(MenuItemImageFactory):
    """Factory for creating fallback image instances"""
    image_url = factory.LazyFunction(
        lambda: f"https://placeholder-images.example.com/food/{uuid.uuid4()}.jpg"
    )
    s3_key = None
    provider = 'Fallback Image Service'
    fallback_used = True

class CategoryFactory(factory.Factory):
    """Factory for creating Category test instances"""
    class Meta:
        model = Category
    
    name = fuzzy.FuzzyChoice([
        'Appetizers', 'Main Dishes', 'Desserts', 'Beverages', 
        'Soups', 'Salads', 'Noodles', 'Rice Dishes', 'Other'
    ])
    description = factory.Faker('sentence', nb_words=8)
    created_at = factory.LazyFunction(datetime.utcnow)

# Composite factories for creating related data

class CompleteSessionFactory(SessionFactory):
    """Factory that creates a session with related menu items"""
    status = 'completed'
    completed_at = factory.LazyFunction(datetime.utcnow)
    
    @factory.post_generation
    def menu_items(self, create, extracted, **kwargs):
        if not create:
            return
        
        # Create 3 completed menu items by default
        item_count = kwargs.get('item_count', 3)
        for i in range(item_count):
            menu_item = CompletedMenuItemFactory.build(
                session_id=self.id,
                item_id=i
            )
            self.menu_items.append(menu_item)

class MenuItemWithProvidersFactory(CompletedMenuItemFactory):
    """Factory that creates a menu item with all processing providers"""
    
    @factory.post_generation
    def providers(self, create, extracted, **kwargs):
        if not create:
            return
        
        # Create providers for all stages
        stages = ['translation', 'description', 'image']
        provider_names = {
            'translation': 'Google Translate API',
            'description': 'OpenAI GPT-4.1-mini', 
            'image': 'Google Imagen 3'
        }
        
        for stage in stages:
            provider = ProcessingProviderFactory.build(
                menu_item_id=self.id,
                stage=stage,
                provider=provider_names[stage]
            )
            self.providers.append(provider)
    
    @factory.post_generation
    def images(self, create, extracted, **kwargs):
        if not create:
            return
        
        # Create one image
        image = MenuItemImageFactory.build(menu_item_id=self.id)
        self.images.append(image)

# Helper functions for creating test data

def create_test_session_with_items(db_session, item_count=3, completed=True):
    """Helper function to create a complete test session with menu items"""
    session = SessionFactory.build(
        total_items=item_count,
        status='completed' if completed else 'processing'
    )
    
    items = []
    for i in range(item_count):
        if completed:
            item = MenuItemWithProvidersFactory.build(
                session_id=session.id,
                item_id=i
            )
        else:
            item = MenuItemFactory.build(
                session_id=session.id,
                item_id=i
            )
        items.append(item)
    
    return session, items

def create_sample_japanese_menu_items():
    """Create sample Japanese menu items for testing"""
    items = [
        {
            "japanese_text": "カレーライス",
            "english_text": "Curry Rice",
            "category": "Main Dishes",
            "description": "Japanese curry sauce served over steamed rice with tender meat and vegetables."
        },
        {
            "japanese_text": "寿司",
            "english_text": "Sushi", 
            "category": "Main Dishes",
            "description": "Fresh raw fish served over seasoned rice, a traditional Japanese delicacy."
        },
        {
            "japanese_text": "味噌汁",
            "english_text": "Miso Soup",
            "category": "Soups", 
            "description": "Traditional Japanese soup made from fermented soybean paste with tofu and seaweed."
        },
        {
            "japanese_text": "抹茶アイス",
            "english_text": "Matcha Ice Cream",
            "category": "Desserts",
            "description": "Creamy ice cream infused with premium Japanese green tea powder."
        }
    ]
    return items
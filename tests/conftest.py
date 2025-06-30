"""
pytest共通設定とフィクスチャ
"""
import os
import sys
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from typing import Dict, Any, Optional
from pathlib import Path

# Database testing imports
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config import settings
from app.services.ocr.base import OCRResult
from app.services.ocr import OCRProvider
from app.services.category.base import CategoryResult, CategoryProvider
from app.services.translation.base import TranslationResult, TranslationProvider
from app.services.description.base import DescriptionResult, DescriptionProvider


@pytest.fixture(scope="session")
def event_loop():
    """イベントループのフィクスチャ"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_menu_text():
    """サンプルメニューテキスト"""
    return """
    お寿司
    まぐろ 500円
    サーモン 450円
    
    飲み物
    ビール 400円
    日本酒 600円
    """


@pytest.fixture
def sample_categorized_menu():
    """サンプルカテゴリ分類済みメニュー"""
    return {
        "お寿司": [
            {"name": "まぐろ", "price": "500円"},
            {"name": "サーモン", "price": "450円"}
        ],
        "飲み物": [
            {"name": "ビール", "price": "400円"},
            {"name": "日本酒", "price": "600円"}
        ]
    }


@pytest.fixture
def sample_translated_menu():
    """サンプル翻訳済みメニュー"""
    return {
        "Sushi": [
            {
                "japanese_name": "まぐろ",
                "english_name": "Tuna",
                "price": "500円"
            },
            {
                "japanese_name": "サーモン", 
                "english_name": "Salmon",
                "price": "450円"
            }
        ],
        "Drinks": [
            {
                "japanese_name": "ビール",
                "english_name": "Beer", 
                "price": "400円"
            },
            {
                "japanese_name": "日本酒",
                "english_name": "Sake",
                "price": "600円"
            }
        ]
    }


@pytest.fixture
def sample_menu_with_descriptions():
    """サンプル説明付きメニュー"""
    return {
        "Sushi": [
            {
                "japanese_name": "まぐろ",
                "english_name": "Tuna",
                "price": "500円",
                "description": "Fresh tuna sashimi with rich flavor"
            },
            {
                "japanese_name": "サーモン",
                "english_name": "Salmon", 
                "price": "450円",
                "description": "Norwegian salmon with tender texture"
            }
        ],
        "Drinks": [
            {
                "japanese_name": "ビール",
                "english_name": "Beer",
                "price": "400円", 
                "description": "Crisp Japanese draft beer"
            },
            {
                "japanese_name": "日本酒",
                "english_name": "Sake",
                "price": "600円",
                "description": "Premium Japanese rice wine"
            }
        ]
    }


@pytest.fixture
def mock_ocr_service():
    """モックOCRサービス"""
    service = Mock()
    service.extract_text = AsyncMock(return_value=OCRResult(
        success=True,
        extracted_text="モックで抽出されたテキスト",
        provider=OCRProvider.GEMINI,
        metadata={"confidence": 0.95}
    ))
    return service


@pytest.fixture
def mock_category_service():
    """モックカテゴリサービス"""
    service = Mock()
    service.categorize_menu = AsyncMock(return_value=CategoryResult(
        success=True,
        categories={"メイン": ["料理1", "料理2"]},
        uncategorized=[],
        provider=CategoryProvider.OPENAI,
        metadata={"model": "gpt-4"}
    ))
    return service


@pytest.fixture
def mock_translation_service():
    """モック翻訳サービス"""
    service = Mock()
    service.translate_menu = AsyncMock(return_value=TranslationResult(
        success=True,
        translated_menu={"Main": [{"japanese_name": "料理1", "english_name": "Dish 1"}]},
        provider=TranslationProvider.GOOGLE_TRANSLATE,
        metadata={"language": "en"}
    ))
    return service


@pytest.fixture
def mock_description_service():
    """モック説明生成サービス"""
    service = Mock()
    service.add_descriptions = AsyncMock(return_value=DescriptionResult(
        success=True,
        menu_with_descriptions={"Main": [{"name": "Dish 1", "description": "Test description"}]},
        provider=DescriptionProvider.OPENAI,
        metadata={"model": "gpt-4"}
    ))
    return service


@pytest.fixture
def test_image_path(tmp_path):
    """テスト用画像パス"""
    # 簡単なテスト画像ファイルを作成
    image_path = tmp_path / "test_menu.jpg"
    image_path.write_bytes(b"fake image data")
    return str(image_path)


@pytest.fixture
def test_session_id():
    """テスト用セッションID"""
    return "test-session-12345"


@pytest.fixture
def mock_settings(monkeypatch):
    """モック設定"""
    test_settings = {
        "GEMINI_API_KEY": "test-gemini-key",
        "OPENAI_API_KEY": "test-openai-key",
        "GOOGLE_CREDENTIALS_JSON": '{"type":"service_account","project_id":"test-project"}',
        "USE_AWS_SECRETS_MANAGER": "false",
        "AWS_REGION": "us-east-1",
        "AWS_SECRET_NAME": "test/menu-sense/credentials",
        "APP_TITLE": "Test Menu Sensor",
        "APP_VERSION": "test",
        "DEBUG": True
    }
    
    for key, value in test_settings.items():
        monkeypatch.setenv(key, value)
        monkeypatch.setattr(settings, key, value)
    
    return test_settings


@pytest.fixture
def mock_file_upload():
    """モックファイルアップロード"""
    mock_file = Mock()
    mock_file.filename = "test_menu.jpg"
    mock_file.content_type = "image/jpeg"
    mock_file.file = Mock()
    mock_file.file.read = Mock(return_value=b"fake image data")
    return mock_file


# テスト用のエラーフィクスチャ
@pytest.fixture
def ocr_error_result():
    """OCRエラー結果"""
    return OCRResult(
        success=False,
        extracted_text="",
        provider=OCRProvider.GEMINI,
        error="API接続エラー",
        metadata={"error_code": "connection_error"}
    )


@pytest.fixture
def category_error_result():
    """カテゴリ分類エラー結果"""
    return CategoryResult(
        success=False,
        categories={},
        uncategorized=[],
        provider=CategoryProvider.OPENAI,
        error="APIキーが無効です",
        metadata={"error_code": "invalid_api_key"}
    )


# ===============================================
# 🗄️ Database Testing Fixtures (NEW)
# ===============================================

@pytest.fixture(scope="session")
def postgres_container():
    """Start PostgreSQL test container for database tests"""
    with PostgresContainer("postgres:15-alpine") as postgres:
        yield postgres

@pytest.fixture(scope="session") 
async def test_engine(postgres_container):
    """Create async engine for testing"""
    connection_url = postgres_container.get_connection_url().replace(
        "postgresql://", "postgresql+asyncpg://"
    )
    engine = create_async_engine(connection_url, echo=False)
    
    # Import models and create tables
    from app.core.database import Base
    from app.models.menu_translation import Session, MenuItem, ProcessingProvider, MenuItemImage, Category
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    await engine.dispose()

@pytest.fixture
async def db_session(test_engine):
    """Create clean database session for each test"""
    async_session = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.rollback()

@pytest.fixture
async def db_session_with_commit(test_engine):
    """Database session that commits changes (for integration tests)"""
    async_session = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        yield session
        await session.commit()

# テスト環境の検証
@pytest.fixture(autouse=True)
def verify_test_environment():
    """テスト環境の検証"""
    # Set testing environment variable
    os.environ["TESTING"] = "true"
    # テスト用の一時ディレクトリが存在することを確認
    os.makedirs("uploads", exist_ok=True)
    yield
    # テスト後のクリーンアップは必要に応じて 
"""
共通テストフィクスチャ・ユーティリティ
app_2の基盤コンポーネントテスト用
"""
import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

# テスト用YAMLコンテンツ
TEST_PROMPT_CONTENT = {
    "description": {
        "system": "You are a culinary expert.",
        "user": "Generate a description for: {menu_item}"
    },
    "allergen": {
        "system": "You are a nutritionist.",
        "user": "List allergens in: {menu_item}"
    }
}


@pytest.fixture
def temp_prompts_dir():
    """テスト用プロンプトディレクトリ"""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # OpenAI/menu_analysis ディレクトリ構造作成
        openai_dir = temp_path / "openai" / "menu_analysis"
        openai_dir.mkdir(parents=True)
        
        # テスト用YAMLファイル作成
        for prompt_name, content in TEST_PROMPT_CONTENT.items():
            yaml_file = openai_dir / f"{prompt_name}.yaml"
            with open(yaml_file, 'w', encoding='utf-8') as f:
                f.write(f"system: \"{content['system']}\"\n")
                f.write(f"user: \"{content['user']}\"\n")
        
        yield str(temp_path)


@pytest.fixture
def mock_settings():
    """テスト用設定モック"""
    settings_mock = Mock()
    
    # Base settings
    settings_mock.base.app_title = "Menu Processor Test"
    settings_mock.base.app_version = "2.0.0-test"
    settings_mock.base.debug_mode = True
    
    # AI settings
    settings_mock.ai.openai_api_key = "test-openai-key"
    settings_mock.ai.openai_model_name = "gpt-4-mini"
    settings_mock.ai.gemini_api_key = "test-google-key"  # Google API key用
    settings_mock.ai.google_search_engine_id = "test-search-id"
    
    # AWS settings
    settings_mock.aws.aws_access_key_id = "test-aws-key"
    settings_mock.aws.aws_secret_access_key = "test-aws-secret"
    settings_mock.aws.s3_bucket_name = "test-bucket"
    
    # Celery settings
    settings_mock.celery.redis_url = "redis://localhost:6379/1"
    
    return settings_mock


@pytest.fixture
def mock_openai_response():
    """OpenAI APIレスポンスモック"""
    response_mock = Mock()
    response_mock.choices = [Mock()]
    response_mock.choices[0].message.content = "Generated test content"
    return response_mock


@pytest.fixture
def mock_google_vision_response():
    """Google Vision APIレスポンスモック"""
    response_mock = Mock()
    text_annotation = Mock()
    text_annotation.description = "Extracted text from image"
    response_mock.text_annotations = [text_annotation]
    return response_mock


@pytest.fixture
def mock_google_translate_response():
    """Google Translate APIレスポンスモック"""
    return {
        'translatedText': 'Translated text result',
        'detectedSourceLanguage': 'en'
    }


@pytest.fixture
def sample_menu_entity():
    """テスト用MenuEntityサンプル"""
    from app_2.domain.entities.menu_entity import MenuEntity
    
    return MenuEntity(
        id="test-menu-001",
        name="Test Pizza",
        translation="テストピザ",
        description="Delicious test pizza",
        allergy="Contains wheat, dairy",
        ingredient="Flour, cheese, tomato",
        search_engine="[{'title': 'Pizza Image', 'link': 'http://example.com/pizza.jpg'}]",
        gen_image="http://example.com/generated-pizza.jpg"
    )


@pytest.fixture
def sample_incomplete_menu_entity():
    """テスト用不完全MenuEntity"""
    from app_2.domain.entities.menu_entity import MenuEntity
    
    return MenuEntity(
        id="test-menu-002",
        name="Incomplete Item",
        translation=""  # 不完全な状態
    )


class AsyncContextManager:
    """非同期コンテキストマネージャーのテスト用ヘルパー"""
    def __init__(self, return_value):
        self.return_value = return_value
    
    async def __aenter__(self):
        return self.return_value
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.fixture
def async_mock_session():
    """非同期セッションモック"""
    session_mock = AsyncMock()
    session_mock.__aenter__ = AsyncMock(return_value=session_mock)
    session_mock.__aexit__ = AsyncMock(return_value=None)
    return session_mock


# テストユーティリティ関数
def assert_no_external_calls():
    """外部API呼び出しがないことを確認するヘルパー"""
    pass  # 実際の実装では外部呼び出し監視


def create_test_image_data():
    """テスト用画像データ作成"""
    return b"fake_image_data_for_testing" 
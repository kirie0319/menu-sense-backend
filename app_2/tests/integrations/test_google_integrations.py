"""
Google API統合テスト
Vision/Translate/Search APIの統合確認（モック使用）
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from google.cloud import vision

from app_2.infrastructure.integrations.google.google_credential_manager import (
    GoogleCredentialManager, get_google_credential_manager
)
from app_2.infrastructure.integrations.google.google_vision_client import GoogleVisionClient
from app_2.infrastructure.integrations.google.google_translate_client import GoogleTranslateClient
from app_2.infrastructure.integrations.google.google_search_client import GoogleSearchClient


class TestGoogleCredentialManager:
    """Google認証マネージャーテスト"""
    
    @patch('app_2.infrastructure.integrations.google.google_credential_manager.settings')
    def test_init_with_settings(self, mock_settings):
        """設定値を使用した初期化テスト"""
        # 実際の設定構造に合わせてモック
        mock_settings.ai.gemini_api_key = "test-api-key"
        mock_settings.ai.google_search_engine_id = "test-engine-id"
        
        manager = GoogleCredentialManager()
        
        assert manager.api_key == "test-api-key"
        assert manager.search_engine_id == "test-engine-id"

    @patch('app_2.infrastructure.integrations.google.google_credential_manager.vision.ImageAnnotatorClient')
    @patch('app_2.infrastructure.integrations.google.google_credential_manager.settings')
    def test_get_vision_client(self, mock_settings, mock_vision_client):
        """Vision APIクライアント取得テスト"""
        mock_settings.ai.gemini_api_key = "test-key"
        mock_settings.ai.google_search_engine_id = "test-engine"
        
        manager = GoogleCredentialManager()
        client = manager.get_vision_client()
        
        assert client is not None
        mock_vision_client.assert_called_once()

    @patch('app_2.infrastructure.integrations.google.google_credential_manager.translate.Client')
    @patch('app_2.infrastructure.integrations.google.google_credential_manager.settings')
    def test_get_translate_client(self, mock_settings, mock_translate_client):
        """Translate APIクライアント取得テスト"""
        mock_settings.ai.gemini_api_key = "test-key"
        mock_settings.ai.google_search_engine_id = "test-engine"
        
        manager = GoogleCredentialManager()
        client = manager.get_translate_client()
        
        assert client is not None
        mock_translate_client.assert_called_once()

    @patch('app_2.infrastructure.integrations.google.google_credential_manager.build')
    @patch('app_2.infrastructure.integrations.google.google_credential_manager.settings')
    def test_get_search_service(self, mock_settings, mock_build):
        """検索サービス取得テスト"""
        mock_settings.ai.gemini_api_key = "test-api-key"
        mock_settings.ai.google_search_engine_id = "test-engine"
        
        manager = GoogleCredentialManager()
        service = manager.get_search_service()
        
        assert service is not None
        mock_build.assert_called_once_with("customsearch", "v1", developerKey="test-api-key")

    @patch('app_2.infrastructure.integrations.google.google_credential_manager.settings')
    def test_get_search_engine_id(self, mock_settings):
        """検索エンジンID取得テスト"""
        mock_settings.ai.gemini_api_key = "test-key"
        mock_settings.ai.google_search_engine_id = "test-engine-id"
        
        manager = GoogleCredentialManager()
        engine_id = manager.get_search_engine_id()
        
        assert engine_id == "test-engine-id"

    @patch('app_2.infrastructure.integrations.google.google_credential_manager.settings')
    def test_singleton_credential_manager(self, mock_settings):
        """認証マネージャーのシングルトンテスト"""
        mock_settings.ai.gemini_api_key = "test-api-key"
        mock_settings.ai.google_search_engine_id = "test-engine"
        
        manager1 = get_google_credential_manager()
        manager2 = get_google_credential_manager()
        
        # lru_cacheによってシングルトンになることを確認
        assert manager1 is manager2


class TestGoogleVisionClient:
    """Google Vision APIクライアントテスト"""
    
    @patch('app_2.infrastructure.integrations.google.google_vision_client.get_google_credential_manager')
    def test_init(self, mock_get_manager):
        """初期化テスト"""
        mock_manager = Mock()
        mock_vision_client = Mock()
        mock_manager.get_vision_client.return_value = mock_vision_client
        mock_get_manager.return_value = mock_manager
        
        client = GoogleVisionClient()
        
        # 実際の実装に合わせて、clientプロパティをテスト
        assert client.client is mock_vision_client
        mock_manager.get_vision_client.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_text_success(self):
        """テキスト抽出成功テスト"""
        # モックレスポンスの設定
        mock_response = Mock()
        mock_response.error.message = None
        mock_annotation = Mock()
        mock_annotation.description = "Test text\nSecond line"
        mock_response.text_annotations = [mock_annotation]
        
        # Vision APIクライアントのモック
        mock_vision_client = Mock()
        mock_vision_client.text_detection.return_value = mock_response
        
        with patch('app_2.infrastructure.integrations.google.google_vision_client.get_google_credential_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_manager.get_vision_client.return_value = mock_vision_client
            mock_get_manager.return_value = mock_manager
            
            client = GoogleVisionClient()
            result = await client.extract_text(b"fake_image_data")
            
            assert result == ["Test text", "Second line"]

    @pytest.mark.asyncio
    async def test_extract_text_no_text_found(self):
        """テキストが見つからない場合のテスト"""
        mock_response = Mock()
        mock_response.error.message = None
        mock_response.text_annotations = []
        
        mock_vision_client = Mock()
        mock_vision_client.text_detection.return_value = mock_response
        
        with patch('app_2.infrastructure.integrations.google.google_vision_client.get_google_credential_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_manager.get_vision_client.return_value = mock_vision_client
            mock_get_manager.return_value = mock_manager
            
            client = GoogleVisionClient()
            result = await client.extract_text(b"fake_image_data")
            
            assert result == []

    @pytest.mark.asyncio
    async def test_extract_text_api_error(self):
        """APIエラーのテスト"""
        mock_response = Mock()
        mock_response.error.message = "API Error occurred"
        
        mock_vision_client = Mock()
        mock_vision_client.text_detection.return_value = mock_response
        
        with patch('app_2.infrastructure.integrations.google.google_vision_client.get_google_credential_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_manager.get_vision_client.return_value = mock_vision_client
            mock_get_manager.return_value = mock_manager
            
            client = GoogleVisionClient()
            
            with pytest.raises(Exception, match="Vision API error: API Error occurred"):
                await client.extract_text(b"fake_image_data")


class TestGoogleTranslateClient:
    """Google Translate APIクライアントテスト"""
    
    @patch('app_2.infrastructure.integrations.google.google_translate_client.get_google_credential_manager')
    def test_init(self, mock_get_manager):
        """初期化テスト"""
        mock_manager = Mock()
        mock_translate_client = Mock()
        mock_manager.get_translate_client.return_value = mock_translate_client
        mock_get_manager.return_value = mock_manager
        
        client = GoogleTranslateClient()
        
        # 実際の実装に合わせて、clientプロパティをテスト
        assert client.client is mock_translate_client
        mock_manager.get_translate_client.assert_called_once()

    @pytest.mark.asyncio
    async def test_translate_success(self):
        """翻訳成功テスト"""
        mock_translate_client = Mock()
        mock_translate_client.translate.return_value = {'translatedText': '翻訳されたテキスト'}
        
        with patch('app_2.infrastructure.integrations.google.google_translate_client.get_google_credential_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_manager.get_translate_client.return_value = mock_translate_client
            mock_get_manager.return_value = mock_manager
            
            client = GoogleTranslateClient()
            result = await client.translate("Test text", "ja")
            
            assert result == "翻訳されたテキスト"
            mock_translate_client.translate.assert_called_once_with("Test text", target_language="ja")

    @pytest.mark.asyncio
    async def test_translate_list_success(self):
        """リスト翻訳成功テスト"""
        mock_translate_client = Mock()
        mock_translate_client.translate.side_effect = [
            {'translatedText': 'テキスト1'},
            {'translatedText': 'テキスト2'}
        ]
        
        with patch('app_2.infrastructure.integrations.google.google_translate_client.get_google_credential_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_manager.get_translate_client.return_value = mock_translate_client
            mock_get_manager.return_value = mock_manager
            
            client = GoogleTranslateClient()
            result = await client.translate_list(["Text 1", "Text 2"], "ja")
            
            assert result == ["テキスト1", "テキスト2"]

    @pytest.mark.asyncio
    async def test_translate_api_error(self):
        """翻訳APIエラーテスト"""
        mock_translate_client = Mock()
        mock_translate_client.translate.side_effect = Exception("Translation API error")
        
        with patch('app_2.infrastructure.integrations.google.google_translate_client.get_google_credential_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_manager.get_translate_client.return_value = mock_translate_client
            mock_get_manager.return_value = mock_manager
            
            client = GoogleTranslateClient()
            
            with pytest.raises(Exception, match="Translation API error"):
                await client.translate("Test text", "ja")


class TestGoogleSearchClient:
    """Google検索クライアントテスト"""
    
    @patch('app_2.infrastructure.integrations.google.google_search_client.get_google_credential_manager')
    def test_init(self, mock_get_manager):
        """初期化テスト"""
        mock_manager = Mock()
        mock_search_service = Mock()
        mock_manager.get_search_service.return_value = mock_search_service
        mock_manager.get_search_engine_id.return_value = "test-engine-id"
        mock_get_manager.return_value = mock_manager
        
        client = GoogleSearchClient()
        
        # 実際の実装に合わせて、serviceプロパティをテスト
        assert client.service is mock_search_service
        assert client.search_engine_id == "test-engine-id"
        mock_manager.get_search_service.assert_called_once()
        mock_manager.get_search_engine_id.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_images_success(self):
        """画像検索成功テスト"""
        mock_result = {
            'items': [
                {
                    'title': 'Test Image 1',
                    'link': 'https://example.com/image1.jpg',
                    'image': {'thumbnailLink': 'https://example.com/thumb1.jpg'}
                },
                {
                    'title': 'Test Image 2', 
                    'link': 'https://example.com/image2.jpg',
                    'image': {'thumbnailLink': 'https://example.com/thumb2.jpg'}
                }
            ]
        }
        
        mock_cse = Mock()
        mock_cse.list.return_value.execute.return_value = mock_result
        mock_service = Mock()
        mock_service.cse.return_value = mock_cse
        
        with patch('app_2.infrastructure.integrations.google.google_search_client.get_google_credential_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_manager.get_search_service.return_value = mock_service
            mock_manager.get_search_engine_id.return_value = "test-engine-id"
            mock_get_manager.return_value = mock_manager
            
            client = GoogleSearchClient()
            result = await client.search_images("pizza", 5)
            
            expected = [
                {
                    'title': 'Test Image 1',
                    'link': 'https://example.com/image1.jpg',
                    'thumbnail': 'https://example.com/thumb1.jpg'
                },
                {
                    'title': 'Test Image 2',
                    'link': 'https://example.com/image2.jpg', 
                    'thumbnail': 'https://example.com/thumb2.jpg'
                }
            ]
            assert result == expected

    @pytest.mark.asyncio
    async def test_search_images_no_results(self):
        """検索結果なしのテスト"""
        mock_result = {}
        
        mock_cse = Mock()
        mock_cse.list.return_value.execute.return_value = mock_result
        mock_service = Mock()
        mock_service.cse.return_value = mock_cse
        
        with patch('app_2.infrastructure.integrations.google.google_search_client.get_google_credential_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_manager.get_search_service.return_value = mock_service
            mock_manager.get_search_engine_id.return_value = "test-engine-id"
            mock_get_manager.return_value = mock_manager
            
            client = GoogleSearchClient()
            result = await client.search_images("nonexistent", 5)
            
            assert result == []

    @pytest.mark.asyncio
    async def test_search_images_api_error(self):
        """検索APIエラーテスト"""
        mock_cse = Mock()
        mock_cse.list.return_value.execute.side_effect = Exception("Search API error")
        mock_service = Mock()
        mock_service.cse.return_value = mock_cse
        
        with patch('app_2.infrastructure.integrations.google.google_search_client.get_google_credential_manager') as mock_get_manager:
            mock_manager = Mock()
            mock_manager.get_search_service.return_value = mock_service
            mock_manager.get_search_engine_id.return_value = "test-engine-id"
            mock_get_manager.return_value = mock_manager
            
            client = GoogleSearchClient()
            
            with pytest.raises(Exception, match="Search API error"):
                await client.search_images("pizza", 5) 
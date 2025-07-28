"""
Google Vision Client Retry Logic Tests
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from google.cloud import vision
from google.api_core import exceptions as google_exceptions

from app_2.infrastructure.integrations.google.google_vision_client import GoogleVisionClient
from app_2.infrastructure.integrations.google.google_credential_manager import GoogleCredentialManager
from app_2.services.ocr_service import OCRService


class TestGoogleVisionClientRetry:
    """Google Vision Clientのリトライロジックをテストする"""

    @pytest.mark.asyncio
    async def test_goaway_error_retry_success(self):
        """GOAWAY エラー時のリトライが成功する場合のテスト"""
        # モック設定
        mock_credential_manager = Mock(spec=GoogleCredentialManager)
        mock_vision_client_1 = Mock()
        mock_vision_client_2 = Mock()
        
        # 1回目: GOAWAY エラー
        mock_response_error = Mock()
        mock_response_error.error.message = None
        mock_vision_client_1.document_text_detection.side_effect = Exception("503 GOAWAY received; Error code: 0; Debug Text: session_timed_out")
        
        # 2回目: 成功
        mock_response_success = Mock()
        mock_response_success.error.message = None
        mock_response_success.full_text_annotation = None
        mock_vision_client_2.document_text_detection.return_value = mock_response_success
        
        # get_vision_client の呼び出し回数に応じて異なるクライアントを返す
        mock_credential_manager.get_vision_client.side_effect = [mock_vision_client_1, mock_vision_client_2]
        mock_credential_manager.reset_vision_client = Mock()
        
        # テスト実行
        client = GoogleVisionClient()
        client.credential_manager = mock_credential_manager
        client.client = mock_vision_client_1
        
        result = await client.extract_text_with_positions(b"fake_image_data", level="paragraph", max_retries=2)
        
        # 検証
        assert result == []
        assert mock_credential_manager.reset_vision_client.called
        assert mock_credential_manager.get_vision_client.call_count == 1

    @pytest.mark.asyncio
    async def test_goaway_error_max_retries_exceeded(self):
        """GOAWAY エラーが最大リトライ回数を超える場合のテスト"""
        # モック設定
        mock_credential_manager = Mock(spec=GoogleCredentialManager)
        mock_vision_client = Mock()
        
        # 常にGOAWAY エラー
        mock_vision_client.document_text_detection.side_effect = Exception("503 GOAWAY received; Error code: 0; Debug Text: session_timed_out")
        mock_credential_manager.get_vision_client.return_value = mock_vision_client
        mock_credential_manager.reset_vision_client = Mock()
        
        # テスト実行
        client = GoogleVisionClient()
        client.credential_manager = mock_credential_manager
        client.client = mock_vision_client
        
        # 例外が発生することを確認
        with pytest.raises(Exception, match="Vision API error after 3 attempts"):
            await client.extract_text_with_positions(b"fake_image_data", level="paragraph", max_retries=2)
        
        # リセットが適切に呼ばれることを確認
        assert mock_credential_manager.reset_vision_client.call_count == 2

    @pytest.mark.asyncio
    async def test_other_error_retry(self):
        """その他のエラー（Rate Limit等）のリトライテスト"""
        # モック設定
        mock_credential_manager = Mock(spec=GoogleCredentialManager)
        mock_vision_client_1 = Mock()
        mock_vision_client_2 = Mock()
        
        # 1回目: Rate Limit エラー
        mock_vision_client_1.document_text_detection.side_effect = Exception("Rate limit exceeded")
        
        # 2回目: 成功
        mock_response_success = Mock()
        mock_response_success.error.message = None
        mock_response_success.full_text_annotation = None
        mock_vision_client_2.document_text_detection.return_value = mock_response_success
        
        mock_credential_manager.get_vision_client.side_effect = [mock_vision_client_1, mock_vision_client_2]
        mock_credential_manager.reset_vision_client = Mock()
        
        # テスト実行
        client = GoogleVisionClient()
        client.credential_manager = mock_credential_manager
        client.client = mock_vision_client_1
        
        result = await client.extract_text_with_positions(b"fake_image_data", level="paragraph", max_retries=2)
        
        # 検証: Rate Limitエラーではクライアントリセットは呼ばれない
        assert result == []
        assert not mock_credential_manager.reset_vision_client.called

    @pytest.mark.asyncio
    async def test_successful_first_attempt(self):
        """1回目で成功する場合のテスト"""
        # モック設定
        mock_credential_manager = Mock(spec=GoogleCredentialManager)
        mock_vision_client = Mock()
        
        mock_response = Mock()
        mock_response.error.message = None
        mock_response.full_text_annotation = None
        mock_vision_client.document_text_detection.return_value = mock_response
        
        mock_credential_manager.get_vision_client.return_value = mock_vision_client
        mock_credential_manager.reset_vision_client = Mock()
        
        # テスト実行
        client = GoogleVisionClient()
        client.credential_manager = mock_credential_manager
        client.client = mock_vision_client
        
        result = await client.extract_text_with_positions(b"fake_image_data", level="paragraph", max_retries=2)
        
        # 検証: リトライなしで成功
        assert result == []
        assert not mock_credential_manager.reset_vision_client.called
        assert mock_vision_client.document_text_detection.call_count == 1


class TestOCRServiceRetry:
    """OCR Serviceのリトライ機能をテストする"""

    @pytest.mark.asyncio
    async def test_ocr_service_with_retry_parameters(self):
        """OCRサービスがリトライパラメータを正しく渡すことのテスト"""
        # モック設定
        mock_vision_client = Mock(spec=GoogleVisionClient)
        mock_vision_client.extract_text_with_positions = AsyncMock(return_value=[])
        
        # テスト実行
        ocr_service = OCRService(vision_client=mock_vision_client)
        result = await ocr_service.extract_text_with_positions(
            image_data=b"fake_image_data",
            level="paragraph",
            max_retries=3
        )
        
        # 検証
        assert result == []
        mock_vision_client.extract_text_with_positions.assert_called_once_with(
            image_data=b"fake_image_data",
            level="paragraph",
            max_retries=3
        )

    @pytest.mark.asyncio
    async def test_ocr_service_error_handling(self):
        """OCRサービスのエラーハンドリングテスト"""
        # モック設定
        mock_vision_client = Mock(spec=GoogleVisionClient)
        mock_vision_client.extract_text_with_positions = AsyncMock(
            side_effect=Exception("Vision API failed after retries")
        )
        
        # テスト実行
        ocr_service = OCRService(vision_client=mock_vision_client)
        
        with pytest.raises(Exception, match="OCR processing failed"):
            await ocr_service.extract_text_with_positions(
                image_data=b"fake_image_data",
                level="paragraph",
                max_retries=2
            )


class TestGoogleCredentialManagerReset:
    """Google Credential Managerのリセット機能をテストする"""

    def test_reset_vision_client(self):
        """Vision クライアントリセット機能のテスト"""
        with patch('app_2.infrastructure.integrations.google.google_credential_manager.vision.ImageAnnotatorClient') as mock_client_class:
            mock_client_instance = Mock()
            mock_client_instance.close = Mock()
            mock_client_class.return_value = mock_client_instance
            
            # テスト実行
            manager = GoogleCredentialManager()
            
            # 最初にクライアントを作成
            client1 = manager.get_vision_client()
            assert client1 == mock_client_instance
            
            # リセット
            manager.reset_vision_client()
            
            # 新しいクライアントが作成されることを確認
            client2 = manager.get_vision_client()
            assert client2 == mock_client_instance
            assert mock_client_class.call_count == 2  # 2回作成された 
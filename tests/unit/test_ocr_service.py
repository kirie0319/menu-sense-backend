"""
OCRサービスのユニットテスト
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
import asyncio

from app.services.ocr import extract_text, get_ocr_service_status
from app.services.ocr.base import OCRResult, OCRProvider
from app.services.ocr.gemini import GeminiOCRService
from app.services.ocr.google_vision import GoogleVisionOCRService


@pytest.mark.unit
@pytest.mark.ocr
class TestOCRService:
    """OCRサービスのテスト"""

    @pytest.mark.asyncio
    async def test_extract_text_success(self, test_image_path, test_session_id):
        """テキスト抽出の成功ケース"""
        with patch('app.services.ocr.ocr_manager.extract_text') as mock_extract:
            # モックの戻り値を設定
            mock_extract.return_value = OCRResult(
                success=True,
                extracted_text="サンプルメニュー\n唐揚げ 800円\nライス 200円",
                provider=OCRProvider.GEMINI,
                metadata={"confidence": 0.95, "processing_time": 2.5}
            )
            
            result = await extract_text(test_image_path, test_session_id)
            
            assert result.success is True
            assert "唐揚げ" in result.extracted_text
            assert result.provider == OCRProvider.GEMINI
            assert result.metadata["confidence"] == 0.95
            mock_extract.assert_called_once_with(test_image_path, test_session_id)

    @pytest.mark.asyncio
    async def test_extract_text_failure(self, test_image_path, test_session_id):
        """テキスト抽出の失敗ケース"""
        with patch('app.services.ocr.ocr_manager.extract_text') as mock_extract:
            # エラーケースのモック
            mock_extract.return_value = OCRResult(
                success=False,
                extracted_text="",
                provider=OCRProvider.GEMINI,
                error="API接続エラー",
                metadata={"error_code": "connection_timeout"}
            )
            
            result = await extract_text(test_image_path, test_session_id)
            
            assert result.success is False
            assert result.error == "API接続エラー"
            assert result.extracted_text == ""
            assert result.metadata["error_code"] == "connection_timeout"

    @pytest.mark.asyncio
    async def test_get_ocr_service_status(self):
        """OCRサービスのステータス取得テスト"""
        with patch('app.services.ocr.ocr_manager.get_service_status') as mock_status:
            mock_status.return_value = {
                "available_services": ["gemini", "google_vision"],
                "default_service": "gemini",
                "health": "healthy"
            }
            
            status = await get_ocr_service_status()
            
            assert "gemini" in status["available_services"]
            assert status["default_service"] == "gemini"
            assert status["health"] == "healthy"


@pytest.mark.unit
@pytest.mark.ocr
class TestGeminiOCRService:
    """Gemini OCRサービスのテスト"""

    def setup_method(self):
        """テストセットアップ"""
        self.service = GeminiOCRService()

    @pytest.mark.asyncio
    async def test_extract_text_with_mock(self, test_image_path, test_session_id):
        """Gemini APIをモックしたテキスト抽出テスト"""
        with patch('google.generativeai.GenerativeModel') as mock_model_class:
            # モックの設定
            mock_model = Mock()
            mock_response = Mock()
            mock_response.text = "抽出されたメニューテキスト\n唐揚げ定食 950円"
            mock_model.generate_content = AsyncMock(return_value=mock_response)
            mock_model_class.return_value = mock_model
            
            # APIキーのモック
            with patch('google.generativeai.configure'):
                result = await self.service.extract_text(test_image_path, test_session_id)
                
                assert result.success is True
                assert "唐揚げ定食" in result.extracted_text
                assert result.provider == OCRProvider.GEMINI

    @pytest.mark.asyncio
    async def test_extract_text_api_error(self, test_image_path, test_session_id):
        """Gemini API エラーのテスト"""
        with patch('google.generativeai.GenerativeModel') as mock_model_class:
            # API エラーのモック
            mock_model = Mock()
            mock_model.generate_content = AsyncMock(side_effect=Exception("API エラー"))
            mock_model_class.return_value = mock_model
            
            with patch('google.generativeai.configure'):
                result = await self.service.extract_text(test_image_path, test_session_id)
                
                assert result.success is False
                assert "API エラー" in result.error
                assert result.extracted_text == ""

    def test_create_ocr_prompt(self):
        """OCR プロンプト作成のテスト"""
        prompt = self.service._create_ocr_prompt()
        
        assert "メニュー" in prompt
        assert "テキスト" in prompt
        assert "抽出" in prompt

    @pytest.mark.asyncio
    async def test_validate_image_file(self, test_image_path):
        """画像ファイル検証のテスト"""
        # 正常な場合
        is_valid = await self.service._validate_image_file(test_image_path)
        assert is_valid is True
        
        # 存在しないファイル
        is_valid = await self.service._validate_image_file("nonexistent.jpg")
        assert is_valid is False


@pytest.mark.unit 
@pytest.mark.ocr
class TestGoogleVisionOCRService:
    """Google Vision OCRサービスのテスト"""

    def setup_method(self):
        """テストセットアップ"""
        self.service = GoogleVisionOCRService()

    @pytest.mark.asyncio
    async def test_extract_text_with_mock(self, test_image_path, test_session_id):
        """Google Vision APIをモックしたテキスト抽出テスト"""
        with patch('google.cloud.vision.ImageAnnotatorClient') as mock_client_class:
            # モックの設定
            mock_client = Mock()
            mock_response = Mock()
            mock_annotation = Mock()
            mock_annotation.description = "Google Vision で抽出されたテキスト\n天ぷら定食 1200円"
            mock_response.text_annotations = [mock_annotation]
            mock_response.error.message = ""
            mock_client.text_detection = Mock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            result = await self.service.extract_text(test_image_path, test_session_id)
            
            assert result.success is True
            assert "天ぷら定食" in result.extracted_text
            assert result.provider == OCRProvider.GOOGLE_VISION

    @pytest.mark.asyncio
    async def test_extract_text_no_text_found(self, test_image_path, test_session_id):
        """テキストが見つからない場合のテスト"""
        with patch('google.cloud.vision.ImageAnnotatorClient') as mock_client_class:
            # テキストなしのモック
            mock_client = Mock()
            mock_response = Mock()
            mock_response.text_annotations = []
            mock_response.error.message = ""
            mock_client.text_detection = Mock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            result = await self.service.extract_text(test_image_path, test_session_id)
            
            assert result.success is False
            assert "テキストが検出されませんでした" in result.error

    @pytest.mark.asyncio 
    async def test_extract_text_api_error(self, test_image_path, test_session_id):
        """Google Vision API エラーのテスト"""
        with patch('google.cloud.vision.ImageAnnotatorClient') as mock_client_class:
            # API エラーのモック
            mock_client = Mock()
            mock_response = Mock()
            mock_response.error.message = "Invalid API key"
            mock_client.text_detection = Mock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            result = await self.service.extract_text(test_image_path, test_session_id)
            
            assert result.success is False
            assert "Invalid API key" in result.error


@pytest.mark.unit
@pytest.mark.ocr
class TestOCRResult:
    """OCRResult データクラスのテスト"""

    def test_successful_result_creation(self):
        """成功結果の作成テスト"""
        result = OCRResult(
            success=True,
            extracted_text="テストテキスト",
            provider=OCRProvider.GEMINI,
            metadata={"confidence": 0.9}
        )
        
        assert result.success is True
        assert result.extracted_text == "テストテキスト"
        assert result.provider == OCRProvider.GEMINI
        assert result.error is None
        assert result.metadata["confidence"] == 0.9

    def test_error_result_creation(self):
        """エラー結果の作成テスト"""
        result = OCRResult(
            success=False,
            extracted_text="",
            provider=OCRProvider.GEMINI,
            error="テストエラー",
            metadata={"error_code": "test_error"}
        )
        
        assert result.success is False
        assert result.extracted_text == ""
        assert result.error == "テストエラー"
        assert result.metadata["error_code"] == "test_error"

    def test_result_to_dict(self):
        """結果の辞書変換テスト"""
        result = OCRResult(
            success=True,
            extracted_text="辞書テスト",
            provider=OCRProvider.GEMINI
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["success"] is True
        assert result_dict["extracted_text"] == "辞書テスト"
        assert result_dict["provider"] == "gemini"


# パフォーマンステスト
@pytest.mark.unit
@pytest.mark.ocr
@pytest.mark.slow
class TestOCRPerformance:
    """OCR パフォーマンステスト"""

    @pytest.mark.asyncio
    async def test_concurrent_ocr_requests(self, test_image_path):
        """並行OCRリクエストのテスト"""
        with patch('app.services.ocr.ocr_manager.extract_text') as mock_extract:
            # 高速なモックレスポンス
            mock_extract.return_value = OCRResult(
                success=True,
                extracted_text="並行テスト",
                provider=OCRProvider.GEMINI
            )
            
            # 複数の並行リクエスト
            tasks = []
            for i in range(5):
                task = extract_text(test_image_path, f"session-{i}")
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            
            assert len(results) == 5
            for result in results:
                assert result.success is True
                assert result.extracted_text == "並行テスト" 
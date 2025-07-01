"""
改良版サービスの包括的テストスイート
BaseResult, BaseService, EnhancedOCRService の全機能をテスト
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
import asyncio

from app.services.base import BaseResult, BaseService
from app.services.ocr.enhanced import EnhancedOCRService, EnhancedOCRResult


# テスト用の具体的なサービス実装
class MockEnhancedService(BaseService):
    def is_available(self) -> bool:
        return True
    
    def get_capabilities(self) -> list:
        return ["test_capability", "mock_feature"]


class TestEnhancedOCRService(EnhancedOCRService):
    def is_available(self) -> bool:
        return True
    
    async def _perform_extraction(self, image_path: str, session_id=None) -> EnhancedOCRResult:
        return self._create_success_result(
            EnhancedOCRResult,
            extracted_text=f"Mock extraction from {image_path}"
        )


@pytest.mark.unit
class TestBaseResult:
    """BaseResult の包括的テスト"""

    def test_base_result_creation_success(self):
        """BaseResult 正常作成テスト"""
        result = BaseResult(success=True, metadata={"test": "value"})
        
        assert result.success is True
        assert result.error is None
        assert result.metadata["test"] == "value"

    def test_add_metadata(self):
        """メタデータ追加機能テスト"""
        result = BaseResult(success=True)
        
        result.add_metadata("key1", "value1")
        result.add_metadata("key2", {"nested": "value"})
        
        assert result.metadata["key1"] == "value1"
        assert result.metadata["key2"]["nested"] == "value"

    def test_is_success(self):
        """成功判定メソッドテスト"""
        success_result = BaseResult(success=True)
        assert success_result.is_success() is True
        
        fail_result = BaseResult(success=False)
        assert fail_result.is_success() is False
        
        error_result = BaseResult(success=True, error="Some error")
        assert error_result.is_success() is False

    def test_to_dict(self):
        """辞書変換メソッドテスト"""
        result = BaseResult(
            success=True,
            metadata={"key1": "value1", "key2": "value2"}
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["success"] is True
        assert result_dict["key1"] == "value1"
        assert result_dict["key2"] == "value2"


@pytest.mark.unit
class TestBaseService:
    """BaseService の包括的テスト"""

    def setup_method(self):
        """テストセットアップ"""
        self.service = MockEnhancedService()

    def test_service_initialization(self):
        """サービス初期化テスト"""
        assert self.service.service_name == "MockEnhancedService"
        assert self.service.provider is None

    def test_get_service_info(self):
        """サービス情報取得テスト"""
        service_info = self.service.get_service_info()
        
        assert service_info["service_name"] == "MockEnhancedService"
        assert service_info["available"] is True
        assert service_info["version"] == "1.0.0"
        assert "test_capability" in service_info["capabilities"]

    def test_create_error_result(self):
        """エラー結果作成テスト"""
        error_result = self.service._create_error_result(
            "Test error message",
            BaseResult,
            error_type="test_error",
            suggestions=["suggestion1", "suggestion2"]
        )
        
        assert error_result.success is False
        assert error_result.error == "Test error message"
        assert error_result.metadata["error_type"] == "test_error"
        assert error_result.metadata["suggestions"] == ["suggestion1", "suggestion2"]


@pytest.mark.unit
class TestEnhancedOCRResult:
    """EnhancedOCRResult の包括的テスト"""

    def test_enhanced_ocr_result_creation(self):
        """EnhancedOCRResult 作成テスト"""
        result = EnhancedOCRResult(
            success=True,
            extracted_text="Test menu text"
        )
        
        assert result.success is True
        assert result.extracted_text == "Test menu text"
        assert isinstance(result, BaseResult)

    def test_enhanced_ocr_result_to_dict(self):
        """EnhancedOCRResult 辞書変換テスト"""
        result = EnhancedOCRResult(
            success=True,
            extracted_text="Menu: Sushi ¥1200",
            metadata={"confidence": 0.95}
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["success"] is True
        assert result_dict["extracted_text"] == "Menu: Sushi ¥1200"
        assert result_dict["confidence"] == 0.95


@pytest.mark.unit
class TestEnhancedOCRServiceUnit:
    """EnhancedOCRService の包括的テスト"""

    def setup_method(self):
        """テストセットアップ"""
        self.service = TestEnhancedOCRService()

    def test_service_initialization(self):
        """サービス初期化テスト"""
        assert self.service.service_name == "TestEnhancedOCRService"
        assert self.service.is_available() is True

    def test_get_capabilities(self):
        """機能一覧取得テスト"""
        capabilities = self.service.get_capabilities()
        
        expected_capabilities = [
            "text_extraction",
            "image_processing", 
            "japanese_text_recognition",
            "menu_text_parsing"
        ]
        
        for capability in expected_capabilities:
            assert capability in capabilities

    @pytest.mark.asyncio
    async def test_extract_text_validation_error(self):
        """テキスト抽出バリデーションエラーテスト"""
        result = await self.service.extract_text("", "test_session")
        
        assert result.success is False
        assert result.metadata["error_type"] == "validation_error"
        assert "Invalid image path" in result.error

    @pytest.mark.asyncio 
    async def test_extract_text_file_error(self):
        """テキスト抽出ファイルエラーテスト"""
        result = await self.service.extract_text("/nonexistent/file.jpg", "test_session")
        
        assert result.success is False
        assert result.metadata["error_type"] == "file_error"
        assert "Image file validation failed" in result.error

    def test_create_compatible_result(self):
        """既存OCRResultとの互換性結果作成テスト"""
        enhanced_result = EnhancedOCRResult(
            success=True,
            extracted_text="Compatible test text",
            metadata={"test": "value"}
        )
        
        compatible_result = self.service.create_compatible_result(enhanced_result)
        
        assert hasattr(compatible_result, 'success')
        assert hasattr(compatible_result, 'extracted_text')
        assert compatible_result.success is True
        assert compatible_result.extracted_text == "Compatible test text" 
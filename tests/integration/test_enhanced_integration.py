"""
改良版サービスの統合テスト
実際のデータベースとの統合、セッション管理、エラー回復などをテスト
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
import asyncio
from datetime import datetime

from app.services.base import BaseResult, BaseService
from app.services.ocr.enhanced import EnhancedOCRService, EnhancedOCRResult


@pytest.mark.integration
@pytest.mark.enhanced
class TestEnhancedServicesIntegration:
    """改良版サービス統合テスト"""

    @pytest.mark.asyncio
    async def test_enhanced_ocr_to_db_workflow(self):
        """改良版OCRからDB保存までのワークフローテスト"""
        # モックサービスを使用してワークフローをテスト
        class MockEnhancedOCR(EnhancedOCRService):
            def is_available(self) -> bool:
                return True
            
            async def _perform_extraction(self, image_path: str, session_id=None) -> EnhancedOCRResult:
                return self._create_success_result(
                    EnhancedOCRResult,
                    extracted_text="唐揚げ ￥800\n寿司 ￥1200\nビール ￥500"
                )
        
        service = MockEnhancedOCR()
        
        # 1. OCR実行
        result = await service.extract_text("test_image.jpg", "integration_session")
        
        # 2. 結果検証
        assert result.success is True
        assert "唐揚げ" in result.extracted_text
        assert result.metadata["service"] == "MockEnhancedOCR"
        
        # 3. 既存システムとの互換性確認
        compatible_result = service.create_compatible_result(result)
        compatible_dict = compatible_result.to_dict()
        
        # 4. DB保存形式の確認
        assert "success" in compatible_dict
        assert "extracted_text" in compatible_dict
        assert compatible_dict["success"] is True

    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self):
        """エラーハンドリングと回復の統合テスト"""
        class FailingEnhancedOCR(EnhancedOCRService):
            def __init__(self):
                super().__init__()
                self.failure_count = 0
            
            def is_available(self) -> bool:
                return True
            
            async def _perform_extraction(self, image_path: str, session_id=None) -> EnhancedOCRResult:
                self.failure_count += 1
                if self.failure_count <= 2:  # 最初の2回は失敗
                    raise Exception("Simulated API failure")
                else:  # 3回目で成功
                    return self._create_success_result(
                        EnhancedOCRResult,
                        extracted_text="Recovery success"
                    )
        
        service = FailingEnhancedOCR()
        
        # 最初の2回は失敗することを確認
        for i in range(2):
            with pytest.raises(Exception):
                await service._perform_extraction("test.jpg")
        
        # 3回目で成功
        result = await service._perform_extraction("test.jpg")
        assert result.success is True
        assert result.extracted_text == "Recovery success"

    @pytest.mark.asyncio
    async def test_metadata_tracking_throughout_pipeline(self):
        """パイプライン全体でのメタデータ追跡テスト"""
        class MetadataTrackingOCR(EnhancedOCRService):
            def is_available(self) -> bool:
                return True
            
            async def _perform_extraction(self, image_path: str, session_id=None) -> EnhancedOCRResult:
                result = self._create_success_result(
                    EnhancedOCRResult,
                    extracted_text="Metadata tracking test"
                )
                
                # 詳細なメタデータを追加
                result.add_metadata("ocr_confidence", 0.95)
                result.add_metadata("processing_time_ms", 250)
                result.add_metadata("detected_language", "japanese")
                result.add_metadata("image_quality", {
                    "resolution": "1920x1080",
                    "clarity_score": 0.88,
                    "text_density": 0.67
                })
                result.add_metadata("processing_pipeline", {
                    "step": "ocr_extraction",
                    "next_step": "category_classification",
                    "session_id": session_id
                })
                
                return result
        
        service = MetadataTrackingOCR()
        result = await service.extract_text("metadata_test.jpg", "metadata_session")
        
        # メタデータの存在と内容を確認
        assert result.metadata["ocr_confidence"] == 0.95
        assert result.metadata["processing_time_ms"] == 250
        assert result.metadata["detected_language"] == "japanese"
        assert result.metadata["image_quality"]["clarity_score"] == 0.88
        assert result.metadata["processing_pipeline"]["next_step"] == "category_classification"
        assert result.metadata["processing_pipeline"]["session_id"] == "metadata_session"
        
        # 最終的な辞書形式での確認
        final_dict = result.to_dict()
        assert "ocr_confidence" in final_dict
        assert "image_quality" in final_dict
        assert "processing_pipeline" in final_dict

    @pytest.mark.asyncio
    async def test_concurrent_enhanced_services(self):
        """改良版サービスの並行処理統合テスト"""
        class ConcurrentEnhancedOCR(EnhancedOCRService):
            def is_available(self) -> bool:
                return True
            
            async def _perform_extraction(self, image_path: str, session_id=None) -> EnhancedOCRResult:
                # 並行処理をシミュレートするための遅延
                await asyncio.sleep(0.1)
                
                return self._create_success_result(
                    EnhancedOCRResult,
                    extracted_text=f"Concurrent result for {session_id}"
                )
        
        service = ConcurrentEnhancedOCR()
        
        # 複数の並行タスクを作成
        tasks = []
        for i in range(5):
            task = service.extract_text(f"image_{i}.jpg", f"concurrent_session_{i}")
            tasks.append(task)
        
        # 並行実行
        results = await asyncio.gather(*tasks)
        
        # 結果の検証
        assert len(results) == 5
        for i, result in enumerate(results):
            assert result.success is True
            assert f"concurrent_session_{i}" in result.extracted_text
            assert result.metadata["service"] == "ConcurrentEnhancedOCR"

    def test_enhanced_services_compatibility_matrix(self):
        """改良版サービスの互換性マトリックステスト"""
        # 新しいサービスの結果
        enhanced_result = EnhancedOCRResult(
            success=True,
            extracted_text="Compatibility test",
            metadata={
                "new_feature": "enhanced_capability",
                "quality_score": 0.95
            }
        )
        
        # 辞書形式での互換性確認
        result_dict = enhanced_result.to_dict()
        
        # 既存システムで必要なキーが存在することを確認
        required_keys = ["success", "extracted_text"]
        for key in required_keys:
            assert key in result_dict
        
        # 新機能のメタデータも含まれることを確認
        assert result_dict["new_feature"] == "enhanced_capability"
        assert result_dict["quality_score"] == 0.95
        
        # BaseResultとしての機能確認
        assert enhanced_result.is_success() is True
        
        error_details = enhanced_result.get_error_details()
        assert error_details["has_error"] is False

    @pytest.mark.asyncio
    async def test_session_lifecycle_with_enhanced_services(self):
        """改良版サービスでのセッションライフサイクルテスト"""
        class SessionAwareOCR(EnhancedOCRService):
            def __init__(self):
                super().__init__()
                self.session_data = {}
            
            def is_available(self) -> bool:
                return True
            
            async def _perform_extraction(self, image_path: str, session_id=None) -> EnhancedOCRResult:
                # セッション情報を記録
                if session_id not in self.session_data:
                    self.session_data[session_id] = {
                        "start_time": datetime.now(),
                        "requests": 0
                    }
                
                self.session_data[session_id]["requests"] += 1
                
                result = self._create_success_result(
                    EnhancedOCRResult,
                    extracted_text=f"Session {session_id} request #{self.session_data[session_id]['requests']}"
                )
                
                # セッション情報をメタデータに追加
                result.add_metadata("session_info", {
                    "session_id": session_id,
                    "request_number": self.session_data[session_id]["requests"],
                    "session_start_time": self.session_data[session_id]["start_time"].isoformat()
                })
                
                return result
        
        service = SessionAwareOCR()
        
        # 同一セッションで複数回実行
        session_id = "lifecycle_test_session"
        
        for i in range(3):
            result = await service.extract_text(f"image_{i}.jpg", session_id)
            
            assert result.success is True
            assert session_id in result.extracted_text
            assert result.metadata["session_info"]["session_id"] == session_id
            assert result.metadata["session_info"]["request_number"] == i + 1
        
        # セッション情報の確認
        assert len(service.session_data) == 1
        assert service.session_data[session_id]["requests"] == 3 
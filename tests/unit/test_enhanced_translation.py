"""
Enhanced Translation Service - 包括的テストスイート

新機能のテスト:
- 翻訳品質指標（カバレッジ、文化的適応度、一貫性）
- エラーハンドリング
- パフォーマンス測定
- 既存システムとの互換性
"""
import pytest
import asyncio
from datetime import datetime
from typing import Dict, Any
from unittest.mock import Mock, patch

from app.services.translation.enhanced import (
    EnhancedTranslationService,
    EnhancedTranslationResult
)
from app.services.translation.base import TranslationResult
from app.services.base import ErrorType, ValidationError


class TestEnhancedTranslationResult:
    """Enhanced Translation Result のテスト"""

    def test_enhanced_result_creation(self):
        """強化版結果の作成テスト"""
        result = EnhancedTranslationResult(
            success=True,
            translated_categories={
                "Appetizers": [
                    {"japanese_name": "枝豆", "english_name": "Edamame", "price": "¥500"}
                ]
            },
            translation_method="enhanced_translation_v2",
            fallback_used=False
        )
        
        assert result.success is True
        assert result.translation_method == "enhanced_translation_v2"
        assert result.fallback_used is False
        assert len(result.translated_categories) == 1
        assert "Appetizers" in result.translated_categories
        print("✅ Enhanced Result Creation: PASS")

    def test_translation_statistics_calculation(self):
        """翻訳統計計算テスト"""
        result = EnhancedTranslationResult(
            success=True,
            translated_categories={
                "Appetizers": [
                    {"japanese_name": "枝豆", "english_name": "Edamame", "price": "¥500"},
                    {"japanese_name": "餃子", "english_name": "Gyoza", "price": "¥600"}
                ],
                "Main Dishes": [
                    {"japanese_name": "寿司", "english_name": "Sushi", "price": "¥1200"}
                ]
            },
            untranslated_items=["unknown_item"]
        )
        
        stats = result.get_translation_statistics()
        
        assert stats["total_items"] == 3
        assert stats["translated_items"] == 3
        assert stats["untranslated_items"] == 1
        assert stats["categories_count"] == 2
        assert stats["translation_rate"] == 1.0  # 3翻訳済み / 3総アイテム
        assert stats["categories_distribution"]["Appetizers"] == 2
        assert stats["categories_distribution"]["Main Dishes"] == 1
        print("✅ Translation Statistics: PASS")

    def test_to_dict_conversion(self):
        """辞書変換テスト"""
        result = EnhancedTranslationResult(
            success=True,
            translated_categories={"Appetizers": []},
            translation_method="enhanced_v2",
            translation_coverage=0.95,
            consistency_score=0.92,
            fallback_used=True
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["success"] is True
        assert result_dict["translated_categories"] == {"Appetizers": []}
        assert result_dict["translation_method"] == "enhanced_v2"
        assert result_dict["translation_coverage"] == 0.95
        assert result_dict["consistency_score"] == 0.92
        assert result_dict["fallback_used"] is True
        print("✅ Dictionary Conversion: PASS")


class TestEnhancedTranslationService:
    """Enhanced Translation Service のテスト"""

    def setup_method(self):
        """各テストメソッドの前に実行"""
        self.service = EnhancedTranslationService()

    def test_service_initialization(self):
        """サービス初期化テスト"""
        assert self.service.provider == "enhanced_translation"
        assert hasattr(self.service, '_translation_stats')
        assert self.service._translation_stats["total_translations"] == 0
        assert self.service._translation_stats["successful_translations"] == 0
        print("✅ Service Initialization: PASS")

    def test_capabilities_listing(self):
        """機能一覧テスト"""
        capabilities = self.service.get_capabilities()
        
        expected_capabilities = [
            "menu_translation",
            "category_mapping", 
            "japanese_to_english",
            "price_preservation",
            "quality_assessment",
            "performance_monitoring",
            "error_recovery",
            "fallback_management",
            "consistency_evaluation"
        ]
        
        for capability in expected_capabilities:
            assert capability in capabilities
        print("✅ Capabilities Listing: PASS")

    def test_category_mapping(self):
        """カテゴリマッピングテスト"""
        mapping = self.service.get_category_mapping()
        
        assert mapping["前菜"] == "Appetizers"
        assert mapping["メイン"] == "Main Dishes"
        assert mapping["ドリンク"] == "Drinks"
        assert mapping["デザート"] == "Desserts"
        assert mapping["その他"] == "Others"
        assert len(mapping) >= 12  # 最低12のカテゴリマッピング
        print("✅ Category Mapping: PASS")



    @pytest.mark.asyncio
    async def test_basic_translation_success(self):
        """基本翻訳成功テスト"""
        categorized_data = {
            "前菜": [
                {"name": "枝豆", "price": "500円"},
                {"name": "餃子", "price": "600円"}
            ],
            "メイン": [
                {"name": "寿司", "price": "1200円"}
            ]
        }
        
        result = await self.service.translate_menu(categorized_data, "test_session")
        
        assert result.success is True
        assert result.translation_method == "basic_pattern_translation"
        assert len(result.translated_categories) == 2
        assert "Appetizers" in result.translated_categories
        assert "Main Dishes" in result.translated_categories
        
        # 品質指標の存在確認
        assert result.translation_coverage is not None
        assert result.consistency_score is not None
        assert result.processing_time is not None
        assert result.quality_score is not None
        
        print(f"✅ Basic Translation Success: PASS")
        print(f"   📊 Quality Score: {result.quality_score:.3f}")
        print(f"   🌍 Translation Coverage: {result.translation_coverage:.3f}")
        print(f"   🔄 Consistency Score: {result.consistency_score:.3f}")

    @pytest.mark.asyncio
    async def test_validation_error_handling(self):
        """バリデーションエラーハンドリングテスト"""
        # 空のデータでテスト
        result = await self.service.translate_menu({}, "test_session")
        
        assert result.success is False
        assert result.error_type == ErrorType.VALIDATION_ERROR
        assert "Invalid categorized data" in result.error
        assert len(result.suggestions) > 0
        assert "有効なカテゴリ分類データを提供してください" in result.suggestions
        print("✅ Validation Error Handling: PASS")

    @pytest.mark.asyncio 
    async def test_empty_categories_validation(self):
        """空カテゴリバリデーションテスト"""
        categorized_data = {
            "前菜": [],
            "メイン": []
        }
        
        result = await self.service.translate_menu(categorized_data, "test_session")
        
        assert result.success is False
        assert result.error_type == ErrorType.VALIDATION_ERROR
        assert "No items found" in result.error
        print("✅ Empty Categories Validation: PASS")



    def test_consistency_evaluation(self):
        """翻訳一貫性評価テスト"""
        # 一貫性のある翻訳結果
        consistent_result = EnhancedTranslationResult(
            success=True,
            translated_categories={
                "Appetizers": [
                    {"japanese_name": "寿司", "english_name": "Sushi", "price": "¥1200"}
                ],
                "Main Dishes": [
                    {"japanese_name": "寿司", "english_name": "Sushi", "price": "¥1500"}
                ]
            }
        )
        
        consistency_score = self.service._evaluate_translation_consistency(consistent_result)
        assert consistency_score == 1.0  # 完全に一貫
        
        # 非一貫性のある翻訳結果
        inconsistent_result = EnhancedTranslationResult(
            success=True,
            translated_categories={
                "Appetizers": [
                    {"japanese_name": "寿司", "english_name": "Sushi", "price": "¥1200"}
                ],
                "Main Dishes": [
                    {"japanese_name": "寿司", "english_name": "Raw Fish", "price": "¥1500"}
                ]
            }
        )
        
        inconsistency_score = self.service._evaluate_translation_consistency(inconsistent_result)
        assert inconsistency_score == 0.5  # 50%の一貫性（1つの非一貫性 / 2つのアイテム）
        
        print(f"✅ Consistency Evaluation: PASS")
        print(f"   🔄 Consistent Score: {consistency_score}")
        print(f"   ⚠️ Inconsistent Score: {inconsistency_score}")

    def test_translation_statistics_update(self):
        """翻訳統計更新テスト"""
        initial_stats = self.service.get_translation_statistics()
        assert initial_stats["total_translations"] == 0
        assert initial_stats["success_rate"] == 0.0
        
        # 成功した翻訳結果を作成
        successful_result = EnhancedTranslationResult(
            success=True,
            translated_categories={"Appetizers": [{"japanese_name": "寿司", "english_name": "Sushi"}]},
            total_items=1,
            fallback_used=False
        )
        
        # 統計を更新
        self.service._update_translation_stats(successful_result)
        
        updated_stats = self.service.get_translation_statistics()
        assert updated_stats["total_translations"] == 1
        assert updated_stats["successful_translations"] == 1
        assert updated_stats["success_rate"] == 1.0
        assert updated_stats["fallback_usage_rate"] == 0.0
        
        print("✅ Translation Statistics Update: PASS")

    def test_compatibility_with_existing_result(self):
        """既存システムとの互換性テスト"""
        enhanced_result = EnhancedTranslationResult(
            success=True,
            translated_categories={"Appetizers": [{"japanese_name": "寿司", "english_name": "Sushi"}]},
            translation_method="enhanced_v2",
            error=None,
            metadata={"test": "compatibility"}
        )
        
        # 既存形式に変換
        compatible_result = self.service.create_compatible_result(enhanced_result)
        
        assert isinstance(compatible_result, TranslationResult)
        assert compatible_result.success is True
        assert compatible_result.translated_categories == enhanced_result.translated_categories
        assert compatible_result.translation_method == "enhanced_v2"
        assert compatible_result.error is None
        assert compatible_result.metadata == {"test": "compatibility"}
        
        print("✅ Compatibility with Existing Result: PASS")

    @pytest.mark.asyncio
    async def test_performance_measurement(self):
        """パフォーマンス測定テスト"""
        categorized_data = {
            "前菜": [{"name": "寿司", "price": "1200円"}]
        }
        
        start_time = datetime.now()
        result = await self.service.translate_menu(categorized_data)
        end_time = datetime.now()
        
        assert result.processing_time is not None
        assert result.processing_time > 0
        assert result.processing_time < 1.0  # 1秒以内で完了
        
        # 実際の処理時間と測定値の妥当性確認
        actual_time = (end_time - start_time).total_seconds()
        assert abs(result.processing_time - actual_time) < 0.1  # 100ms以内の誤差
        
        print(f"✅ Performance Measurement: PASS")
        print(f"   ⏱️ Processing Time: {result.processing_time:.4f}s")

    @pytest.mark.asyncio
    async def test_quality_assessment_comprehensive(self):
        """包括的品質評価テスト"""
        categorized_data = {
            "前菜": [
                {"name": "寿司", "price": "1200円"},
                {"name": "刺身", "price": "1500円"},
                {"name": "枝豆", "price": "500円"}
            ],
            "メイン": [
                {"name": "天ぷら", "price": "2000円"},
                {"name": "ラーメン", "price": "800円"}
            ]
        }
        
        result = await self.service.translate_menu(categorized_data)
        
        assert result.success is True
        
        # 品質指標の範囲確認
        assert 0.0 <= result.quality_score <= 1.0
        assert 0.0 <= result.confidence <= 1.0
        assert 0.0 <= result.translation_coverage <= 1.0
        assert 0.0 <= result.consistency_score <= 1.0
        
        # 一貫性は完全であることを期待
        assert result.consistency_score == 1.0
        
        print(f"✅ Comprehensive Quality Assessment: PASS")
        print(f"   📊 Overall Quality: {result.quality_score:.3f}")
        print(f"   🎯 Confidence: {result.confidence:.3f}")
        print(f"   🌍 Coverage: {result.translation_coverage:.3f}")
        print(f"   🔄 Consistency: {result.consistency_score:.3f}")


@pytest.mark.asyncio
async def test_enhanced_translation_integration():
    """Enhanced Translation統合テスト"""
    service = EnhancedTranslationService()
    
    # 日本語メニューデータ
    categorized_data = {
        "前菜": [
            {"name": "枝豆", "price": "500円"},
            {"name": "餃子", "price": "600円"},
            {"name": "刺身", "price": "1500円"}
        ],
        "メイン": [
            {"name": "寿司", "price": "1200円"},
            {"name": "天ぷら", "price": "2000円"},
            {"name": "ラーメン", "price": "800円"}
        ],
        "ドリンク": [
            {"name": "ビール", "price": "500円"}
        ]
    }
    
    # 翻訳実行
    result = await service.translate_menu(categorized_data, "integration_test_session")
    
    # 基本的な成功確認
    assert result.success is True
    assert len(result.translated_categories) == 3
    assert "Appetizers" in result.translated_categories
    assert "Main Dishes" in result.translated_categories
    assert "Drinks" in result.translated_categories
    
    # 統計情報確認
    stats = result.get_translation_statistics()
    assert stats["total_items"] == 7
    assert stats["categories_count"] == 3
    assert stats["translation_rate"] == 1.0
    
    # 品質指標確認
    assert result.quality_score > 0.8  # 高品質翻訳を期待
    assert result.consistency_score == 1.0  # 一貫性は完全を期待
    
    # メタデータ確認
    assert "translation_statistics" in result.metadata
    assert "processing_details" in result.metadata
    assert result.metadata["processing_details"]["session_id"] == "integration_test_session"
    
    # パフォーマンス確認
    assert result.processing_time < 0.1  # 100ms以内
    
    # 具体的な翻訳内容確認
    appetizers = result.translated_categories["Appetizers"]
    assert any(item["english_name"] == "Edamame" for item in appetizers)
    assert any(item["english_name"] == "Sashimi" for item in appetizers)
    
    main_dishes = result.translated_categories["Main Dishes"]
    assert any(item["english_name"] == "Sushi" for item in main_dishes)
    assert any(item["english_name"] == "Tempura" for item in main_dishes)
    
    print(f"✅ Enhanced Translation Integration: PASS")
    print(f"   📈 Overall Score: {result.quality_score:.3f}")
    print(f"   ⏱️ Processing: {result.processing_time:.4f}s")
    print(f"   🌍 Coverage: {result.translation_coverage:.3f}")
    print(f"   🔄 Consistency: {result.consistency_score:.3f}")


if __name__ == "__main__":
    print("🧪 Running Enhanced Translation Service Tests...")
    print("=" * 60)
    
    # 基本テスト実行
    test_result = TestEnhancedTranslationResult()
    test_result.test_enhanced_result_creation()
    test_result.test_translation_statistics_calculation()
    test_result.test_to_dict_conversion()
    
    test_service = TestEnhancedTranslationService()
    test_service.setup_method()
    test_service.test_service_initialization()
    test_service.test_capabilities_listing()
    test_service.test_category_mapping()
    
    # 非同期テストは手動実行が必要
    print("\n🔄 For async tests, run: pytest tests/unit/test_enhanced_translation.py -v")
    print("=" * 60)
    print("✅ Enhanced Translation Service Tests: READY FOR EXECUTION") 
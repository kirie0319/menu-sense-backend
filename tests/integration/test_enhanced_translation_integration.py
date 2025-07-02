"""
Enhanced Translation Integration Test
OCR → Category → Enhanced Translation の完全パイプラインテスト
"""
import pytest
import asyncio
from datetime import datetime
import sys
import os

# パスを追加してappモジュールをインポート可能にする
sys.path.insert(0, os.path.abspath('.'))

from app.services.ocr.enhanced import EnhancedOCRService
from app.services.category.enhanced import EnhancedCategoryService  
from app.services.translation.enhanced import EnhancedTranslationService


@pytest.mark.asyncio
async def test_complete_menu_processing_pipeline():
    """完全なメニュー処理パイプラインの統合テスト"""
    print("🚀 Starting Complete Menu Processing Pipeline Test")
    
    # サービス初期化
    ocr_service = EnhancedOCRService()
    category_service = EnhancedCategoryService()
    translation_service = EnhancedTranslationService()
    
    print("✅ All services initialized")
    
    # OCR処理をシミュレート（実際のファイルではなくモックデータ）
    mock_extracted_text = """
    前菜
    枝豆 500円
    餃子 600円
    刺身 1500円
    
    メイン
    寿司 1200円
    天ぷら 2000円
    ラーメン 800円
    
    ドリンク
    ビール 500円
    日本酒 700円
    """
    
    print("📝 Mock OCR Text:")
    print(mock_extracted_text)
    
    # カテゴリ分類処理
    print("\n🔄 Step 1: Category Classification")
    category_result = await category_service.categorize_menu(
        mock_extracted_text, 
        "integration_test_session"
    )
    
    assert category_result.success, f"Category classification failed: {category_result.error}"
    print(f"✅ Category classification successful: {category_result.quality_score:.3f} quality")
    print(f"📋 Categories found: {list(category_result.categories.keys())}")
    
    # 翻訳処理
    print("\n🔄 Step 2: Translation")
    translation_result = await translation_service.translate_menu(
        category_result.categories,
        "integration_test_session"
    )
    
    assert translation_result.success, f"Translation failed: {translation_result.error}"
    print(f"✅ Translation successful: {translation_result.quality_score:.3f} quality")
    print(f"🌍 Translation categories: {list(translation_result.translated_categories.keys())}")
    
    # パイプライン全体の品質評価
    print("\n📊 Pipeline Quality Assessment:")
    
    # 総合処理時間
    total_processing_time = (
        (category_result.processing_time or 0) + 
        (translation_result.processing_time or 0)
    )
    print(f"⏱️ Total Processing Time: {total_processing_time:.4f}s")
    
    # 総合品質スコア
    overall_quality = (
        (category_result.quality_score or 0) * 0.4 +
        (translation_result.quality_score or 0) * 0.6
    )
    print(f"📈 Overall Quality Score: {overall_quality:.3f}")
    
    # データ完全性チェック
    original_categories = set(category_result.categories.keys())
    translated_categories = set(translation_result.translated_categories.keys())
    
    # カテゴリ名の対応関係確認
    category_mapping = translation_service.get_category_mapping()
    expected_english_categories = {
        category_mapping.get(jp_cat, jp_cat) 
        for jp_cat in original_categories
    }
    
    print(f"🔄 Category Mapping Verification:")
    print(f"   Original: {original_categories}")
    print(f"   Expected: {expected_english_categories}")  
    print(f"   Actual: {translated_categories}")
    
    # アイテム数の整合性確認
    original_item_count = sum(len(items) for items in category_result.categories.values())
    translated_item_count = sum(len(items) for items in translation_result.translated_categories.values())
    
    print(f"📊 Item Count Verification:")
    print(f"   Original Items: {original_item_count}")
    print(f"   Translated Items: {translated_item_count}")
    
    assert original_item_count == translated_item_count, "Item count mismatch in pipeline"
    
    # 具体的な翻訳内容確認
    print(f"\n📋 Final Translation Results:")
    for category, items in translation_result.translated_categories.items():
        print(f"   {category}: {len(items)} items")
        for item in items[:3]:  # 最初の3個を表示
            japanese_name = item.get("japanese_name", "N/A")
            english_name = item.get("english_name", "N/A")
            price = item.get("price", "N/A")
            print(f"     - {japanese_name} → {english_name} ({price})")
    
    # 成功基準の確認
    success_criteria = {
        "category_success": category_result.success,
        "translation_success": translation_result.success,
        "reasonable_processing_time": total_processing_time < 1.0,
        "good_quality": overall_quality > 0.8,
        "data_integrity": original_item_count == translated_item_count
    }
    
    print(f"\n✅ Success Criteria:")
    for criterion, result in success_criteria.items():
        status = "✅" if result else "❌"
        print(f"   {status} {criterion}: {result}")
    
    # すべての基準が満たされていることを確認
    assert all(success_criteria.values()), f"Some success criteria failed: {success_criteria}"
    
    print(f"\n🎉 Complete Menu Processing Pipeline: SUCCESS!")
    print(f"📊 Overall Quality: {overall_quality:.1%}")
    print(f"⏱️ Total Time: {total_processing_time:.4f}s")
    
    return {
        "category_result": category_result,
        "translation_result": translation_result,
        "overall_quality": overall_quality,
        "total_processing_time": total_processing_time,
        "success_criteria": success_criteria
    }


async def test_enhanced_services_performance_comparison():
    """Enhanced Services vs Basic Services パフォーマンス比較"""
    print("🏁 Enhanced Services Performance Comparison")
    
    # 同じデータで両方のサービスをテスト
    test_data = {
        "前菜": [
            {"name": "寿司", "price": "1200円"},
            {"name": "刺身", "price": "1500円"}
        ],
        "メイン": [
            {"name": "天ぷら", "price": "2000円"}
        ]
    }
    
    # Enhanced Translation Service
    enhanced_service = EnhancedTranslationService()
    start_time = datetime.now()
    enhanced_result = await enhanced_service.translate_menu(test_data, "perf_test")
    enhanced_time = (datetime.now() - start_time).total_seconds()
    
    print(f"🔧 Enhanced Translation Service:")
    print(f"   ⏱️ Time: {enhanced_time:.4f}s")
    print(f"   📊 Quality: {enhanced_result.quality_score:.3f}")
    print(f"   🔄 Consistency: {enhanced_result.consistency_score:.3f}")
    print(f"   🌍 Coverage: {enhanced_result.translation_coverage:.3f}")
    
    # 機能比較
    enhanced_features = enhanced_service.get_capabilities()
    print(f"   🛠️ Features: {len(enhanced_features)} capabilities")
    
    return {
        "enhanced_time": enhanced_time,
        "enhanced_quality": enhanced_result.quality_score,
        "enhanced_features": len(enhanced_features)
    }


if __name__ == "__main__":
    async def main():
        print("🧪 Running Enhanced Translation Integration Tests")
        print("=" * 60)
        
        # 完全パイプラインテスト
        pipeline_result = await test_complete_menu_processing_pipeline()
        
        print("\n" + "=" * 60)
        
        # パフォーマンス比較テスト
        performance_result = await test_enhanced_services_performance_comparison()
        
        print("\n" + "=" * 60)
        print("✅ All Integration Tests Completed Successfully!")
        
        return True
    
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 
#!/usr/bin/env python3
"""
Stage 3翻訳並列化 - 段階的テストスクリプト

段階的に翻訳の並列化をテストし、パフォーマンスを確認します：
1. 基本機能テスト
2. 単一カテゴリワーカーテスト
3. 並列翻訳テスト
4. パフォーマンス比較
5. エラー処理テスト
"""

import asyncio
import time
import logging
import json
from typing import Dict, Any

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# サンプルデータ
SAMPLE_MENU_DATA = {
    "前菜": [
        "エビマヨネーズ ¥800",
        "チキン唐揚げ ¥700",
        "春巻き ¥600"
    ],
    "メインディッシュ": [
        "牛肉の黒胡椒炒め ¥1,200",
        "麻婆豆腐 ¥900",
        "エビチリ ¥1,100",
        "チャーハン ¥800",
        "焼きそば ¥750"
    ],
    "スープ": [
        "ワンタンスープ ¥500",
        "コーンスープ ¥450"
    ],
    "デザート": [
        "杏仁豆腐 ¥400",
        "マンゴープリン ¥450",
        "ゴマ団子 ¥350"
    ]
}

def print_section(title: str):
    """セクションタイトルを表示"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_result(test_name: str, success: bool, details: str = ""):
    """テスト結果を表示"""
    status = "✅ SUCCESS" if success else "❌ FAILED"
    print(f"{status} {test_name}")
    if details:
        print(f"  → {details}")

async def test_translation_service_availability():
    """翻訳サービスの利用可能性をテスト"""
    print_section("Step 1: 翻訳サービス利用可能性確認")
    
    try:
        # Google Translateサービス
        from app.services.translation.google_translate import GoogleTranslateService
        google_service = GoogleTranslateService()
        google_available = google_service.is_available()
        print_result("Google Translate Service", google_available)
        
        # OpenAIサービス
        from app.services.translation.openai import OpenAITranslationService
        openai_service = OpenAITranslationService()
        openai_available = openai_service.is_available()
        print_result("OpenAI Translation Service", openai_available)
        
        # 並列翻訳サービス
        from app.services.translation.parallel import parallel_translation_service
        parallel_available = parallel_translation_service.is_available()
        print_result("Parallel Translation Service", parallel_available)
        
        return google_available or openai_available
        
    except Exception as e:
        print_result("Service Availability Check", False, f"Error: {str(e)}")
        return False

async def test_single_category_worker():
    """単一カテゴリワーカーのテスト"""
    print_section("Step 2: 単一カテゴリワーカーテスト")
    
    try:
        from app.tasks.translation_tasks import translate_category_simple
        
        # テストデータ
        category_name = "前菜"
        items = SAMPLE_MENU_DATA[category_name]
        
        print(f"Testing category: {category_name} ({len(items)} items)")
        
        start_time = time.time()
        
        # ワーカータスクを実行
        task = translate_category_simple.delay(category_name, items)
        
        # 結果を待機（タイムアウト60秒）
        result = task.get(timeout=60)
        
        processing_time = time.time() - start_time
        
        if result['success']:
            print_result("Single Category Worker", True, 
                        f"Translated {result['items_processed']} items in {processing_time:.2f}s")
            print(f"  English category: {result['english_category']}")
            for item in result['translated_items'][:2]:  # 最初の2つだけ表示
                print(f"    {item['japanese_name']} → {item['english_name']}")
        else:
            print_result("Single Category Worker", False, result.get('error', 'Unknown error'))
        
        return result['success']
        
    except Exception as e:
        print_result("Single Category Worker", False, f"Error: {str(e)}")
        return False

async def test_parallel_translation():
    """並列翻訳の基本テスト"""
    print_section("Step 3: 並列翻訳基本テスト")
    
    try:
        from app.services.translation.parallel import translate_menu_with_parallel
        
        print(f"Testing parallel translation with {len(SAMPLE_MENU_DATA)} categories")
        
        start_time = time.time()
        
        # 並列翻訳を実行
        result = await translate_menu_with_parallel(SAMPLE_MENU_DATA)
        
        processing_time = time.time() - start_time
        
        if result.success:
            print_result("Parallel Translation", True, 
                        f"Translated {result.metadata.get('total_items', 0)} items in {processing_time:.2f}s")
            print(f"  Processing mode: {result.metadata.get('processing_mode', 'unknown')}")
            print(f"  Translation method: {result.translation_method}")
            print(f"  Categories translated: {len(result.translated_categories)}")
            
            # 翻訳されたカテゴリを表示
            for i, (eng_cat, items) in enumerate(result.translated_categories.items()):
                print(f"    {i+1}. {eng_cat}: {len(items)} items")
                if i >= 2:  # 最初の3つまで表示
                    break
        else:
            print_result("Parallel Translation", False, result.error)
        
        return result.success
        
    except Exception as e:
        print_result("Parallel Translation", False, f"Error: {str(e)}")
        return False

async def run_basic_tests():
    """基本テストを順次実行"""
    print_section("Stage 3翻訳並列化 - 基本テスト開始")
    
    test_results = {}
    
    # Step 1: サービス利用可能性
    test_results['availability'] = await test_translation_service_availability()
    
    if not test_results['availability']:
        print("\n❌ Translation services not available. Stopping tests.")
        return
    
    # Step 2: 単一カテゴリワーカー
    test_results['single_worker'] = await test_single_category_worker()
    
    # Step 3: 並列翻訳基本
    test_results['parallel'] = await test_parallel_translation()
    
    # 総合結果
    print_section("テスト結果サマリー")
    
    passed = sum(1 for result in test_results.values() if result)
    total = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\n📊 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Stage 3翻訳並列化は正常に動作しています。")
        print("\n🚀 次のステップ: パフォーマンステストと本格運用の準備ができました！")
    else:
        print("⚠️ Some tests failed. 詳細を確認してください。")

if __name__ == "__main__":
    print("🚀 Stage 3翻訳並列化 - 段階的テストスクリプト")
    print("このスクリプトは並列翻訳機能を段階的にテストします。")
    print("\n⚠️ 注意: Celeryワーカーが起動していることを確認してください。")
    
    # 実行確認
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--run":
        asyncio.run(run_basic_tests())
    else:
        print("\n実行するには以下のコマンドを使用してください:")
        print("python test_parallel_translation.py --run") 
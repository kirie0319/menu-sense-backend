#!/usr/bin/env python3
"""
Stage 4詳細説明並列化テストスクリプト

段階的な詳細説明並列処理のテスト
"""

import asyncio
import time
import json
import sys
import os

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings

async def test_description_service_availability():
    """詳細説明サービスの利用可能性をテスト"""
    print("=== Stage 4詳細説明サービス利用可能性テスト ===")
    
    try:
        from app.services.description.parallel import ParallelDescriptionService
        
        parallel_service = ParallelDescriptionService()
        is_available = parallel_service.is_available()
        
        print(f"✅ 並列詳細説明サービス: {'利用可能' if is_available else '利用不可'}")
        
        if is_available:
            print("   🔧 OpenAI API接続: OK")
            print("   🚀 並列処理準備: OK")
        else:
            print("   ❌ OpenAI API接続エラーまたは設定不備")
        
        return is_available
        
    except Exception as e:
        print(f"❌ サービス利用可能性テスト失敗: {e}")
        return False

def test_single_category_worker():
    """単一カテゴリ詳細説明ワーカーをテスト"""
    print("\n=== 単一カテゴリ詳細説明ワーカーテスト ===")
    
    try:
        from app.tasks.description_tasks import add_descriptions_to_category
        
        # テスト用翻訳データ
        translated_items = [
            {
                "japanese_name": "鶏の唐揚げ",
                "english_name": "Fried Chicken",
                "price": "¥800"
            },
            {
                "japanese_name": "野菜サラダ",
                "english_name": "Vegetable Salad",
                "price": "¥600"
            },
            {
                "japanese_name": "味噌汁",
                "english_name": "Miso Soup",
                "price": "¥200"
            }
        ]
        
        print(f"🔄 カテゴリ詳細説明ワーカーテスト開始 ({len(translated_items)}アイテム)")
        
        start_time = time.time()
        
        # ワーカータスクを実行
        task = add_descriptions_to_category.delay("Main Dishes", translated_items, "test-session")
        
        # 結果を取得（タイムアウト60秒）
        result = task.get(timeout=60)
        
        processing_time = time.time() - start_time
        
        if result['success']:
            print(f"✅ カテゴリ詳細説明ワーカー成功!")
            print(f"   ⏱️  処理時間: {processing_time:.2f}秒")
            print(f"   📦 処理アイテム数: {result['items_processed']}")
            print(f"   📝 詳細説明メソッド: {result['description_method']}")
            
            # 結果サンプルを表示
            if result['final_items']:
                sample_item = result['final_items'][0]
                print(f"   🍽️  サンプル結果:")
                print(f"      英語名: {sample_item.get('english_name', 'N/A')}")
                print(f"      詳細説明: {sample_item.get('description', 'N/A')[:80]}...")
            
            return True
        else:
            print(f"❌ カテゴリ詳細説明ワーカー失敗: {result.get('error', 'Unknown error')}")
            return False
        
    except Exception as e:
        print(f"❌ 単一カテゴリワーカーテスト失敗: {e}")
        return False

async def test_parallel_description_basic():
    """基本的な並列詳細説明テスト"""
    print("\n=== 基本並列詳細説明テスト ===")
    
    try:
        from app.services.description.parallel import add_descriptions_with_parallel
        
        # テスト用翻訳データ（複数カテゴリ）
        translated_data = {
            "Appetizers": [
                {
                    "japanese_name": "枝豆",
                    "english_name": "Edamame",
                    "price": "¥400"
                },
                {
                    "japanese_name": "冷奴",
                    "english_name": "Cold Tofu",
                    "price": "¥350"
                }
            ],
            "Main Dishes": [
                {
                    "japanese_name": "鶏の唐揚げ",
                    "english_name": "Fried Chicken",
                    "price": "¥800"
                },
                {
                    "japanese_name": "豚肉の生姜焼き",
                    "english_name": "Ginger Pork",
                    "price": "¥900"
                },
                {
                    "japanese_name": "鮭の塩焼き",
                    "english_name": "Grilled Salmon",
                    "price": "¥1000"
                }
            ],
            "Drinks": [
                {
                    "japanese_name": "緑茶",
                    "english_name": "Green Tea",
                    "price": "¥200"
                },
                {
                    "japanese_name": "烏龍茶",
                    "english_name": "Oolong Tea",
                    "price": "¥200"
                }
            ]
        }
        
        total_items = sum(len(items) for items in translated_data.values())
        print(f"🔄 並列詳細説明テスト開始 ({len(translated_data)}カテゴリ, {total_items}アイテム)")
        
        start_time = time.time()
        
        # 並列詳細説明を実行
        result = await add_descriptions_with_parallel(translated_data, "test-session")
        
        processing_time = time.time() - start_time
        
        if result.success:
            print(f"✅ 並列詳細説明基本テスト成功!")
            print(f"   ⏱️  処理時間: {processing_time:.2f}秒")
            print(f"   📦 処理カテゴリ数: {result.metadata.get('categories_processed', 0)}")
            print(f"   📝 処理モード: {result.metadata.get('processing_mode', 'unknown')}")
            print(f"   🚀 並列処理: {'有効' if result.metadata.get('parallel_enabled', False) else '無効'}")
            
            # 処理速度計算
            processing_rate = total_items / processing_time if processing_time > 0 else 0
            print(f"   ⚡ 処理速度: {processing_rate:.2f}アイテム/秒")
            
            return True
        else:
            print(f"❌ 並列詳細説明基本テスト失敗: {result.error}")
            return False
        
    except Exception as e:
        print(f"❌ 基本並列詳細説明テスト失敗: {e}")
        return False

async def run_all_stage4_tests():
    """全Stage 4詳細説明並列化テストを実行"""
    print("🚀 Stage 4詳細説明並列化テスト開始")
    print("=" * 60)
    
    # テスト結果追跡
    test_results = {}
    
    # 1. サービス利用可能性テスト
    test_results['service_availability'] = await test_description_service_availability()
    
    if not test_results['service_availability']:
        print("\n❌ 詳細説明サービスが利用できないため、テストを中止します")
        return
    
    # 2. 単一カテゴリワーカーテスト
    test_results['single_category_worker'] = test_single_category_worker()
    
    # 3. 基本並列詳細説明テスト
    test_results['parallel_description_basic'] = await test_parallel_description_basic()
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print("🎯 Stage 4詳細説明並列化テスト結果サマリー")
    print("=" * 60)
    
    total_tests = len(test_results)
    passed_tests = sum(1 for result in test_results.values() if result)
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        test_display_name = test_name.replace('_', ' ').title()
        print(f"{status} {test_display_name}")
    
    print(f"\n📊 テスト結果: {passed_tests}/{total_tests} ({passed_tests/total_tests*100:.1f}%)")
    
    if passed_tests == total_tests:
        print("🎉 全テスト成功! Stage 4詳細説明並列化は正常に動作しています")
    else:
        print("❌ 一部テスト失敗。設定やシステムを確認してください")
    
    return test_results

if __name__ == "__main__":
    # 設定情報表示
    print("🔧 Stage 4詳細説明並列化設定:")
    print(f"   ENABLE_PARALLEL_DESCRIPTION: {getattr(settings, 'ENABLE_PARALLEL_DESCRIPTION', 'Not set')}")
    print(f"   PARALLEL_DESCRIPTION_CATEGORY_THRESHOLD: {getattr(settings, 'PARALLEL_DESCRIPTION_CATEGORY_THRESHOLD', 'Not set')}")
    print(f"   PARALLEL_DESCRIPTION_ITEM_THRESHOLD: {getattr(settings, 'PARALLEL_DESCRIPTION_ITEM_THRESHOLD', 'Not set')}")
    print()
    
    # 非同期テスト実行
    asyncio.run(run_all_stage4_tests()) 
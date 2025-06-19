#!/usr/bin/env python3
"""
メイン翻訳エンドポイント並列翻訳統合テスト

実際の/api/translateエンドポイントで並列翻訳が正常に動作するかテスト
"""

import asyncio
import json
import time
from typing import Dict, Any

def create_test_data():
    """テスト用のカテゴリ分類データを作成"""
    return {
        "前菜": [
            "エビマヨネーズ ¥800",
            "チキン唐揚げ ¥700",
            "春巻き ¥600",
            "餃子 ¥550"
        ],
        "メインディッシュ": [
            "牛肉の黒胡椒炒め ¥1,200",
            "麻婆豆腐 ¥900",
            "エビチリ ¥1,100",
            "チャーハン ¥800",
            "焼きそば ¥750",
            "酢豚 ¥1,000"
        ],
        "スープ": [
            "ワンタンスープ ¥500",
            "コーンスープ ¥450",
            "酸辣湯 ¥520"
        ],
        "デザート": [
            "杏仁豆腐 ¥400",
            "マンゴープリン ¥450",
            "ゴマ団子 ¥350"
        ]
    }

async def test_stage3_parallel_translation():
    """Stage 3並列翻訳の統合テスト"""
    
    print("🎯 Stage 3並列翻訳統合テスト開始")
    print("="*60)
    
    # テストデータ準備
    test_data = create_test_data()
    total_items = sum(len(items) for items in test_data.values())
    
    print(f"📊 テストデータ:")
    print(f"  - カテゴリ数: {len(test_data)}")
    print(f"  - 総アイテム数: {total_items}")
    
    try:
        # Stage 3翻訳処理を直接テスト
        from app.workflows.stages import stage3_translate_with_fallback
        
        print(f"\n🚀 並列翻訳開始...")
        start_time = time.time()
        
        # 並列翻訳実行
        result = await stage3_translate_with_fallback(test_data)
        
        processing_time = time.time() - start_time
        
        if result['success']:
            print(f"\n✅ Stage 3並列翻訳成功！")
            print("="*60)
            print(f"⏱️  処理時間: {processing_time:.2f}秒")
            print(f"⚡ 処理速度: {total_items/processing_time:.2f} アイテム/秒")
            print(f"🏗️  アーキテクチャ: {result['translation_architecture']}")
            print(f"🎯 処理モード: {result.get('processing_mode', 'unknown')}")
            print(f"🚀 並列処理: {'有効' if result.get('parallel_enabled', False) else '無効'}")
            print(f"📈 翻訳カテゴリ: {result['total_categories']}")
            print(f"🔢 翻訳アイテム: {result['total_items']}")
            
            # 失敗したカテゴリのチェック
            failed_categories = result.get('failed_categories')
            if failed_categories:
                print(f"⚠️  失敗カテゴリ: {len(failed_categories)}")
                for failed in failed_categories:
                    print(f"    - {failed.get('category', 'Unknown')}: {failed.get('error', 'Unknown error')}")
            else:
                print("🎉 全カテゴリ翻訳成功！")
            
            # 翻訳結果サンプル
            print(f"\n📊 翻訳結果サンプル:")
            translated_categories = result['translated_categories']
            for i, (eng_category, items) in enumerate(translated_categories.items()):
                if i < 2:  # 最初の2カテゴリのみ表示
                    print(f"  {eng_category}: {len(items)}アイテム")
                    if len(items) > 0:
                        sample = items[0]
                        jp_name = sample.get('japanese_name', 'N/A')
                        en_name = sample.get('english_name', 'N/A')
                        print(f"    例: {jp_name} → {en_name}")
            
            # パフォーマンス評価
            print(f"\n🏆 パフォーマンス評価:")
            items_per_second = total_items / processing_time
            if items_per_second > 8:
                print("    🚀 優秀 - 高速並列処理成功")
            elif items_per_second > 5:
                print("    ⚡ 良好 - 並列処理効果あり")
            elif items_per_second > 3:
                print("    📈 標準 - 基本並列処理動作")
            else:
                print("    ⚠️  要改善 - 並列処理効果限定的")
            
            return True
            
        else:
            print(f"\n❌ Stage 3並列翻訳失敗")
            print(f"エラー: {result['error']}")
            return False
            
    except Exception as e:
        print(f"\n💥 テスト実行エラー: {str(e)}")
        return False

async def test_full_endpoint_workflow():
    """エンドポイント全体のワークフローテスト（Stage 1-4）"""
    
    print("\n" + "="*60)
    print("🔧 エンドポイント全体ワークフローテスト")
    print("="*60)
    
    # テスト用の抽出テキスト（Stage 1の結果をシミュレート）
    extracted_text = """
前菜
エビマヨネーズ ¥800
チキン唐揚げ ¥700
春巻き ¥600

メインディッシュ
牛肉の黒胡椒炒め ¥1,200
麻婆豆腐 ¥900
エビチリ ¥1,100
チャーハン ¥800

スープ
ワンタンスープ ¥500
コーンスープ ¥450

デザート
杏仁豆腐 ¥400
マンゴープリン ¥450
"""
    
    try:
        from app.workflows.stages import (
            stage2_categorize_openai_exclusive,
            stage3_translate_with_fallback,
            stage4_add_descriptions
        )
        
        print("📝 Stage 2: カテゴライズ開始...")
        start_time = time.time()
        
        # Stage 2: カテゴライズ
        stage2_result = await stage2_categorize_openai_exclusive(extracted_text)
        
        if not stage2_result['success']:
            print(f"❌ Stage 2失敗: {stage2_result['error']}")
            return False
        
        stage2_time = time.time() - start_time
        print(f"✅ Stage 2完了: {stage2_time:.2f}秒")
        
        # Stage 3: 並列翻訳
        print("🚀 Stage 3: 並列翻訳開始...")
        stage3_start = time.time()
        
        stage3_result = await stage3_translate_with_fallback(stage2_result['categories'])
        
        if not stage3_result['success']:
            print(f"❌ Stage 3失敗: {stage3_result['error']}")
            return False
        
        stage3_time = time.time() - stage3_start
        print(f"✅ Stage 3完了: {stage3_time:.2f}秒 (並列処理: {'有効' if stage3_result.get('parallel_enabled', False) else '無効'})")
        
        # Stage 4: 詳細説明
        print("📝 Stage 4: 詳細説明開始...")
        stage4_start = time.time()
        
        stage4_result = await stage4_add_descriptions(stage3_result['translated_categories'])
        
        stage4_time = time.time() - stage4_start
        
        if stage4_result['success']:
            print(f"✅ Stage 4完了: {stage4_time:.2f}秒")
        else:
            print(f"⚠️ Stage 4失敗（続行）: {stage4_result['error']}")
        
        # 総合結果
        total_time = time.time() - start_time
        total_items = stage3_result.get('total_items', 0)
        
        print(f"\n🎉 エンドポイント全体テスト完了！")
        print("="*60)
        print(f"⏱️  総処理時間: {total_time:.2f}秒")
        print(f"    - Stage 2: {stage2_time:.2f}秒")
        print(f"    - Stage 3: {stage3_time:.2f}秒 ← 並列翻訳")
        print(f"    - Stage 4: {stage4_time:.2f}秒")
        print(f"⚡ 全体処理速度: {total_items/total_time:.2f} アイテム/秒")
        print(f"🚀 並列翻訳効果: Stage 3が全体の{(stage3_time/total_time*100):.1f}%を占有")
        
        return True
        
    except Exception as e:
        print(f"💥 ワークフローテストエラー: {str(e)}")
        return False

async def run_integration_tests():
    """統合テストを実行"""
    
    print("🎯 メイン翻訳エンドポイント並列翻訳統合テスト")
    print("このテストは実際のエンドポイントで並列翻訳が動作するかを確認します")
    print("\n⚠️ 注意: Celeryワーカーが起動していることを確認してください")
    
    results = {}
    
    # Test 1: Stage 3並列翻訳単体
    results['stage3_parallel'] = await test_stage3_parallel_translation()
    
    # Test 2: エンドポイント全体ワークフロー  
    results['full_workflow'] = await test_full_endpoint_workflow()
    
    # 総合結果
    print("\n" + "="*60)
    print("📊 統合テスト結果サマリー")
    print("="*60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        test_display = {
            'stage3_parallel': 'Stage 3並列翻訳',
            'full_workflow': 'エンドポイント全体ワークフロー'
        }
        print(f"{status} {test_display.get(test_name, test_name)}")
    
    print(f"\n📈 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 全テスト成功！メイン翻訳エンドポイントの並列翻訳統合完了。")
        print("🚀 ユーザー体験が大幅に改善されました！")
    else:
        print("⚠️ 一部テスト失敗。詳細を確認してください。")

if __name__ == "__main__":
    asyncio.run(run_integration_tests()) 
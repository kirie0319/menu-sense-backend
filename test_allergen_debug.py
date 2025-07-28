#!/usr/bin/env python3
"""
アレルギー分析デバッグテスト
個別メニューアイテムのアレルギー分析をテストしてログで詳細を確認
"""
import asyncio
import logging
from typing import Dict, Any

# ログ設定
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# テスト対象メニューアイテム（異なるアレルゲン特性を持つ）
TEST_MENU_ITEMS = [
    {"name": "エビフライ", "category": "Fried Foods", "expected_allergens": ["shellfish", "wheat", "egg"]},
    {"name": "カルボナーラ", "category": "Pasta", "expected_allergens": ["egg", "milk", "wheat"]},
    {"name": "寿司", "category": "Japanese", "expected_allergens": ["fish", "soy"]},
    {"name": "サラダ", "category": "Salads", "expected_allergens": []},
    {"name": "アーモンドケーキ", "category": "Desserts", "expected_allergens": ["tree nuts", "egg", "milk", "wheat"]},
    {"name": "豆腐ハンバーグ", "category": "Main", "expected_allergens": ["soy"]},
    {"name": "コーヒー", "category": "Beverages", "expected_allergens": []},
    {"name": "パン", "category": "Bread", "expected_allergens": ["wheat", "egg", "milk"]}
]

async def test_allergen_analysis():
    """アレルギー分析のテスト実行"""
    print("🧪 アレルギー分析デバッグテスト開始")
    print("=" * 60)
    
    try:
        # サービスインポート（非同期環境内でインポート）
        from app_2.services.allergen_service import get_allergen_service
        
        allergen_service = get_allergen_service()
        results = []
        
        for item in TEST_MENU_ITEMS:
            print(f"\n🔍 テスト中: {item['name']} ({item['category']})")
            print(f"期待されるアレルゲン: {item['expected_allergens']}")
            
            try:
                # アレルギー分析実行
                result = await allergen_service.analyze_allergens(
                    menu_item=item['name'], 
                    category=item['category']
                )
                
                print(f"✅ 分析結果:")
                print(f"   アレルゲン: {result.get('allergens', [])}")
                print(f"   アレルゲンフリー: {result.get('allergen_free', False)}")
                print(f"   信頼度: {result.get('confidence', 0)}")
                print(f"   ノート: {result.get('notes', 'なし')}")
                
                # 結果を保存
                results.append({
                    "menu_item": item['name'],
                    "category": item['category'],
                    "expected": item['expected_allergens'],
                    "actual": result.get('allergens', []),
                    "allergen_free": result.get('allergen_free', False),
                    "confidence": result.get('confidence', 0),
                    "success": True
                })
                
            except Exception as e:
                print(f"❌ エラー: {str(e)}")
                results.append({
                    "menu_item": item['name'],
                    "category": item['category'],
                    "expected": item['expected_allergens'],
                    "actual": [],
                    "allergen_free": False,
                    "confidence": 0,
                    "success": False,
                    "error": str(e)
                })
        
        # 結果サマリー
        print("\n" + "=" * 60)
        print("📊 テスト結果サマリー")
        print("=" * 60)
        
        successful_tests = sum(1 for r in results if r['success'])
        print(f"成功したテスト: {successful_tests}/{len(results)}")
        
        for result in results:
            print(f"\n📋 {result['menu_item']} ({result['category']}):")
            if result['success']:
                actual_allergens = result['actual']
                expected_allergens = result['expected']
                
                print(f"   期待: {expected_allergens}")
                print(f"   実際: {actual_allergens}")
                
                # 一致度計算
                if not expected_allergens and not actual_allergens:
                    match_status = "✅ 完全一致（アレルゲンなし）"
                elif set(expected_allergens) == set(actual_allergens):
                    match_status = "✅ 完全一致"
                else:
                    overlap = set(expected_allergens) & set(actual_allergens)
                    match_status = f"⚠️ 部分一致 (重複: {list(overlap)})"
                
                print(f"   状態: {match_status}")
                print(f"   信頼度: {result['confidence']}")
            else:
                print(f"   ❌ エラー: {result.get('error', '不明')}")
        
        print("\n🎯 アレルゲン個別分析テスト完了")
        return results
        
    except Exception as e:
        print(f"💥 テスト実行エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

async def main():
    """メイン実行関数"""
    print("🚀 アレルギー分析デバッグツール")
    print("個別メニューアイテムのアレルギー分析をテスト")
    
    results = await test_allergen_analysis()
    
    if results:
        print(f"\n📈 {len(results)}件のテストが完了しました")
        
        # 個別分析が正しく動作しているかチェック
        unique_results = set()
        for result in results:
            if result['success']:
                allergen_tuple = tuple(sorted(result['actual']))
                unique_results.add(allergen_tuple)
        
        print(f"🔍 異なるアレルゲンパターン数: {len(unique_results)}")
        if len(unique_results) > 1:
            print("✅ 個別分析が正常に動作しています！")
        else:
            print("⚠️ 全てのアイテムが同じアレルゲン情報を返しています")
            print("プロンプトまたはスキーマに問題がある可能性があります")
    
    print("\n🏁 テスト終了")

if __name__ == "__main__":
    asyncio.run(main()) 
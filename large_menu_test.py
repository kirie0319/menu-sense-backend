#!/usr/bin/env python3
"""
大規模メニュー並列翻訳パフォーマンステスト

実際のレストランメニューサイズでの並列翻訳性能を測定
"""

import asyncio
import time
from app.services.translation.parallel import translate_menu_with_parallel

# 大規模テストデータ（実際のレストランメニュー相当）
LARGE_MENU_DATA = {
    "前菜": [
        "エビマヨネーズ ¥800",
        "チキン唐揚げ ¥700", 
        "春巻き ¥600",
        "餃子 ¥550",
        "海老餃子 ¥650",
        "小籠包 ¥680",
        "ワンタン揚げ ¥520"
    ],
    "メインディッシュ": [
        "牛肉の黒胡椒炒め ¥1,200",
        "麻婆豆腐 ¥900",
        "エビチリ ¥1,100",
        "チャーハン ¥800",
        "焼きそば ¥750",
        "酢豚 ¥1,000",
        "青椒肉絲 ¥950",
        "回鍋肉 ¥980",
        "マーボー茄子 ¥850",
        "四川風担々麺 ¥980",
        "五目チャーハン ¥850",
        "海鮮焼きそば ¥920"
    ],
    "スープ": [
        "ワンタンスープ ¥500",
        "コーンスープ ¥450",
        "酸辣湯 ¥520",
        "中華スープ ¥400",
        "海鮮スープ ¥580",
        "キャベツスープ ¥380"
    ],
    "デザート": [
        "杏仁豆腐 ¥400",
        "マンゴープリン ¥450",
        "ゴマ団子 ¥350",
        "タピオカ ¥380",
        "アイスクリーム ¥320",
        "フルーツ盛り合わせ ¥680"
    ],
    "飲み物": [
        "ジャスミン茶 ¥300",
        "ウーロン茶 ¥300",
        "コーラ ¥250",
        "オレンジジュース ¥280",
        "緑茶 ¥250",
        "ビール ¥400",
        "紹興酒 ¥450",
        "レモンサワー ¥380"
    ],
    "サラダ": [
        "バンバンジーサラダ ¥650",
        "中華風海藻サラダ ¥480",
        "蒸し鶏サラダ ¥580",
        "キュウリの和え物 ¥320"
    ]
}

async def performance_test():
    """大規模メニューでのパフォーマンステスト"""
    
    total_items = sum(len(items) for items in LARGE_MENU_DATA.values())
    print("🚀 大規模メニュー並列翻訳パフォーマンステスト")
    print("="*60)
    print(f"📊 テストデータ:")
    print(f"  - カテゴリ数: {len(LARGE_MENU_DATA)}")
    print(f"  - 総アイテム数: {total_items}")
    
    for category, items in LARGE_MENU_DATA.items():
        print(f"  - {category}: {len(items)}アイテム")
    
    print("\n🔄 並列翻訳開始...")
    start_time = time.time()
    
    try:
        result = await translate_menu_with_parallel(LARGE_MENU_DATA)
        
        processing_time = time.time() - start_time
        
        if result.success:
            print(f"\n✅ 並列翻訳完了！")
            print("="*60)
            print(f"⏱️  総処理時間: {processing_time:.2f}秒")
            print(f"⚡ 処理速度: {total_items/processing_time:.2f} アイテム/秒")
            print(f"🎯 処理モード: {result.metadata.get('processing_mode', 'unknown')}")
            print(f"📈 翻訳完了カテゴリ: {len(result.translated_categories)}")
            print(f"🔢 翻訳完了アイテム: {result.metadata.get('total_items', 0)}")
            
            # 失敗したカテゴリがあるかチェック
            failed_categories = result.metadata.get('failed_categories', [])
            if failed_categories:
                print(f"⚠️  失敗カテゴリ: {len(failed_categories)}")
                for failed in failed_categories:
                    print(f"    - {failed['category']}: {failed['error']}")
            else:
                print("🎉 全カテゴリ翻訳成功！")
            
            print("\n📊 翻訳結果サンプル:")
            for i, (eng_category, items) in enumerate(result.translated_categories.items()):
                if i < 3:  # 最初の3カテゴリのみ表示
                    print(f"  {eng_category}: {len(items)}アイテム")
                    if len(items) > 0:
                        sample_item = items[0]
                        jp_name = sample_item.get('japanese_name', 'N/A')
                        en_name = sample_item.get('english_name', 'N/A')
                        print(f"    例: {jp_name} → {en_name}")
            
            # パフォーマンス評価
            print("\n🏆 パフォーマンス評価:")
            items_per_second = total_items / processing_time
            if items_per_second > 8:
                print("    🚀 優秀 - 高速並列処理成功")
            elif items_per_second > 5:
                print("    ⚡ 良好 - 並列処理効果あり")
            elif items_per_second > 3:
                print("    📈 標準 - 基本並列処理動作")
            else:
                print("    ⚠️  要改善 - 並列処理効果限定的")
                
        else:
            print(f"\n❌ 並列翻訳失敗")
            print(f"エラー: {result.error}")
            
    except Exception as e:
        print(f"\n💥 テスト実行エラー: {str(e)}")

if __name__ == "__main__":
    asyncio.run(performance_test()) 
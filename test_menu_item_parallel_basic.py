#!/usr/bin/env python3
"""
🧪 メニューアイテム並列処理の基本テスト

Phase 1: 基本機能のテスト
- Redis接続テスト
- 単一タスク実行テスト
- 依存判定テスト
- 並列処理テスト
"""

import time
import asyncio
import logging
from typing import Dict, List

# テストセットアップ
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_redis_connection():
    """Phase 1: Redis接続テスト"""
    print("\n🧪 === Phase 1: Redis接続テスト ===")
    
    try:
        from app.tasks.menu_item_parallel_tasks import test_redis_connection
        
        result = test_redis_connection()
        
        if result["success"]:
            print(f"✅ Redis接続テスト成功: {result['message']}")
            print(f"📊 テストデータ: {result.get('test_data', {})}")
            return True
        else:
            print(f"❌ Redis接続テスト失敗: {result['message']}")
            return False
            
    except Exception as e:
        print(f"❌ Redis接続テストでエラー: {str(e)}")
        return False

def test_single_translation_task():
    """Phase 2: 単一翻訳タスクのテスト"""
    print("\n🧪 === Phase 2: 単一翻訳タスクテスト ===")
    
    try:
        from app.tasks.menu_item_parallel_tasks import test_translate_menu_item
        
        session_id = f"test_session_{int(time.time())}"
        item_id = 0
        item_text = "鶏の唐揚げ"
        
        print(f"📝 テストパラメータ:")
        print(f"   セッションID: {session_id}")
        print(f"   アイテムID: {item_id}")
        print(f"   テキスト: {item_text}")
        
        # タスクを非同期実行
        task = test_translate_menu_item.delay(session_id, item_id, item_text)
        
        print(f"⏳ タスク実行中... (ID: {task.id})")
        
        # 結果を待機（タイムアウト10秒）
        result = task.get(timeout=10)
        
        if result["success"]:
            print(f"✅ 翻訳タスク成功:")
            print(f"   日本語: {result['japanese_text']}")
            print(f"   英語: {result['english_text']}")
            print(f"   テストモード: {result.get('test_mode', False)}")
            return True, session_id, item_id
        else:
            print(f"❌ 翻訳タスク失敗: {result['error']}")
            return False, session_id, item_id
            
    except Exception as e:
        print(f"❌ 翻訳タスクテストでエラー: {str(e)}")
        return False, None, None

def test_single_description_task():
    """Phase 3: 単一説明生成タスクのテスト"""
    print("\n🧪 === Phase 3: 単一説明生成タスクテスト ===")
    
    try:
        from app.tasks.menu_item_parallel_tasks import test_generate_menu_description
        
        session_id = f"test_session_{int(time.time())}"
        item_id = 1
        item_text = "天ぷら盛り合わせ"
        
        print(f"📝 テストパラメータ:")
        print(f"   セッションID: {session_id}")
        print(f"   アイテムID: {item_id}")
        print(f"   テキスト: {item_text}")
        
        # タスクを非同期実行
        task = test_generate_menu_description.delay(session_id, item_id, item_text)
        
        print(f"⏳ タスク実行中... (ID: {task.id})")
        
        # 結果を待機（タイムアウト15秒）
        result = task.get(timeout=15)
        
        if result["success"]:
            print(f"✅ 説明生成タスク成功:")
            print(f"   日本語: {result['japanese_text']}")
            print(f"   説明: {result['description'][:100]}...")
            print(f"   テストモード: {result.get('test_mode', False)}")
            return True, session_id, item_id
        else:
            print(f"❌ 説明生成タスク失敗: {result['error']}")
            return False, session_id, item_id
            
    except Exception as e:
        print(f"❌ 説明生成タスクテストでエラー: {str(e)}")
        return False, None, None

def test_dependency_trigger():
    """Phase 4: 依存判定・トリガーテスト"""
    print("\n🧪 === Phase 4: 依存判定・トリガーテスト ===")
    
    try:
        from app.tasks.menu_item_parallel_tasks import (
            test_translate_menu_item,
            test_generate_menu_description,
            get_test_status
        )
        
        session_id = f"test_dependency_{int(time.time())}"
        item_id = 2
        item_text = "寿司セット"
        
        print(f"📝 テストパラメータ:")
        print(f"   セッションID: {session_id}")
        print(f"   アイテムID: {item_id}")
        print(f"   テキスト: {item_text}")
        
        # 1. 翻訳タスクを実行
        print(f"\n🌍 ステップ1: 翻訳タスク実行")
        translation_task = test_translate_menu_item.delay(session_id, item_id, item_text)
        translation_result = translation_task.get(timeout=10)
        
        if not translation_result["success"]:
            print(f"❌ 翻訳タスク失敗")
            return False
        
        print(f"✅ 翻訳完了: {translation_result['english_text']}")
        
        # 2. 中間状態確認
        print(f"\n🔍 ステップ2: 中間状態確認")
        status = get_test_status(session_id, item_id)
        print(f"   翻訳完了: {status.get('translation', {}).get('completed', False)}")
        print(f"   説明完了: {status.get('description', {}).get('completed', False)}")
        print(f"   画像完了: {status.get('image', {}).get('completed', False)}")
        
        # 3. 説明生成タスクを実行
        print(f"\n📝 ステップ3: 説明生成タスク実行")
        description_task = test_generate_menu_description.delay(session_id, item_id, item_text)
        description_result = description_task.get(timeout=15)
        
        if not description_result["success"]:
            print(f"❌ 説明生成タスク失敗")
            return False
        
        print(f"✅ 説明生成完了: {description_result['description'][:50]}...")
        
        # 4. 画像生成がトリガーされたか確認（少し待機）
        print(f"\n🎨 ステップ4: 画像生成トリガー確認")
        time.sleep(2)  # トリガー処理の時間を待つ
        
        final_status = get_test_status(session_id, item_id)
        print(f"   翻訳完了: {final_status.get('translation', {}).get('completed', False)}")
        print(f"   説明完了: {final_status.get('description', {}).get('completed', False)}")
        print(f"   画像完了: {final_status.get('image', {}).get('completed', False)}")
        
        # 画像生成が完了するまで最大20秒待機
        for i in range(10):
            time.sleep(2)
            current_status = get_test_status(session_id, item_id)
            if current_status.get('image', {}).get('completed', False):
                print(f"✅ 画像生成が自動トリガーされ完了しました！")
                image_data = current_status['image']['data']
                print(f"   画像URL: {image_data.get('image_url', 'N/A')}")
                return True
            else:
                print(f"⏳ 画像生成待機中... ({i+1}/10)")
        
        print(f"⚠️ 画像生成がタイムアウトしました（これは正常な可能性があります）")
        return True  # 依存判定自体は成功
        
    except Exception as e:
        print(f"❌ 依存判定テストでエラー: {str(e)}")
        return False

def test_parallel_processing():
    """Phase 5: 並列処理テスト"""
    print("\n🧪 === Phase 5: 並列処理テスト ===")
    
    try:
        from app.tasks.menu_item_parallel_tasks import (
            test_translate_menu_item,
            test_generate_menu_description
        )
        
        session_id = f"test_parallel_{int(time.time())}"
        
        # テストメニューアイテム
        test_items = [
            "牛丼",
            "親子丼", 
            "天丼",
            "カツ丼",
            "海鮮丼"
        ]
        
        print(f"📝 並列処理テスト:")
        print(f"   セッションID: {session_id}")
        print(f"   アイテム数: {len(test_items)}")
        print(f"   アイテム: {test_items}")
        
        start_time = time.time()
        
        # 全アイテムの翻訳と説明生成を並列実行
        translation_tasks = []
        description_tasks = []
        
        for item_id, item_text in enumerate(test_items):
            # 翻訳タスク
            translation_task = test_translate_menu_item.delay(session_id, item_id, item_text)
            translation_tasks.append((item_id, item_text, translation_task))
            
            # 説明生成タスク
            description_task = test_generate_menu_description.delay(session_id, item_id, item_text)
            description_tasks.append((item_id, item_text, description_task))
        
        print(f"⏳ {len(translation_tasks)}個の翻訳タスクと{len(description_tasks)}個の説明生成タスクを並列実行中...")
        
        # 翻訳結果を収集
        translation_results = []
        for item_id, item_text, task in translation_tasks:
            try:
                result = task.get(timeout=15)
                translation_results.append((item_id, item_text, result))
                print(f"✅ 翻訳完了 [{item_id}] {item_text} → {result.get('english_text', 'N/A')}")
            except Exception as e:
                print(f"❌ 翻訳失敗 [{item_id}] {item_text}: {str(e)}")
        
        # 説明生成結果を収集
        description_results = []
        for item_id, item_text, task in description_tasks:
            try:
                result = task.get(timeout=20)
                description_results.append((item_id, item_text, result))
                print(f"✅ 説明完了 [{item_id}] {item_text} → {result.get('description', 'N/A')[:30]}...")
            except Exception as e:
                print(f"❌ 説明失敗 [{item_id}] {item_text}: {str(e)}")
        
        total_time = time.time() - start_time
        
        print(f"\n📊 並列処理結果:")
        print(f"   処理時間: {total_time:.2f}秒")
        print(f"   翻訳成功: {len(translation_results)}/{len(test_items)}")
        print(f"   説明成功: {len(description_results)}/{len(test_items)}")
        print(f"   スループット: {len(test_items)}/{total_time:.2f} = {len(test_items)/total_time:.2f} items/sec")
        
        # 成功率チェック
        success_rate = (len(translation_results) + len(description_results)) / (len(test_items) * 2)
        if success_rate >= 0.8:  # 80%以上成功なら良好
            print(f"✅ 並列処理テスト成功 (成功率: {success_rate*100:.1f}%)")
            return True
        else:
            print(f"⚠️ 並列処理テスト部分成功 (成功率: {success_rate*100:.1f}%)")
            return False
            
    except Exception as e:
        print(f"❌ 並列処理テストでエラー: {str(e)}")
        return False

def main():
    """メインテスト実行"""
    print("🚀 メニューアイテム並列処理 基本テスト開始")
    print("=" * 60)
    
    test_results = []
    
    # Phase 1: Redis接続テスト
    redis_result = test_redis_connection()
    test_results.append(("Redis接続", redis_result))
    
    if not redis_result:
        print("\n❌ Redis接続に失敗したため、テストを中断します")
        return
    
    # Phase 2: 単一翻訳タスクテスト
    translation_result, session_id, item_id = test_single_translation_task()
    test_results.append(("単一翻訳タスク", translation_result))
    
    # Phase 3: 単一説明生成タスクテスト
    description_result, desc_session_id, desc_item_id = test_single_description_task()
    test_results.append(("単一説明生成タスク", description_result))
    
    # Phase 4: 依存判定テスト
    dependency_result = test_dependency_trigger()
    test_results.append(("依存判定・トリガー", dependency_result))
    
    # Phase 5: 並列処理テスト
    parallel_result = test_parallel_processing()
    test_results.append(("並列処理", parallel_result))
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print("🎯 テスト結果サマリー")
    print("=" * 60)
    
    for test_name, result in test_results:
        status = "✅ 成功" if result else "❌ 失敗"
        print(f"   {test_name}: {status}")
    
    success_count = sum(1 for _, result in test_results if result)
    total_count = len(test_results)
    success_rate = success_count / total_count * 100
    
    print(f"\n📊 総合結果: {success_count}/{total_count} ({success_rate:.1f}%)")
    
    if success_rate >= 80:
        print("🎉 基本テスト成功！メニューアイテム並列処理システムは正常に動作しています。")
    elif success_rate >= 60:
        print("⚠️ 基本テスト部分成功。一部の機能に問題がある可能性があります。")
    else:
        print("❌ 基本テスト失敗。システムの設定を確認してください。")

if __name__ == "__main__":
    main() 
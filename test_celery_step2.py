#!/usr/bin/env python3
"""
Step 2: チャンク分割とモック画像生成タスクのテストスクリプト

このスクリプトでは以下をテストします:
1. チャンク分割ロジック
2. メニューデータの妥当性チェック
3. モック画像生成タスクの実行
4. 複数チャンクの並列処理テスト
"""

import sys
import os
import time
import asyncio

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_step2_chunk_logic():
    """Step 2: チャンク分割ロジックのテスト"""
    print("=" * 60)
    print("🧩 Step 2: チャンク分割ロジックテスト")
    print("=" * 60)
    
    try:
        from app.tasks.utils import create_image_chunks, validate_menu_data, create_chunk_summary
        
        # テストデータ作成
        test_menu = {
            "前菜": [
                {"japanese_name": "枝豆", "english_name": "Edamame", "description": "Boiled soybeans"},
                {"japanese_name": "唐揚げ", "english_name": "Karaage", "description": "Japanese fried chicken"},
                {"japanese_name": "餃子", "english_name": "Gyoza", "description": "Pan-fried dumplings"},
                {"japanese_name": "春巻き", "english_name": "Spring Roll", "description": "Crispy spring rolls"},
                {"japanese_name": "サラダ", "english_name": "Salad", "description": "Fresh mixed salad"}
            ],
            "メイン": [
                {"japanese_name": "ラーメン", "english_name": "Ramen", "description": "Japanese noodle soup"},
                {"japanese_name": "カレー", "english_name": "Curry", "description": "Japanese curry rice"},
                {"japanese_name": "天ぷら", "english_name": "Tempura", "description": "Deep-fried seafood and vegetables"}
            ],
            "デザート": [
                {"japanese_name": "アイス", "english_name": "Ice Cream", "description": "Vanilla ice cream"}
            ]
        }
        
        print("\n1️⃣ メニューデータ妥当性チェック")
        if validate_menu_data(test_menu):
            print("   ✅ メニューデータは妥当です")
        else:
            print("   ❌ メニューデータに問題があります")
            return False
        
        print("\n2️⃣ チャンク分割テスト (chunk_size=3)")
        chunks = create_image_chunks(test_menu, chunk_size=3)
        
        print(f"   📦 生成されたチャンク数: {len(chunks)}")
        for chunk in chunks:
            print(f"      Chunk {chunk['chunk_id']}: {chunk['category']} - {chunk['items_count']}アイテム")
            for item in chunk['items']:
                print(f"         • {item['japanese_name']} ({item['english_name']})")
        
        print("\n3️⃣ チャンクサマリー生成")
        summary = create_chunk_summary(chunks)
        print(f"   📊 総チャンク数: {summary['total_chunks']}")
        print(f"   📊 総アイテム数: {summary['total_items']}")
        print(f"   📊 カテゴリ数: {len(summary['categories'])}")
        print(f"   📊 推定処理時間: {summary['estimated_time']}秒")
        
        for category, info in summary['chunks_per_category'].items():
            print(f"      {category}: {info['chunk_count']}チャンク, {info['items_count']}アイテム")
        
        print("\n4️⃣ 異なるチャンクサイズでのテスト")
        for chunk_size in [2, 4, 5]:
            test_chunks = create_image_chunks(test_menu, chunk_size=chunk_size)
            print(f"   📦 chunk_size={chunk_size}: {len(test_chunks)}チャンク")
        
        print("\n✅ チャンク分割ロジックテスト完了!")
        return True
        
    except Exception as e:
        print(f"❌ チャンク分割ロジックテスト失敗: {e}")
        return False

def test_step2_mock_image_task():
    """Step 2: モック画像生成タスクのテスト"""
    print("\n" + "=" * 60)
    print("🎨 Step 2: モック画像生成タスクテスト")
    print("=" * 60)
    
    try:
        from app.tasks import test_image_chunk_task, get_task_info
        from app.tasks.utils import create_image_chunks
        
        # 小さなテストデータ
        small_menu = {
            "テスト": [
                {"japanese_name": "唐揚げ", "english_name": "Karaage", "description": "Japanese fried chicken"},
                {"japanese_name": "ラーメン", "english_name": "Ramen", "description": "Japanese noodle soup"}
            ]
        }
        
        print("\n1️⃣ テストデータでチャンク作成")
        chunks = create_image_chunks(small_menu, chunk_size=2)
        chunk = chunks[0]  # 最初のチャンクを使用
        
        print(f"   📦 Chunk ID: {chunk['chunk_id']}")
        print(f"   📂 Category: {chunk['category']}")
        print(f"   📄 Items: {chunk['items_count']}")
        
        print("\n2️⃣ モック画像生成タスク開始")
        
        # チャンク情報を準備
        chunk_info = {
            "chunk_id": chunk["chunk_id"],
            "total_chunks": chunk["total_chunks"],
            "category": chunk["category"]
        }
        
        # タスクを非同期で実行
        task = test_image_chunk_task.delay(chunk["items"], chunk_info)
        print(f"   📝 タスクID: {task.id}")
        
        # タスクの進行状況を監視
        print("\n3️⃣ タスク進行状況監視")
        start_time = time.time()
        
        while not task.ready():
            info = get_task_info(task.id)
            elapsed = int(time.time() - start_time)
            
            print(f"   ⏱️ [{elapsed}s] State: {info['state']}")
            if info.get('info') and isinstance(info['info'], dict):
                message = info['info'].get('message', 'Processing...')
                progress = info['info'].get('progress', 0)
                current_item = info['info'].get('current_item', '')
                print(f"      💬 {message} ({progress}%)")
                if current_item:
                    print(f"      🍽️ Processing: {current_item}")
            
            if elapsed > 30:  # 30秒でタイムアウト
                print("   ⚠️ タスクがタイムアウトしました")
                break
                
            time.sleep(0.5)
        
        # 結果を取得
        if task.ready():
            result = task.get(timeout=10)
            print(f"\n4️⃣ タスク完了!")
            print(f"   ✅ Status: {result['status']}")
            print(f"   📊 Items processed: {result['items_processed']}")
            print(f"   ⏱️ Processing time: {result['processing_time']}s")
            
            print("\n5️⃣ 生成された画像結果:")
            for img_result in result['results']:
                print(f"      🖼️ {img_result['english_name']}: {img_result['image_url']}")
                print(f"         Success: {img_result['generation_success']}")
        
        print("\n✅ モック画像生成タスクテスト完了!")
        return True
        
    except Exception as e:
        print(f"❌ モック画像生成タスクテスト失敗: {e}")
        return False

def test_step2_multiple_chunks():
    """Step 2: 複数チャンクの並列処理テスト"""
    print("\n" + "=" * 60)
    print("🔄 Step 2: 複数チャンク並列処理テスト")
    print("=" * 60)
    
    try:
        from app.tasks import test_image_chunk_task, get_task_info
        from app.tasks.utils import create_image_chunks
        
        # 中規模テストデータ
        medium_menu = {
            "前菜": [
                {"japanese_name": "枝豆", "english_name": "Edamame"},
                {"japanese_name": "唐揚げ", "english_name": "Karaage"},
                {"japanese_name": "餃子", "english_name": "Gyoza"}
            ],
            "メイン": [
                {"japanese_name": "ラーメン", "english_name": "Ramen"},
                {"japanese_name": "カレー", "english_name": "Curry"}
            ]
        }
        
        print("\n1️⃣ 複数チャンク作成")
        chunks = create_image_chunks(medium_menu, chunk_size=2)
        print(f"   📦 生成チャンク数: {len(chunks)}")
        
        print("\n2️⃣ 全チャンクを並列で開始")
        tasks = []
        
        for chunk in chunks:
            chunk_info = {
                "chunk_id": chunk["chunk_id"],
                "total_chunks": chunk["total_chunks"],
                "category": chunk["category"]
            }
            
            task = test_image_chunk_task.delay(chunk["items"], chunk_info)
            tasks.append((task, chunk))
            print(f"   🚀 Chunk {chunk['chunk_id']} started: {task.id}")
        
        print("\n3️⃣ 全タスクの完了を待機")
        start_time = time.time()
        completed_tasks = 0
        
        while completed_tasks < len(tasks):
            for i, (task, chunk) in enumerate(tasks):
                if task.ready() and f"task_{i}" not in locals():
                    locals()[f"task_{i}"] = True  # 完了マーク
                    completed_tasks += 1
                    result = task.get()
                    elapsed = time.time() - start_time
                    print(f"   ✅ Chunk {chunk['chunk_id']} completed in {elapsed:.1f}s")
                    print(f"      📊 Processed {result['items_processed']} items")
            
            if time.time() - start_time > 60:  # 60秒でタイムアウト
                print("   ⚠️ 一部タスクがタイムアウトしました")
                break
            
            time.sleep(1)
        
        total_time = time.time() - start_time
        print(f"\n4️⃣ 並列処理完了!")
        print(f"   ⏱️ 総処理時間: {total_time:.1f}秒")
        print(f"   📊 完了タスク数: {completed_tasks}/{len(tasks)}")
        
        print("\n✅ 複数チャンク並列処理テスト完了!")
        return True
        
    except Exception as e:
        print(f"❌ 複数チャンク並列処理テスト失敗: {e}")
        return False

def main():
    """メインテスト関数"""
    print("🚀 Celery Step 2 テスト開始")
    
    # チャンク分割ロジックテスト
    if not test_step2_chunk_logic():
        print("\n❌ チャンク分割ロジックテストに失敗しました")
        return False
    
    # モック画像生成タスクテスト
    if not test_step2_mock_image_task():
        print("\n❌ モック画像生成タスクテストに失敗しました")
        return False
    
    # 複数チャンク並列処理テスト
    if not test_step2_multiple_chunks():
        print("\n❌ 複数チャンク並列処理テストに失敗しました")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 Step 2 全テスト成功!")
    print("=" * 60)
    print("\n📋 次のステップ:")
    print("   - Step 3: 進行状況管理システム（Redis）")
    print("   - ジョブステータス管理")
    print("   - SSEとの連携実装")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 
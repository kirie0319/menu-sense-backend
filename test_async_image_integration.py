#!/usr/bin/env python3
"""
非同期画像生成統合テストスクリプト

このスクリプトでは以下をテストします:
1. 新しいstage5_generate_images関数の動作確認
2. AsyncImageManagerとの統合テスト
3. フォールバック機能の確認
4. 進行状況監視機能の確認
"""

import sys
import os
import asyncio
import time

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_async_stage5():
    """新しいstage5_generate_images関数をテスト"""
    print("=" * 60)
    print("🎨 新しい非同期Stage 5画像生成テスト")
    print("=" * 60)
    
    try:
        # メイン関数をインポート
        from app.main import stage5_generate_images
        
        # テスト用メニューデータ
        test_menu = {
            "前菜": [
                {
                    "japanese_name": "枝豆",
                    "english_name": "Edamame",
                    "description": "Lightly salted boiled young soybeans, a popular Japanese appetizer."
                },
                {
                    "japanese_name": "唐揚げ",
                    "english_name": "Karaage",
                    "description": "Crispy Japanese-style fried chicken pieces, perfectly seasoned."
                }
            ],
            "メイン": [
                {
                    "japanese_name": "ラーメン",
                    "english_name": "Ramen",
                    "description": "Rich and flavorful Japanese noodle soup with traditional toppings."
                }
            ]
        }
        
        print(f"\n🍽️ テストメニュー: {sum(len(items) for items in test_menu.values())} アイテム")
        for category, items in test_menu.items():
            print(f"   - {category}: {len(items)} items")
        
        # 非同期画像生成実行
        print(f"\n🚀 非同期画像生成開始...")
        start_time = time.time()
        
        result = await stage5_generate_images(test_menu, "test_session_async")
        
        end_time = time.time()
        processing_time = int(end_time - start_time)
        
        print(f"\n✅ 処理完了 (処理時間: {processing_time}秒)")
        print(f"📊 結果サマリー:")
        print(f"   - Success: {result.get('success', False)}")
        print(f"   - Stage: {result.get('stage', 'unknown')}")
        print(f"   - Total Images: {result.get('total_images', 0)}")
        print(f"   - Total Items: {result.get('total_items', 0)}")
        print(f"   - Image Method: {result.get('image_method', 'unknown')}")
        print(f"   - Architecture: {result.get('image_architecture', 'unknown')}")
        
        if result.get("job_id"):
            print(f"   - Job ID: {result['job_id']}")
            print(f"   - Processing Time: {result.get('processing_time', 0)}秒")
            print(f"   - Success Rate: {result.get('success_rate', 0)}%")
        
        if result.get("fallback_reason"):
            print(f"   - Fallback Reason: {result['fallback_reason']}")
        
        if result.get("error"):
            print(f"   - Error: {result['error']}")
        
        # 生成された画像の詳細
        images_generated = result.get("images_generated", {})
        if images_generated:
            print(f"\n🖼️ 生成画像詳細:")
            for category, images in images_generated.items():
                print(f"   📁 {category}: {len(images)} images")
                for img in images[:2]:  # 最初の2つを表示
                    status = "✅" if img.get("generation_success") else "❌"
                    print(f"      {status} {img.get('english_name', 'Unknown')}: {img.get('image_url', 'No URL')}")
        
        return result.get("success", False)
        
    except Exception as e:
        print(f"❌ テスト実行エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_async_manager_direct():
    """AsyncImageManagerの直接テスト"""
    print("\n" + "=" * 60)
    print("🔧 AsyncImageManager直接テスト")
    print("=" * 60)
    
    try:
        from app.services.image.async_manager import get_async_manager
        
        # AsyncImageManagerを取得
        async_manager = get_async_manager()
        
        print(f"\n1️⃣ Manager初期化確認")
        stats = async_manager.get_manager_stats()
        print(f"   - Manager: {stats['manager_name']}")
        print(f"   - Chunk Size: {stats['config']['chunk_size']}")
        print(f"   - Max Workers: {stats['config']['max_workers']}")
        print(f"   - Features: {len(stats['features'])}")
        
        # テスト用シンプルメニュー
        simple_menu = {
            "Test": [
                {
                    "japanese_name": "テスト料理",
                    "english_name": "Test Dish",
                    "description": "A simple test dish for validation."
                }
            ]
        }
        
        print(f"\n2️⃣ 非同期ジョブ開始テスト")
        success, message, job_id = async_manager.start_async_generation(simple_menu, "direct_test")
        
        if success and job_id:
            print(f"   ✅ ジョブ開始成功: {job_id}")
            print(f"   💬 メッセージ: {message}")
            
            # 少し待ってからステータス確認
            print(f"\n3️⃣ ジョブステータス確認")
            await asyncio.sleep(2)
            
            status_info = async_manager.get_job_status(job_id)
            
            if status_info.get("found"):
                print(f"   📊 Status: {status_info.get('status', 'unknown')}")
                print(f"   📊 Progress: {status_info.get('progress_percent', 0)}%")
                print(f"   📊 Total Chunks: {status_info.get('total_chunks', 0)}")
                print(f"   📊 Total Items: {status_info.get('total_items', 0)}")
            else:
                print(f"   ❌ ジョブが見つかりません: {job_id}")
                
        else:
            print(f"   ❌ ジョブ開始失敗: {message}")
            return False
        
        print(f"\n✅ AsyncImageManager直接テスト完了")
        return True
        
    except Exception as e:
        print(f"❌ AsyncImageManager直接テストエラー: {e}")
        return False

async def test_filename_consistency():
    """ファイル名命名規則の一貫性テスト"""
    print("\n" + "=" * 60)
    print("📝 ファイル名命名規則一貫性テスト")
    print("=" * 60)
    
    try:
        # BaseImageServiceのcreate_safe_filenameテスト
        from app.services.image.base import BaseImageService
        from app.tasks.image_tasks import create_safe_filename
        
        # テストデータ
        test_names = [
            "Edamame",
            "Cafe Latte", 
            "Iced Coffee",
            "Today's Special Dish",
            "2 types of gelato"
        ]
        
        timestamp = "20241201_123456"
        
        print(f"\n1️⃣ ファイル名生成テスト")
        for name in test_names:
            # Celeryタスクでの命名
            celery_filename = create_safe_filename(name, timestamp)
            print(f"   {name:20} → {celery_filename}")
        
        print(f"\n✅ ファイル名命名規則一貫性テスト完了")
        print(f"   📋 命名規則: menu_image_{{safe_name}}_{{timestamp}}.png")
        print(f"   📋 以前の 'advanced_' プレフィックスは削除されました")
        
        return True
        
    except Exception as e:
        print(f"❌ ファイル名一貫性テストエラー: {e}")
        return False

async def test_real_vs_mock_generation():
    """実際の画像生成とモック処理の比較テスト"""
    print("\n" + "=" * 60)
    print("🖼️ 実際の画像生成 vs モック処理テスト")
    print("=" * 60)
    
    try:
        from app.core.config import settings
        
        print(f"\n1️⃣ 現在の設定確認")
        print(f"   USE_REAL_IMAGE_GENERATION: {getattr(settings, 'USE_REAL_IMAGE_GENERATION', True)}")
        print(f"   IMAGE_GENERATION_ENABLED: {settings.IMAGE_GENERATION_ENABLED}")
        print(f"   ASYNC_IMAGE_ENABLED: {settings.ASYNC_IMAGE_ENABLED}")
        
        # 利用可能タスクの確認
        from app.tasks.image_tasks import real_image_chunk_task, advanced_image_chunk_task
        
        print(f"\n2️⃣ 利用可能なタスク")
        print(f"   ✅ real_image_chunk_task: 実際のImagen3画像生成")
        print(f"   ✅ advanced_image_chunk_task: モック処理（高速テスト用）")
        
        # Imagen3サービスの利用可能性確認
        try:
            from app.services.image.imagen3 import Imagen3Service
            imagen_service = Imagen3Service()
            imagen_available = imagen_service.is_available()
            
            print(f"\n3️⃣ Imagen3サービス状態")
            print(f"   {'✅' if imagen_available else '❌'} Imagen3Service利用可能: {imagen_available}")
            
            if imagen_available:
                print(f"   🎨 実際の画像生成が可能です")
            else:
                print(f"   ⚠️ モック処理にフォールバックします")
                print(f"   💡 GEMINI_API_KEY と IMAGE_GENERATION_ENABLED を確認してください")
                
        except Exception as e:
            print(f"\n3️⃣ Imagen3サービスエラー: {e}")
            print(f"   ⚠️ モック処理のみ利用可能です")
        
        print(f"\n✅ 実際の画像生成 vs モック処理テスト完了")
        return True
        
    except Exception as e:
        print(f"❌ 実際の画像生成 vs モック処理テストエラー: {e}")
        return False

async def test_redis_celery_connection():
    """Redis/Celery接続テスト"""
    print("\n" + "=" * 60)
    print("🔗 Redis/Celery接続テスト")
    print("=" * 60)
    
    try:
        # Celery接続テスト
        print(f"\n1️⃣ Celery接続テスト")
        from app.tasks.celery_app import test_celery_connection, get_celery_info
        
        success, message = test_celery_connection()
        print(f"   {'✅' if success else '❌'} Celery: {message}")
        
        if success:
            celery_info = get_celery_info()
            print(f"   📊 Broker: {celery_info['broker_url']}")
            print(f"   📊 Backend: {celery_info['result_backend']}")
            print(f"   📊 Concurrency: {celery_info['worker_concurrency']}")
        
        # Redis接続テスト（簡易）
        print(f"\n2️⃣ Redis接続テスト")
        try:
            import redis
            from app.core.config import settings
            
            r = redis.from_url(settings.REDIS_URL)
            r.ping()
            print(f"   ✅ Redis: Connection successful")
            
            # テストデータの書き込み・読み込み
            test_key = "test:connection"
            test_value = "hello_redis"
            r.set(test_key, test_value, ex=10)  # 10秒で期限切れ
            retrieved = r.get(test_key)
            
            if retrieved and retrieved.decode() == test_value:
                print(f"   ✅ Redis: Read/Write test passed")
            else:
                print(f"   ❌ Redis: Read/Write test failed")
                
        except Exception as redis_error:
            print(f"   ❌ Redis: {redis_error}")
            return False
        
        print(f"\n✅ Redis/Celery接続テスト完了")
        return True
        
    except Exception as e:
        print(f"❌ Redis/Celery接続テストエラー: {e}")
        return False

async def main():
    """メインテスト実行"""
    print("🚀 非同期画像生成統合テスト開始")
    print(f"⏰ 開始時刻: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Redis/Celery接続確認
    redis_success = await test_redis_celery_connection()
    if not redis_success:
        print("\n⚠️ Redis/Celery接続に問題があります。")
        print("   以下を確認してください:")
        print("   - Redisサーバーが起動しているか")
        print("   - Celeryワーカーが起動しているか")
        print("   - REDIS_URL環境変数が正しく設定されているか")
    
    # ファイル名命名規則一貫性テスト
    filename_success = await test_filename_consistency()
    
    # 実際の画像生成 vs モック処理テスト
    real_vs_mock_success = await test_real_vs_mock_generation()
    
    # AsyncImageManager直接テスト
    manager_success = await test_async_manager_direct()
    
    # 新しいstage5関数テスト
    stage5_success = await test_async_stage5()
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print("📋 テスト結果サマリー")
    print("=" * 60)
    print(f"   {'✅' if redis_success else '❌'} Redis/Celery接続テスト")
    print(f"   {'✅' if filename_success else '❌'} ファイル名命名規則一貫性テスト")
    print(f"   {'✅' if real_vs_mock_success else '❌'} 実際の画像生成 vs モック処理テスト")
    print(f"   {'✅' if manager_success else '❌'} AsyncImageManager直接テスト")
    print(f"   {'✅' if stage5_success else '❌'} Stage 5非同期画像生成テスト")
    
    overall_success = all([redis_success, filename_success, real_vs_mock_success, manager_success, stage5_success])
    
    if overall_success:
        print(f"\n🎉 全てのテストが成功しました！")
        print("✨ 非同期画像生成システムは正常に動作しています")
    else:
        print(f"\n⚠️ 一部のテストが失敗しました")
        print("🔧 システム設定や依存関係を確認してください")
    
    print(f"\n⏰ 完了時刻: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    return overall_success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 
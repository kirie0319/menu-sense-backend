#!/usr/bin/env python3
"""
Step 1: Celery基盤設定テストスクリプト

このスクリプトでは以下をテストします:
1. Celery設定の読み込み
2. Redis接続確認  
3. 基本的なタスク実行テスト
"""

import sys
import os
import time

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_step1_basic_setup():
    """Step 1: 基本設定のテスト"""
    print("=" * 60)
    print("🧪 Step 1: Celery基盤設定テスト")
    print("=" * 60)
    
    # 1. モジュールインポートテスト
    print("\n1️⃣ モジュールインポートテスト")
    try:
        from app.tasks import celery_app, test_celery_connection, get_celery_info
        print("   ✅ tasksモジュールのインポート成功")
    except Exception as e:
        print(f"   ❌ tasksモジュールのインポート失敗: {e}")
        return False
    
    # 2. 設定確認
    print("\n2️⃣ Celery設定確認")
    try:
        info = get_celery_info()
        print(f"   📋 Broker URL: {info['broker_url']}")
        print(f"   📋 Result Backend: {info['result_backend']}")
        print(f"   📋 Worker Concurrency: {info['worker_concurrency']}")
        print(f"   📋 Task Serializer: {info['task_serializer']}")
        print("   ✅ Celery設定確認成功")
    except Exception as e:
        print(f"   ❌ Celery設定確認失敗: {e}")
        return False
    
    # 3. Redis接続テスト
    print("\n3️⃣ Redis接続テスト")
    try:
        success, message = test_celery_connection()
        if success:
            print(f"   ✅ {message}")
        else:
            print(f"   ❌ {message}")
            print("   💡 Redis が起動していることを確認してください")
            print("   💡 コマンド: redis-server")
            return False
    except Exception as e:
        print(f"   ❌ Redis接続テスト例外: {e}")
        return False
    
    print("\n🎉 Step 1 基本設定テスト完了！")
    return True

def test_step1_hello_world():
    """Step 1: Hello Worldタスクテスト"""
    print("\n" + "=" * 60)
    print("🌍 Hello World タスクテスト")
    print("=" * 60)
    
    try:
        from app.tasks import hello_world_task, get_task_info
        
        print("\n1️⃣ Hello Worldタスクを開始...")
        
        # タスクを非同期で実行
        task = hello_world_task.delay()
        print(f"   📝 タスクID: {task.id}")
        
        # タスクの進行状況を監視
        print("\n2️⃣ タスク進行状況監視...")
        start_time = time.time()
        
        while not task.ready():
            # タスクの現在の状態を取得
            info = get_task_info(task.id)
            elapsed = int(time.time() - start_time)
            
            print(f"   ⏱️ [{elapsed}s] State: {info['state']}")
            if info.get('info') and isinstance(info['info'], dict):
                message = info['info'].get('message', 'Processing...')
                progress = info['info'].get('progress', 0)
                print(f"      💬 {message} ({progress}%)")
            
            time.sleep(1)
        
        # 結果を取得
        result = task.get(timeout=10)
        print(f"\n3️⃣ タスク完了!")
        print(f"   ✅ Status: {result['status']}")
        print(f"   💬 Message: {result['message']}")
        print(f"   📊 Progress: {result['progress']}%")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Hello Worldタスクテスト失敗: {e}")
        return False

def main():
    """メインテスト関数"""
    print("🚀 Celery Step 1 テスト開始")
    
    # 基本設定テスト
    if not test_step1_basic_setup():
        print("\n❌ 基本設定テストに失敗しました")
        print("💡 Redisが起動していることを確認してください:")
        print("   redis-server")
        return False
    
    # Hello Worldタスクテスト
    if not test_step1_hello_world():
        print("\n❌ Hello Worldタスクテストに失敗しました")
        print("💡 Celeryワーカーが起動していることを確認してください:")
        print("   celery -A app.tasks.celery_app worker --loglevel=info")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 Step 1 全テスト成功!")
    print("=" * 60)
    print("\n📋 次のステップ:")
    print("   - Step 2: チャンク分割ロジックの実装")
    print("   - モック画像生成タスクのテスト")
    print("   - 進行状況管理システムの実装")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 
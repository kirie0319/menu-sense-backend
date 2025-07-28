#!/usr/bin/env python3
"""
Search Image Task Test Script - Menu Processor v2
修正されたsearch_image_taskの動作確認用テストスクリプト
"""

import asyncio
import sys
import time
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent.parent))

from app_2.tasks.search_image_task import search_image_menu_task
from app_2.core.config import settings
from app_2.utils.logger import get_logger

logger = get_logger("test_search_image")


def test_search_image_task():
    """search_image_taskの動作テスト"""
    
    print("🔍 Search Image Task Test Starting...")
    print("=" * 60)
    
    # 設定確認
    print("📊 Configuration Check:")
    print(f"  Redis URL: {settings.celery.redis_url}")
    print(f"  Google Search Engine ID: {settings.ai.google_search_engine_id}")
    print(f"  Gemini API Key: {'✅ Set' if settings.ai.gemini_api_key else '❌ Missing'}")
    print()
    
    # テストデータ準備
    test_session_id = f"test-session-{int(time.time())}"
    test_menu_items = [
        {
            "id": "test-menu-001",
            "name": "寿司",
            "category": "Main Course",
            "translation": "Sushi"
        },
        {
            "id": "test-menu-002", 
            "name": "ラーメン",
            "category": "Main Course",
            "translation": "Ramen"
        },
        {
            "id": "test-menu-003",
            "name": "コーヒー",
            "category": "Drinks",
            "translation": "Coffee"
        }
    ]
    
    print(f"🎯 Test Data:")
    print(f"  Session ID: {test_session_id}")
    print(f"  Menu Items: {len(test_menu_items)}")
    for item in test_menu_items:
        print(f"    - {item['name']} ({item['translation']}) [{item['category']}]")
    print()
    
    try:
        print("🚀 Sending search_image_task to Celery...")
        
        # タスクを非同期で送信
        result = search_image_menu_task.delay(test_session_id, test_menu_items)
        
        print(f"✅ Task sent successfully!")
        print(f"  Task ID: {result.id}")
        print(f"  Task State: {result.state}")
        print()
        
        print("⏳ Waiting for task completion...")
        
        # タスク完了を待機（最大60秒）
        timeout = 60
        start_time = time.time()
        
        while not result.ready() and (time.time() - start_time) < timeout:
            print(f"  Status: {result.state} (elapsed: {int(time.time() - start_time)}s)")
            time.sleep(2)
        
        if result.ready():
            print(f"🎉 Task completed!")
            print(f"  Final State: {result.state}")
            
            if result.successful():
                task_result = result.get()
                print("✅ Task executed successfully!")
                print("📊 Results:")
                print(f"  Status: {task_result.get('status', 'unknown')}")
                print(f"  Session ID: {task_result.get('session_id', 'unknown')}")
                print(f"  Task ID: {task_result.get('task_id', 'unknown')}")
                print(f"  Completed Items: {task_result.get('completed_items', 0)}")
                print(f"  Total Items: {task_result.get('total_items', 0)}")
                print(f"  Success Rate: {task_result.get('success_rate', 0)}%")
                
                return True
                
            else:
                print("❌ Task failed!")
                try:
                    error = result.get(propagate=True)
                    print(f"  Error: {error}")
                except Exception as e:
                    print(f"  Exception: {e}")
                return False
                
        else:
            print("⏰ Task timed out!")
            print(f"  Current State: {result.state}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_worker_status():
    """ワーカーの状態確認"""
    
    print("🔧 Worker Status Check...")
    print("=" * 60)
    
    try:
        from celery import current_app
        
        # アクティブなワーカーを確認
        inspect = current_app.control.inspect()
        
        print("📋 Active Workers:")
        active_workers = inspect.active()
        if active_workers:
            for worker_name, tasks in active_workers.items():
                print(f"  Worker: {worker_name}")
                print(f"    Active Tasks: {len(tasks)}")
                for task in tasks:
                    print(f"      - {task.get('name', 'unknown')} (ID: {task.get('id', 'unknown')})")
        else:
            print("  ⚠️ No active workers found")
        
        print()
        
        # 登録されたタスクを確認
        print("📝 Registered Tasks:")
        registered = inspect.registered()
        if registered:
            for worker_name, tasks in registered.items():
                print(f"  Worker: {worker_name}")
                search_tasks = [task for task in tasks if 'search_image' in task]
                if search_tasks:
                    for task in search_tasks:
                        print(f"    ✅ {task}")
                else:
                    print("    ⚠️ No search_image tasks found")
        else:
            print("  ❌ No registered tasks found")
            
        print()
        
        # キューの状態確認
        print("📦 Queue Status:")
        reserved = inspect.reserved()
        if reserved:
            for worker_name, tasks in reserved.items():
                search_tasks = [task for task in tasks if 'search_image' in task.get('name', '')]
                if search_tasks:
                    print(f"  Worker: {worker_name} - {len(search_tasks)} search tasks in queue")
        else:
            print("  ✅ No reserved tasks")
            
    except Exception as e:
        print(f"❌ Worker status check failed: {e}")


def main():
    """メインテスト実行"""
    
    print("🧪 Search Image Task Integration Test")
    print("=" * 60)
    print()
    
    # ワーカー状態確認
    test_worker_status()
    print()
    
    # タスクテスト実行
    success = test_search_image_task()
    
    print()
    print("=" * 60)
    if success:
        print("🎉 All tests passed! Search image task is working correctly.")
    else:
        print("❌ Tests failed! Check logs and worker status.")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 
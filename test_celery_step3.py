#!/usr/bin/env python3
"""
Step 3: Redis進行状況管理システムのテストスクリプト

このスクリプトでは以下をテストします:
1. Redis進行状況管理機能
2. ジョブ情報の保存・取得
3. チャンク結果の管理
4. 全体進行状況の計算
"""

import sys
import os
import time

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_step3_redis_progress_management():
    """Step 3: Redis進行状況管理のテスト"""
    print("=" * 60)
    print("🔄 Step 3: Redis進行状況管理テスト")
    print("=" * 60)
    
    try:
        from app.tasks.utils import (
            save_job_info, get_job_info, update_job_progress, 
            save_chunk_result, get_chunk_result, get_all_chunk_results,
            calculate_job_progress, cleanup_job_data, generate_job_id
        )
        
        # テストジョブID生成
        test_job_id = generate_job_id()
        print(f"\n1️⃣ テストジョブID生成: {test_job_id}")
        
        # ジョブ情報保存テスト
        print("\n2️⃣ ジョブ情報保存テスト")
        job_data = {
            "job_id": test_job_id,
            "status": "pending",
            "total_chunks": 3,
            "session_id": "test_session_123",
            "created_at": time.time(),
            "menu_data": {
                "前菜": ["item1", "item2"],
                "メイン": ["item3", "item4"],
                "デザート": ["item5"]
            }
        }
        
        if save_job_info(test_job_id, job_data):
            print("   ✅ ジョブ情報保存成功")
        else:
            print("   ❌ ジョブ情報保存失敗")
            return False
        
        # ジョブ情報取得テスト
        print("\n3️⃣ ジョブ情報取得テスト")
        retrieved_job = get_job_info(test_job_id)
        if retrieved_job:
            print(f"   ✅ ジョブ情報取得成功: {retrieved_job['status']}")
            print(f"      Total chunks: {retrieved_job['total_chunks']}")
            print(f"      Session ID: {retrieved_job['session_id']}")
        else:
            print("   ❌ ジョブ情報取得失敗")
            return False
        
        # 進行状況更新テスト
        print("\n4️⃣ 進行状況更新テスト")
        progress_updates = [
            {"chunk_1": {"status": "processing", "progress": 25, "message": "Chunk 1 started"}},
            {"chunk_2": {"status": "processing", "progress": 10, "message": "Chunk 2 started"}},
            {"chunk_1": {"status": "processing", "progress": 75, "message": "Chunk 1 almost done"}},
        ]
        
        for i, progress in enumerate(progress_updates):
            if update_job_progress(test_job_id, progress):
                print(f"   ✅ 進行状況更新 {i+1}/3 成功")
            else:
                print(f"   ❌ 進行状況更新 {i+1}/3 失敗")
        
        # チャンク結果保存テスト
        print("\n5️⃣ チャンク結果保存テスト")
        chunk_results = [
            {
                "chunk_id": 1,
                "status": "completed",
                "results": [
                    {"japanese_name": "枝豆", "english_name": "Edamame", "image_url": "/uploads/edamame.png"},
                    {"japanese_name": "唐揚げ", "english_name": "Karaage", "image_url": "/uploads/karaage.png"}
                ]
            },
            {
                "chunk_id": 2,
                "status": "completed", 
                "results": [
                    {"japanese_name": "ラーメン", "english_name": "Ramen", "image_url": "/uploads/ramen.png"}
                ]
            },
            {
                "chunk_id": 3,
                "status": "failed",
                "error": "Mock error for testing"
            }
        ]
        
        for chunk_result in chunk_results:
            chunk_id = chunk_result["chunk_id"]
            if save_chunk_result(test_job_id, chunk_id, chunk_result):
                print(f"   ✅ Chunk {chunk_id} 結果保存成功")
            else:
                print(f"   ❌ Chunk {chunk_id} 結果保存失敗")
        
        # チャンク結果取得テスト
        print("\n6️⃣ チャンク結果取得テスト")
        for chunk_id in [1, 2, 3]:
            chunk_result = get_chunk_result(test_job_id, chunk_id)
            if chunk_result:
                status = chunk_result.get("status", "unknown")
                print(f"   ✅ Chunk {chunk_id}: {status}")
                if status == "completed":
                    print(f"      Results: {len(chunk_result.get('results', []))} items")
                elif status == "failed":
                    print(f"      Error: {chunk_result.get('error', 'No error info')}")
            else:
                print(f"   ❌ Chunk {chunk_id} 結果取得失敗")
        
        # 全チャンク結果取得テスト
        print("\n7️⃣ 全チャンク結果取得テスト")
        all_chunks = get_all_chunk_results(test_job_id)
        print(f"   📦 取得チャンク数: {len(all_chunks)}")
        for chunk_id, result in all_chunks.items():
            print(f"      Chunk {chunk_id}: {result.get('status', 'unknown')}")
        
        # 全体進行状況計算テスト
        print("\n8️⃣ 全体進行状況計算テスト")
        overall_progress = calculate_job_progress(test_job_id)
        if "error" not in overall_progress:
            print(f"   📊 進行状況: {overall_progress['progress_percent']}%")
            print(f"   📊 ステータス: {overall_progress['status']}")
            print(f"   📊 完了チャンク: {overall_progress['completed_chunks']}/{overall_progress['total_chunks']}")
            print(f"   📊 失敗チャンク: {overall_progress['failed_chunks']}")
        else:
            print(f"   ❌ 進行状況計算エラー: {overall_progress['error']}")
        
        # クリーンアップテスト
        print("\n9️⃣ クリーンアップテスト")
        if cleanup_job_data(test_job_id):
            print("   ✅ ジョブデータ削除成功")
            
            # 削除確認
            if get_job_info(test_job_id) is None:
                print("   ✅ ジョブデータ削除確認")
            else:
                print("   ⚠️ ジョブデータが残っています")
        else:
            print("   ❌ ジョブデータ削除失敗")
        
        print("\n✅ Redis進行状況管理テスト完了!")
        return True
        
    except Exception as e:
        print(f"❌ Redis進行状況管理テスト失敗: {e}")
        return False

def main():
    """メインテスト関数"""
    print("🚀 Celery Step 3 テスト開始")
    
    # Redis進行状況管理テスト
    if not test_step3_redis_progress_management():
        print("\n❌ Redis進行状況管理テストに失敗しました")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 Step 3 テスト成功!")
    print("=" * 60)
    print("\n📋 次のステップ:")
    print("   - Step 4: 非同期APIエンドポイントの実装")
    print("   - async_manager.py の実装")
    print("   - 既存SSEシステムとの連携")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 
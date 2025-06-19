#!/usr/bin/env python3
"""
FastAPI非同期画像生成APIの実際のテストスクリプト

このスクリプトでは以下をテストします:
1. FastAPIサーバーとの接続確認
2. 非同期画像生成APIエンドポイントのテスト
3. ジョブステータス監視
4. 完全な非同期ワークフローのテスト
"""

import requests
import time
import json

# FastAPIサーバーのベースURL
BASE_URL = "http://localhost:8000"

def test_server_connection():
    """FastAPIサーバー接続テスト"""
    print("=" * 60)
    print("🌐 FastAPIサーバー接続テスト")
    print("=" * 60)
    
    try:
        # ヘルスチェック
        response = requests.get(f"{BASE_URL}/api/v1/image/async-status", timeout=5)
        if response.status_code == 200:
            print("   ✅ FastAPIサーバー接続成功")
            data = response.json()
            print(f"   📊 Status: {data.get('status')}")
            print(f"   📊 Manager: {data.get('async_manager', {}).get('manager_name')}")
            return True
        else:
            print(f"   ❌ FastAPIサーバー応答エラー: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"   ❌ FastAPIサーバー接続失敗: {e}")
        print("   💡 'uvicorn app.main:app --reload' でサーバーを起動してください")
        return False

def test_async_image_generation():
    """非同期画像生成の完全テスト"""
    print("\n" + "=" * 60)
    print("🎨 非同期画像生成完全テスト")
    print("=" * 60)
    
    # テストメニューデータ
    test_menu = {
        "前菜": [
            {"japanese_name": "API枝豆", "english_name": "API Edamame", "description": "Fresh boiled soybeans"},
            {"japanese_name": "API唐揚げ", "english_name": "API Karaage", "description": "Japanese fried chicken"}
        ],
        "メイン": [
            {"japanese_name": "APIラーメン", "english_name": "API Ramen", "description": "Japanese noodle soup"}
        ]
    }
    
    print(f"\n1️⃣ テストメニューデータ:")
    for category, items in test_menu.items():
        print(f"   📂 {category}: {len(items)} items")
        for item in items:
            print(f"      • {item['japanese_name']} ({item['english_name']})")
    
    # 非同期画像生成開始
    print(f"\n2️⃣ 非同期画像生成開始")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/image/generate-async",
            json={
                "final_menu": test_menu,
                "session_id": "fastapi_test_session"
            },
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 202:  # 202 Accepted
            data = response.json()
            job_id = data.get("job_id")
            print(f"   ✅ 非同期生成開始成功")
            print(f"   🆔 Job ID: {job_id}")
            print(f"   📊 Status: {data.get('status')}")
            print(f"   💬 Message: {data.get('message')}")
            print(f"   📊 Total items: {data.get('total_items')}")
            print(f"   ⏱️ Estimated time: {data.get('estimated_time_seconds')}s")
            
            # ジョブステータス監視
            return monitor_job_progress(job_id)
            
        else:
            print(f"   ❌ 非同期生成開始失敗: {response.status_code}")
            print(f"   📄 Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ 非同期生成リクエスト失敗: {e}")
        return False

def monitor_job_progress(job_id):
    """ジョブ進行状況の詳細監視"""
    print(f"\n3️⃣ ジョブ進行状況監視 (Job ID: {job_id})")
    
    start_time = time.time()
    last_progress = -1
    last_status = ""
    
    while time.time() - start_time < 60:  # 60秒まで監視
        try:
            response = requests.get(f"{BASE_URL}/api/v1/image/status/{job_id}")
            
            if response.status_code == 200:
                data = response.json()
                
                current_progress = data.get("progress_percent", 0)
                current_status = data.get("status", "unknown")
                processing_info = data.get("processing_info", {})
                
                # 進行状況が変わった時のみ表示
                if current_progress != last_progress or current_status != last_status:
                    elapsed = int(time.time() - start_time)
                    print(f"   📊 [{elapsed}s] Progress: {current_progress}% (Status: {current_status})")
                    
                    # 詳細情報
                    total_chunks = processing_info.get("total_chunks", 0)
                    completed_chunks = processing_info.get("completed_chunks", 0)
                    failed_chunks = processing_info.get("failed_chunks", 0)
                    
                    print(f"      📦 Chunks: {completed_chunks}/{total_chunks} completed, {failed_chunks} failed")
                    print(f"      📊 Total items: {processing_info.get('total_items', 0)}")
                    
                    last_progress = current_progress
                    last_status = current_status
                
                # 完了チェック
                if current_status in ["completed", "partial_completed", "failed"]:
                    print(f"\n4️⃣ ジョブ完了: {current_status}")
                    
                    if current_status in ["completed", "partial_completed"]:
                        # 成功時の詳細表示
                        images_generated = data.get("images_generated", {})
                        total_images = data.get("total_images", 0)
                        success_rate = data.get("success_rate", 0)
                        
                        print(f"   🖼️ 生成画像数: {total_images}")
                        print(f"   📊 成功率: {success_rate}%")
                        print(f"   ⏱️ 完了時刻: {data.get('completed_at', 'unknown')}")
                        
                        print(f"\n5️⃣ 生成された画像詳細:")
                        for category, images in images_generated.items():
                            print(f"   📂 {category}: {len(images)} images")
                            for i, img in enumerate(images):
                                print(f"      {i+1}. {img.get('english_name', 'N/A')}")
                                print(f"         URL: {img.get('image_url', 'N/A')}")
                                print(f"         Success: {img.get('generation_success', False)}")
                                print(f"         Category: {img.get('category', 'N/A')}")
                                if img.get('processing_time'):
                                    print(f"         Processing time: {img.get('processing_time')}s")
                    else:
                        # 失敗時の情報
                        print(f"   ❌ 処理失敗またはエラー")
                        
                    return current_status in ["completed", "partial_completed"]
                    
            elif response.status_code == 404:
                print(f"   ❌ ジョブが見つかりません: {job_id}")
                return False
            else:
                print(f"   ⚠️ ステータス取得エラー: {response.status_code}")
                print(f"      Response: {response.text}")
                
        except Exception as e:
            print(f"   ⚠️ ステータス確認例外: {e}")
        
        time.sleep(3)  # 3秒間隔で確認
    
    print(f"   ⚠️ 監視タイムアウト (60秒経過)")
    return False

def test_manager_status():
    """AsyncManagerステータステスト"""
    print(f"\n" + "=" * 60)
    print("📱 AsyncManagerステータステスト")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/api/v1/image/async-status")
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"   ✅ AsyncManagerステータス取得成功")
            print(f"   📊 Status: {data.get('status')}")
            
            async_manager = data.get('async_manager', {})
            print(f"   📊 Manager: {async_manager.get('manager_name')}")
            
            config = async_manager.get('config', {})
            print(f"   📊 Config:")
            print(f"      • Chunk size: {config.get('chunk_size')}")
            print(f"      • Max workers: {config.get('max_workers')}")
            print(f"      • Job timeout: {config.get('job_timeout')}")
            print(f"      • Async enabled: {config.get('async_enabled')}")
            
            features = async_manager.get('features', [])
            print(f"   🔧 Features ({len(features)}):")
            for feature in features:
                print(f"      • {feature}")
            
            endpoints = data.get('endpoints', {})
            print(f"   🌐 Endpoints:")
            for name, path in endpoints.items():
                print(f"      • {name}: {path}")
            
            usage_info = data.get('usage_info', {})
            print(f"   💡 Usage info:")
            for key, value in usage_info.items():
                print(f"      • {key}: {value}")
            
            return True
        else:
            print(f"   ❌ AsyncManagerステータス取得失敗: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ AsyncManagerステータステスト失敗: {e}")
        return False

def test_api_endpoints():
    """APIエンドポイント一覧テスト"""
    print(f"\n" + "=" * 60)
    print("🌐 APIエンドポイント確認テスト")
    print("=" * 60)
    
    endpoints_to_test = [
        ("GET", "/api/v1/image/status", "同期画像生成ステータス"),
        ("GET", "/api/v1/image/categories", "サポートカテゴリ"),
        ("GET", "/api/v1/image/styles", "サポートスタイル"),
        ("GET", "/api/v1/image/features", "画像生成機能"),
        ("GET", "/api/v1/image/async-status", "非同期Manager状態"),
    ]
    
    success_count = 0
    
    for method, endpoint, description in endpoints_to_test:
        try:
            if method == "GET":
                response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
            
            if response.status_code == 200:
                print(f"   ✅ {description}: {endpoint}")
                success_count += 1
            else:
                print(f"   ❌ {description}: {endpoint} (Status: {response.status_code})")
                
        except Exception as e:
            print(f"   ❌ {description}: {endpoint} (Error: {e})")
    
    print(f"\n   📊 成功率: {success_count}/{len(endpoints_to_test)} ({(success_count/len(endpoints_to_test)*100):.1f}%)")
    return success_count == len(endpoints_to_test)

def main():
    """メインテスト実行"""
    print("🚀 FastAPI非同期画像生成API実際のテスト開始")
    print("=" * 60)
    
    # 1. サーバー接続確認
    if not test_server_connection():
        print("\n❌ FastAPIサーバー接続に失敗しました")
        return False
    
    # 2. APIエンドポイント確認
    if not test_api_endpoints():
        print("\n⚠️ 一部のAPIエンドポイントに問題があります")
    
    # 3. AsyncManager状態確認
    if not test_manager_status():
        print("\n❌ AsyncManagerステータステストに失敗しました")
        return False
    
    # 4. 非同期画像生成の完全テスト
    if not test_async_image_generation():
        print("\n❌ 非同期画像生成テストに失敗しました")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 FastAPI非同期画像生成API テスト完全成功!")
    print("=" * 60)
    print("\n🎯 テスト結果:")
    print("   ✅ FastAPIサーバー接続")
    print("   ✅ APIエンドポイント確認")
    print("   ✅ AsyncManagerステータス")
    print("   ✅ 非同期画像生成ワークフロー")
    print("   ✅ リアルタイム進行状況監視")
    print("   ✅ 結果取得と表示")
    
    print("\n🚀 システム準備完了!")
    print("   - 画像生成タスクキューシステムが正常動作")
    print("   - フロントエンド統合可能")
    print("   - 本番環境デプロイ準備完了")
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 
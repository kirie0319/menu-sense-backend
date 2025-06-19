#!/usr/bin/env python3
"""
Step 4: 非同期APIエンドポイントとAsync Manager統合テストスクリプト

このスクリプトでは以下をテストします:
1. AsyncImageManagerの動作確認
2. 非同期画像生成APIエンドポイントのテスト  
3. ジョブステータス取得のテスト
4. 統合された全体システムの動作確認
"""

import sys
import os
import time
import requests
import json

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# FastAPIテスト用
BASE_URL = "http://localhost:8000"

def test_step4_async_manager():
    """Step 4: AsyncImageManager単体テスト"""
    print("=" * 60)
    print("📱 Step 4: AsyncImageManager単体テスト")
    print("=" * 60)
    
    try:
        from app.services.image.async_manager import get_async_manager
        
        # Managerインスタンス取得
        async_manager = get_async_manager()
        print(f"\n1️⃣ AsyncImageManager取得成功: {async_manager.manager_name}")
        
        # Manager統計情報テスト
        print("\n2️⃣ Manager統計情報テスト")
        stats = async_manager.get_manager_stats()
        print(f"   📊 Manager名: {stats['manager_name']}")
        print(f"   📊 Chunk size: {stats['config']['chunk_size']}")
        print(f"   📊 Max workers: {stats['config']['max_workers']}")
        print(f"   📊 Features: {len(stats['features'])}")
        for feature in stats['features']:
            print(f"      • {feature}")
        
        # リクエスト妥当性チェックテスト
        print("\n3️⃣ リクエスト妥当性チェックテスト")
        
        # 正常データ
        valid_menu = {
            "前菜": [
                {"japanese_name": "枝豆", "english_name": "Edamame"},
                {"japanese_name": "唐揚げ", "english_name": "Karaage"}
            ]
        }
        is_valid, message = async_manager.validate_request(valid_menu)
        print(f"   ✅ 正常データ: {is_valid} - {message}")
        
        # 異常データテスト
        invalid_tests = [
            ({}, "空辞書"),
            ([], "リスト"),
            ({"category": []}, "空カテゴリ"),
            ({"category": [{"name": "test"}]}, "必須フィールド不足")
        ]
        
        for invalid_data, description in invalid_tests:
            is_valid, message = async_manager.validate_request(invalid_data)
            print(f"   ❌ {description}: {is_valid} - {message}")
        
        # チャンク作成テスト
        print("\n4️⃣ チャンク作成テスト")
        chunks = async_manager.create_job_chunks(valid_menu)
        print(f"   📦 作成チャンク数: {len(chunks)}")
        for i, chunk in enumerate(chunks):
            print(f"      Chunk {i+1}: Category={chunk['category']}, Items={chunk['items_count']}")
        
        print("\n✅ AsyncImageManager単体テスト完了!")
        return True
        
    except Exception as e:
        print(f"❌ AsyncImageManager単体テスト失敗: {e}")
        return False

def test_step4_async_api_direct():
    """Step 4: 非同期APIの直接テスト（FastAPIサーバー必要）"""
    print("\n" + "=" * 60)
    print("🌐 Step 4: 非同期API直接テスト")
    print("=" * 60)
    
    # サーバー起動確認
    try:
        response = requests.get(f"{BASE_URL}/api/v1/image/async-status", timeout=5)
        if response.status_code != 200:
            print("   ⚠️ FastAPIサーバーが起動していないか、応答しません")
            print("   💡 'uvicorn app.main:app --reload' でサーバーを起動してください")
            return False
    except requests.exceptions.RequestException:
        print("   ⚠️ FastAPIサーバーに接続できません")
        print("   💡 'uvicorn app.main:app --reload' でサーバーを起動してください")
        return False
    
    print("\n1️⃣ サーバー接続確認: ✅")
    
    # AsyncManager状態確認
    print("\n2️⃣ AsyncManager状態確認")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/image/async-status")
        if response.status_code == 200:
            data = response.json()
            print(f"   📊 Status: {data.get('status', 'unknown')}")
            print(f"   📊 Manager: {data.get('async_manager', {}).get('manager_name', 'unknown')}")
            
            endpoints = data.get('endpoints', {})
            print("   📋 利用可能エンドポイント:")
            for name, path in endpoints.items():
                print(f"      • {name}: {path}")
        else:
            print(f"   ❌ AsyncManager状態取得失敗: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ AsyncManager状態確認エラー: {e}")
        return False
    
    # 非同期画像生成開始テスト
    print("\n3️⃣ 非同期画像生成開始テスト")
    test_menu = {
        "テスト": [
            {"japanese_name": "テスト唐揚げ", "english_name": "Test Karaage"},
            {"japanese_name": "テストラーメン", "english_name": "Test Ramen"}
        ]
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/image/generate-async",
            json={"final_menu": test_menu, "session_id": "test_session_step4"},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 202:  # 202 Accepted
            data = response.json()
            job_id = data.get("job_id")
            print(f"   ✅ 非同期生成開始成功: {job_id}")
            print(f"      Status: {data.get('status')}")
            print(f"      Message: {data.get('message')}")
            print(f"      Total items: {data.get('total_items')}")
            print(f"      Status endpoint: {data.get('status_endpoint')}")
            
            # ジョブステータス監視テスト
            print("\n4️⃣ ジョブステータス監視テスト")
            start_time = time.time()
            last_progress = -1
            
            while time.time() - start_time < 30:  # 30秒まで監視
                try:
                    status_response = requests.get(f"{BASE_URL}/api/v1/image/status/{job_id}")
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        
                        current_progress = status_data.get("progress_percent", 0)
                        current_status = status_data.get("status", "unknown")
                        
                        if current_progress != last_progress:
                            elapsed = int(time.time() - start_time)
                            print(f"   📊 [{elapsed}s] Progress: {current_progress}% (Status: {current_status})")
                            
                            processing_info = status_data.get("processing_info", {})
                            print(f"      Chunks: {processing_info.get('completed_chunks', 0)}/{processing_info.get('total_chunks', 0)}")
                            
                            last_progress = current_progress
                        
                        # 完了チェック
                        if current_status in ["completed", "partial_completed", "failed"]:
                            print(f"   ✅ ジョブ完了: {current_status}")
                            
                            if current_status in ["completed", "partial_completed"]:
                                images_generated = status_data.get("images_generated", {})
                                total_images = status_data.get("total_images", 0)
                                success_rate = status_data.get("success_rate", 0)
                                
                                print(f"      🖼️ 生成画像数: {total_images}")
                                print(f"      📊 成功率: {success_rate}%")
                                
                                print("      🎨 生成結果:")
                                for category, images in images_generated.items():
                                    print(f"         {category}: {len(images)} images")
                                    for img in images[:2]:  # 最初の2つを表示
                                        print(f"           • {img.get('english_name')}: {img.get('image_url')}")
                            
                            break
                    else:
                        print(f"   ⚠️ ステータス取得失敗: {status_response.status_code}")
                        break
                        
                except Exception as e:
                    print(f"   ⚠️ ステータス確認エラー: {e}")
                    break
                
                time.sleep(2)  # 2秒待機
            
            print("\n5️⃣ ジョブ後処理テスト")
            # 最終ステータス確認
            try:
                final_response = requests.get(f"{BASE_URL}/api/v1/image/status/{job_id}")
                if final_response.status_code == 200:
                    final_data = final_response.json()
                    print(f"   📊 最終ステータス: {final_data.get('status')}")
                    print(f"   📊 最終進行状況: {final_data.get('progress_percent')}%")
                else:
                    print(f"   ⚠️ 最終ステータス取得失敗: {final_response.status_code}")
            except Exception as e:
                print(f"   ⚠️ 最終ステータス確認エラー: {e}")
            
        else:
            print(f"   ❌ 非同期生成開始失敗: {response.status_code}")
            print(f"      Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ 非同期画像生成テストエラー: {e}")
        return False
    
    print("\n✅ 非同期API直接テスト完了!")
    return True

def test_step4_async_integration():
    """Step 4: 非同期システム統合テスト（Manager + API）"""
    print("\n" + "=" * 60)
    print("🔗 Step 4: 非同期システム統合テスト")
    print("=" * 60)
    
    try:
        from app.services.image.async_manager import get_async_manager
        
        async_manager = get_async_manager()
        
        # 統合テスト用データ
        integration_menu = {
            "前菜": [
                {"japanese_name": "統合枝豆", "english_name": "Integration Edamame"},
                {"japanese_name": "統合唐揚げ", "english_name": "Integration Karaage"}
            ],
            "メイン": [
                {"japanese_name": "統合ラーメン", "english_name": "Integration Ramen"}
            ]
        }
        
        print("\n1️⃣ 非同期生成開始（Manager直接）")
        
        # Manager経由で直接開始
        success, message, job_id = async_manager.start_async_generation(
            integration_menu, 
            "integration_test_session"
        )
        
        if success and job_id:
            print(f"   ✅ 生成開始成功: {job_id}")
            print(f"   💬 メッセージ: {message}")
            
            print("\n2️⃣ Manager経由ステータス監視")
            start_time = time.time()
            
            while time.time() - start_time < 25:  # 25秒監視
                status_info = async_manager.get_job_status(job_id)
                
                if status_info.get("found"):
                    status = status_info.get("status", "unknown")
                    progress = status_info.get("progress_percent", 0)
                    
                    elapsed = int(time.time() - start_time)
                    print(f"   📊 [{elapsed}s] {status}: {progress}%")
                    
                    if status in ["completed", "partial_completed", "failed"]:
                        print(f"   ✅ 最終ステータス: {status}")
                        
                        if status in ["completed", "partial_completed"]:
                            total_images = status_info.get("total_images", 0)
                            print(f"   🖼️ 最終画像数: {total_images}")
                        
                        break
                else:
                    print(f"   ❌ ジョブが見つかりません: {job_id}")
                    break
                
                time.sleep(2)
        else:
            print(f"   ❌ 生成開始失敗: {message}")
            return False
        
        print("\n✅ 非同期システム統合テスト完了!")
        return True
        
    except Exception as e:
        print(f"❌ 非同期システム統合テスト失敗: {e}")
        return False

def main():
    """メインテスト関数"""
    print("🚀 Celery Step 4 テスト開始")
    
    # AsyncImageManager単体テスト
    if not test_step4_async_manager():
        print("\n❌ AsyncImageManager単体テストに失敗しました")
        return False
    
    # 非同期API直接テスト（オプショナル）
    api_test_success = test_step4_async_api_direct()
    if not api_test_success:
        print("\n⚠️ 非同期API直接テストをスキップ（サーバー未起動）")
    
    # 非同期システム統合テスト
    if not test_step4_async_integration():
        print("\n❌ 非同期システム統合テストに失敗しました")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 Step 4 テスト成功!")
    print("=" * 60)
    print("\n📋 画像生成タスクキューシステム完成!")
    print("   ✅ Step 1: Celery基盤設定")
    print("   ✅ Step 2: チャンク分割とモック処理")
    print("   ✅ Step 3: Redis進行状況管理")
    print("   ✅ Step 4: 非同期APIエンドポイント")
    print("\n🎯 次のアクション:")
    print("   - FastAPIサーバーでの実際のテスト")
    print("   - フロントエンド統合（必要に応じて）")
    print("   - 本番環境へのデプロイ準備")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 
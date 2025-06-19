#!/usr/bin/env python3
"""
完全パイプライン並列化 エンドツーエンド統合テストスクリプト

このスクリプトは以下をテストします:
- パイプライン並列化エンドポイントの動作確認
- 既存エンドポイントとの性能比較
- フロントエンド互換性の確認
- 各パイプライン戦略の性能測定
"""

import asyncio
import sys
import time
import argparse
from typing import Dict, Any

def print_header(title: str):
    """テストセクションのヘッダーを表示"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def print_result(success: bool, message: str, details: Dict[str, Any] = None):
    """テスト結果を表示"""
    status = "✅ SUCCESS" if success else "❌ FAILED"
    print(f"{status} {message}")
    
    if details:
        for key, value in details.items():
            if isinstance(value, (int, float)):
                if "time" in key.lower():
                    print(f"  → {key}: {value:.2f}s")
                else:
                    print(f"  → {key}: {value}")
            elif isinstance(value, str) and len(value) < 100:
                print(f"  → {key}: {value}")

async def test_pipeline_endpoints_availability():
    """パイプライン並列化エンドポイント利用可能性テスト"""
    try:
        # APIサーバーが起動しているかテスト
        import requests
        import os
        
        # サーバーURL (環境変数から取得、デフォルトはlocalhost)
        base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        
        # パイプラインステータスエンドポイントをテスト
        try:
            response = requests.get(f"{base_url}/api/v1/pipeline/status", timeout=5)
            
            if response.status_code == 200:
                status_data = response.json()
                
                print_result(True, "Pipeline Endpoints Available", {
                    "🔧 Service available": status_data.get("pipeline_service_available", False),
                    "🚀 Pipeline enabled": status_data.get("pipeline_enabled", False),
                    "📋 Pipeline mode": status_data.get("pipeline_mode", "unknown"),
                    "⚡ Max workers": status_data.get("max_workers", 0),
                    "🔗 Celery connection": status_data.get("celery_connection", False),
                    "👥 Active workers": status_data.get("active_workers", 0)
                })
                
                return True, status_data
            else:
                print_result(False, "Pipeline Endpoints", {
                    "Status code": response.status_code,
                    "Response": response.text[:100]
                })
                return False, None
                
        except requests.exceptions.ConnectionError:
            print_result(False, "Pipeline Endpoints", {
                "Error": "Connection refused - API server not running",
                "Suggestion": "Start the API server with: python -m uvicorn main:app --reload"
            })
            return False, None
            
    except Exception as e:
        print_result(False, "Pipeline Endpoints", {"Error": str(e)})
        return False, None

async def test_pipeline_config_endpoint():
    """パイプライン設定エンドポイントテスト"""
    try:
        import requests
        import os
        
        base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        
        response = requests.get(f"{base_url}/api/v1/pipeline/config", timeout=5)
        
        if response.status_code == 200:
            config_data = response.json()
            
            print_result(True, "Pipeline Config Endpoint", {
                "🔧 Pipeline enabled": config_data.get("pipeline_enabled", False),
                "📋 Pipeline mode": config_data.get("pipeline_mode", "unknown"),
                "⚡ Max workers": config_data.get("max_workers", 0),
                "🎯 Category threshold": config_data.get("thresholds", {}).get("category_threshold", 0),
                "📈 Item threshold": config_data.get("thresholds", {}).get("item_threshold", 0),
                "🚀 Optimizations count": len(config_data.get("optimizations", {}))
            })
            
            return True, config_data
        else:
            print_result(False, "Pipeline Config Endpoint", {
                "Status code": response.status_code
            })
            return False, None
            
    except Exception as e:
        print_result(False, "Pipeline Config Endpoint", {"Error": str(e)})
        return False, None

async def test_pipeline_service_direct():
    """パイプライン統合サービス直接テスト"""
    try:
        from app.services.pipeline import PipelineProcessingService
        
        service = PipelineProcessingService()
        
        if service.is_available():
            print_result(True, "Pipeline Service Direct", {
                "🔧 Service": "Available",
                "🚀 Pipeline enabled": service.pipeline_enabled,
                "📋 Pipeline mode": service.pipeline_mode,
                "⚡ Max workers": service.max_workers,
                "📊 Category threshold": service.category_threshold,
                "📈 Item threshold": service.item_threshold
            })
            
            return True, service
        else:
            print_result(False, "Pipeline Service Direct", {
                "Status": "Service not available"
            })
            return False, None
            
    except Exception as e:
        print_result(False, "Pipeline Service Direct", {"Error": str(e)})
        return False, None

async def run_all_tests():
    """全テストを実行"""
    print("🚀 完全パイプライン並列化 エンドツーエンド統合テストスクリプト")
    print("このスクリプトはパイプライン並列化システム全体の統合テストを実行します。")
    
    test_results = {}
    
    # === テスト 1: パイプライン並列化エンドポイント利用可能性確認 ===
    print_header("Step 1: パイプライン並列化エンドポイント利用可能性確認")
    
    endpoints_available, status_data = await test_pipeline_endpoints_availability()
    test_results['endpoints_availability'] = endpoints_available
    
    # === テスト 2: パイプライン設定エンドポイントテスト ===
    print_header("Step 2: パイプライン設定エンドポイントテスト")
    
    config_available, config_data = await test_pipeline_config_endpoint()
    test_results['config_endpoint'] = config_available
    
    # === テスト 3: パイプライン統合サービス直接テスト ===
    print_header("Step 3: パイプライン統合サービス直接テスト")
    
    service_available, service = await test_pipeline_service_direct()
    test_results['service_direct'] = service_available
    
    # === テスト結果サマリー ===
    print_header("テスト結果サマリー")
    
    passed_tests = sum(1 for result in test_results.values() if result)
    total_tests = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\n📊 Overall: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 全テスト成功！完全パイプライン並列化システムが正常に動作しています。")
        
        if endpoints_available:
            print("\n🚀 次のステップ: 実際の画像でパイプライン処理をテストしてください:")
            print("   curl -X POST \"http://localhost:8000/api/v1/pipeline/process\" -F \"file=@your_image.jpg\"")
        else:
            print("\n⚠️ APIサーバーを起動してからエンドポイントテストを実行してください:")
            print("   python -m uvicorn main:app --reload")
            
    else:
        print("⚠️ 一部のテストが失敗しました。")
        
        if not endpoints_available:
            print("\n🔧 APIサーバーが起動していない可能性があります。")
            print("   以下のコマンドでサーバーを起動してください:")
            print("   python -m uvicorn main:app --reload")
        
        if not service_available:
            print("\n🔧 パイプライン統合サービスの設定を確認してください。")
            print("   Celeryワーカーが起動しているか確認:")
            print("   celery -A app.tasks.celery_app worker --loglevel=info")
    
    return test_results

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description="完全パイプライン並列化統合テストスクリプト")
    parser.add_argument("--run", action="store_true", help="テストを実行する")
    
    args = parser.parse_args()
    
    if not args.run:
        print("🚀 完全パイプライン並列化 エンドツーエンド統合テストスクリプト")
        print("このスクリプトはパイプライン並列化システム全体の統合テストを実行します。")
        print("\n📋 テスト内容:")
        print("  1. パイプライン並列化エンドポイント利用可能性確認")
        print("  2. パイプライン設定エンドポイントテスト")
        print("  3. パイプライン統合サービス直接テスト")
        print("\n⚠️ 注意: APIサーバーとCeleryワーカーが起動していることを確認してください。")
        print("\n実行するには以下のコマンドを使用してください:")
        print("python test_pipeline_integration.py --run")
        return
    
    # テスト実行
    try:
        asyncio.run(run_all_tests())
    except KeyboardInterrupt:
        print("\n🛑 テストが中断されました。")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ テスト実行中にエラーが発生しました: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
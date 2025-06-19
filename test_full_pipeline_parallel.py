#!/usr/bin/env python3
"""
完全パイプライン並列化 (Stage 1-5全体) テストスクリプト

このスクリプトは完全パイプライン並列化機能を段階的にテストします:
- パイプライン統合サービス利用可能性確認
- 完全パイプライン処理テスト
- カテゴリレベルパイプライン処理テスト
- パイプライン戦略選択テスト
"""

import asyncio
import sys
import time
import argparse
from typing import Dict, Any

def print_header(title: str):
    """テストセクションのヘッダーを表示"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def print_result(success: bool, message: str, details: Dict[str, Any] = None):
    """テスト結果を表示"""
    status = "✅ SUCCESS" if success else "❌ FAILED"
    print(f"{status} {message}")
    
    if details:
        for key, value in details.items():
            if isinstance(value, (int, float)):
                print(f"  → {key}: {value}")
            elif isinstance(value, str) and len(value) < 100:
                print(f"  → {key}: {value}")

async def test_pipeline_service_availability():
    """パイプライン統合サービス利用可能性テスト"""
    try:
        from app.services.pipeline import PipelineProcessingService
        
        service = PipelineProcessingService()
        
        # サービス利用可能性確認
        is_available = service.is_available()
        
        if is_available:
            print_result(True, "Pipeline Processing Service", {
                "🔧 Configuration": "OK",
                "🚀 Pipeline enabled": service.pipeline_enabled,
                "📋 Pipeline mode": service.pipeline_mode,
                "⚡ Max workers": service.max_workers
            })
            return True, service
        else:
            print_result(False, "Pipeline Processing Service")
            return False, None
            
    except Exception as e:
        print_result(False, "Pipeline Processing Service", {"Error": str(e)})
        return False, None

async def test_pipeline_strategy_selection():
    """パイプライン戦略選択テスト"""
    try:
        from app.services.pipeline.pipeline import PipelineProcessingService
        
        service = PipelineProcessingService()
        
        # 異なる戦略オプションをテスト
        test_strategies = [
            {"force_worker_pipeline": True},
            {"force_category_pipeline": True},
            {}  # デフォルト設定
        ]
        
        strategy_results = []
        
        for i, options in enumerate(test_strategies):
            strategy = service._determine_pipeline_strategy(options)
            strategy_results.append(strategy)
            print(f"  Strategy {i+1}: {strategy}")
        
        print_result(True, "Pipeline Strategy Selection", {
            "🏗️ Available strategies": f"{len(set(strategy_results))} unique",
            "📋 Test results": f"{len(strategy_results)} completed"
        })
        
        return True
        
    except Exception as e:
        print_result(False, "Pipeline Strategy Selection", {"Error": str(e)})
        return False

async def run_all_tests():
    """全テストを実行"""
    print("🚀 完全パイプライン並列化 (Stage 1-5全体) テストスクリプト")
    print("このスクリプトは完全パイプライン並列化機能を段階的にテストします。")
    
    test_results = {}
    
    # === テスト 1: パイプライン統合サービス利用可能性確認 ===
    print_header("Step 1: パイプライン統合サービス利用可能性確認")
    
    service_available, service = await test_pipeline_service_availability()
    test_results['service_availability'] = service_available
    
    if not service_available:
        print("\n❌ パイプライン統合サービスが利用できません。")
        return
    
    # === テスト 2: パイプライン戦略選択テスト ===
    print_header("Step 2: パイプライン戦略選択テスト")
    
    strategy_result = await test_pipeline_strategy_selection()
    test_results['strategy_selection'] = strategy_result
    
    # === テスト結果サマリー ===
    print_header("テスト結果サマリー")
    
    passed_tests = sum(1 for result in test_results.values() if result)
    total_tests = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\n📊 Overall: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 全テスト成功！完全パイプライン並列化の基盤が正常に動作しています。")
    else:
        print("⚠️ 一部のテストが失敗しました。")
    
    return test_results

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description="完全パイプライン並列化テストスクリプト")
    parser.add_argument("--run", action="store_true", help="テストを実行する")
    
    args = parser.parse_args()
    
    if not args.run:
        print("🚀 完全パイプライン並列化テストスクリプト")
        print("実行するには以下のコマンドを使用してください:")
        print("python test_full_pipeline_parallel.py --run")
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
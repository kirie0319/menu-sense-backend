#!/usr/bin/env python3
"""
Stage 2 並列カテゴライズテストスクリプト

Stage 2カテゴライズ並列化の動作確認：
- 並列カテゴライズサービス利用可能性確認
- テキスト分割並列処理テスト
- 既存システムとの互換性確認
- パフォーマンス比較テスト
"""

import asyncio
import time
import json
import sys
import os
from typing import Dict, Any

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath('.'))

def print_separator(title: str):
    """セクション分離線を印刷"""
    print("\n" + "="*60)
    print(f"📋 {title}")
    print("="*60)

def print_result(test_name: str, success: bool, details: Any = None):
    """テスト結果を整形して印刷"""
    status = "✅ 成功" if success else "❌ 失敗" 
    print(f"\n{status} {test_name}")
    
    if details:
        if isinstance(details, dict):
            for key, value in details.items():
                if isinstance(value, (dict, list)):
                    print(f"  {key}: {json.dumps(value, ensure_ascii=False, indent=2)}")
                else:
                    print(f"  {key}: {value}")
        else:
            print(f"  詳細: {details}")

async def test_parallel_categorization_service():
    """並列カテゴライズサービスの基本テスト"""
    print_separator("並列カテゴライズサービス 基本テスト")
    
    try:
        from app.services.category.parallel import get_parallel_categorization_service
        
        # サービス取得
        service = get_parallel_categorization_service()
        print_result("サービス取得", True, {
            "service_name": service.service_name,
            "supported_modes": service.supported_modes
        })
        
        # 利用可能性チェック
        is_available = service.is_available()
        print_result("サービス利用可能性", is_available)
        
        if is_available:
            # サービス情報取得
            service_info = service.get_service_info()
            print_result("サービス情報取得", True, {
                "capabilities": service_info.get("capabilities", []),
                "configuration": service_info.get("configuration", {})
            })
        
        return True
        
    except Exception as e:
        print_result("並列カテゴライズサービステスト", False, str(e))
        return False

async def test_parallel_categorization_function():
    """並列カテゴライズ関数のテスト"""
    print_separator("並列カテゴライズ関数テスト")
    
    # テストメニューテキスト
    test_menu_text = """
【前菜】
サラダ - 800円
スープ - 600円

【メイン】
ステーキ - 2500円
パスタ - 1200円
カレー - 1000円

【ドリンク】
コーヒー - 400円
ビール - 500円

【デザート】
アイスクリーム - 500円
"""
    
    try:
        from app.services.category.parallel import categorize_menu_with_parallel
        
        print(f"📝 テストメニューテキスト ({len(test_menu_text)} 文字):")
        print(test_menu_text)
        
        # 並列カテゴライズ実行
        start_time = time.time()
        result = await categorize_menu_with_parallel(test_menu_text, "test_session")
        processing_time = time.time() - start_time
        
        # 結果確認
        success = result.success
        
        print_result("並列カテゴライズ実行", success, {
            "categories": list(result.categories.keys()) if success else None,
            "total_items": sum(len(items) for items in result.categories.values()) if success else 0,
            "uncategorized_count": len(result.uncategorized) if success else 0,
            "processing_time": f"{processing_time:.2f}秒",
            "error": result.error if not success else None
        })
        
        # 詳細カテゴリ情報
        if success:
            print("\n📊 詳細カテゴリ情報:")
            for category, items in result.categories.items():
                print(f"  {category}: {len(items)} 項目")
                for item in items[:2]:  # 最初の2項目を表示
                    item_name = item.get('name', str(item)) if isinstance(item, dict) else str(item)
                    item_price = item.get('price', '') if isinstance(item, dict) else ''
                    print(f"    - {item_name} {item_price}")
                if len(items) > 2:
                    print(f"    ... 他 {len(items) - 2} 項目")
        
        return success
        
    except Exception as e:
        print_result("並列カテゴライズ関数テスト", False, str(e))
        return False

async def test_stage2_parallel_function():
    """Stage 2並列処理関数のテスト"""
    print_separator("Stage 2並列処理関数テスト")
    
    # テストメニューテキスト（より大きなサイズ）
    test_menu_text = """
【前菜・サラダ】
シーザーサラダ - 1200円 - 新鮮なロメインレタスとクルトン
ギリシャサラダ - 1100円 - フェタチーズとオリーブ
海鮮サラダ - 1800円 - エビとアボカドのサラダ

【スープ】
コーンスープ - 600円 - 甘みのあるコーンスープ
ミネストローネ - 700円 - トマトベースの野菜スープ
クラムチャウダー - 800円 - あさりの濃厚スープ

【メイン料理】
ビーフステーキ - 2500円 - 国産牛のステーキ
チキンカツレツ - 1600円 - サクサクのチキンカツ
サーモングリル - 2200円 - ノルウェーサーモンのグリル
パスタ・ボロネーゼ - 1200円 - ミートソースパスタ
マルゲリータピザ - 1500円 - トマトとモッツァレラのピザ
牛肉カレー - 1000円 - スパイシーなビーフカレー

【ドリンク】
コーヒー - 400円 - 深煎りコーヒー
アイスティー - 350円 - レモンティー
生ビール - 500円 - キリン一番搾り
赤ワイン - 800円 - フランス産赤ワイン
白ワイン - 750円 - イタリア産白ワイン

【デザート】
チョコレートケーキ - 600円 - 濃厚チョコケーキ
ティラミス - 650円 - マスカルポーネのティラミス
アイスクリーム - 500円 - バニラ・チョコ・ストロベリー
"""
    
    try:
        from app.workflows.stages import stage2_categorize_openai_exclusive
        
        print(f"📝 テストメニューテキスト ({len(test_menu_text)} 文字):")
        print(f"  テキスト長: {len(test_menu_text)} 文字")
        print(f"  行数: {len(test_menu_text.splitlines())} 行")
        
        # Stage 2並列処理実行
        start_time = time.time()
        result = await stage2_categorize_openai_exclusive(test_menu_text, "test_session")
        processing_time = time.time() - start_time
        
        # 結果確認
        success = result.get("success", False)
        
        print_result("Stage 2並列処理実行", success, {
            "stage": result.get("stage"),
            "categorization_engine": result.get("categorization_engine"),
            "mode": result.get("mode"),
            "total_items": result.get("total_items", 0),
            "total_categories": result.get("total_categories", 0),
            "uncategorized_count": result.get("uncategorized_count", 0),
            "processing_time": f"{processing_time:.2f}秒",
            "parallel_processing": result.get("parallel_processing", False),
            "parallel_strategy": result.get("parallel_strategy"),
            "error": result.get("error") if not success else None
        })
        
        # カテゴリ詳細情報
        if success:
            categories = result.get("categories", {})
            print("\n📊 Stage 2カテゴリ分類結果:")
            for category, items in categories.items():
                print(f"  {category}: {len(items)} 項目")
                for item in items[:3]:  # 最初の3項目を表示
                    if isinstance(item, dict):
                        item_name = item.get('name', 'Unknown')
                        item_price = item.get('price', '')
                        print(f"    - {item_name} {item_price}")
                    else:
                        print(f"    - {item}")
                if len(items) > 3:
                    print(f"    ... 他 {len(items) - 3} 項目")
        
        return success
        
    except Exception as e:
        print_result("Stage 2並列処理関数テスト", False, str(e))
        return False

async def test_categorization_performance():
    """カテゴライズ性能比較テスト"""
    print_separator("カテゴライズ性能比較テスト")
    
    # テスト用大容量メニューテキスト
    large_menu_text = """
【前菜・サラダ】
シーザーサラダ - 1200円
ギリシャサラダ - 1100円
海鮮サラダ - 1800円
コブサラダ - 1300円
ルッコラサラダ - 1000円

【スープ】
コーンスープ - 600円
ミネストローネ - 700円
クラムチャウダー - 800円
オニオンスープ - 650円
トマトスープ - 550円

【メイン料理】
ビーフステーキ - 2500円
チキンカツレツ - 1600円
サーモングリル - 2200円
パスタ・ボロネーゼ - 1200円
マルゲリータピザ - 1500円
牛肉カレー - 1000円
チキンテリヤキ - 1400円
エビフライ - 1800円
ハンバーグ - 1300円
ポークソテー - 1700円

【ドリンク】
コーヒー - 400円
アイスティー - 350円
生ビール - 500円
赤ワイン - 800円
白ワイン - 750円
日本酒 - 600円
焼酎 - 500円
カクテル - 700円
ソフトドリンク - 300円
ジュース - 350円

【デザート】
チョコレートケーキ - 600円
ティラミス - 650円
アイスクリーム - 500円
プリン - 450円
フルーツタルト - 700円
""" * 2  # テキストを2倍にして性能テスト
    
    try:
        print(f"📊 性能テスト用メニューテキスト:")
        print(f"  テキスト長: {len(large_menu_text)} 文字")
        print(f"  行数: {len(large_menu_text.splitlines())} 行")
        
        # 並列処理版テスト
        from app.workflows.stages import stage2_categorize_openai_exclusive
        
        print("\n🚀 並列処理版実行中...")
        parallel_start = time.time()
        parallel_result = await stage2_categorize_openai_exclusive(large_menu_text, "test_parallel")
        parallel_time = time.time() - parallel_start
        
        parallel_success = parallel_result.get("success", False)
        
        print_result("並列処理版", parallel_success, {
            "処理時間": f"{parallel_time:.2f}秒",
            "総アイテム数": parallel_result.get("total_items", 0),
            "カテゴリ数": parallel_result.get("total_categories", 0),
            "並列戦略": parallel_result.get("parallel_strategy"),
            "エンジン": parallel_result.get("categorization_engine")
        })
        
        # 従来版テスト（比較用）
        try:
            from app.workflows.stages import stage2_categorize_openai_exclusive_legacy
            
            print("\n📝 従来版実行中...")
            legacy_start = time.time()
            legacy_result = await stage2_categorize_openai_exclusive_legacy(large_menu_text, "test_legacy")
            legacy_time = time.time() - legacy_start
            
            legacy_success = legacy_result.get("success", False)
            
            print_result("従来版", legacy_success, {
                "処理時間": f"{legacy_time:.2f}秒",
                "総アイテム数": legacy_result.get("total_items", 0),
                "カテゴリ数": legacy_result.get("total_categories", 0),
                "エンジン": legacy_result.get("categorization_engine")
            })
            
            # 性能比較
            if parallel_success and legacy_success:
                improvement = ((legacy_time - parallel_time) / legacy_time) * 100
                print(f"\n📈 性能比較結果:")
                print(f"  並列処理版: {parallel_time:.2f}秒")
                print(f"  従来版: {legacy_time:.2f}秒")
                print(f"  性能向上: {improvement:+.1f}%")
                
                if improvement > 0:
                    print(f"  ✅ 並列処理により {improvement:.1f}% 高速化")
                else:
                    print(f"  ⚠️ 並列処理でも従来版と同等またはそれ以下の性能")
        
        except Exception as legacy_error:
            print_result("従来版テスト", False, f"従来版テスト失敗: {legacy_error}")
        
        return parallel_success
        
    except Exception as e:
        print_result("カテゴライズ性能比較テスト", False, str(e))
        return False

async def test_celery_workers():
    """Celeryワーカーの状態確認"""
    print_separator("Celeryワーカー状態確認")
    
    try:
        from app.tasks.celery_app import celery_app, get_worker_stats
        
        # ワーカー統計取得
        worker_stats = get_worker_stats()
        
        if "error" in worker_stats:
            print_result("ワーカー統計取得", False, worker_stats["error"])
            return False
        
        worker_count = worker_stats.get("worker_count", 0)
        active_tasks = worker_stats.get("active_tasks", {})
        registered_tasks = worker_stats.get("registered_tasks", {})
        
        print_result("Celeryワーカー状態", worker_count > 0, {
            "ワーカー数": worker_count,
            "アクティブタスク数": len(active_tasks),
            "登録済みタスク数": sum(len(tasks) for tasks in registered_tasks.values()) if registered_tasks else 0
        })
        
        # カテゴライズタスクの登録確認
        categorization_tasks = []
        if registered_tasks:
            for worker, tasks in registered_tasks.items():
                for task in tasks:
                    if "categorization" in task:
                        categorization_tasks.append(task)
        
        print_result("カテゴライズタスク登録", len(categorization_tasks) > 0, {
            "登録されたカテゴライズタスク": categorization_tasks
        })
        
        return worker_count > 0
        
    except Exception as e:
        print_result("Celeryワーカー状態確認", False, str(e))
        return False

async def main():
    """メインテスト実行"""
    print("🏷️ Stage 2 並列カテゴライズ テストスクリプト")
    print("="*60)
    
    tests = [
        ("並列カテゴライズサービス", test_parallel_categorization_service),
        ("Celeryワーカー状態", test_celery_workers),
        ("並列カテゴライズ関数", test_parallel_categorization_function),
        ("Stage 2並列処理関数", test_stage2_parallel_function),
        ("カテゴライズ性能比較", test_categorization_performance),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results[test_name] = result
        except Exception as e:
            print_result(test_name, False, f"テスト実行エラー: {str(e)}")
            results[test_name] = False
    
    # 最終結果サマリー
    print_separator("テスト結果サマリー")
    
    total_tests = len(results)
    passed_tests = sum(1 for success in results.values() if success)
    
    for test_name, success in results.items():
        status = "✅ 成功" if success else "❌ 失敗"
        print(f"{status} {test_name}")
    
    print(f"\n📊 総合結果: {passed_tests}/{total_tests} テスト成功")
    
    if passed_tests == total_tests:
        print("🎉 Stage 2並列カテゴライズが正常に動作しています！")
        return True
    else:
        print("⚠️ 一部のテストが失敗しました。設定やサービス状態を確認してください。")
        return False

if __name__ == "__main__":
    asyncio.run(main()) 
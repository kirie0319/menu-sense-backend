"""
Complete Test Runner - Menu Processor v2
データベースクリア → 完全パイプラインテスト → 結果検証の統合ランナー
"""
import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
import time


async def main():
    """統合テストメイン関数"""
    print("🔬 Complete Test Suite - Menu Processor v2")
    print("=" * 80)
    print("実際のテスト画像を使用した完全なパイプラインテスト")
    print("データベースクリア → OCR → Categorize → DB Save → Translation → Verification")
    print()
    
    print("選択してください:")
    print("1. 完全テスト実行（データベースクリア + パイプラインテスト）")
    print("2. パイプラインテストのみ")
    print("3. データベース状態確認")
    print("4. データベースクリア")
    
    choice = input("\n選択 (1/2/3/4): ").strip()
    
    start_time = time.time()
    
    try:
        if choice == "1":
            await run_complete_test_suite()
            
        elif choice == "2":
            await run_pipeline_test_only()
            
        elif choice == "3":
            await show_database_status()
            
        elif choice == "4":
            await clear_database_only()
            
        else:
            print("❌ 無効な選択です")
            return
        
        end_time = time.time()
        elapsed = end_time - start_time
        print(f"\n⏱️ 総実行時間: {elapsed:.2f} 秒")
        
    except KeyboardInterrupt:
        print("\n⏹️ テスト中断")
    except Exception as e:
        print(f"\n💥 予期しないエラー: {e}")


async def run_complete_test_suite():
    """完全テストスイート実行"""
    print("\n🚀 Complete Test Suite - 実行開始")
    print("=" * 80)
    
    # Step 1: データベースクリア
    print("Step 1: データベースクリア")
    print("-" * 40)
    
    from scripts.clear_database import clear_all_data, show_current_data
    
    print("データベース状態（クリア前）:")
    await show_current_data()
    
    print("\nデータベースクリア実行中...")
    clear_success = await clear_all_data()
    
    if not clear_success:
        print("❌ データベースクリアに失敗しました")
        return
    
    # Step 2: パイプラインテスト実行
    print("\n" + "=" * 80)
    print("Step 2: Complete Pipeline Test")
    print("-" * 40)
    
    from scripts.test_complete_pipeline import CompletePipelineTest
    
    pipeline_test = CompletePipelineTest()
    pipeline_success = await pipeline_test.run_complete_test()
    
    # Step 3: 最終結果サマリー
    print("\n" + "=" * 80)
    print("🏁 Complete Test Suite - 最終結果")
    print("=" * 80)
    
    if clear_success and pipeline_success:
        print("🎉 Complete Test Suite - SUCCESS!")
        print("✅ データベースクリア成功")
        print("✅ パイプラインテスト成功")
        print("✅ OCR → Categorize → DB Save → Translation の全フロー正常動作")
    else:
        print("❌ Complete Test Suite - FAILED!")
        print(f"   データベースクリア: {'✅' if clear_success else '❌'}")
        print(f"   パイプラインテスト: {'✅' if pipeline_success else '❌'}")


async def run_pipeline_test_only():
    """パイプラインテストのみ実行"""
    print("\n🧪 Pipeline Test Only")
    print("=" * 80)
    
    from scripts.test_complete_pipeline import CompletePipelineTest
    
    pipeline_test = CompletePipelineTest()
    success = await pipeline_test.run_complete_test()
    
    if success:
        print("\n🎉 Pipeline Test - SUCCESS!")
    else:
        print("\n❌ Pipeline Test - FAILED!")


async def show_database_status():
    """データベース状態確認"""
    print("\n🔍 Database Status Check")
    print("=" * 80)
    
    from scripts.clear_database import show_current_data
    await show_current_data()


async def clear_database_only():
    """データベースクリアのみ実行"""
    print("\n🧹 Database Clear Only")
    print("=" * 80)
    
    from scripts.clear_database import clear_all_data, show_current_data
    
    print("現在のデータベース状態:")
    await show_current_data()
    
    confirm = input("\n⚠️ 全データを削除しますか？ (yes/no): ").strip().lower()
    if confirm in ["yes", "y"]:
        success = await clear_all_data()
        
        if success:
            print("\nクリア後の状態:")
            await show_current_data()
    else:
        print("❌ 削除をキャンセルしました")


if __name__ == "__main__":
    asyncio.run(main()) 
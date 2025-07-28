"""
Database Clear Script - Menu Processor v2
テスト用データベースクリアスクリプト
"""
import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import asyncio
from sqlalchemy import text
from app_2.core.database import async_session_factory, engine
from app_2.infrastructure.models.menu_model import MenuModel
from app_2.infrastructure.models.session_model import SessionModel
from app_2.utils.logger import get_logger

logger = get_logger("database_clear")


async def clear_all_data():
    """全てのデータをクリア"""
    print("🧹 Database Clear - データベースクリア開始")
    print("=" * 60)
    
    try:
        async with async_session_factory() as session:
            # メニューテーブルクリア
            print("📋 メニューテーブルをクリア中...")
            result = await session.execute(text("DELETE FROM menus"))
            menu_count = result.rowcount
            print(f"   削除されたメニューアイテム: {menu_count} 個")
            
            # セッションテーブルクリア
            print("📋 セッションテーブルをクリア中...")
            result = await session.execute(text("DELETE FROM processing_sessions"))
            session_count = result.rowcount
            print(f"   削除されたセッション: {session_count} 個")
            
            # コミット
            await session.commit()
            
            print("\n✅ データベースクリア完了!")
            print(f"📊 削除サマリー:")
            print(f"   - メニューアイテム: {menu_count} 個")
            print(f"   - セッション: {session_count} 個")
            
            return True
            
    except Exception as e:
        logger.error(f"Database clear failed: {e}")
        print(f"❌ データベースクリア失敗: {e}")
        return False


async def show_current_data():
    """現在のデータベース内容を表示"""
    print("🔍 Current Database Content")
    print("=" * 60)
    
    try:
        async with async_session_factory() as session:
            # メニュー数確認
            menu_result = await session.execute(text("SELECT COUNT(*) FROM menus"))
            menu_count = menu_result.scalar()
            
            # セッション数確認
            session_result = await session.execute(text("SELECT COUNT(*) FROM processing_sessions"))
            session_count = session_result.scalar()
            
            print(f"📊 現在のデータ:")
            print(f"   - メニューアイテム: {menu_count} 個")
            print(f"   - セッション: {session_count} 個")
            
            # 最新のセッション情報表示
            if session_count > 0:
                print("\n📋 最新セッション情報:")
                latest_sessions = await session.execute(text(
                    "SELECT session_id, status, created_at FROM processing_sessions "
                    "ORDER BY created_at DESC LIMIT 5"
                ))
                
                for row in latest_sessions:
                    print(f"   - {row.session_id}: {row.status} ({row.created_at})")
            
            # メニューサンプル表示
            if menu_count > 0:
                print("\n📋 メニューサンプル:")
                sample_menus = await session.execute(text(
                    "SELECT id, name, category, translation FROM menus LIMIT 5"
                ))
                
                for row in sample_menus:
                    translation = row.translation or "未翻訳"
                    print(f"   - {row.id}: {row.name} ({row.category}) → {translation}")
            
    except Exception as e:
        logger.error(f"Database inspection failed: {e}")
        print(f"❌ データベース確認失敗: {e}")


async def main():
    """メイン実行関数"""
    print("🗄️ Database Management - Menu Processor v2")
    print("=" * 60)
    
    print("\n選択してください:")
    print("1. 現在のデータ確認")
    print("2. 全データクリア")
    print("3. データ確認 → クリア → 確認")
    
    choice = input("\n選択 (1/2/3): ").strip()
    
    try:
        if choice == "1":
            await show_current_data()
            
        elif choice == "2":
            # 確認
            confirm = input("\n⚠️ 全データを削除しますか？ (yes/no): ").strip().lower()
            if confirm in ["yes", "y"]:
                await clear_all_data()
            else:
                print("❌ 削除をキャンセルしました")
                
        elif choice == "3":
            print("\n--- データ確認 ---")
            await show_current_data()
            
            if input("\n削除を実行しますか？ (yes/no): ").strip().lower() in ["yes", "y"]:
                print("\n--- データクリア ---")
                success = await clear_all_data()
                
                if success:
                    print("\n--- クリア後確認 ---")
                    await show_current_data()
            else:
                print("❌ 削除をキャンセルしました")
                
        else:
            print("❌ 無効な選択です")
        
    except KeyboardInterrupt:
        print("\n⏹️ 操作中断")
    except Exception as e:
        print(f"\n💥 予期しないエラー: {e}")


if __name__ == "__main__":
    asyncio.run(main()) 
#!/usr/bin/env python3
"""
Railway DBのデータをクリアするスクリプト
複数の方法を提供：
1. 全テーブルのデータを削除（構造は保持）
2. 全テーブルを削除して再作成
3. 特定のセッションのみ削除
"""
import asyncio
import os
import sys
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.database import get_database_url, Base
from app.models.menu_translation import Session, MenuItem, ProcessingProvider, MenuItemImage, Category

async def clear_all_data(engine):
    """全テーブルのデータを削除（構造は保持）"""
    print("🗑️  全テーブルのデータを削除中...")
    
    async with engine.begin() as conn:
        # 外部キー制約を一時的に無効化
        await conn.execute(text("SET session_replication_role = 'replica';"))
        
        # 各テーブルのデータを削除（依存関係の逆順）
        tables = [
            "menu_item_images",
            "categories", 
            "processing_providers",
            "menu_items",
            "sessions"
        ]
        
        for table in tables:
            try:
                result = await conn.execute(text(f"DELETE FROM {table}"))
                print(f"  ✅ {table}: {result.rowcount}件削除")
            except Exception as e:
                print(f"  ❌ {table}: エラー - {e}")
        
        # 外部キー制約を再度有効化
        await conn.execute(text("SET session_replication_role = 'origin';"))
        
        # シーケンスをリセット（IDを1から開始）
        sequences = [
            ("sessions", "id"),
            ("menu_items", "id"),
            ("processing_providers", "id"),
            ("menu_item_images", "id"),
            ("categories", "id")
        ]
        
        print("\n🔄 IDシーケンスをリセット中...")
        for table, id_col in sequences:
            try:
                await conn.execute(text(f"ALTER SEQUENCE {table}_{id_col}_seq RESTART WITH 1"))
                print(f"  ✅ {table}のIDシーケンスをリセット")
            except Exception as e:
                print(f"  ⚠️  {table}: {e}")

async def drop_and_recreate_tables(engine):
    """全テーブルを削除して再作成"""
    print("🔨 全テーブルを削除して再作成中...")
    
    async with engine.begin() as conn:
        # 全テーブルを削除
        await conn.execute(text("DROP TABLE IF EXISTS menu_item_images CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS categories CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS processing_providers CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS menu_items CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS sessions CASCADE"))
        print("  ✅ 全テーブルを削除しました")
        
    # テーブルを再作成
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print("  ✅ 全テーブルを再作成しました")

async def delete_specific_session(engine, session_id):
    """特定のセッションとその関連データを削除"""
    print(f"🎯 セッション {session_id} とその関連データを削除中...")
    
    async with engine.begin() as conn:
        # セッションの存在確認
        result = await conn.execute(
            text("SELECT id FROM sessions WHERE id = :session_id"),
            {"session_id": session_id}
        )
        if not result.scalar():
            print(f"  ❌ セッション {session_id} が見つかりません")
            return
        
        # カスケード削除（menu_itemsとその関連データは自動的に削除される）
        result = await conn.execute(
            text("DELETE FROM sessions WHERE id = :session_id"),
            {"session_id": session_id}
        )
        print(f"  ✅ セッション {session_id} と関連データを削除しました")

async def show_current_data_summary(engine):
    """現在のデータの概要を表示"""
    print("\n📊 現在のデータ概要:")
    
    async with engine.connect() as conn:
        # 各テーブルのレコード数を取得
        tables = ["sessions", "menu_items", "processing_providers", "menu_item_images", "categories"]
        
        for table in tables:
            try:
                result = await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                print(f"  - {table}: {count}件")
            except Exception as e:
                print(f"  - {table}: テーブルが存在しません")

async def main():
    """メイン処理"""
    print("🚂 Railway DBクリアツール\n")
    
    # データベース接続確認
    db_url = get_database_url()
    if not db_url or "railway" not in db_url:
        print("❌ Railway DBの接続情報が設定されていません")
        print("DATABASE_URL環境変数を設定してください")
        return
    
    # 接続先を表示（パスワードは隠す）
    display_url = db_url
    if "@" in display_url:
        start = display_url.find("://") + 3
        end = display_url.find("@")
        if ":" in display_url[start:end]:
            user_pass = display_url[start:end]
            user = user_pass.split(":")[0]
            display_url = display_url.replace(user_pass, f"{user}:****")
    
    print(f"接続先: {display_url}\n")
    
    # エンジン作成
    engine = create_async_engine(db_url, echo=False)
    
    try:
        # 現在のデータ概要を表示
        await show_current_data_summary(engine)
        
        # オプション表示
        print("\n🔧 実行可能な操作:")
        print("1. 全データを削除（テーブル構造は保持）")
        print("2. 全テーブルを削除して再作成")
        print("3. 特定のセッションを削除")
        print("4. 何もせずに終了")
        
        # ユーザー入力待ち
        choice = input("\n選択してください (1-4): ").strip()
        
        if choice == "1":
            # 確認
            confirm = input("\n⚠️  本当に全データを削除しますか？ (yes/no): ").strip().lower()
            if confirm == "yes":
                await clear_all_data(engine)
                print("\n✅ 全データを削除しました")
                await show_current_data_summary(engine)
            else:
                print("❌ キャンセルしました")
                
        elif choice == "2":
            # 確認
            confirm = input("\n⚠️  本当に全テーブルを削除して再作成しますか？ (yes/no): ").strip().lower()
            if confirm == "yes":
                await drop_and_recreate_tables(engine)
                print("\n✅ 全テーブルを削除して再作成しました")
                await show_current_data_summary(engine)
            else:
                print("❌ キャンセルしました")
                
        elif choice == "3":
            session_id = input("\n削除するセッションIDを入力してください: ").strip()
            if session_id:
                await delete_specific_session(engine, session_id)
                await show_current_data_summary(engine)
            else:
                print("❌ セッションIDが入力されませんでした")
                
        elif choice == "4":
            print("👋 終了します")
        else:
            print("❌ 無効な選択です")
            
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await engine.dispose()

if __name__ == "__main__":
    # コマンドライン引数で直接実行も可能
    if len(sys.argv) > 1:
        if sys.argv[1] == "--clear-all":
            # 全データ削除を直接実行
            async def quick_clear():
                engine = create_async_engine(get_database_url(), echo=False)
                try:
                    await clear_all_data(engine)
                    await show_current_data_summary(engine)
                finally:
                    await engine.dispose()
            asyncio.run(quick_clear())
        elif sys.argv[1] == "--drop-all":
            # 全テーブル削除を直接実行
            async def quick_drop():
                engine = create_async_engine(get_database_url(), echo=False)
                try:
                    await drop_and_recreate_tables(engine)
                    await show_current_data_summary(engine)
                finally:
                    await engine.dispose()
            asyncio.run(quick_drop())
        else:
            print("使用方法:")
            print("  python clear_railway_db.py          # 対話モード")
            print("  python clear_railway_db.py --clear-all  # 全データ削除")
            print("  python clear_railway_db.py --drop-all   # 全テーブル削除して再作成")
    else:
        asyncio.run(main()) 
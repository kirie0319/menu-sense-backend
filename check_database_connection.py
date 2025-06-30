#!/usr/bin/env python3
"""
データベース接続確認スクリプト
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.database import get_database_url, async_session_factory
from app.repositories.menu_translation_repository import MenuTranslationRepository

async def check_database_connection():
    """データベース接続を確認"""
    print("🔍 データベース接続を確認中...\n")
    
    # 1. 基本的な接続テスト
    db_url = get_database_url()
    print(f"📊 接続先: {db_url.replace(':menu_password@', ':****@')}")
    
    engine = create_async_engine(db_url)
    
    try:
        # 接続テスト
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print("✅ データベース接続: 成功\n")
            
            # PostgreSQLバージョン確認
            version_result = await conn.execute(text("SELECT version()"))
            version = version_result.scalar()
            print(f"📌 PostgreSQL バージョン:\n   {version}\n")
            
    except Exception as e:
        print(f"❌ データベース接続: 失敗\n   エラー: {e}\n")
        return False
    finally:
        await engine.dispose()
    
    # 2. テーブルの存在確認
    print("📋 テーブル一覧:")
    async with async_session_factory() as session:
        result = await session.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
        )
        tables = result.fetchall()
        for table in tables:
            print(f"   - {table[0]}")
    
    # 3. データ件数確認
    print("\n📊 データ件数:")
    async with async_session_factory() as session:
        # セッション数
        sessions_count = await session.execute(text("SELECT COUNT(*) FROM sessions"))
        print(f"   - セッション: {sessions_count.scalar()}件")
        
        # メニューアイテム数
        items_count = await session.execute(text("SELECT COUNT(*) FROM menu_items"))
        print(f"   - メニューアイテム: {items_count.scalar()}件")
        
        # 画像数
        images_count = await session.execute(text("SELECT COUNT(*) FROM menu_item_images"))
        print(f"   - 画像: {images_count.scalar()}件")
        
        # プロバイダー記録数
        providers_count = await session.execute(text("SELECT COUNT(*) FROM processing_providers"))
        print(f"   - 処理プロバイダー: {providers_count.scalar()}件")
    
    # 4. リポジトリ経由でのアクセステスト
    print("\n🔧 リポジトリ経由のアクセステスト:")
    async with async_session_factory() as session:
        repository = MenuTranslationRepository(session)
        
        # 最新のセッションを取得
        latest_session = await session.execute(
            text("SELECT session_id, created_at FROM sessions ORDER BY created_at DESC LIMIT 1")
        )
        latest = latest_session.fetchone()
        
        if latest:
            print(f"   📅 最新セッション: {latest[0]} (作成: {latest[1]})")
            
            # セッションの進捗を取得
            progress = await repository.get_session_progress(latest[0])
            print(f"   📊 進捗: {progress['progress_percentage']:.1f}%")
            print(f"      - 翻訳: {progress['translation_completed']}/{progress['total_items']}")
            print(f"      - 説明: {progress['description_completed']}/{progress['total_items']}")
            print(f"      - 画像: {progress['image_completed']}/{progress['total_items']}")
        else:
            print("   ⚠️  セッションが見つかりません")
    
    print("\n✅ データベース接続確認完了!")
    return True

if __name__ == "__main__":
    asyncio.run(check_database_connection())

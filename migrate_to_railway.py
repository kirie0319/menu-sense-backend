#!/usr/bin/env python3
"""
ローカルDBからRailway DBへのデータ移行スクリプト
"""
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.database import Base

async def migrate_to_railway():
    """ローカルDBからRailway DBへデータを移行"""
    print("🚂 Railway DBへのデータ移行\n")
    
    # ローカルDB URL
    local_db_url = "postgresql+asyncpg://menu_user:menu_password@localhost:5432/menu_translation_db"
    
    # Railway DB URL（環境変数から取得）
    railway_db_url = os.getenv("DATABASE_URL")
    if not railway_db_url:
        print("❌ DATABASE_URL環境変数が設定されていません")
        return False
    
    # asyncpg形式に変換
    if railway_db_url.startswith("postgresql://"):
        railway_db_url = railway_db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    # SSL追加
    if "sslmode=" not in railway_db_url:
        separator = "&" if "?" in railway_db_url else "?"
        railway_db_url += f"{separator}sslmode=require"
    
    print("📊 移行元（ローカル）: localhost:5432/menu_translation_db")
    print("📊 移行先（Railway）: Railway PostgreSQL\n")
    
    local_engine = create_async_engine(local_db_url)
    railway_engine = create_async_engine(railway_db_url)
    
    try:
        # 1. Railway DBにテーブルを作成
        print("📋 Railway DBにテーブルを作成中...")
        async with railway_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ テーブル作成完了\n")
        
        # 2. データをコピー
        tables = ['sessions', 'menu_items', 'processing_providers', 'menu_item_images', 'categories']
        
        for table in tables:
            print(f"📦 {table} をコピー中...")
            
            # ローカルからデータ取得
            async with local_engine.connect() as local_conn:
                result = await local_conn.execute(text(f"SELECT * FROM {table}"))
                rows = result.fetchall()
                columns = result.keys()
                
            if rows:
                # Railway DBに挿入
                async with railway_engine.connect() as railway_conn:
                    # 既存データをクリア
                    await railway_conn.execute(text(f"DELETE FROM {table}"))
                    await railway_conn.commit()
                    
                    # データ挿入
                    for row in rows:
                        placeholders = ", ".join([f":{col}" for col in columns])
                        col_names = ", ".join(columns)
                        query = f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})"
                        await railway_conn.execute(text(query), dict(zip(columns, row)))
                    await railway_conn.commit()
                
                print(f"   ✅ {len(rows)}件のデータをコピー")
            else:
                print(f"   ⏭️  データなし")
        
        print("\n✅ データ移行完了!")
        
        # 3. 移行結果を確認
        print("\n📊 移行結果:")
        async with railway_engine.connect() as conn:
            for table in tables:
                result = await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                print(f"   - {table}: {count}件")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 移行エラー: {e}")
        return False
        
    finally:
        await local_engine.dispose()
        await railway_engine.dispose()

if __name__ == "__main__":
    if not os.getenv("DATABASE_URL"):
        print("⚠️  Railway DATABASE_URLが設定されていません")
        print("\n使用方法:")
        print("export DATABASE_URL='postgresql://...' # Railwayダッシュボードからコピー")
        print("python migrate_to_railway.py")
    else:
        asyncio.run(migrate_to_railway())

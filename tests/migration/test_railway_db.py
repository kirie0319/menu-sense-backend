#!/usr/bin/env python3
"""
Railway PostgreSQL接続テストスクリプト
"""
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.database import get_database_url

async def test_railway_connection():
    """Railway DBへの接続をテスト"""
    print("🚂 Railway PostgreSQL接続テスト\n")
    
    # 現在の設定を表示（パスワードは隠す）
    db_url = get_database_url()
    display_url = db_url
    if "@" in display_url:
        # パスワード部分を隠す
        start = display_url.find("://") + 3
        end = display_url.find("@")
        if ":" in display_url[start:end]:
            user_pass = display_url[start:end]
            user = user_pass.split(":")[0]
            display_url = display_url.replace(user_pass, f"{user}:****")
    
    print(f"📊 接続先: {display_url}")
    print(f"🔒 SSL Mode: {os.getenv('DB_SSL_MODE', 'なし')}\n")
    
    # エンジン作成
    engine = create_async_engine(db_url, echo=False)
    
    try:
        # 1. 接続テスト
        print("🔍 接続テスト中...")
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print("✅ 接続成功!\n")
            
            # 2. データベース情報取得
            # 現在のデータベース名
            db_name_result = await conn.execute(text("SELECT current_database()"))
            db_name = db_name_result.scalar()
            print(f"📁 データベース名: {db_name}")
            
            # PostgreSQLバージョン
            version_result = await conn.execute(text("SELECT version()"))
            version = version_result.scalar()
            print(f"📌 PostgreSQL: {version.split(',')[0]}")
            
            # 接続情報
            host_result = await conn.execute(text("SELECT inet_server_addr()"))
            host = host_result.scalar()
            print(f"🌐 サーバーアドレス: {host}")
            
            # SSL接続確認
            ssl_result = await conn.execute(text("SELECT ssl_is_used()"))
            ssl_used = ssl_result.scalar()
            print(f"🔐 SSL接続: {'✅ 有効' if ssl_used else '❌ 無効'}")
            
    except Exception as e:
        print(f"❌ 接続失敗: {e}")
        print("\n🔧 トラブルシューティング:")
        print("1. Railway ダッシュボードから DATABASE_URL をコピーしたか確認")
        print("2. 環境変数が正しく設定されているか確認:")
        print("   export DATABASE_URL='postgresql://...'")
        print("3. Railway DBがアクティブか確認")
        print("4. ファイアウォール/ネットワーク設定を確認")
        return False
    finally:
        await engine.dispose()
    
    print("\n✅ Railway DB接続テスト完了!")
    return True

if __name__ == "__main__":
    # 使用方法を表示
    if not os.getenv("DATABASE_URL") and not os.getenv("DB_HOST"):
        print("⚠️  Railway DB接続情報が設定されていません\n")
        print("📋 設定方法:")
        print("1. Railwayダッシュボードから DATABASE_URL をコピー")
        print("2. 以下のコマンドで環境変数を設定:")
        print("   export DATABASE_URL='postgresql://user:pass@host.railway.app:port/dbname'")
        print("   export DB_SSL_MODE=require")
        print("\nまたは .env ファイルを作成して設定してください")
    else:
        asyncio.run(test_railway_connection())

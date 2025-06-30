import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.database import Base, get_database_url
from app.models.menu_translation import Session, MenuItem, ProcessingProvider, MenuItemImage

async def test_database_setup():
    """データベース接続とテーブル作成をテスト"""
    print("🔍 データベース接続をテスト中...")
    
    # データベースURL取得
    db_url = get_database_url()
    print(f"📊 データベースURL: {db_url}")
    
    # エンジン作成
    engine = create_async_engine(db_url, echo=True)
    
    try:
        # テーブル作成
        print("\n📋 テーブルを作成中...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        print("\n✅ テーブル作成完了!")
        
        # 作成されたテーブルを確認
        async with engine.connect() as conn:
            result = await conn.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")
            tables = result.fetchall()
            
            print("\n📊 作成されたテーブル:")
            for table in tables:
                print(f"  - {table[0]}")
                
        return True
        
    except Exception as e:
        print(f"\n❌ エラー: {e}")
        return False
        
    finally:
        await engine.dispose()

if __name__ == "__main__":
    success = asyncio.run(test_database_setup())
    sys.exit(0 if success else 1)

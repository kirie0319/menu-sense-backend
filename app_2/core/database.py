"""
Database Configuration - Menu Processor v2
Clean Architecture-based database connection management

このファイルはデータベース接続の管理を担当します:
- PostgreSQL + AsyncPG による非同期接続
- SQLAlchemy ORM の設定
- 接続プールの最適化
- 環境別設定対応
"""

from typing import AsyncGenerator

from sqlalchemy import MetaData, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from app_2.core.config import settings
from app_2.utils.logger import get_logger

logger = get_logger("database")

# モデルのインポートは init_database() 内で行う（循環インポート回避）

# ==========================================
# Database Configuration
# ==========================================

# Declarative base for ORM models
Base = declarative_base()

# Metadata configuration with naming conventions
metadata = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s"
    }
)
Base.metadata = metadata


def get_database_url() -> str:
    """
    データベースURLを取得
    環境変数の優先順位に従ってデータベース接続URLを構築
    
    Returns:
        str: データベース接続URL
    """
    
    # Priority 1: DATABASE_URL (Heroku, Railway などのクラウドサービス用)
    if settings.base.database_url:
        db_url = settings.base.database_url
        
        # postgres:// を postgresql+asyncpg:// に変換
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        
        logger.info(f"📊 Using DATABASE_URL connection")
        return db_url
    
    # Priority 2: 個別設定による構築
    db_host = settings.base.db_host
    db_port = settings.base.db_port
    db_user = settings.base.db_user
    db_password = settings.base.db_password
    db_name = settings.base.db_name
    
    
    url = f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    logger.info(f"📊 Using constructed database URL: {db_host}:{db_port}/{db_name}")
    
    return url


def get_engine_config() -> dict:
    """最小限のデータベースエンジン設定"""
    return {
        "echo": settings.base.debug_mode,  # デバッグ時のみSQLログ出力
        "pool_pre_ping": True,  # 接続の健全性チェック
    }


# ==========================================
# Database Engine and Session
# ==========================================

# 非同期データベースエンジンの作成
engine = create_async_engine(
    get_database_url(),
    **get_engine_config()
)

# 非同期セッションファクトリの作成
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=True,
    autocommit=False
)


# ==========================================
# Database Session Management
# ==========================================

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    データベースセッションを取得（依存性注入用）
    
    Yields:
        AsyncSession: 非同期データベースセッション
    """
    async with async_session_factory() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Database session error: {e}")
            raise
        finally:
            await session.close()


class DatabaseManager:
    """データベース管理クラス"""
    
    @staticmethod
    async def create_tables():
        """データベーステーブルを作成"""
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("✅ Database tables created successfully")
        except Exception as e:
            logger.error(f"❌ Failed to create database tables: {e}")
            raise
    
    @staticmethod
    async def drop_tables():
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            logger.info("🗑️ Database tables dropped successfully")
        except Exception as e:
            logger.error(f"❌ Failed to drop database tables: {e}")
            raise
    
    @staticmethod
    async def check_connection() -> bool:
        """データベース接続をチェック"""
        try:
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("✅ Database connection successful")
            return True
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            return False
    
    @staticmethod
    async def close_connections():
        """データベース接続を閉じる"""
        try:
            await engine.dispose()
            logger.info("🔌 Database connections closed")
        except Exception as e:
            logger.error(f"❌ Failed to close database connections: {e}")
            raise
    
    @staticmethod
    async def get_connection_info() -> dict:
        """データベース接続情報を取得"""
        return {
            "url": get_database_url().split("@")[-1] if "@" in get_database_url() else "masked",
            "pool_size": engine.pool.size(),
            "checked_out": engine.pool.checkedout(),
            "checked_in": engine.pool.checkedin(),
            "echo_enabled": engine.echo
        }


# ==========================================
# Database Initialization
# ==========================================

async def init_database():
    """
    データベースの初期化
    アプリケーション起動時に呼び出される
    
    AUTO_RESET_DATABASE=true の場合、既存テーブルを削除してから再作成
    """
    logger.info("🔄 Initializing database...")
    
    # モデルのインポート（Base.metadataへの登録のため）
    try:
        from app_2.infrastructure.models.menu_model import MenuModel  # noqa: F401
        from app_2.infrastructure.models.session_model import SessionModel  # noqa: F401
        logger.info("📊 MenuModel imported and registered")
        logger.info("📊 SessionModel imported and registered")
    except ImportError as e:
        logger.warning(f"⚠️ Failed to import models: {e}")
    
    # 接続チェック
    if not await DatabaseManager.check_connection():
        raise RuntimeError("Database connection failed")
    
    # 自動リセット機能チェック
    if settings.base.auto_reset_database:
        logger.info("🗑️ AUTO_RESET_DATABASE enabled - Dropping existing tables...")
        try:
            await DatabaseManager.drop_tables()
            logger.info("✅ Existing tables dropped successfully")
        except Exception as e:
            logger.warning(f"⚠️ Failed to drop tables (may not exist): {e}")
    
    # テーブル作成
    await DatabaseManager.create_tables()
    
    if settings.base.auto_reset_database:
        logger.info("✅ Database reset and initialization completed")
    else:
        logger.info("✅ Database initialization completed")


async def shutdown_database():
    """
    データベースのシャットダウン
    アプリケーション終了時に呼び出される
    """
    logger.info("🛑 Shutting down database...")
    await DatabaseManager.close_connections()


# ==========================================
# Export
# ==========================================

__all__ = [
    # Base classes
    "Base",
    "metadata",
    
    # Engine and sessions
    "engine",
    "async_session_factory",
    "get_db_session",
    
    # Management
    "DatabaseManager",
    
    # Lifecycle functions
    "init_database",
    "shutdown_database",
    
    # Utility functions
    "get_database_url"
]

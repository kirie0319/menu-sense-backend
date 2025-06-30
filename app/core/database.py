"""
Database configuration and connection management for Menu Translation system
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import os

# Create declarative base for models
Base = declarative_base()

# Database URL configuration
def get_database_url() -> str:
    """Get database URL from environment variables"""
    # Priority 1: DATABASE_URL (for Railway and other cloud services)
    if os.getenv("DATABASE_URL"):
        db_url = os.getenv("DATABASE_URL")
        # Convert postgres:// to postgresql+asyncpg://
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return db_url
    
    # For testing, use test database
    if os.getenv("TESTING"):
        return os.getenv("TEST_DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test_menu_db")
    
    # For production/development
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_user = os.getenv("DB_USER", "menu_user")
    db_password = os.getenv("DB_PASSWORD", "menu_password")
    db_name = os.getenv("DB_NAME", "menu_translation_db")
    
    return f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

# Create async engine
engine = create_async_engine(
    get_database_url(),
    echo=os.getenv("DB_ECHO", "false").lower() == "true",
    future=True
)

# Create async session factory
async_session_factory = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

async def get_db_session() -> AsyncSession:
    """Dependency to get database session"""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_database():
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def close_database():
    """Close database connection"""
    await engine.dispose()
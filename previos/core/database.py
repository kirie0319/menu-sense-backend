"""
Database configuration and connection management for Menu Translation system
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
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
        
        # Add SSL mode for production (Railway requires this)
        if "sslmode" not in db_url and os.getenv("RAILWAY_ENVIRONMENT") == "production":
            # Add sslmode=require to the connection string
            if "?" in db_url:
                db_url += "&sslmode=require"
            else:
                db_url += "?sslmode=require"
        
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

# Create async engine with production-ready settings
engine = create_async_engine(
    get_database_url(),
    echo=os.getenv("DB_ECHO", "false").lower() == "true",
    future=True,
    # Connection pool settings for production
    pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
    pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "30")),
    pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "1800")),  # 30 minutes
    # Additional settings for Railway
    connect_args={
        "server_settings": {"jit": "off"},  # Disable JIT for compatibility
        "command_timeout": 60,
        "ssl": os.getenv("RAILWAY_ENVIRONMENT") == "production" if os.getenv("RAILWAY_ENVIRONMENT") else None
    } if "asyncpg" in get_database_url() else {}
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
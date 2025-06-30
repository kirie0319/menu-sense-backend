#!/usr/bin/env python3
"""
Railway Database Connection Checker

This script helps diagnose database connection issues in Railway production environment.
"""
import os
import sys
import asyncio
import logging
from urllib.parse import urlparse
import asyncpg
import psycopg2
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def check_environment_variables():
    """Check if required environment variables are set"""
    logger.info("=" * 50)
    logger.info("🔍 Checking Environment Variables")
    logger.info("=" * 50)
    
    required_vars = ["DATABASE_URL", "RAILWAY_ENVIRONMENT"]
    optional_vars = ["DB_POOL_SIZE", "DB_MAX_OVERFLOW", "REDIS_URL"]
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive data
            if var == "DATABASE_URL":
                parsed = urlparse(value)
                masked = f"{parsed.scheme}://{parsed.username}:****@{parsed.hostname}:{parsed.port}/{parsed.path}"
                logger.info(f"✅ {var}: {masked}")
            else:
                logger.info(f"✅ {var}: {value}")
        else:
            logger.error(f"❌ {var}: NOT SET")
    
    for var in optional_vars:
        value = os.getenv(var)
        logger.info(f"ℹ️  {var}: {value if value else 'NOT SET'}")


async def test_raw_asyncpg_connection():
    """Test raw asyncpg connection"""
    logger.info("\n" + "=" * 50)
    logger.info("🔍 Testing Raw asyncpg Connection")
    logger.info("=" * 50)
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("❌ DATABASE_URL not set")
        return False
    
    # Convert postgres:// to postgresql://
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    try:
        # Parse URL to add SSL if needed
        parsed = urlparse(database_url)
        
        # Try with SSL
        logger.info("🔄 Attempting connection with SSL...")
        conn = await asyncpg.connect(
            database_url,
            ssl='require' if os.getenv("RAILWAY_ENVIRONMENT") == "production" else None
        )
        
        # Test query
        result = await conn.fetchval("SELECT version()")
        logger.info(f"✅ Connected successfully!")
        logger.info(f"📊 PostgreSQL version: {result}")
        
        # Check connection info
        server_version = conn.get_server_version()
        logger.info(f"📊 Server version tuple: {server_version}")
        
        await conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ asyncpg connection failed: {type(e).__name__}: {e}")
        
        # Try without SSL
        try:
            logger.info("🔄 Attempting connection without SSL...")
            conn = await asyncpg.connect(database_url, ssl=None)
            await conn.close()
            logger.warning("⚠️  Connected without SSL - consider enabling SSL for production")
            return True
        except Exception as e2:
            logger.error(f"❌ asyncpg connection failed (no SSL): {type(e2).__name__}: {e2}")
            return False


def test_psycopg2_connection():
    """Test psycopg2 connection as fallback"""
    logger.info("\n" + "=" * 50)
    logger.info("🔍 Testing psycopg2 Connection (Fallback)")
    logger.info("=" * 50)
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("❌ DATABASE_URL not set")
        return False
    
    try:
        # psycopg2 accepts postgres:// format
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        cursor.execute("SELECT version()")
        result = cursor.fetchone()
        logger.info(f"✅ psycopg2 connected successfully!")
        logger.info(f"📊 PostgreSQL version: {result[0]}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ psycopg2 connection failed: {type(e).__name__}: {e}")
        return False


async def test_sqlalchemy_async():
    """Test SQLAlchemy async connection"""
    logger.info("\n" + "=" * 50)
    logger.info("🔍 Testing SQLAlchemy Async Connection")
    logger.info("=" * 50)
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("❌ DATABASE_URL not set")
        return False
    
    # Convert to asyncpg format
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    # Add SSL mode for production
    if "sslmode" not in database_url and os.getenv("RAILWAY_ENVIRONMENT") == "production":
        if "?" in database_url:
            database_url += "&sslmode=require"
        else:
            database_url += "?sslmode=require"
    
    try:
        engine = create_async_engine(
            database_url,
            echo=False,
            pool_size=5,
            max_overflow=10,
            connect_args={
                "ssl": "require" if os.getenv("RAILWAY_ENVIRONMENT") == "production" else None
            }
        )
        
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            logger.info(f"✅ SQLAlchemy async connected successfully!")
            logger.info(f"📊 PostgreSQL version: {version}")
        
        await engine.dispose()
        return True
        
    except Exception as e:
        logger.error(f"❌ SQLAlchemy async connection failed: {type(e).__name__}: {e}")
        return False


def test_sqlalchemy_sync():
    """Test SQLAlchemy sync connection"""
    logger.info("\n" + "=" * 50)
    logger.info("🔍 Testing SQLAlchemy Sync Connection")
    logger.info("=" * 50)
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("❌ DATABASE_URL not set")
        return False
    
    # Use psycopg2 for sync
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    
    try:
        engine = create_engine(database_url, echo=False)
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            logger.info(f"✅ SQLAlchemy sync connected successfully!")
            logger.info(f"📊 PostgreSQL version: {version}")
        
        engine.dispose()
        return True
        
    except Exception as e:
        logger.error(f"❌ SQLAlchemy sync connection failed: {type(e).__name__}: {e}")
        return False


async def check_tables():
    """Check if tables exist"""
    logger.info("\n" + "=" * 50)
    logger.info("🔍 Checking Database Tables")
    logger.info("=" * 50)
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return
    
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    try:
        conn = await asyncpg.connect(
            database_url,
            ssl='require' if os.getenv("RAILWAY_ENVIRONMENT") == "production" else None
        )
        
        # Check tables
        tables = await conn.fetch("""
            SELECT tablename FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename
        """)
        
        if tables:
            logger.info(f"✅ Found {len(tables)} tables:")
            for table in tables:
                logger.info(f"   📋 {table['tablename']}")
        else:
            logger.warning("⚠️  No tables found in public schema")
        
        # Check specific tables
        expected_tables = ['sessions', 'menu_items', 'images', 'provider_records']
        for table_name in expected_tables:
            count = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
            logger.info(f"   📊 {table_name}: {count} records")
        
        await conn.close()
        
    except Exception as e:
        logger.error(f"❌ Failed to check tables: {type(e).__name__}: {e}")


async def main():
    """Run all checks"""
    logger.info("🚀 Railway Database Connection Diagnostic Tool")
    logger.info(f"🕒 Running at: {os.getenv('RAILWAY_ENVIRONMENT', 'local')} environment")
    
    # Run checks
    check_environment_variables()
    
    # Test connections
    asyncpg_ok = await test_raw_asyncpg_connection()
    psycopg2_ok = test_psycopg2_connection()
    sqlalchemy_async_ok = await test_sqlalchemy_async()
    sqlalchemy_sync_ok = test_sqlalchemy_sync()
    
    # Check tables if any connection works
    if any([asyncpg_ok, psycopg2_ok, sqlalchemy_async_ok, sqlalchemy_sync_ok]):
        await check_tables()
    
    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("📊 Summary")
    logger.info("=" * 50)
    logger.info(f"asyncpg:          {'✅ OK' if asyncpg_ok else '❌ FAILED'}")
    logger.info(f"psycopg2:         {'✅ OK' if psycopg2_ok else '❌ FAILED'}")
    logger.info(f"SQLAlchemy Async: {'✅ OK' if sqlalchemy_async_ok else '❌ FAILED'}")
    logger.info(f"SQLAlchemy Sync:  {'✅ OK' if sqlalchemy_sync_ok else '❌ FAILED'}")
    
    if not any([asyncpg_ok, psycopg2_ok, sqlalchemy_async_ok, sqlalchemy_sync_ok]):
        logger.error("\n❌ All connection methods failed!")
        logger.info("\n💡 Recommendations:")
        logger.info("1. Check if DATABASE_URL is correctly set in Railway")
        logger.info("2. Verify the database is running and accessible")
        logger.info("3. Check Railway logs for any network/firewall issues")
        logger.info("4. Consider using psycopg2 as a fallback driver")
        sys.exit(1)
    else:
        logger.info("\n✅ At least one connection method works!")
        if not asyncpg_ok and (psycopg2_ok or sqlalchemy_sync_ok):
            logger.info("\n💡 Consider using psycopg2 driver instead of asyncpg")


if __name__ == "__main__":
    asyncio.run(main()) 
"""
Repository Dependencies - Service Layer
Repository implementations dependency injection configuration
"""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app_2.core.database import get_db_session
from app_2.domain.repositories.menu_repository import MenuRepositoryInterface
from app_2.domain.repositories.session_repository import SessionRepositoryInterface
from app_2.infrastructure.repositories.menu_repository_impl import MenuRepositoryImpl
from app_2.infrastructure.repositories.session_repository_impl import SessionRepositoryImpl

# Redis dependencies
from app_2.infrastructure.integrations.redis.redis_client import RedisClient
from app_2.infrastructure.integrations.redis.redis_publisher import RedisPublisher
from app_2.infrastructure.integrations.redis.redis_subscriber import RedisSubscriber


# ==========================================
# Repository Dependencies
# ==========================================

def get_menu_repository(
    db_session: Annotated[AsyncSession, Depends(get_db_session)]
) -> MenuRepositoryInterface:
    """
    MenuRepositoryInterface実装を取得
    
    Args:
        db_session: データベースセッション
        
    Returns:
        MenuRepositoryInterface: メニューリポジトリ実装
    """
    return MenuRepositoryImpl(db_session)


def get_session_repository(
    db_session: Annotated[AsyncSession, Depends(get_db_session)]
) -> SessionRepositoryInterface:
    """
    SessionRepositoryInterface実装を取得
    
    Args:
        db_session: データベースセッション
        
    Returns:
        SessionRepositoryInterface: セッションリポジトリ実装
    """
    return SessionRepositoryImpl(db_session)


# ==========================================
# Redis Dependencies
# ==========================================

@lru_cache(maxsize=1)
def get_redis_client() -> RedisClient:
    """
    RedisClientシングルトンインスタンスを取得
    
    Returns:
        RedisClient: Redis クライアント
    """
    return RedisClient()


def get_redis_publisher(
    redis_client: Annotated[RedisClient, Depends(get_redis_client)]
) -> RedisPublisher:
    """
    RedisPublisher実装を取得
    
    Args:
        redis_client: Redis クライアント
        
    Returns:
        RedisPublisher: Redis パブリッシャー
    """
    return RedisPublisher(redis_client)


def get_redis_subscriber(
    redis_client: Annotated[RedisClient, Depends(get_redis_client)]
) -> RedisSubscriber:
    """
    RedisSubscriber実装を取得
    
    Args:
        redis_client: Redis クライアント
        
    Returns:
        RedisSubscriber: Redis サブスクライバー
    """
    return RedisSubscriber(redis_client)


# ==========================================
# Type Aliases for Dependency Injection
# ==========================================

# Repository Dependencies
MenuRepositoryDep = Annotated[MenuRepositoryInterface, Depends(get_menu_repository)]
SessionRepositoryDep = Annotated[SessionRepositoryInterface, Depends(get_session_repository)]
DBSessionDep = Annotated[AsyncSession, Depends(get_db_session)]

# Redis Dependencies
RedisClientDep = Annotated[RedisClient, Depends(get_redis_client)]
RedisPublisherDep = Annotated[RedisPublisher, Depends(get_redis_publisher)]
RedisSubscriberDep = Annotated[RedisSubscriber, Depends(get_redis_subscriber)] 
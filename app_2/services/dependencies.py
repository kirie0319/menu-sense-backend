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

# Google integrations dependencies
from app_2.infrastructure.integrations.google.google_vision_client import GoogleVisionClient, get_google_vision_client
from app_2.infrastructure.integrations.google.google_translate_client import GoogleTranslateClient, get_google_translate_client
from app_2.infrastructure.integrations.google.google_credential_manager import GoogleCredentialManager, get_google_credential_manager


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
# Google Integrations Dependencies
# ==========================================

@lru_cache(maxsize=1)
def get_google_credential_manager_dep() -> GoogleCredentialManager:
    """
    GoogleCredentialManagerシングルトンインスタンスを取得
    
    Returns:
        GoogleCredentialManager: Google認証管理クライアント
    """
    return get_google_credential_manager()


@lru_cache(maxsize=1)  
def get_google_vision_client_dep() -> GoogleVisionClient:
    """
    GoogleVisionClientシングルトンインスタンスを取得
    
    Returns:
        GoogleVisionClient: Google Vision API クライアント
    """
    return get_google_vision_client()


@lru_cache(maxsize=1)  
def get_google_translate_client_dep() -> GoogleTranslateClient:
    """
    GoogleTranslateClientシングルトンインスタンスを取得
    
    Returns:
        GoogleTranslateClient: Google Translate API クライアント
    """
    return get_google_translate_client()


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

# Google Integrations Dependencies
GoogleCredentialManagerDep = Annotated[GoogleCredentialManager, Depends(get_google_credential_manager_dep)]
GoogleVisionClientDep = Annotated[GoogleVisionClient, Depends(get_google_vision_client_dep)]
GoogleTranslateClientDep = Annotated[GoogleTranslateClient, Depends(get_google_translate_client_dep)] 
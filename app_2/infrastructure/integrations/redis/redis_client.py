"""
Redis Client - Infrastructure Layer
Simple Redis client for MVP (Simplified)
"""

from typing import Optional, Union, List, Any
from contextlib import asynccontextmanager

import redis.asyncio as redis
from redis.asyncio import Redis
from redis.exceptions import RedisError, ConnectionError

from app_2.core.config import settings
from app_2.utils.logger import get_logger

logger = get_logger("redis_client")


class RedisClient:
    """
    シンプルRedis非同期クライアント（MVP版）
    
    基本的な接続管理とエラーハンドリングを提供
    """
    
    def __init__(self):
        """Redis クライアントを初期化"""
        self._client: Optional[Redis] = None
        self._is_initialized = False

    async def initialize(self) -> None:
        """
        Redis接続を初期化
        
        Raises:
            ConnectionError: Redis接続に失敗した場合
        """
        if self._is_initialized:
            return
        
        try:
            # シンプルな接続設定
            self._client = redis.from_url(
                settings.celery.redis_url,
                decode_responses=True
            )
            
            # 接続テスト
            await self._client.ping()
            
            self._is_initialized = True
            logger.info("✅ Redis client initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Redis client: {e}")
            await self.cleanup()
            raise ConnectionError(f"Redis initialization failed: {e}")

    async def cleanup(self) -> None:
        """Redis接続をクリーンアップ"""
        try:
            if self._client:
                await self._client.aclose()
                self._client = None
            
            self._is_initialized = False
            logger.info("🔌 Redis client cleaned up")
            
        except Exception as e:
            logger.error(f"❌ Redis cleanup error: {e}")

    async def health_check(self) -> bool:
        """
        Redis接続の健全性をチェック
        
        Returns:
            bool: 接続が健全かどうか
        """
        if not self._is_initialized or not self._client:
            return False
        
        try:
            await self._client.ping()
            return True
        except Exception as e:
            logger.warning(f"⚠️ Redis health check failed: {e}")
            return False

    @asynccontextmanager
    async def get_connection(self):
        """
        Redis接続を取得（コンテキストマネージャー）
        
        Yields:
            Redis: Redis接続
        """
        if not self._is_initialized:
            await self.initialize()
        
        if not self._client:
            raise ConnectionError("Redis client not initialized")
        
        try:
            yield self._client
        except RedisError as e:
            logger.error(f"❌ Redis operation error: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected Redis error: {e}")
            raise

    async def publish(self, channel: str, message: str) -> int:
        """
        チャンネルにメッセージを送信
        
        Args:
            channel: チャンネル名
            message: メッセージ
            
        Returns:
            int: メッセージを受信したサブスクライバー数
        """
        try:
            async with self.get_connection() as client:
                result = await client.publish(channel, message)
                logger.debug(f"📢 Published to {channel}: {len(message)} bytes -> {result} subscribers")
                return result
        except Exception as e:
            logger.error(f"❌ Failed to publish to {channel}: {e}")
            return 0

    async def set(
        self, 
        key: str, 
        value: Union[str, bytes], 
        ex: Optional[int] = None, 
        nx: bool = False
    ) -> Union[bool, None]:
        """
        キーに値を設定（分散ロック対応）
        
        Args:
            key: キー名
            value: 値
            ex: 有効期限（秒）
            nx: キーが存在しない場合のみ設定
            
        Returns:
            Union[bool, None]: 設定成功時True、失敗時None
        """
        try:
            async with self.get_connection() as client:
                result = await client.set(key, value, ex=ex, nx=nx)
                logger.debug(f"🔑 Set key {key}: nx={nx}, ex={ex}, result={result}")
                return result
        except Exception as e:
            logger.error(f"❌ Failed to set key {key}: {e}")
            return None

    async def eval(
        self, 
        script: str, 
        keys: List[str], 
        args: List[str]
    ) -> Any:
        """
        Luaスクリプトを実行（分散ロック解放用）
        
        Args:
            script: Luaスクリプト
            keys: キーリスト
            args: 引数リスト
            
        Returns:
            Any: スクリプト実行結果
        """
        try:
            async with self.get_connection() as client:
                result = await client.eval(script, len(keys), *keys, *args)
                logger.debug(f"🔧 Executed Lua script with {len(keys)} keys, result={result}")
                return result
        except Exception as e:
            logger.error(f"❌ Failed to execute Lua script: {e}")
            return None

    async def get(self, key: str) -> Optional[str]:
        """
        キーの値を取得
        
        Args:
            key: キー名
            
        Returns:
            Optional[str]: キーの値（存在しない場合None）
        """
        try:
            async with self.get_connection() as client:
                result = await client.get(key)
                logger.debug(f"🔍 Get key {key}: {result}")
                return result
        except Exception as e:
            logger.error(f"❌ Failed to get key {key}: {e}")
            return None

    def get_client(self) -> Redis:
        """
        生のRedisクライアントを取得（上級者向け）
        
        Returns:
            Redis: Redis クライアント
            
        Raises:
            ConnectionError: クライアントが初期化されていない場合
        """
        if not self._is_initialized or not self._client:
            raise ConnectionError("Redis client not initialized")
        
        return self._client


# ==========================================
# Export
# ==========================================

__all__ = ["RedisClient"] 
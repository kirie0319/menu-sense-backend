"""
Redis Distributed Lock - Menu Processor v2
Redis を使用した分散ロック実装
"""
import asyncio
import time
import uuid
from typing import Optional, AsyncContextManager
from contextlib import asynccontextmanager

from app_2.infrastructure.integrations.redis.redis_client import RedisClient
from app_2.utils.logger import get_logger

logger = get_logger("redis_distributed_lock")


class RedisDistributedLock:
    """
    Redis分散ロック実装
    
    複数のワーカーが同じリソースに対して並行してアクセスするのを防ぐ
    """
    
    def __init__(self, redis_client=None):
        self.redis_client = redis_client or RedisClient()
        
    @asynccontextmanager
    async def acquire_lock(
        self, 
        resource_key: str, 
        timeout: int = 30,
        retry_delay: float = 0.1
    ) -> AsyncContextManager[bool]:
        """
        分散ロックを取得
        
        Args:
            resource_key: ロック対象のリソースキー
            timeout: ロック保持タイムアウト（秒）
            retry_delay: リトライ間隔（秒）
            
        Yields:
            bool: ロック取得成功の場合True
        """
        lock_key = f"lock:{resource_key}"
        lock_value = str(uuid.uuid4())
        acquired = False
        
        try:
            # ロック取得試行
            start_time = time.time()
            while time.time() - start_time < timeout:
                acquired = await self._try_acquire_lock(lock_key, lock_value, timeout)
                if acquired:
                    logger.debug(f"Lock acquired: {lock_key}")
                    break
                
                await asyncio.sleep(retry_delay)
            
            if not acquired:
                logger.warning(f"Failed to acquire lock within timeout: {lock_key}")
                yield False
                return
            
            yield True
            
        finally:
            if acquired:
                await self._release_lock(lock_key, lock_value)
                logger.debug(f"Lock released: {lock_key}")
    
    async def _try_acquire_lock(self, lock_key: str, lock_value: str, timeout: int) -> bool:
        """
        ロック取得を試行
        
        Args:
            lock_key: ロックキー
            lock_value: ロック値（一意性保証）
            timeout: タイムアウト
            
        Returns:
            bool: 取得成功の場合True
        """
        try:
            # SET lock_key lock_value EX timeout NX
            result = await self.redis_client.set(
                lock_key, 
                lock_value, 
                ex=timeout, 
                nx=True
            )
            return result is True
            
        except Exception as e:
            logger.error(f"Error trying to acquire lock {lock_key}: {e}")
            return False
    
    async def _release_lock(self, lock_key: str, lock_value: str) -> bool:
        """
        ロックを解放
        
        Args:
            lock_key: ロックキー
            lock_value: ロック値（一意性確認用）
            
        Returns:
            bool: 解放成功の場合True
        """
        try:
            # Lua スクリプトで原子的にロック解放
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
            
            result = await self.redis_client.eval(lua_script, [lock_key], [lock_value])
            return result == 1
            
        except Exception as e:
            logger.error(f"Error releasing lock {lock_key}: {e}")
            return False


# ファクトリー関数
def get_redis_distributed_lock() -> RedisDistributedLock:
    """
    RedisDistributedLockのインスタンスを取得
    
    Returns:
        RedisDistributedLock: Redis分散ロック
    """
    return RedisDistributedLock() 
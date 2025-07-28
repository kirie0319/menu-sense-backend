"""
Redis Subscriber - Infrastructure Layer
Simple message subscriber for SSE communication (MVP Simplified)
"""

import json
import asyncio
from typing import Dict, Any, Optional, AsyncGenerator, Callable

from app_2.infrastructure.integrations.redis.redis_client import RedisClient
from app_2.core.config import settings
from app_2.utils.logger import get_logger

logger = get_logger("redis_subscriber")


class RedisSubscriber:
    """
    Redis メッセージ受信クライアント（MVP版）
    
    SSE用メッセージ受信の基本機能を提供
    """
    
    def __init__(self, redis_client: Optional[RedisClient] = None):
        """
        Redis Subscriber を初期化
        
        Args:
            redis_client: Redis クライアント（オプション）
        """
        self.redis_client = redis_client or RedisClient()
        self._pubsub = None
        self._is_subscribed = False

    async def subscribe_to_session(self, session_id: str) -> None:
        """
        セッション用チャンネルを購読
        
        Args:
            session_id: セッションID
        """
        try:
            # Redis接続を初期化
            await self.redis_client.initialize()
            
            # PubSubオブジェクトを取得
            client = self.redis_client.get_client()
            self._pubsub = client.pubsub()
            
            # チャンネルを購読
            channel = settings.celery.get_sse_channel(session_id)
            await self._pubsub.subscribe(channel)
            
            self._is_subscribed = True
            logger.info(f"📡 Subscribed to session channel: {channel}")
            
        except Exception as e:
            logger.error(f"❌ Failed to subscribe to session {session_id}: {e}")
            raise

    async def listen_for_messages(self) -> AsyncGenerator[Dict[str, Any], None]:
        """
        メッセージを受信する非同期ジェネレーター
        
        Yields:
            Dict[str, Any]: 受信したメッセージ
        """
        if not self._is_subscribed or not self._pubsub:
            raise ValueError("Not subscribed to any channel")
        
        try:
            async for message in self._pubsub.listen():
                # 購読確認メッセージはスキップ
                if message["type"] == "subscribe":
                    logger.debug(f"✅ Subscription confirmed: {message['channel']}")
                    continue
                
                # 実際のメッセージのみ処理
                if message["type"] == "message":
                    try:
                        # JSON文字列をパース
                        message_data = json.loads(message["data"])
                        
                        logger.debug(f"📨 Received message: {message_data['type']}")
                        yield message_data
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ Failed to parse message JSON: {e}")
                        continue
                    except Exception as e:
                        logger.error(f"❌ Error processing message: {e}")
                        continue
                        
        except asyncio.CancelledError:
            logger.info("📡 Message listening cancelled")
            raise
        except Exception as e:
            logger.error(f"❌ Error in message listening: {e}")
            raise

    async def listen_for_session_messages(
        self, 
        session_id: str,
        message_handler: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        セッション用メッセージを受信（購読と受信を一括実行）
        
        Args:
            session_id: セッションID
            message_handler: メッセージハンドラー（オプション）
            
        Yields:
            Dict[str, Any]: 受信したメッセージ
        """
        try:
            # セッションチャンネルを購読
            await self.subscribe_to_session(session_id)
            
            # メッセージを受信
            async for message in self.listen_for_messages():
                # メッセージハンドラーがあれば実行
                if message_handler:
                    try:
                        message_handler(message)
                    except Exception as e:
                        logger.error(f"❌ Message handler error: {e}")
                
                yield message
                
        except asyncio.CancelledError:
            logger.info(f"📡 Session {session_id} message listening cancelled")
            raise
        except Exception as e:
            logger.error(f"❌ Error in session message listening: {e}")
            raise
        finally:
            await self.cleanup()

    async def unsubscribe(self) -> None:
        """チャンネル購読を解除"""
        try:
            if self._pubsub and self._is_subscribed:
                await self._pubsub.unsubscribe()
                self._is_subscribed = False
                logger.info("📡 Unsubscribed from channels")
                
        except Exception as e:
            logger.error(f"❌ Error during unsubscribe: {e}")

    async def cleanup(self) -> None:
        """リソースクリーンアップ"""
        try:
            # 購読解除
            await self.unsubscribe()
            
            # PubSub接続をクリーンアップ
            if self._pubsub:
                await self._pubsub.aclose()
                self._pubsub = None
            
            # Redis クライアントクリーンアップ
            if self.redis_client:
                await self.redis_client.cleanup()
            
            logger.info("🔌 Redis subscriber cleaned up")
            
        except Exception as e:
            logger.error(f"❌ Redis subscriber cleanup error: {e}")

    def is_subscribed(self) -> bool:
        """購読状態を確認"""
        return self._is_subscribed 
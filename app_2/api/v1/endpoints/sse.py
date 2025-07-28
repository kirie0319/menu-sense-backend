"""
SSE (Server-Sent Events) Endpoint - Real-time Communication
Redis Pub/Sub経由でクライアントにリアルタイム更新を配信
"""

import asyncio
import json
from typing import AsyncGenerator, List, Dict
from fastapi import APIRouter, HTTPException, status, Request
from fastapi.responses import StreamingResponse


from app_2.infrastructure.integrations.redis.redis_subscriber import RedisSubscriber
from app_2.utils.logger import get_logger

logger = get_logger("sse_endpoint")

router = APIRouter(prefix="/sse", tags=["sse"])


class SSEConnectionManager:
    """SSE接続管理クラス"""
    
    def __init__(self):
        self.active_connections: dict = {}
    
    def add_connection(self, session_id: str, connection_id: str):
        """接続を追加"""
        if session_id not in self.active_connections:
            self.active_connections[session_id] = set()
        self.active_connections[session_id].add(connection_id)
        logger.info(f"📡 SSE connection added: session={session_id}, connection={connection_id}")
    
    def remove_connection(self, session_id: str, connection_id: str):
        """接続を削除"""
        if session_id in self.active_connections:
            self.active_connections[session_id].discard(connection_id)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
        logger.info(f"📡 SSE connection removed: session={session_id}, connection={connection_id}")
    
    def get_connection_count(self, session_id: str) -> int:
        """セッションの接続数を取得"""
        return len(self.active_connections.get(session_id, set()))


# グローバル接続マネージャー
connection_manager = SSEConnectionManager()


async def format_sse_message(message_data: dict) -> str:
    """
    SSE形式のメッセージをフォーマット
    
    Args:
        message_data: メッセージデータ
        
    Returns:
        str: SSE形式の文字列
    """
    try:
        # メッセージタイプを取得
        message_type = message_data.get("type", "unknown")
        
        # JSONデータを文字列化
        data_json = json.dumps(message_data, ensure_ascii=False)
        
        # SSE形式でフォーマット
        sse_message = f"event: {message_type}\n"
        sse_message += f"data: {data_json}\n\n"
        
        return sse_message
        
    except Exception as e:
        logger.error(f"❌ Failed to format SSE message: {e}")
        # エラー時はエラーメッセージを送信
        error_data = {
            "type": "error",
            "data": {
                "error": "message_format_error",
                "message": str(e)
            }
        }
        error_json = json.dumps(error_data, ensure_ascii=False)
        return f"event: error\ndata: {error_json}\n\n"


async def create_sse_stream(session_id: str, connection_id: str) -> AsyncGenerator[str, None]:
    """
    SSEストリームを作成
    
    Args:
        session_id: セッションID
        connection_id: 接続ID
        
    Yields:
        str: SSE形式のメッセージ
    """
    subscriber = None
    
    try:
        # Redis Subscriberを初期化
        subscriber = RedisSubscriber()
        
        # 接続をマネージャーに追加
        connection_manager.add_connection(session_id, connection_id)
        
        # 接続開始メッセージを送信
        initial_message = {
            "type": "connection_established",
            "session_id": session_id,
            "data": {
                "status": "connected",
                "connection_id": connection_id,
                "active_connections": connection_manager.get_connection_count(session_id),
                "message": f"SSE connection established for session {session_id}"
            },
            "timestamp": "now"
        }
        
        yield await format_sse_message(initial_message)
        
        logger.info(f"📡 SSE stream started for session: {session_id}")
        
        # 🎯 セッション状態をチェックして既存の進捗履歴を送信
        history_messages = await get_session_history(session_id)
        for history_message in history_messages:
            yield await format_sse_message(history_message)
        
        # Redisメッセージを受信してSSE配信
        async for message in subscriber.listen_for_session_messages(session_id):
            try:
                # メッセージをSSE形式でフォーマット
                sse_message = await format_sse_message(message)
                
                logger.debug(f"📨 SSE message sent: session={session_id}, type={message.get('type', 'unknown')}")
                yield sse_message
                
            except Exception as e:
                logger.error(f"❌ Error processing SSE message: {e}")
                
                # エラーメッセージを送信
                error_message = {
                    "type": "error",
                    "session_id": session_id,
                    "data": {
                        "error": "message_processing_error",
                        "message": str(e)
                    }
                }
                yield await format_sse_message(error_message)
                
    except asyncio.CancelledError:
        logger.info(f"📡 SSE stream cancelled for session: {session_id}")
        raise
        
    except Exception as e:
        logger.error(f"❌ SSE stream error for session {session_id}: {e}")
        
        # 最終エラーメッセージを送信
        final_error_message = {
            "type": "error",
            "session_id": session_id,
            "data": {
                "error": "stream_error", 
                "message": str(e)
            }
        }
        yield await format_sse_message(final_error_message)
        
    finally:
        # クリーンアップ
        try:
            connection_manager.remove_connection(session_id, connection_id)
            
            if subscriber:
                await subscriber.cleanup()
                
            logger.info(f"🔌 SSE stream cleanup completed for session: {session_id}")
            
        except Exception as cleanup_error:
            logger.error(f"❌ SSE cleanup error: {cleanup_error}")


async def get_session_history(session_id: str) -> List[Dict]:
    """
    セッション履歴を取得する関数
    
    既に完了した段階があれば、進捗履歴として返す
    
    Returns:
        List[Dict]: 履歴メッセージのリスト
    """
    try:
        from app_2.core.database import async_session_factory
        from sqlalchemy import select
        from app_2.infrastructure.models.session_model import SessionModel
        
        history_messages = []
        
        async with async_session_factory() as db_session:
            # セッション状態を取得
            stmt = select(SessionModel).where(SessionModel.session_id == session_id)
            result = await db_session.execute(stmt)
            session_model = result.scalar_one_or_none()
            
            if not session_model:
                logger.warning(f"⚠️ Session not found for history: {session_id}")
                return history_messages
            
            stages_data = session_model.get_stages_data()
            
            if not stages_data:
                logger.info(f"📝 No stage history found for session: {session_id}")
                return history_messages
            
            logger.info(f"📜 Loading session history for {session_id}: {list(stages_data.keys())}")
            
            # 完了した段階を順番に送信
            stage_order = ['ocr_completed', 'mapping_completed', 'categorize_completed']
            
            for stage_key in stage_order:
                if stage_key in stages_data:
                    # 段階名を正規化 (ocr_completed -> ocr)
                    stage_name = stage_key.replace('_completed', '')
                    
                    # stage_completedメッセージとして準備
                    history_message = {
                        "type": "stage_completed",
                        "session_id": session_id,
                        "data": {
                            "stage": stage_name,
                            "completion_data": stages_data[stage_key],
                            "timestamp": stages_data[stage_key].get("stage_completed_at", "unknown"),
                            "ui_action": f"update_{stage_name}_display",
                            "is_history": True  # 履歴メッセージであることを示す
                        },
                        "timestamp": stages_data[stage_key].get("stage_completed_at", "unknown")
                    }
                    
                    history_messages.append(history_message)
                    logger.info(f"📨 Prepared history: {stage_name} for session {session_id}")
            
            # 進捗更新メッセージも追加
            if stages_data:
                completed_count = len([k for k in stages_data.keys() if k.endswith('_completed')])
                progress_percentage = min(completed_count * 20, 100)  # 各段階20%
                
                progress_message = {
                    "type": "progress_update",
                    "session_id": session_id,
                    "data": {
                        "message": f"履歴復元完了 - {completed_count}個の段階が完了済み",
                        "progress": progress_percentage,
                        "completed_stages": list(stages_data.keys()),
                        "is_history": True
                    },
                    "timestamp": "now"
                }
                
                history_messages.append(progress_message)
                logger.info(f"📊 Session history loaded: {completed_count} stages completed")
            
        return history_messages
            
    except Exception as e:
        logger.error(f"❌ Failed to get session history for {session_id}: {e}")
        return []


@router.get("/stream/{session_id}")
async def stream_session_events(session_id: str, request: Request):
    """
    SSEエンドポイント - セッション固有のリアルタイム更新を配信
    
    Args:
        session_id: セッションID
        request: HTTPリクエスト
        
    Returns:
        StreamingResponse: SSEストリーミングレスポンス
        
    Example:
        GET /api/v1/sse/stream/abc-123-def
        
        # レスポンス例
        event: connection_established
        data: {"type": "connection_established", "session_id": "abc-123-def", ...}
        
        event: stage_completed
        data: {"type": "stage_completed", "data": {"stage": "ocr", ...}}
        
        event: menu_update  
        data: {"type": "menu_update", "data": {"menu_id": "menu_123", ...}}
    """
    # セッションIDの基本バリデーション
    if not session_id or len(session_id) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session_id format"
        )
    
    # 接続IDを生成（クライアントIPとユーザーエージェントから）
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")[:50]
    connection_id = f"{client_ip}_{hash(user_agent) % 10000}"
    
    logger.info(f"🚀 SSE connection requested: session={session_id}, client={client_ip}")
    
    # SSEヘッダーを設定
    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Cache-Control",
        "X-Accel-Buffering": "no",  # nginxでのバッファリング無効化
    }
    
    try:
        # SSEストリームを作成
        return StreamingResponse(
            create_sse_stream(session_id, connection_id),
            media_type="text/event-stream",
            headers=headers
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to create SSE stream for session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to establish SSE connection: {str(e)}"
        )


@router.get("/health")
async def sse_health_check():
    """
    SSEサービスのヘルスチェック
    
    Returns:
        dict: ヘルスチェック結果
    """
    from app_2.core.config import settings
    
    # Redis接続チェック（非同期版を使用）
    redis_available = await settings.celery.async_is_redis_available()
    
    # アクティブ接続数を取得
    total_sessions = len(connection_manager.active_connections)
    total_connections = sum(
        len(connections) for connections in connection_manager.active_connections.values()
    )
    
    return {
        "status": "healthy" if redis_available else "degraded",
        "service": "sse_endpoint",
        "version": "1.0.0",
        "redis_available": redis_available,
        "active_sessions": total_sessions,
        "active_connections": total_connections,
        "connection_details": {
            session_id: len(connections) 
            for session_id, connections in connection_manager.active_connections.items()
        },
        "features": [
            "Real-time event streaming",
            "Session-based message filtering", 
            "Connection management",
            "Automatic cleanup"
        ],
        "message": "SSE endpoint ready for real-time communication"
    }


@router.get("/sessions")
async def get_active_sessions():
    """
    アクティブなSSEセッション一覧を取得
    
    Returns:
        dict: アクティブセッション情報
    """
    return {
        "active_sessions": list(connection_manager.active_connections.keys()),
        "session_details": {
            session_id: {
                "connection_count": len(connections),
                "connection_ids": list(connections)
            }
            for session_id, connections in connection_manager.active_connections.items()
        },
        "total_sessions": len(connection_manager.active_connections),
        "total_connections": sum(
            len(connections) for connections in connection_manager.active_connections.values()
        )
    }


@router.post("/test/{session_id}")
async def test_sse_message(session_id: str, message: dict):
    """
    SSE配信テスト用エンドポイント
    
    Args:
        session_id: セッションID
        message: テストメッセージ
        
    Returns:
        dict: 送信結果
    """
    try:
        from app_2.infrastructure.integrations.redis.redis_publisher import RedisPublisher
        
        publisher = RedisPublisher()
        
        # テストメッセージを送信
        success = await publisher.publish_session_message(
            session_id=session_id,
            message_type="test_message",
            data=message
        )
        
        return {
            "status": "success" if success else "failed",
            "session_id": session_id,
            "message_sent": message,
            "active_connections": connection_manager.get_connection_count(session_id)
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to send test message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send test message: {str(e)}"
        )

"""
📡 SSEManager - SSEストリーミング管理専用サービス

このサービスはServer-Sent Events (SSE) のストリーミング管理を担当します。
グローバル状態を排除し、セッション別のストリーミング管理を提供します。
"""

import json
import time
import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum
from fastapi import Request
from fastapi.responses import StreamingResponse

from app.core.config.sse import sse_settings


class EventType(Enum):
    """SSEイベントタイプ"""
    CONNECTION_ESTABLISHED = "connection_established"
    PROCESSING_STARTED = "processing_started"
    PARALLEL_PROCESSING_STARTED = "parallel_processing_started"
    ITEM_TASK_QUEUED = "item_task_queued"
    TASKS_QUEUED = "tasks_queued"
    PROGRESS_UPDATE = "progress_update"
    PROCESSING_COMPLETED = "processing_completed"
    HEARTBEAT = "heartbeat"
    STREAM_ERROR = "stream_error"


@dataclass
class SSEEvent:
    """SSEイベント"""
    event_type: EventType
    session_id: str
    data: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)

    def to_json(self) -> str:
        """JSON形式に変換"""
        event_data = {
            "type": self.event_type.value,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            **self.data
        }
        return json.dumps(event_data)


@dataclass
class StreamSession:
    """ストリーミングセッション"""
    session_id: str
    start_time: float
    last_heartbeat: float
    total_items: int
    connection_active: bool
    event_queue: List[SSEEvent] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def uptime(self) -> float:
        """アップタイム"""
        return time.time() - self.start_time

    @property
    def last_activity(self) -> float:
        """最終活動からの経過時間"""
        return time.time() - self.last_heartbeat

    def add_event(self, event: SSEEvent) -> None:
        """イベントをキューに追加"""
        self.event_queue.append(event)
        self.last_heartbeat = time.time()
        
        # キューサイズ制限
        if len(self.event_queue) > 100:
            self.event_queue = self.event_queue[-50:]

    def pop_events(self) -> List[SSEEvent]:
        """キューからイベントを取得"""
        events = self.event_queue.copy()
        self.event_queue.clear()
        return events


class SSEManager:
    """
    SSEストリーミング管理専用サービス
    
    責任:
    - SSEストリーム作成・管理
    - イベント配信
    - セッション状態管理
    - ハートビート管理
    """

    def __init__(self):
        self._stream_sessions: Dict[str, StreamSession] = {}
        self._session_timeout = 3600  # 1時間

    async def create_stream(self, session_id: str, request: Request) -> StreamingResponse:
        """
        SSEストリームを作成
        
        Args:
            session_id: セッションID
            request: HTTPリクエスト
            
        Returns:
            StreamingResponse: SSEストリーミングレスポンス
        """
        # ストリーミングセッション初期化
        if session_id not in self._stream_sessions:
            self._stream_sessions[session_id] = StreamSession(
                session_id=session_id,
                start_time=time.time(),
                last_heartbeat=time.time(),
                total_items=0,
                connection_active=True
            )
        
        # イベント生成器作成
        event_generator = self._create_event_generator(session_id, request)
        
        return StreamingResponse(
            event_generator,
            media_type="text/event-stream",
            headers=sse_settings.get_event_headers()
        )

    async def send_event(self, session_id: str, event_data: Dict[str, Any]) -> bool:
        """
        イベントを送信キューに追加
        
        Args:
            session_id: セッションID
            event_data: イベントデータ
            
        Returns:
            bool: 送信成功フラグ
        """
        stream_session = self._stream_sessions.get(session_id)
        if stream_session is None:
            return False
        
        # イベントタイプを判定
        event_type_str = event_data.get("type", "unknown")
        try:
            event_type = EventType(event_type_str)
        except ValueError:
            event_type = EventType.PROGRESS_UPDATE
        
        # SSEイベント作成
        event = SSEEvent(
            event_type=event_type,
            session_id=session_id,
            data=event_data
        )
        
        # イベントをキューに追加
        stream_session.add_event(event)
        return True

    async def send_connection_event(self, session_id: str) -> bool:
        """接続確認イベントを送信"""
        event_data = {
            "type": EventType.CONNECTION_ESTABLISHED.value,
            "message": "🔄 Real-time streaming connected",
            "api_integration": "real_api_integration"
        }
        return await self.send_event(session_id, event_data)

    async def send_heartbeat(self, session_id: str) -> bool:
        """ハートビートイベントを送信"""
        stream_session = self._stream_sessions.get(session_id)
        if stream_session is None:
            return False
        
        event_data = {
            "type": EventType.HEARTBEAT.value,
            "message": "💓 Connection alive",
            "uptime": stream_session.uptime
        }
        return await self.send_event(session_id, event_data)

    async def send_error_event(self, session_id: str, error: str) -> bool:
        """エラーイベントを送信"""
        event_data = {
            "type": EventType.STREAM_ERROR.value,
            "error": error,
            "message": "⚠️ Streaming error occurred"
        }
        return await self.send_event(session_id, event_data)

    def update_session_info(self, session_id: str, total_items: int) -> bool:
        """
        セッション情報を更新
        
        Args:
            session_id: セッションID
            total_items: 合計アイテム数
            
        Returns:
            bool: 更新成功フラグ
        """
        stream_session = self._stream_sessions.get(session_id)
        if stream_session is None:
            return False
        
        stream_session.total_items = total_items
        return True

    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        セッション情報を取得
        
        Args:
            session_id: セッションID
            
        Returns:
            Dict: セッション情報
        """
        stream_session = self._stream_sessions.get(session_id)
        if stream_session is None:
            return None
        
        return {
            "session_id": stream_session.session_id,
            "start_time": stream_session.start_time,
            "uptime": stream_session.uptime,
            "last_activity": stream_session.last_activity,
            "total_items": stream_session.total_items,
            "connection_active": stream_session.connection_active,
            "queued_events": len(stream_session.event_queue),
            "metadata": stream_session.metadata
        }

    async def cleanup_session(self, session_id: str) -> bool:
        """
        セッションをクリーンアップ
        
        Args:
            session_id: セッションID
            
        Returns:
            bool: クリーンアップ実行フラグ
        """
        if session_id in self._stream_sessions:
            self._stream_sessions[session_id].connection_active = False
            del self._stream_sessions[session_id]
            return True
        return False

    async def cleanup_inactive_sessions(self) -> int:
        """
        非アクティブセッションをクリーンアップ
        
        Returns:
            int: クリーンアップされたセッション数
        """
        inactive_sessions = [
            session_id for session_id, session in self._stream_sessions.items()
            if not session.connection_active or session.last_activity > self._session_timeout
        ]
        
        cleanup_count = 0
        for session_id in inactive_sessions:
            if await self.cleanup_session(session_id):
                cleanup_count += 1
        
        return cleanup_count

    def get_streaming_statistics(self) -> Dict[str, Any]:
        """
        ストリーミング統計を取得
        
        Returns:
            Dict: 統計情報
        """
        active_sessions = [s for s in self._stream_sessions.values() if s.connection_active]
        total_events = sum(len(s.event_queue) for s in self._stream_sessions.values())
        
        return {
            "total_sessions": len(self._stream_sessions),
            "active_sessions": len(active_sessions),
            "total_queued_events": total_events,
            "average_events_per_session": total_events / len(self._stream_sessions) if self._stream_sessions else 0,
            "oldest_session_uptime": max((s.uptime for s in self._stream_sessions.values()), default=0),
            "memory_usage_estimate": len(str(self._stream_sessions)) / 1024  # KB
        }

    async def _create_event_generator(
        self, 
        session_id: str, 
        request: Request
    ) -> AsyncGenerator[str, None]:
        """SSEイベント生成器を作成"""
        stream_session = self._stream_sessions[session_id]
        
        try:
            # 接続確認イベント送信
            await self.send_connection_event(session_id)
            
            heartbeat_interval = sse_settings.sse_heartbeat_interval
            last_heartbeat = time.time()
            
            while stream_session.connection_active:
                current_time = time.time()
                
                # クライアント切断チェック
                if await request.is_disconnected():
                    print(f"🔌 Client disconnected from SSE stream: {session_id}")
                    break
                
                # キューからイベントを取得・送信
                events = stream_session.pop_events()
                for event in events:
                    yield f"data: {event.to_json()}\n\n"
                    last_heartbeat = current_time
                
                # ハートビート送信
                if current_time - last_heartbeat > heartbeat_interval:
                    await self.send_heartbeat(session_id)
                    heartbeat_event = stream_session.event_queue.pop() if stream_session.event_queue else None
                    if heartbeat_event:
                        yield f"data: {heartbeat_event.to_json()}\n\n"
                        last_heartbeat = current_time
                
                # 短時間待機
                await asyncio.sleep(2)
        
        except Exception as e:
            print(f"❌ SSE stream error for {session_id}: {str(e)}")
            await self.send_error_event(session_id, str(e))
            error_events = stream_session.pop_events()
            for event in error_events:
                yield f"data: {event.to_json()}\n\n"
        
        finally:
            # クリーンアップ
            stream_session.connection_active = False
            print(f"🧹 SSE stream cleanup completed for {session_id}")
"""
リアルタイム通信サービス

このモジュールは以下の機能を提供します：
- SSE (Server-Sent Events) による進行状況通知
- Ping/Pong によるリアルタイム接続監視
- セッション状態管理
"""

# 主要クラス
from .session_manager import SessionManager, get_session_manager
from .sse_manager import SSEManager, get_sse_manager
from .types import (
    ProgressStatus, ProgressData, PingData, PingPongSession,
    SessionId, ProgressStore, PingPongSessions
)

# 便利な関数をエクスポート（後方互換性のため）
def get_progress_store():
    """進行状況ストアを取得（後方互換性）"""
    return get_session_manager().progress_store

def get_ping_pong_sessions():
    """Ping/Pongセッションを取得（後方互換性）"""
    return get_session_manager().ping_pong_sessions

async def send_progress(session_id: str, stage: int, status: str, message: str, data: dict = None):
    """進行状況を送信（後方互換性）"""
    return await get_sse_manager().send_progress(session_id, stage, status, message, data)

async def send_ping(session_id: str):
    """Pingを送信（後方互換性）"""
    return await get_sse_manager().send_ping(session_id)

async def start_ping_pong(session_id: str):
    """Ping/Pongを開始（後方互換性）"""
    return await get_sse_manager().start_ping_pong(session_id)

async def handle_pong(session_id: str):
    """Pongを処理（後方互換性）"""
    return await get_sse_manager().handle_pong(session_id)

async def stage4_heartbeat(session_id: str, initial_message: str):
    """廃止済みハートビート（後方互換性）"""
    return await get_sse_manager().stage4_heartbeat(session_id, initial_message)

# 統計情報取得
def get_realtime_stats():
    """リアルタイム通信の統計情報を取得"""
    session_stats = get_session_manager().get_stats()
    return {
        "service": "realtime_communication",
        "version": "1.0.0",
        "session_stats": session_stats,
        "features": [
            "SSE progress notifications",
            "Ping/Pong connection monitoring", 
            "Session state management",
            "Real-time data logging"
        ]
    }

__all__ = [
    # クラス
    'SessionManager', 'SSEManager',
    'ProgressStatus', 'ProgressData', 'PingData', 'PingPongSession',
    
    # インスタンス取得関数
    'get_session_manager', 'get_sse_manager',
    
    # 後方互換性関数
    'get_progress_store', 'get_ping_pong_sessions',
    'send_progress', 'send_ping', 'start_ping_pong', 'handle_pong', 'stage4_heartbeat',
    
    # ユーティリティ
    'get_realtime_stats',
    
    # 型
    'SessionId', 'ProgressStore', 'PingPongSessions'
] 
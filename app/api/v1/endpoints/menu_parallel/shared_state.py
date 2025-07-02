"""
🔄 SSEストリーミング用の共有状態管理

このファイルはメニュー並列処理APIで使用される共有状態とSSEイベント管理を担当します。
複数のエンドポイントファイル間で状態を共有するための中央管理モジュールです。
"""

import time
from typing import Dict, List, Any


# ===============================================
# 🌐 グローバル共有状態
# ===============================================

# 進行状況管理用の辞書（本来はRedis使用推奨）
_progress_streams: Dict[str, List[Dict]] = {}
_active_sessions: Dict[str, Dict] = {}


# ===============================================
# 🔔 SSEイベント管理関数
# ===============================================

def send_sse_event(session_id: str, event_data: Dict[str, Any]) -> None:
    """
    SSEイベントを送信キューに追加
    
    Args:
        session_id: セッションID
        event_data: イベントデータ
    """
    if session_id not in _progress_streams:
        _progress_streams[session_id] = []
    
    event_data["timestamp"] = time.time()
    _progress_streams[session_id].append(event_data)
    
    # キューサイズ制限（メモリ節約）
    if len(_progress_streams[session_id]) > 100:
        _progress_streams[session_id] = _progress_streams[session_id][-50:]


def get_progress_streams() -> Dict[str, List[Dict]]:
    """進行状況ストリーム辞書を取得"""
    return _progress_streams


def get_active_sessions() -> Dict[str, Dict]:
    """アクティブセッション辞書を取得"""
    return _active_sessions


def cleanup_session_state(session_id: str) -> bool:
    """
    指定セッションの状態をクリーンアップ
    
    Args:
        session_id: クリーンアップするセッションID
        
    Returns:
        bool: クリーンアップが実行されたかどうか
    """
    cleaned = False
    
    if session_id in _progress_streams:
        del _progress_streams[session_id]
        cleaned = True
    
    if session_id in _active_sessions:
        del _active_sessions[session_id]
        cleaned = True
    
    return cleaned


def get_sse_statistics() -> Dict[str, Any]:
    """
    SSE統計情報を取得
    
    Returns:
        Dict: 統計情報
    """
    return {
        "active_sessions": len(_active_sessions),
        "total_events_queued": sum(len(events) for events in _progress_streams.values()),
        "sessions_with_events": len(_progress_streams),
        "memory_usage": {
            "progress_streams_kb": sum(len(str(events)) for events in _progress_streams.values()) / 1024,
            "active_sessions_kb": len(str(_active_sessions)) / 1024
        }
    }


def initialize_session(session_id: str, total_items: int = 0) -> None:
    """
    新しいセッションを初期化
    
    Args:
        session_id: セッションID
        total_items: 合計アイテム数
    """
    _active_sessions[session_id] = {
        "start_time": time.time(),
        "total_items": total_items,
        "connection_active": False,
        "last_heartbeat": time.time()
    }


# エクスポート用
__all__ = [
    "_progress_streams",
    "_active_sessions", 
    "send_sse_event",
    "get_progress_streams",
    "get_active_sessions",
    "cleanup_session_state",
    "get_sse_statistics",
    "initialize_session"
] 
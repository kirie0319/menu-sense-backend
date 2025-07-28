"""
🔄 共有状態管理 - レガシー互換レイヤー

このファイルは既存のコードとの後方互換性を維持するためのレガシー互換レイヤーです。
内部的には新しいサービス層を使用し、グローバル状態を排除しています。

⚠️ 廃止予定：新しいコードでは app.services.streaming を直接使用してください
"""

import time
import asyncio
from typing import Dict, List, Any

# 新しいサービス層をインポート
from app.services.streaming import create_streaming_suite


# ===============================================
# 🌐 サービス層インスタンス（グローバル状態の代替）
# ===============================================

# シングルトンサービスインスタンス
_sse_manager, _progress_tracker, _event_broadcaster = create_streaming_suite()


# ===============================================
# 🔔 レガシー互換SSEイベント管理関数
# ===============================================

def send_sse_event(session_id: str, event_data: Dict[str, Any]) -> None:
    """
    SSEイベントを送信キューに追加（レガシー互換）
    
    Args:
        session_id: セッションID
        event_data: イベントデータ
        
    Note: 新しいコードでは EventBroadcaster を使用してください
    """
    print(f"⚠️  Legacy send_sse_event called for session {session_id}")
    print(f"    Event type: {event_data.get('type', 'unknown')}")
    
    # 新しいサービス層に委譲
    try:
        # asyncio.run を使って非同期関数を実行
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success = loop.run_until_complete(_event_broadcaster.sse_manager.send_event(session_id, event_data))
        loop.close()
        
        if not success:
            print(f"    Warning: Session {session_id} not found in SSE manager")
    except Exception as e:
        print(f"    Error: Failed to send SSE event: {str(e)}")


def get_progress_streams() -> Dict[str, List[Dict]]:
    """
    進行状況ストリーム辞書を取得（レガシー互換）
    
    Returns:
        Dict: 空の辞書（レガシー互換性のため）
        
    Note: 新しいコードでは ProgressTracker を使用してください
    """
    print("⚠️  Legacy get_progress_streams called")
    print("    Returning empty dict for compatibility")
    return {}


def get_active_sessions() -> Dict[str, Dict]:
    """
    アクティブセッション辞書を取得（レガシー互換）
    
    Returns:
        Dict: SSEManagerの統計情報を基にした互換データ
        
    Note: 新しいコードでは SSEManager を使用してください
    """
    print("⚠️  Legacy get_active_sessions called")
    
    try:
        # 新しいサービス層から統計を取得
        stats = _sse_manager.get_streaming_statistics()
        
        # レガシー形式に変換
        return {
            "total_sessions": stats["total_sessions"],
            "active_sessions": stats["active_sessions"],
            "legacy_compatibility": True
        }
    except Exception as e:
        print(f"    Error: Failed to get session stats: {str(e)}")
        return {}


def cleanup_session_state(session_id: str) -> bool:
    """
    指定セッションの状態をクリーンアップ（レガシー互換）
    
    Args:
        session_id: クリーンアップするセッションID
        
    Returns:
        bool: クリーンアップが実行されたかどうか
        
    Note: 新しいコードでは各サービスのクリーンアップメソッドを使用してください
    """
    print(f"⚠️  Legacy cleanup_session_state called for session {session_id}")
    
    try:
        # 新しいサービス層でクリーンアップを実行
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # SSEセッションクリーンアップ
        sse_cleaned = loop.run_until_complete(_sse_manager.cleanup_session(session_id))
        
        # 進行状況キャッシュクリーンアップ
        progress_cleaned = loop.run_until_complete(_progress_tracker.cleanup_session_cache(session_id))
        
        loop.close()
        
        print(f"    Cleanup results: SSE={sse_cleaned}, Progress={progress_cleaned}")
        return sse_cleaned or progress_cleaned
        
    except Exception as e:
        print(f"    Error: Failed to cleanup session: {str(e)}")
        return False


def get_sse_statistics() -> Dict[str, Any]:
    """
    SSE統計情報を取得（レガシー互換）
    
    Returns:
        Dict: 統計情報
        
    Note: 新しいコードでは各サービスの統計メソッドを使用してください
    """
    print("⚠️  Legacy get_sse_statistics called")
    
    try:
        # 新しいサービス層から統計を取得
        sse_stats = _sse_manager.get_streaming_statistics()
        progress_stats = _progress_tracker.get_tracking_statistics()
        
        # レガシー形式に変換
        return {
            "active_sessions": sse_stats["active_sessions"],
            "total_events_queued": sse_stats["total_queued_events"],
            "sessions_with_events": sse_stats["active_sessions"],
            "memory_usage": {
                "progress_streams_kb": sse_stats["memory_usage_estimate"],
                "active_sessions_kb": progress_stats["memory_usage_estimate"]
            },
            "new_service_layer": True,
            "legacy_compatibility": True
        }
        
    except Exception as e:
        print(f"    Error: Failed to get SSE statistics: {str(e)}")
        return {
            "active_sessions": 0,
            "total_events_queued": 0,
            "sessions_with_events": 0,
            "memory_usage": {"progress_streams_kb": 0, "active_sessions_kb": 0},
            "error": str(e)
        }


def initialize_session(session_id: str, total_items: int = 0) -> None:
    """
    新しいセッションを初期化（レガシー互換）
    
    Args:
        session_id: セッションID
        total_items: 合計アイテム数
        
    Note: 新しいコードでは SSEManager.update_session_info を使用してください
    """
    print(f"⚠️  Legacy initialize_session called for session {session_id}")
    print(f"    Total items: {total_items}")
    
    try:
        # 新しいサービス層でセッション情報を更新
        success = _sse_manager.update_session_info(session_id, total_items)
        print(f"    Session initialization: {'success' if success else 'failed'}")
        
    except Exception as e:
        print(f"    Error: Failed to initialize session: {str(e)}")


# ===============================================
# 廃止予定の互換性エクスポート
# ===============================================

# レガシー互換性のためのエクスポート（すべて空またはダミー値）
_progress_streams: Dict[str, List[Dict]] = {}
_active_sessions: Dict[str, Dict] = {}

# エクスポート用
__all__ = [
    "_progress_streams",      # 廃止予定：空の辞書
    "_active_sessions",       # 廃止予定：空の辞書
    "send_sse_event",         # 互換：EventBroadcaster.sse_manager.send_event に委譲
    "get_progress_streams",   # 互換：空の辞書を返却
    "get_active_sessions",    # 互換：SSEManager統計に委譲
    "cleanup_session_state",  # 互換：各サービスのクリーンアップに委譲
    "get_sse_statistics",     # 互換：各サービスの統計に委譲
    "initialize_session"      # 互換：SSEManager.update_session_info に委譲
]


# ===============================================
# 移行ガイド
# ===============================================

def _print_migration_guide():
    """移行ガイドを表示"""
    print("""
🔄 MIGRATION GUIDE - shared_state.py の置き換え

このファイルは廃止予定です。新しいサービス層を使用してください：

# 古い方法（廃止予定）
from .shared_state import send_sse_event, initialize_session

# 新しい方法（推奨）
from app.services.dependencies import EventBroadcasterDep, SSEManagerDep
from fastapi import Depends

async def my_endpoint(broadcaster: EventBroadcasterDep):
    await broadcaster.sse_manager.send_event(session_id, event_data)
    broadcaster.sse_manager.update_session_info(session_id, total_items)

主な変更点：
- グローバル変数 → サービスインスタンス
- 同期関数 → 非同期関数
- 手動状態管理 → 自動管理
- 単一ファイル → 専用サービス
    """)


# 初回インポート時に移行ガイドを表示
# if __name__ != "__main__":
#     _print_migration_guide() 
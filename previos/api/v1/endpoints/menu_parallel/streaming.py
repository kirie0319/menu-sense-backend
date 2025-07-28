"""
📡 SSEストリーミングAPI - リファクタリング版

このファイルはSSEリアルタイムストリーミングAPIエンドポイントを提供します。
ストリーミング管理はサービス層に委譲し、HTTPハンドリングのみを担当します。

エンドポイント:
- GET /stream/{session_id}: リアルタイムSSEストリーミング
- POST /notify/{session_id}: 外部SSEイベント通知
"""

import time
from typing import Dict, Any
from fastapi import APIRouter, Request, HTTPException

from app.services.dependencies import SSEManagerDep, EventBroadcasterDep, IntegratedStreamingDep

# FastAPIルーター作成
router = APIRouter()


@router.get("/stream/{session_id}")
async def stream_real_time_progress(
    session_id: str, 
    request: Request,
    sse_manager: SSEManagerDep
):
    """
    🔄 メニューアイテム並列処理のリアルタイムSSEストリーミング
    
    ストリーミング管理をサービス層に完全委譲し、エンドポイントはHTTP処理のみ担当
    """
    try:
        # ストリーミング開始をサービス層に委譲
        return await sse_manager.create_stream(session_id, request)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create SSE stream: {str(e)}")


@router.get("/stream/{session_id}/with-progress")
async def stream_with_integrated_progress(
    session_id: str, 
    request: Request,
    streaming_services: IntegratedStreamingDep,
    total_items: int = 10
):
    """
    🔄 統合進行状況付きSSEストリーミング
    
    進行状況追跡とSSE配信を統合したストリーミング
    """
    try:
        sse_manager, progress_tracker, event_broadcaster = streaming_services
        
        # セッション情報更新
        sse_manager.update_session_info(session_id, total_items)
        
        # バックグラウンドで進行状況を監視・配信
        async def progress_monitor():
            """進行状況を定期的にチェックしてSSEで配信"""
            while True:
                try:
                    # 進行状況更新を配信
                    await event_broadcaster.broadcast_progress_update(session_id, total_items)
                    
                    # 2秒間隔でチェック
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    print(f"⚠️ Progress monitor error: {str(e)}")
                    break
        
        # 進行状況監視開始（バックグラウンド）
        import asyncio
        asyncio.create_task(progress_monitor())
        
        # SSEストリーミング開始
        return await sse_manager.create_stream(session_id, request)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create integrated SSE stream: {str(e)}")


@router.post("/notify/{session_id}")
async def notify_sse_event(
    session_id: str, 
    event_data: Dict[str, Any],
    event_broadcaster: EventBroadcasterDep
):
    """
    🔔 外部からのSSEイベント通知エンドポイント
    
    イベント配信をサービス層に委譲し、HTTPレスポンス変換のみ担当
    """
    try:
        # イベント配信をサービス層に委譲
        success = await event_broadcaster.sse_manager.send_event(session_id, event_data)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
        
        # HTTPレスポンス構築
        return {
            "success": True,
            "session_id": session_id,
            "message": "SSE event queued successfully",
            "event_type": event_data.get("type", "unknown"),
            "timestamp": time.time()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to queue SSE event: {str(e)}")


@router.get("/statistics")
async def get_streaming_statistics(
    streaming_services: IntegratedStreamingDep
):
    """
    📊 ストリーミング統計情報を取得
    
    サービス層に委譲し、統計情報を統合して返却
    """
    try:
        sse_manager, progress_tracker, event_broadcaster = streaming_services
        
        # 各サービスの統計を取得
        sse_stats = sse_manager.get_streaming_statistics()
        progress_stats = progress_tracker.get_tracking_statistics()
        
        # 統合統計情報構築
        return {
            "success": True,
            "streaming_statistics": sse_stats,
            "progress_statistics": progress_stats,
            "service_status": "active",
            "features": [
                "real_time_streaming",
                "progress_tracking", 
                "event_broadcasting",
                "session_management",
                "automatic_cleanup"
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get streaming statistics: {str(e)}")


@router.delete("/cleanup/{session_id}")
async def cleanup_streaming_session(
    session_id: str,
    streaming_services: IntegratedStreamingDep
):
    """
    🧹 ストリーミングセッションクリーンアップ
    
    サービス層に委譲し、全サービスのクリーンアップを実行
    """
    try:
        sse_manager, progress_tracker, event_broadcaster = streaming_services
        
        # 各サービスのクリーンアップを実行
        cleanup_results = {}
        
        # SSEセッションクリーンアップ
        sse_cleaned = await sse_manager.cleanup_session(session_id)
        cleanup_results["sse_session"] = sse_cleaned
        
        # 進行状況キャッシュクリーンアップ
        progress_cleaned = await progress_tracker.cleanup_session_cache(session_id)
        cleanup_results["progress_cache"] = progress_cleaned
        
        # HTTPレスポンス構築
        return {
            "success": True,
            "session_id": session_id,
            "cleanup_results": cleanup_results,
            "message": f"Streaming session {session_id} cleaned up successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cleanup streaming session: {str(e)}")


# エクスポート用
__all__ = ["router"] 
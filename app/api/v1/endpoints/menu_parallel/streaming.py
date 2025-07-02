"""
📡 SSEリアルタイムストリーミング機能

このファイルはメニュー並列処理のリアルタイム進行状況をSSE（Server-Sent Events）で
クライアントに配信する機能を提供します。
"""

import time
import json
import asyncio
from typing import Dict, Any
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse

from .shared_state import (
    _progress_streams, _active_sessions,
    send_sse_event, get_sse_statistics
)
from app.tasks.menu_item_parallel_tasks import get_real_status

# FastAPIルーター作成
router = APIRouter()


@router.get("/stream/{session_id}")
async def stream_real_time_progress(session_id: str, request: Request):
    """
    🔄 メニューアイテム並列処理のリアルタイムSSEストリーミング
    
    Args:
        session_id: セッションID
        request: FastAPIリクエスト（切断検出用）
        
    Returns:
        StreamingResponse: SSEストリーム
    """
    
    async def event_generator():
        """SSEイベント生成器"""
        try:
            # セッション初期化
            if session_id not in _progress_streams:
                _progress_streams[session_id] = []
            
            if session_id not in _active_sessions:
                _active_sessions[session_id] = {
                    "start_time": time.time(),
                    "last_heartbeat": time.time(),
                    "total_items": 0,
                    "connection_active": True
                }
            
            # 接続確認イベント
            connection_event = {
                "type": "connection_established",
                "session_id": session_id,
                "timestamp": time.time(),
                "message": "🔄 Real-time streaming connected",
                "api_integration": "real_api_integration"
            }
            yield f"data: {json.dumps(connection_event)}\n\n"
            
            heartbeat_interval = 30  # 30秒間隔でハートビート
            last_heartbeat = time.time()
            last_item_count = 0
            
            while True:
                current_time = time.time()
                
                # クライアント切断チェック
                if await request.is_disconnected():
                    print(f"🔌 Client disconnected from SSE stream: {session_id}")
                    break
                
                # 新しい進行状況イベントをチェック
                if _progress_streams.get(session_id):
                    event_data = _progress_streams[session_id].pop(0)
                    yield f"data: {json.dumps(event_data)}\n\n"
                    last_heartbeat = current_time
                    continue
                
                # 実際の進行状況を定期的にチェック（Redis から）
                try:
                    # セッション情報を推測
                    if session_id not in _active_sessions or not _active_sessions[session_id].get("total_items"):
                        # セッション情報を推測（通常は10-40アイテム）
                        estimated_total = 10
                        _active_sessions[session_id]["total_items"] = estimated_total
                    
                    total_items = _active_sessions[session_id]["total_items"]
                    
                    # 各アイテムの状況をチェック
                    completed_count = 0
                    in_progress_count = 0
                    translation_completed = 0
                    description_completed = 0
                    image_completed = 0
                    
                    items_status = []
                    
                    for item_id in range(total_items):
                        status = get_real_status(session_id, item_id)
                        
                        if "error" not in status:
                            t_complete = status.get("translation", {}).get("completed", False)
                            d_complete = status.get("description", {}).get("completed", False)  
                            i_complete = status.get("image", {}).get("completed", False)
                            
                            if t_complete:
                                translation_completed += 1
                            if d_complete:
                                description_completed += 1
                            if i_complete:
                                image_completed += 1
                                
                            if t_complete and d_complete and i_complete:
                                completed_count += 1
                            elif t_complete or d_complete:
                                in_progress_count += 1
                            
                            # 実際のデータ追加
                            item_data = {
                                "item_id": item_id,
                                "translation_completed": t_complete,
                                "description_completed": d_complete,
                                "image_completed": i_complete
                            }
                            
                            # 実際のAPI結果データ
                            if t_complete:
                                t_data = status.get("translation", {}).get("data", {})
                                item_data["japanese_text"] = t_data.get("japanese_text", "")
                                item_data["english_text"] = t_data.get("english_text", "")
                                item_data["translation_provider"] = t_data.get("provider", "")
                            
                            if d_complete:
                                d_data = status.get("description", {}).get("data", {})
                                item_data["description"] = d_data.get("description", "")
                                item_data["description_provider"] = d_data.get("provider", "")
                            
                            if i_complete:
                                i_data = status.get("image", {}).get("data", {})
                                item_data["image_url"] = i_data.get("image_url", "")
                                item_data["image_provider"] = i_data.get("provider", "")
                                item_data["fallback_used"] = i_data.get("fallback_used", False)
                            
                            items_status.append(item_data)
                    
                    # 進行状況に変化があった場合のみ送信
                    current_item_count = completed_count + in_progress_count
                    if current_item_count > last_item_count or completed_count > 0:
                        progress_percentage = (completed_count / total_items * 100) if total_items > 0 else 0
                        
                        progress_event = {
                            "type": "progress_update",
                            "session_id": session_id,
                            "timestamp": current_time,
                            "total_items": total_items,
                            "completed_items": completed_count,
                            "in_progress_items": in_progress_count,
                            "progress_percentage": progress_percentage,
                            "api_stats": {
                                "translation_completed": translation_completed,
                                "description_completed": description_completed,
                                "image_completed": image_completed
                            },
                            "items_status": items_status,
                            "api_integration": "real_api_integration",
                            "elapsed_time": current_time - _active_sessions[session_id]["start_time"]
                        }
                        
                        yield f"data: {json.dumps(progress_event)}\n\n"
                        last_item_count = current_item_count
                        last_heartbeat = current_time
                        
                        # 完了チェック
                        if completed_count >= total_items:
                            completion_event = {
                                "type": "processing_completed",
                                "session_id": session_id,
                                "timestamp": current_time,
                                "total_time": current_time - _active_sessions[session_id]["start_time"],
                                "final_stats": {
                                    "total_items": total_items,
                                    "completed_items": completed_count,
                                    "success_rate": (completed_count / total_items * 100) if total_items > 0 else 0,
                                    "api_integration": "real_api_integration"
                                },
                                "message": "🎉 All menu items processed successfully!"
                            }
                            yield f"data: {json.dumps(completion_event)}\n\n"
                            
                            # ストリーミング終了の準備
                            await asyncio.sleep(2)
                            break
                
                except Exception as status_error:
                    print(f"⚠️ Status check error in SSE: {status_error}")
                
                # ハートビート送信
                if current_time - last_heartbeat > heartbeat_interval:
                    heartbeat_event = {
                        "type": "heartbeat", 
                        "session_id": session_id,
                        "timestamp": current_time,
                        "uptime": current_time - _active_sessions[session_id]["start_time"],
                        "message": "💓 Connection alive"
                    }
                    yield f"data: {json.dumps(heartbeat_event)}\n\n"
                    last_heartbeat = current_time
                
                # 短時間待機
                await asyncio.sleep(2)
                
        except Exception as e:
            print(f"❌ SSE stream error for {session_id}: {str(e)}")
            
            error_event = {
                "type": "stream_error",
                "session_id": session_id,
                "timestamp": time.time(),
                "error": str(e),
                "message": "⚠️ Streaming error occurred"
            }
            yield f"data: {json.dumps(error_event)}\n\n"
            
        finally:
            # クリーンアップ
            if session_id in _active_sessions:
                _active_sessions[session_id]["connection_active"] = False
            print(f"🧹 SSE stream cleanup completed for {session_id}")
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Expose-Headers": "*",
            "X-Accel-Buffering": "no",  # Nginxバッファリング無効
            "Content-Encoding": "identity",  # モバイル圧縮問題回避
            "Transfer-Encoding": "chunked"  # チャンク転送
        }
    )


@router.post("/notify/{session_id}")
async def notify_sse_event(session_id: str, event_data: Dict[str, Any]):
    """
    🔔 外部からのSSEイベント通知エンドポイント（タスクから呼び出し用）
    
    Args:
        session_id: セッションID
        event_data: イベントデータ
        
    Returns:
        Dict: 通知結果
    """
    
    try:
        send_sse_event(session_id, event_data)
        
        return {
            "success": True,
            "session_id": session_id,
            "message": "SSE event queued successfully",
            "event_type": event_data.get("type", "unknown"),
            "timestamp": time.time()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to queue SSE event: {str(e)}")


# エクスポート用
__all__ = ["router"] 
"""
進行状況管理関連のAPIハンドラー
"""
import asyncio
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.core.config import settings

router = APIRouter()

# グローバル状態変数の取得関数（リアルタイム通信サービスから取得）
def get_progress_state():
    """進行状況管理の状態を取得"""
    try:
        from app.services.realtime import get_progress_store, get_ping_pong_sessions
        return {
            "progress_store": get_progress_store(),
            "ping_pong_sessions": get_ping_pong_sessions()
        }
    except ImportError as e:
        print(f"⚠️ Progress state import error: {e}")
        # フォールバック用の空状態
        return {
            "progress_store": {},
            "ping_pong_sessions": {}
        }

# 進行状況管理関数の取得
def get_progress_functions():
    """進行状況管理関数を取得"""
    try:
        from app.services.realtime import send_progress, send_ping, start_ping_pong, handle_pong
        return {
            "send_progress": send_progress,
            "send_ping": send_ping,  
            "start_ping_pong": start_ping_pong,
            "handle_pong": handle_pong
        }
    except ImportError as e:
        print(f"⚠️ Progress functions import error: {e}")
        # フォールバック関数（後で実装）
        return {
            "send_progress": None,
            "send_ping": None,
            "start_ping_pong": None,
            "handle_pong": None
        }

@router.get("/api/progress/{session_id}")
async def get_progress(session_id: str):
    """Server-Sent Eventsで進行状況を送信（モバイル対応版）"""
    
    # 状態を取得
    state = get_progress_state()
    progress_store = state["progress_store"]
    ping_pong_sessions = state["ping_pong_sessions"]
    
    async def event_generator():
        completed = False
        last_heartbeat = asyncio.get_event_loop().time()
        heartbeat_interval = settings.SSE_HEARTBEAT_INTERVAL  # ハートビート間隔（モバイル向け）
        
        while not completed and session_id in progress_store:
            current_time = asyncio.get_event_loop().time()
            
            # 新しい進行状況があるか確認
            if progress_store[session_id]:
                progress_data = progress_store[session_id].pop(0)
                yield f"data: {json.dumps(progress_data)}\n\n"
                last_heartbeat = current_time
                
                # 完了チェック
                if progress_data.get("stage") == 6:
                    completed = True
            else:
                # ハートビート送信（モバイル接続維持用）
                if current_time - last_heartbeat > heartbeat_interval:
                    heartbeat_data = {
                        "type": "heartbeat",
                        "timestamp": current_time,
                        "session_id": session_id
                    }
                    yield f"data: {json.dumps(heartbeat_data)}\n\n"
                    last_heartbeat = current_time
                
                await asyncio.sleep(0.2)
        
        # セッション終了とクリーンアップ
        if session_id in progress_store:
            del progress_store[session_id]
            
        # Ping/Pong機能の停止
        if session_id in ping_pong_sessions:
            ping_pong_sessions[session_id]["active"] = False
            print(f"🏓 Ping/Pong stopped for SSE disconnect: {session_id}")
    
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

@router.post("/api/pong/{session_id}")
async def receive_pong(session_id: str):
    """クライアントからのPongを受信"""
    
    # 進行状況管理関数を取得
    functions = get_progress_functions()
    handle_pong = functions["handle_pong"]
    
    if handle_pong is None:
        # フォールバック実装
        state = get_progress_state()
        ping_pong_sessions = state["ping_pong_sessions"]
        
        if session_id in ping_pong_sessions:
            ping_pong_sessions[session_id]["last_pong"] = asyncio.get_event_loop().time()
            print(f"🏓 Pong received from {session_id}")
            return {"status": "pong_received", "session_id": session_id}
        else:
            return {"status": "session_not_found", "session_id": session_id}
    else:
        # main.pyのhandle_pong関数を使用
        success = await handle_pong(session_id)
        if success:
            return {"status": "pong_received", "session_id": session_id}
        else:
            return {"status": "session_not_found", "session_id": session_id} 
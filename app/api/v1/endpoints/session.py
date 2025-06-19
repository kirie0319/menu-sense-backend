from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import asyncio
import json

from app.core.config import settings

router = APIRouter()

@router.get("/progress/{session_id}")
async def get_progress(session_id: str):
    """Server-Sent Eventsで進行状況を送信（モバイル対応版）"""
    
    # インポートを移動 - 循環インポート回避
    from app.services.realtime import get_session_manager
    
    session_manager = get_session_manager()
    
    async def event_generator():
        completed = False
        last_heartbeat = asyncio.get_event_loop().time()
        heartbeat_interval = settings.SSE_HEARTBEAT_INTERVAL  # ハートビート間隔（モバイル向け）
        
        while not completed and session_manager.session_exists(session_id):
            current_time = asyncio.get_event_loop().time()
            
            # 新しい進行状況があるか確認
            if session_manager.has_progress(session_id):
                progress_data = session_manager.pop_progress(session_id)
                if progress_data:
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
        session_manager.delete_session(session_id)
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

@router.post("/pong/{session_id}")
async def receive_pong(session_id: str):
    """クライアントからのPongを受信"""
    
    # インポートを移動 - 循環インポート回避
    from app.services.realtime import handle_pong
    
    success = await handle_pong(session_id)
    if success:
        return {"status": "pong_received", "session_id": session_id}
    else:
        return {"status": "session_not_found", "session_id": session_id} 
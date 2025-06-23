"""
🎯 メニューアイテム並列処理API（実際のAPI統合版）

40品のメニューを受信して、1品ずつ並列処理を開始
- Google Translate API
- OpenAI GPT-4.1-mini  
- Google Imagen 3
"""

import time
import uuid
import json
import asyncio
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.tasks.menu_item_parallel_tasks import (
    sse_translate_menu_item,
    sse_generate_menu_description,
    get_sse_status,
    sse_redis_connection
)

router = APIRouter()

class MenuItemsRequest(BaseModel):
    """メニューアイテムリクエスト"""
    menu_items: List[str]  # 日本語メニューテキストのリスト
    test_mode: Optional[bool] = False  # Phase 2では実際のAPI統合がデフォルト

class MenuItemsResponse(BaseModel):
    """メニューアイテムレスポンス"""
    success: bool
    session_id: str
    total_items: int
    message: str
    test_mode: bool
    api_integration: str

class ItemStatusResponse(BaseModel):
    """アイテム状況レスポンス"""
    success: bool
    session_id: str
    item_id: int
    translation: Dict[str, Any]
    description: Dict[str, Any]
    image: Dict[str, Any]

class SessionStatusResponse(BaseModel):
    """セッション全体の状況レスポンス"""
    success: bool
    session_id: str
    total_items: int
    completed_items: int
    progress_percentage: float
    items_status: List[Dict[str, Any]]
    api_integration: str

# ===============================================
# 🔄 SSEリアルタイムストリーミング機能
# ===============================================

# 進行状況管理用の辞書（本来はRedis使用推奨）
_progress_streams: Dict[str, List[Dict]] = {}
_active_sessions: Dict[str, Dict] = {}

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
                        status = get_sse_status(session_id, item_id)
                        
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

def send_sse_event(session_id: str, event_data: Dict[str, Any]):
    """SSEイベントを送信キューに追加"""
    if session_id not in _progress_streams:
        _progress_streams[session_id] = []
    
    event_data["timestamp"] = time.time()
    _progress_streams[session_id].append(event_data)
    
    # キューサイズ制限（メモリ節約）
    if len(_progress_streams[session_id]) > 100:
        _progress_streams[session_id] = _progress_streams[session_id][-50:]

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

# ===============================================
# 🎯 既存のエンドポイント群
# ===============================================

@router.post("/process-menu-items", response_model=MenuItemsResponse)
async def process_menu_items(request: MenuItemsRequest):
    """
    🎯 メニューアイテムを実際のAPI統合で1品ずつ並列処理開始
    
    処理の流れ:
    1. セッションIDを生成
    2. 各アイテムにGoogle Translate翻訳タスクとOpenAI説明生成タスクを投入
    3. 翻訳+説明完了時にGoogle Imagen画像生成が自動トリガー
    4. クライアントは別エンドポイントで進行状況を監視
    """
    
    try:
        # セッションID生成
        session_id = f"real_{int(time.time())}_{str(uuid.uuid4())[:8]}"
        
        # バリデーション
        if not request.menu_items:
            raise HTTPException(status_code=400, detail="Menu items cannot be empty")
        
        if len(request.menu_items) > 100:  # 安全のため上限設定
            raise HTTPException(status_code=400, detail="Too many menu items (max: 100)")
        
        # Redis接続確認
        redis_status = sse_redis_connection()
        if not redis_status["success"]:
            raise HTTPException(status_code=500, detail=f"Redis connection failed: {redis_status['message']}")
        
        # API統合モード判定
        api_mode = "test_mode" if request.test_mode else "real_api_integration"
        
        # SSE用セッション初期化
        _active_sessions[session_id] = {
            "start_time": time.time(),
            "total_items": len(request.menu_items),
            "connection_active": False
        }
        
        # 処理開始SSEイベント
        start_event = {
            "type": "processing_started",
            "session_id": session_id,
            "total_items": len(request.menu_items),
            "menu_items": request.menu_items,
            "api_integration": api_mode,
            "message": f"🚀 Started processing {len(request.menu_items)} menu items with real API integration"
        }
        send_sse_event(session_id, start_event)
        
        # 各メニューアイテムに対してSSE専用タスクを並列投入
        for item_id, item_text in enumerate(request.menu_items):
            # Google Translate翻訳タスク投入（SSE専用キュー）
            sse_translate_menu_item.apply_async(
                args=[session_id, item_id, item_text],
                queue='sse_translate_queue'
            )
            
            # OpenAI説明生成タスク投入（SSE専用キュー）
            sse_generate_menu_description.apply_async(
                args=[session_id, item_id, item_text],
                queue='sse_description_queue'
            )
            
            # タスク投入SSEイベント
            task_event = {
                "type": "tasks_queued",
                "session_id": session_id,
                "item_id": item_id,
                "item_text": item_text,
                "queued_tasks": ["translation", "description"],
                "message": f"📤 Queued processing tasks for: {item_text}"
            }
            send_sse_event(session_id, task_event)
        
        return MenuItemsResponse(
            success=True,
            session_id=session_id,
            total_items=len(request.menu_items),
            message=f"Started real API integration processing for {len(request.menu_items)} menu items. Google Translate + OpenAI GPT-4.1-mini + Google Imagen 3. Use /stream/{session_id} for real-time progress.",
            test_mode=request.test_mode,
            api_integration=api_mode
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start real API processing: {str(e)}")

@router.get("/status/{session_id}/item/{item_id}", response_model=ItemStatusResponse)
async def get_item_status(session_id: str, item_id: int):
    """
    🔍 特定アイテムの実際の処理状況を取得
    
    Args:
        session_id: セッションID
        item_id: アイテムID
        
    Returns:
        アイテムの翻訳・説明・画像の状況（実際のAPI結果）
    """
    
    try:
        status = get_sse_status(session_id, item_id)
        
        if "error" in status:
            raise HTTPException(status_code=500, detail=status["error"])
        
        return ItemStatusResponse(
            success=True,
            session_id=session_id,
            item_id=item_id,
            translation=status.get("translation", {"completed": False, "data": None}),
            description=status.get("description", {"completed": False, "data": None}),
            image=status.get("image", {"completed": False, "data": None})
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get real item status: {str(e)}")

@router.get("/status/{session_id}", response_model=SessionStatusResponse)
async def get_session_status(session_id: str, total_items: int):
    """
    📊 セッション全体の実際の進行状況を取得
    
    Args:
        session_id: セッションID
        total_items: 合計アイテム数
        
    Returns:
        セッション全体の進行状況（実際のAPI結果）
    """
    
    try:
        items_status = []
        completed_count = 0
        
        # API統合モード判定
        api_mode = "real_api_integration"
        if "test_" in session_id:
            api_mode = "test_mode"
        
        # 各アイテムの状況を取得
        for item_id in range(total_items):
            status = get_sse_status(session_id, item_id)
            
            if "error" in status:
                # エラーがあっても継続
                item_status = {
                    "item_id": item_id,
                    "translation_completed": False,
                    "description_completed": False,
                    "image_completed": False,
                    "error": status["error"]
                }
            else:
                translation_completed = status.get("translation", {}).get("completed", False)
                description_completed = status.get("description", {}).get("completed", False)
                image_completed = status.get("image", {}).get("completed", False)
                
                # 全ての処理が完了したアイテムをカウント
                if translation_completed and description_completed and image_completed:
                    completed_count += 1
                
                # 実際のAPIデータを含める
                translation_data = status.get("translation", {}).get("data", {})
                description_data = status.get("description", {}).get("data", {})
                image_data = status.get("image", {}).get("data", {})
                
                item_status = {
                    "item_id": item_id,
                    "translation_completed": translation_completed,
                    "description_completed": description_completed,
                    "image_completed": image_completed,
                    "translation_data": translation_data,
                    "description_data": description_data,
                    "image_data": image_data,
                    # API統合詳細情報
                    "api_providers": {
                        "translation": translation_data.get("provider", "unknown"),
                        "description": description_data.get("provider", "unknown"),
                        "image": image_data.get("provider", "unknown")
                    },
                    "processing_quality": {
                        "translation_fallback": translation_data.get("provider") == "GoogleTranslateAPI",
                        "description_fallback": description_data.get("provider") == "OpenAI_GPT4.1-mini",
                        "image_fallback": image_data.get("fallback_used", False)
                    }
                }
            
            items_status.append(item_status)
        
        progress_percentage = (completed_count / total_items * 100) if total_items > 0 else 0
        
        return SessionStatusResponse(
            success=True,
            session_id=session_id,
            total_items=total_items,
            completed_items=completed_count,
            progress_percentage=progress_percentage,
            items_status=items_status,
            api_integration=api_mode
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get real session status: {str(e)}")

# ===============================================
# 🧪 デバッグ・テスト用エンドポイント
# ===============================================

@router.get("/test/redis")
async def test_redis():
    """Redis接続テスト用エンドポイント（実際のAPI統合版）"""
    try:
        result = sse_redis_connection()
        return {
            "success": result["success"],
            "message": result["message"],
            "test_data": result.get("test_data", {}),
            "timestamp": time.time(),
            "redis_mode": "real_api_integration"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Real Redis test failed: {str(e)}")

@router.post("/test/single-item")
async def test_single_item_processing(
    item_text: str,
    test_translation: bool = True,
    test_description: bool = True,
    use_real_apis: bool = True
):
    """単一アイテムの実際のAPI処理テスト"""
    try:
        session_id = f"single_real_{int(time.time())}"
        item_id = 0
        
        tasks = []
        
        if test_translation:
            translation_task = sse_translate_menu_item.delay(session_id, item_id, item_text)
            tasks.append(("sse_translation", translation_task.id))
        
        if test_description:
            description_task = sse_generate_menu_description.delay(session_id, item_id, item_text)
            tasks.append(("sse_description", description_task.id))
        
        return {
            "success": True,
            "session_id": session_id,
            "item_id": item_id,
            "item_text": item_text,
            "tasks": tasks,
            "api_integration": "real_apis" if use_real_apis else "test_mode",
            "apis_used": [
                "Google Translate API",
                "OpenAI GPT-4.1-mini",
                "Google Imagen 3 (auto-trigger)"
            ],
            "streaming_url": f"/api/v1/menu-parallel/stream/{session_id}",
            "message": "Real API single item test started. Check status with GET /status/{session_id}/item/{item_id}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Real API single item test failed: {str(e)}")

@router.delete("/cleanup/{session_id}")
async def cleanup_session(session_id: str):
    """
    🧹 セッションデータのクリーンアップ（実際のAPI統合版）
    
    Note: 実際のRedisキー削除は実装していません（安全のため）
    """
    try:
        # SSEストリーミングのクリーンアップ
        if session_id in _progress_streams:
            del _progress_streams[session_id]
        
        if session_id in _active_sessions:
            del _active_sessions[session_id]
        
        return {
            "success": True,
            "session_id": session_id,
            "message": "Real API session cleanup completed (SSE streams and active sessions cleared)",
            "timestamp": time.time(),
            "cleanup_mode": "real_api_session"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Real API cleanup failed: {str(e)}")

# ===============================================
# 📊 統計・監視用エンドポイント（実際のAPI統合版）
# ===============================================

@router.get("/stats/system")
async def get_system_stats():
    """システム統計情報を取得（実際のAPI統合版）"""
    try:
        # Redis統計
        redis_status = sse_redis_connection()
        
        # API利用可能性チェック
        from app.services.translation.google_translate import GoogleTranslateService
        from app.services.description.openai import OpenAIDescriptionService
        from app.services.image.imagen3 import Imagen3Service
        
        google_translate = GoogleTranslateService()
        openai_description = OpenAIDescriptionService()
        imagen3_service = Imagen3Service()
        
        # Celery統計（基本情報のみ）
        celery_status = {
            "available": True,  # 後で celery inspect を追加
            "queues": ["sse_translate_queue", "sse_description_queue", "sse_image_queue", "default"],
            "sse_api_integration": True
        }
        
        # SSE統計
        sse_stats = {
            "active_streams": len(_active_sessions),
            "total_events_queued": sum(len(events) for events in _progress_streams.values()),
            "sessions_with_events": len(_progress_streams)
        }
        
        return {
            "success": True,
            "redis": redis_status,
            "celery": celery_status,
            "sse_streaming": sse_stats,
            "api_services": {
                "google_translate": {
                    "available": google_translate.is_available(),
                    "service": "Google Translate API",
                    "queue": "sse_translate_queue"
                },
                "openai_description": {
                    "available": openai_description.is_available(),
                    "service": "OpenAI GPT-4.1-mini",
                    "queue": "sse_description_queue"
                },
                "imagen3_image": {
                    "available": imagen3_service.is_available(),
                    "service": "Google Imagen 3",
                    "queue": "sse_image_queue"
                }
            },
            "system": {
                "timestamp": time.time(),
                "version": "2.1.0-real-api-sse",
                "mode": "real_api_integration_with_sse",
                "features": [
                    "google_translate_api_integration",
                    "openai_gpt4.1_mini_integration",
                    "google_imagen3_integration",
                    "redis_state_management", 
                    "celery_queue_separation",
                    "dependency_based_triggering",
                    "parallel_processing",
                    "fallback_mechanisms",
                    "sse_real_time_streaming",
                    "progress_monitoring",
                    "connection_management"
                ]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get real API system stats: {str(e)}")

@router.get("/stats/api-health")
async def get_api_health():
    """実際のAPI統合の健康状態チェック"""
    try:
        from app.services.translation.google_translate import GoogleTranslateService
        from app.services.description.openai import OpenAIDescriptionService
        from app.services.image.imagen3 import Imagen3Service
        
        # 各APIサービスの健康状態
        health_status = {}
        overall_health = True
        
        # Google Translate
        try:
            translate_service = GoogleTranslateService()
            health_status["google_translate"] = {
                "status": "healthy" if translate_service.is_available() else "unavailable",
                "service": "Google Translate API",
                "critical": True
            }
            if not translate_service.is_available():
                overall_health = False
        except Exception as e:
            health_status["google_translate"] = {
                "status": "error",
                "error": str(e),
                "critical": True
            }
            overall_health = False
        
        # OpenAI GPT-4.1-mini
        try:
            description_service = OpenAIDescriptionService()
            health_status["openai_gpt4_1_mini"] = {
                "status": "healthy" if description_service.is_available() else "unavailable",
                "service": "OpenAI GPT-4.1-mini",
                "critical": True
            }
            if not description_service.is_available():
                overall_health = False
        except Exception as e:
            health_status["openai_gpt4_1_mini"] = {
                "status": "error",
                "error": str(e),
                "critical": True
            }
            overall_health = False
        
        # Google Imagen 3
        try:
            image_service = Imagen3Service()
            health_status["google_imagen3"] = {
                "status": "healthy" if image_service.is_available() else "unavailable",
                "service": "Google Imagen 3",
                "critical": False  # 画像生成はオプショナル
            }
        except Exception as e:
            health_status["google_imagen3"] = {
                "status": "error",
                "error": str(e),
                "critical": False
            }
        
        # SSE健康状態
        health_status["sse_streaming"] = {
            "status": "healthy",
            "service": "SSE Real-time Streaming",
            "critical": False,
            "active_streams": len(_active_sessions),
            "events_queued": sum(len(events) for events in _progress_streams.values())
        }
        
        return {
            "overall_health": "healthy" if overall_health else "degraded",
            "api_services": health_status,
            "integration_mode": "real_api_integration_with_sse",
            "timestamp": time.time(),
            "recommendations": [
                "All critical APIs (Google Translate + OpenAI) should be healthy",
                "Google Imagen 3 is optional but recommended for full functionality",
                "SSE streaming provides real-time progress updates",
                "Check API keys and authentication if any service is unavailable"
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"API health check failed: {str(e)}")

@router.get("/stats/sse")
async def get_sse_stats():
    """SSEストリーミング統計情報"""
    try:
        active_sessions_info = []
        
        for session_id, session_data in _active_sessions.items():
            uptime = time.time() - session_data["start_time"]
            
            session_info = {
                "session_id": session_id,
                "uptime": uptime,
                "total_items": session_data.get("total_items", 0),
                "connection_active": session_data.get("connection_active", False),
                "events_queued": len(_progress_streams.get(session_id, []))
            }
            active_sessions_info.append(session_info)
        
        return {
            "success": True,
            "sse_statistics": {
                "active_sessions": len(_active_sessions),
                "total_events_queued": sum(len(events) for events in _progress_streams.values()),
                "sessions_with_events": len(_progress_streams),
                "memory_usage": {
                    "progress_streams_kb": sum(len(str(events)) for events in _progress_streams.values()) / 1024,
                    "active_sessions_kb": len(str(_active_sessions)) / 1024
                }
            },
            "active_sessions": active_sessions_info,
            "features": [
                "real_time_progress_streaming",
                "automatic_heartbeat",
                "connection_management",
                "event_queuing",
                "memory_efficient_cleanup"
            ],
            "timestamp": time.time()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get SSE stats: {str(e)}") 
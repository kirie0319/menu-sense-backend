"""
🎯 メインメニューアイテム処理API

このファイルはメニューアイテムの並列処理を管理するコアAPIエンドポイントを提供します。
- メニューアイテム並列処理開始
- アイテム個別状況取得
- セッション全体進行状況取得
"""

import time
import uuid
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException

from .models import MenuItemsRequest, MenuItemsResponse, ItemStatusResponse, SessionStatusResponse
from .shared_state import send_sse_event, initialize_session
from app.tasks.menu_item_parallel_tasks import (
    real_translate_menu_item,
    real_generate_menu_description,
    test_translate_menu_item,
    test_generate_menu_description,
    get_real_status,
    test_redis_connection
)

# FastAPIルーター作成
router = APIRouter()


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
        redis_status = test_redis_connection()
        if not redis_status["success"]:
            raise HTTPException(status_code=500, detail=f"Redis connection failed: {redis_status['message']}")
        
        # API統合モード判定
        api_mode = "test_mode" if request.test_mode else "real_api_integration"
        
        # SSE用セッション初期化
        initialize_session(session_id, len(request.menu_items))
        
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
        
        # 各メニューアイテムに対して実API統合タスクを並列投入
        for item_id, item_text in enumerate(request.menu_items):
            if request.test_mode:
                # テストモード（後方互換性）
                test_translate_menu_item.apply_async(
                    args=[session_id, item_id, item_text],
                    queue='translate_queue'
                )
                test_generate_menu_description.apply_async(
                    args=[session_id, item_id, item_text],
                    queue='description_queue'
                )
            else:
                # 実API統合モード（デフォルト）
                real_translate_menu_item.apply_async(
                    args=[session_id, item_id, item_text, "Other"],
                    queue='real_translate_queue'
                )
                real_generate_menu_description.apply_async(
                    args=[session_id, item_id, item_text, "", "Other"],
                    queue='real_description_queue'
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
        status = get_real_status(session_id, item_id)
        
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
        api_mode = "real_api_integration"  # デフォルト
        
        for item_id in range(total_items):
            try:
                status = get_real_status(session_id, item_id)
                
                if "error" not in status:
                    # 各サービスの完了状況
                    translation_data = status.get("translation", {})
                    description_data = status.get("description", {})
                    image_data = status.get("image", {})
                    
                    t_completed = translation_data.get("completed", False)
                    d_completed = description_data.get("completed", False)
                    i_completed = image_data.get("completed", False)
                    
                    # 全て完了している場合のみカウント
                    if t_completed and d_completed and i_completed:
                        completed_count += 1
                    
                    # アイテム状況データ構築
                    item_status = {
                        "item_id": item_id,
                        "translation_completed": t_completed,
                        "description_completed": d_completed,
                        "image_completed": i_completed,
                        "overall_completed": t_completed and d_completed and i_completed
                    }
                    
                    # 実際のデータを追加（利用可能な場合）
                    if t_completed and translation_data.get("data"):
                        t_data = translation_data["data"]
                        item_status.update({
                            "japanese_text": t_data.get("japanese_text", ""),
                            "english_text": t_data.get("english_text", ""),
                            "translation_provider": t_data.get("provider", "")
                        })
                    
                    if d_completed and description_data.get("data"):
                        d_data = description_data["data"]
                        item_status.update({
                            "description": d_data.get("description", ""),
                            "description_provider": d_data.get("provider", "")
                        })
                    
                    if i_completed and image_data.get("data"):
                        i_data = image_data["data"]
                        item_status.update({
                            "image_url": i_data.get("image_url", ""),
                            "image_provider": i_data.get("provider", ""),
                            "fallback_used": i_data.get("fallback_used", False)
                        })
                    
                    items_status.append(item_status)
                    
                else:
                    # エラー状況のアイテム
                    items_status.append({
                        "item_id": item_id,
                        "translation_completed": False,
                        "description_completed": False,
                        "image_completed": False,
                        "overall_completed": False,
                        "error": status.get("error", "Unknown error")
                    })
                    
            except Exception as item_error:
                # 個別アイテムエラー
                items_status.append({
                    "item_id": item_id,
                    "translation_completed": False,
                    "description_completed": False,
                    "image_completed": False,
                    "overall_completed": False,
                    "error": f"Status check failed: {str(item_error)}"
                })
        
        # 進行率計算
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


# エクスポート用
__all__ = ["router"] 
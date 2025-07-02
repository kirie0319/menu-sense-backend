"""
🧪 デバッグ・テスト用エンドポイント

このファイルは開発・運用時のテスト、デバッグ、メンテナンス用のAPIエンドポイントを提供します。
- Redis接続テスト
- 単一アイテム処理テスト
- セッションクリーンアップ
"""

import time
import uuid
from typing import Dict, Any
from fastapi import APIRouter, HTTPException

from .shared_state import cleanup_session_state
from app.tasks.menu_item_parallel_tasks import (
    test_redis_connection,
    real_translate_menu_item,
    real_generate_menu_description,
    test_translate_menu_item,
    test_generate_menu_description
)

# FastAPIルーター作成
router = APIRouter()


@router.get("/test/redis")
async def test_redis():
    """Redis接続テスト用エンドポイント（実際のAPI統合版）"""
    try:
        result = test_redis_connection()
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
            if use_real_apis:
                translation_task = real_translate_menu_item.delay(session_id, item_id, item_text, "Other")
                tasks.append(("real_translation", translation_task.id))
            else:
                translation_task = test_translate_menu_item.delay(session_id, item_id, item_text)
                tasks.append(("test_translation", translation_task.id))
        
        if test_description:
            if use_real_apis:
                description_task = real_generate_menu_description.delay(session_id, item_id, item_text, "", "Other")
                tasks.append(("real_description", description_task.id))
            else:
                description_task = test_generate_menu_description.delay(session_id, item_id, item_text)
                tasks.append(("test_description", description_task.id))
        
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
        cleaned = cleanup_session_state(session_id)
        
        return {
            "success": True,
            "session_id": session_id,
            "message": "Real API session cleanup completed (SSE streams and active sessions cleared)",
            "cleaned": cleaned,
            "timestamp": time.time(),
            "cleanup_mode": "real_api_session"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Real API cleanup failed: {str(e)}")


@router.get("/test/system-info")
async def get_system_test_info():
    """システムテスト情報を取得"""
    try:
        # Redis接続状況
        redis_status = test_redis_connection()
        
        return {
            "success": True,
            "system_info": {
                "redis_connection": redis_status,
                "available_test_endpoints": [
                    "/test/redis",
                    "/test/single-item", 
                    "/cleanup/{session_id}",
                    "/test/system-info"
                ],
                "supported_apis": [
                    "Google Translate API",
                    "OpenAI GPT-4.1-mini", 
                    "Google Imagen 3"
                ],
                "test_modes": ["real_apis", "test_mode"],
                "celery_queues": [
                    "real_translate_queue",
                    "real_description_queue", 
                    "real_image_queue",
                    "translate_queue",
                    "description_queue"
                ]
            },
            "timestamp": time.time(),
            "version": "2.1.0-real-api-integration"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system test info: {str(e)}")


@router.post("/test/bulk-cleanup")
async def bulk_cleanup_sessions(session_ids: list[str]):
    """複数セッションの一括クリーンアップ"""
    try:
        cleanup_results = {}
        total_cleaned = 0
        
        for session_id in session_ids:
            try:
                cleaned = cleanup_session_state(session_id)
                cleanup_results[session_id] = {
                    "success": True,
                    "cleaned": cleaned
                }
                if cleaned:
                    total_cleaned += 1
            except Exception as session_error:
                cleanup_results[session_id] = {
                    "success": False,
                    "error": str(session_error)
                }
        
        return {
            "success": True,
            "total_sessions": len(session_ids),
            "total_cleaned": total_cleaned,
            "cleanup_results": cleanup_results,
            "message": f"Bulk cleanup completed. {total_cleaned}/{len(session_ids)} sessions cleaned.",
            "timestamp": time.time()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bulk cleanup failed: {str(e)}")


# エクスポート用
__all__ = ["router"] 
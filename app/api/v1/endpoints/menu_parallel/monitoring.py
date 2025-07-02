"""
📊 統計・監視機能

このファイルはシステムの監視、統計情報の取得、健康状態チェック機能を提供します。
- システム統計情報
- API健康状態チェック
- SSE統計情報
"""

import time
from typing import Dict, Any
from fastapi import APIRouter, HTTPException

from .shared_state import get_sse_statistics, get_active_sessions
from app.tasks.menu_item_parallel_tasks import test_redis_connection

# FastAPIルーター作成
router = APIRouter()


@router.get("/stats/system")
async def get_system_stats():
    """システム統計情報を取得（実際のAPI統合版）"""
    try:
        # Redis統計
        redis_status = test_redis_connection()
        
        # API利用可能性チェック
        try:
            from app.services.translation.google_translate import GoogleTranslateService
            from app.services.description.openai import OpenAIDescriptionService
            from app.services.image.imagen3 import Imagen3Service
            
            google_translate = GoogleTranslateService()
            openai_description = OpenAIDescriptionService()
            imagen3_service = Imagen3Service()
            
            api_services = {
                "google_translate": {
                    "available": google_translate.is_available(),
                    "service": "Google Translate API",
                    "queue": "real_translate_queue"
                },
                "openai_description": {
                    "available": openai_description.is_available(),
                    "service": "OpenAI GPT-4.1-mini",
                    "queue": "real_description_queue"
                },
                "imagen3_image": {
                    "available": imagen3_service.is_available(),
                    "service": "Google Imagen 3",
                    "queue": "real_image_queue"
                }
            }
        except ImportError as import_error:
            api_services = {
                "import_error": str(import_error),
                "note": "Some API services could not be imported"
            }
        
        # Celery統計（基本情報のみ）
        celery_status = {
            "available": True,  # 後で celery inspect を追加
            "queues": ["real_translate_queue", "real_description_queue", "real_image_queue", "default"],
            "real_api_integration": True
        }
        
        # SSE統計
        sse_stats = get_sse_statistics()
        
        return {
            "success": True,
            "redis": redis_status,
            "celery": celery_status,
            "sse_streaming": sse_stats,
            "api_services": api_services,
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
        # 各APIサービスの健康状態
        health_status = {}
        overall_health = True
        
        # Google Translate
        try:
            from app.services.translation.google_translate import GoogleTranslateService
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
            from app.services.description.openai import OpenAIDescriptionService
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
            from app.services.image.imagen3 import Imagen3Service
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
        
        # Redis健康状態
        try:
            redis_test = test_redis_connection()
            health_status["redis"] = {
                "status": "healthy" if redis_test["success"] else "unavailable",
                "service": "Redis State Management",
                "critical": True,
                "details": redis_test
            }
            if not redis_test["success"]:
                overall_health = False
        except Exception as e:
            health_status["redis"] = {
                "status": "error",
                "error": str(e),
                "critical": True
            }
            overall_health = False
        
        # SSE健康状態
        sse_stats = get_sse_statistics()
        health_status["sse_streaming"] = {
            "status": "healthy",
            "service": "SSE Real-time Streaming",
            "critical": False,
            "active_streams": sse_stats["active_sessions"],
            "events_queued": sse_stats["total_events_queued"]
        }
        
        return {
            "overall_health": "healthy" if overall_health else "degraded",
            "api_services": health_status,
            "integration_mode": "real_api_integration_with_sse",
            "timestamp": time.time(),
            "recommendations": [
                "All critical APIs (Google Translate + OpenAI + Redis) should be healthy",
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
        # 基本SSE統計
        sse_stats = get_sse_statistics()
        active_sessions = get_active_sessions()
        
        # 詳細セッション情報
        active_sessions_info = []
        
        for session_id, session_data in active_sessions.items():
            uptime = time.time() - session_data["start_time"]
            
            session_info = {
                "session_id": session_id,
                "uptime": uptime,
                "total_items": session_data.get("total_items", 0),
                "connection_active": session_data.get("connection_active", False),
                "events_queued": len(sse_stats.get("progress_streams", {}).get(session_id, []))
            }
            active_sessions_info.append(session_info)
        
        return {
            "success": True,
            "sse_statistics": sse_stats,
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


@router.get("/stats/performance")
async def get_performance_stats():
    """パフォーマンス統計情報"""
    try:
        # SSE統計
        sse_stats = get_sse_statistics()
        active_sessions = get_active_sessions()
        
        # メモリ使用量計算
        memory_stats = sse_stats.get("memory_usage", {})
        
        # 現在のロード計算
        current_load = {
            "active_sessions": sse_stats["active_sessions"],
            "total_events_queued": sse_stats["total_events_queued"],
            "memory_usage_kb": memory_stats.get("progress_streams_kb", 0) + memory_stats.get("active_sessions_kb", 0)
        }
        
        # セッション持続時間統計
        session_durations = []
        current_time = time.time()
        
        for session_data in active_sessions.values():
            duration = current_time - session_data["start_time"]
            session_durations.append(duration)
        
        # 統計計算
        if session_durations:
            avg_session_duration = sum(session_durations) / len(session_durations)
            max_session_duration = max(session_durations)
            min_session_duration = min(session_durations)
        else:
            avg_session_duration = max_session_duration = min_session_duration = 0
        
        return {
            "success": True,
            "current_load": current_load,
            "session_statistics": {
                "total_active": len(active_sessions),
                "average_duration": avg_session_duration,
                "max_duration": max_session_duration,
                "min_duration": min_session_duration
            },
            "memory_statistics": memory_stats,
            "performance_indicators": {
                "low_memory_usage": memory_stats.get("progress_streams_kb", 0) < 1024,  # < 1MB
                "reasonable_session_count": len(active_sessions) < 50,
                "manageable_queue_size": sse_stats["total_events_queued"] < 1000
            },
            "timestamp": time.time()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get performance stats: {str(e)}")


# エクスポート用
__all__ = ["router"] 
#!/usr/bin/env python3
"""
責任分離された翻訳エンドポイント

責任分担:
- FastAPI層: HTTP/SSE通信、セッション管理、エラーハンドリング
- Service層: ビジネスロジック（通信なし）
- Celery層: 純粋な処理
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from typing import Dict, Optional
import logging
import time

from app.services.translation.properly_separated import (
    properly_separated_service, 
    TaskProgressEvent, 
    EventType,
    translate_menu_properly_separated
)

logger = logging.getLogger(__name__)

router = APIRouter()

class CommunicationLayer:
    """
    通信責任を担当するクラス
    
    責任:
    - SSE送信
    - セッション管理
    - クライアント通信
    """
    
    def __init__(self):
        self.session_progress = {}
    
    async def send_progress_event(self, session_id: str, event: TaskProgressEvent):
        """
        イベントをSSE形式でクライアントに送信
        
        Args:
            session_id: セッションID
            event: サービス層からのイベント
        """
        try:
            from app.services.realtime import send_progress
            
            if event.event_type == EventType.PROCESSING_STARTED:
                await send_progress(
                    session_id, 3, "active",
                    f"🔄 責任分離処理開始: {event.total_items}アイテムを処理します",
                    {
                        "processing_mode": "properly_separated",
                        "total_items": event.total_items,
                        "responsibility_separation": True,
                        "max_concurrent": event.metadata.get("max_concurrent", 4),
                        "total_batches": event.metadata.get("total_batches", 0),
                        "message": "適切な責任分離でリアルタイム処理を開始"
                    }
                )
            
            elif event.event_type == EventType.ITEM_COMPLETED:
                # アイテム完了の即座配信
                progress_percent = int((event.completed_count / event.total_items) * 100)
                
                await send_progress(
                    session_id, 3, "active",
                    f"✅ {event.item_data['japanese_name']} → {event.item_data['english_name']}",
                    {
                        "type": "item_completed",
                        "item_completed": {
                            "japanese_name": event.item_data['japanese_name'],
                            "english_name": event.item_data['english_name'],
                            "price": event.item_data['price'],
                            "category": event.item_data['category'],
                            "original_category": event.item_data['original_category']
                        },
                        "progress": {
                            "completed_count": event.completed_count,
                            "total_items": event.total_items,
                            "progress_percent": progress_percent
                        },
                        "processing_mode": "properly_separated",
                        "responsibility_separation": True,
                        "realtime_delivery": True,
                        "timestamp": event.timestamp,
                        "batch_info": {
                            "batch_index": event.metadata.get("batch_index", 0),
                            "batch_total": event.metadata.get("batch_total", 0)
                        }
                    }
                )
            
            elif event.event_type == EventType.BATCH_COMPLETED:
                batch_index = event.metadata.get("batch_index", 0)
                total_batches = event.metadata.get("total_batches", 0)
                batch_time = event.metadata.get("batch_time", 0)
                
                await send_progress(
                    session_id, 3, "active",
                    f"📦 バッチ {batch_index}/{total_batches} 完了 ({batch_time:.2f}s)",
                    {
                        "type": "batch_completed",
                        "batch_progress": {
                            "batch_index": batch_index,
                            "total_batches": total_batches,
                            "batch_time": batch_time,
                            "completed_count": event.completed_count,
                            "total_items": event.total_items
                        },
                        "processing_mode": "properly_separated",
                        "responsibility_separation": True
                    }
                )
            
            elif event.event_type == EventType.PROCESSING_COMPLETED:
                success_rate = event.metadata.get("success_rate", 0)
                processing_time = event.metadata.get("processing_time", 0)
                items_per_second = event.metadata.get("items_per_second", 0)
                translated_categories = event.metadata.get("translated_categories", {})
                
                await send_progress(
                    session_id, 3, "completed",
                    f"✅ 責任分離処理完了！{event.completed_count}/{event.total_items}アイテム処理済み",
                    {
                        "translatedCategories": translated_categories,
                        "total_translated_items": event.completed_count,
                        "total_original_items": event.total_items,
                        "success_rate": f"{success_rate:.1%}",
                        "total_categories": len(translated_categories),
                        "translation_method": "properly_separated_processing",
                        "show_translated_menu": True,
                        "completion_status": "success",
                        "processing_mode": "properly_separated",
                        "responsibility_separation": True,
                        "performance_metrics": {
                            "processing_time": processing_time,
                            "items_per_second": round(items_per_second, 2),
                            "clean_architecture": True
                        }
                    }
                )
            
            elif event.event_type == EventType.ERROR:
                await send_progress(
                    session_id, 3, "error",
                    f"❌ エラー: {event.error_message}",
                    {
                        "error_type": "processing_error",
                        "error_message": event.error_message,
                        "processing_mode": "properly_separated",
                        "responsibility_separation": True,
                        "error_metadata": event.metadata
                    }
                )
            
            elif event.event_type == EventType.PROCESSING_FAILED:
                await send_progress(
                    session_id, 3, "error",
                    f"❌ 処理失敗: {event.error_message}",
                    {
                        "error_type": "processing_failed",
                        "error_message": event.error_message,
                        "processing_mode": "properly_separated",
                        "responsibility_separation": True,
                        "failure_metadata": event.metadata
                    }
                )
                
        except Exception as e:
            logger.error(f"Failed to send progress event: {str(e)}")

# 通信層インスタンス
communication_layer = CommunicationLayer()

@router.post("/translate-separated")
async def translate_menu_with_proper_separation(
    request: Request,
    categorized_data: Dict,
    session_id: Optional[str] = None
):
    """
    適切な責任分離での翻訳エンドポイント
    
    責任分担:
    - この関数: HTTP処理、SSE通信、エラーレスポンス
    - Service層: ビジネスロジック実行
    - Celery層: 純粋な翻訳処理
    """
    start_time = time.time()
    
    try:
        # セッションIDの生成（未指定の場合）
        if not session_id:
            import uuid
            session_id = str(uuid.uuid4())
        
        logger.info(f"🔄 Starting properly separated translation for session: {session_id}")
        
        # 🔄 責任分離: 進行状況コールバック定義（通信層の責任）
        async def progress_callback(event: TaskProgressEvent):
            """進行状況をSSEで送信（通信層の責任）"""
            await communication_layer.send_progress_event(session_id, event)
        
        # 🔄 サービス層呼び出し（ビジネスロジック委譲）
        result = await properly_separated_service.translate_menu_separated(
            categorized_data, 
            progress_callback  # 通信責任を渡す
        )
        
        # レスポンス処理（通信層の責任）
        processing_time = time.time() - start_time
        
        if result.success:
            logger.info(f"✅ Properly separated translation completed in {processing_time:.2f}s")
            
            response_data = {
                "success": True,
                "session_id": session_id,
                "translated_categories": result.translated_categories,
                "translation_method": result.translation_method,
                "processing_mode": "properly_separated",
                "responsibility_separation": True,
                "metadata": {
                    **result.metadata,
                    "communication_layer_processing_time": processing_time,
                    "clean_architecture": True
                }
            }
            
            return JSONResponse(content=response_data)
        else:
            logger.error(f"❌ Properly separated translation failed: {result.error}")
            
            raise HTTPException(
                status_code=500,
                detail={
                    "error": result.error,
                    "processing_mode": "properly_separated",
                    "responsibility_separation": True,
                    "communication_layer_processing_time": processing_time
                }
            )
        
    except HTTPException:
        raise
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"❌ Communication layer error: {str(e)}")
        
        # 通信層エラーの通知
        try:
            if session_id:
                from app.services.realtime import send_progress
                await send_progress(
                    session_id, 3, "error",
                    f"❌ 通信層エラー: {str(e)}",
                    {
                        "error_type": "communication_layer_error",
                        "error_message": str(e),
                        "processing_mode": "properly_separated",
                        "responsibility_separation": True
                    }
                )
        except:
            pass
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": f"Communication layer error: {str(e)}",
                "error_type": "communication_layer_error",
                "processing_mode": "properly_separated",
                "responsibility_separation": True,
                "communication_layer_processing_time": processing_time
            }
        )

@router.get("/separated-status")
async def get_separation_status():
    """責任分離ステータスの確認エンドポイント"""
    
    try:
        service_available = properly_separated_service.is_available()
        
        return JSONResponse(content={
            "responsibility_separation": True,
            "service_layer": {
                "available": service_available,
                "service_name": properly_separated_service.service_name,
                "max_concurrent_tasks": properly_separated_service.max_concurrent_tasks,
                "communication_dependency": False
            },
            "communication_layer": {
                "available": True,
                "responsibilities": [
                    "HTTP/SSE通信",
                    "セッション管理",
                    "エラーハンドリング",
                    "クライアント通知"
                ]
            },
            "celery_layer": {
                "responsibilities": [
                    "純粋な翻訳処理",
                    "APIコール実行",
                    "結果データ生成"
                ]
            },
            "architecture_features": [
                "proper_responsibility_separation",
                "event_driven_architecture",
                "testable_design",
                "scalable_processing",
                "clean_communication_boundaries"
            ]
        })
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Status check failed: {str(e)}"
        )

# エクスポート用のコンビニエンス関数
async def process_translation_with_separation(
    categorized_data: Dict,
    session_id: str,
    progress_callback: Optional[callable] = None
):
    """
    責任分離での翻訳処理便利関数
    
    Args:
        categorized_data: カテゴリ分類データ
        session_id: セッションID
        progress_callback: カスタム進行状況コールバック
    """
    if progress_callback is None:
        # デフォルトの通信層コールバック
        async def default_callback(event: TaskProgressEvent):
            await communication_layer.send_progress_event(session_id, event)
        progress_callback = default_callback
    
    return await properly_separated_service.translate_menu_separated(
        categorized_data,
        progress_callback
    ) 
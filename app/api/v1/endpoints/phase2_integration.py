#!/usr/bin/env python3
"""
Phase 2統合処理APIエンドポイント

3つずつ翻訳→詳細説明→画像生成統合処理のAPIエンドポイント
- Phase 1責任分離アーキテクチャ準拠
- SSEリアルタイム配信
- イベント駆動型通信
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, List, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services.realtime.session_manager import get_session_manager, SessionManager
from app.services.translation.phase2_integration import (
    Phase2IntegrationService,
    IntegrationEventType,
    IntegrationProgressEvent
)

logger = logging.getLogger(__name__)

# APIルーター
router = APIRouter()

class Phase2TranslationRequest(BaseModel):
    """Phase 2統合処理翻訳リクエスト"""
    menu_items: List[Dict[str, Any]] = Field(..., description="翻訳するメニューアイテムリスト")
    session_id: Optional[str] = Field(None, description="セッションID（省略時は自動生成）")
    batch_size: Optional[int] = Field(3, description="バッチサイズ（デフォルト3）")
    timeout_per_item: Optional[int] = Field(20, description="アイテムあたりのタイムアウト（秒）")

class Phase2CommunicationLayer:
    """Phase 2通信レイヤー - SSE配信担当"""
    
    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager
        
    async def send_integration_event(self, session_id: str, event: IntegrationProgressEvent):
        """統合処理イベントをSSE配信"""
        try:
            # イベントデータの構築
            event_data = {
                'event_type': event.event_type.value,
                'timestamp': event.timestamp,
                'batch_id': event.batch_id,
                'total_items': event.total_items,
                'session_id': event.session_id,
                'current_item_index': event.current_item_index,
                'progress_percentage': event.progress_percentage,
                'processing_step': event.processing_step,
                'error_message': event.error_message
            }
            
            # アイテムデータの追加
            if event.item_data:
                event_data['item_data'] = event.item_data
                
            # 完了アイテムリストの追加
            if event.completed_items:
                event_data['completed_items'] = event.completed_items
                
            # 処理時間情報の追加
            if event.processing_times:
                event_data['processing_times'] = event.processing_times
            
            # SSE形式で送信
            sse_data = {
                'type': 'phase2_integration_progress',
                'data': event_data
            }
            
            await self.session_manager.send_to_session(session_id, sse_data)
            logger.debug(f"Sent integration event {event.event_type.value} to session {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to send integration event: {str(e)}")

@router.post("/translate-phase2-integration")
async def translate_menu_phase2_integration(
    request: Phase2TranslationRequest,
    session_manager: SessionManager = Depends(get_session_manager)
):
    """
    Phase 2統合処理翻訳（翻訳→詳細説明→画像生成）
    
    3つずつのバッチで統合処理を行い、リアルタイムでSSE配信
    """
    
    # セッションID生成
    session_id = request.session_id or str(uuid.uuid4())
    
    try:
        logger.info(f"Starting Phase 2 integration translation: {len(request.menu_items)} items (session: {session_id})")
        
        # 通信レイヤー初期化
        communication = Phase2CommunicationLayer(session_manager)
        
        # サービス初期化
        service = Phase2IntegrationService()
        
        # バッチサイズとタイムアウトの設定
        if request.batch_size:
            service.batch_size = request.batch_size
        if request.timeout_per_item:
            service.timeout_per_item = request.timeout_per_item
        
        # プログレスコールバック（通信レイヤーへの転送）
        async def progress_callback(event: IntegrationProgressEvent):
            await communication.send_integration_event(session_id, event)
        
        # 統合処理実行
        result = await service.translate_menu_integrated(
            menu_items=request.menu_items,
            progress_callback=progress_callback,
            session_id=session_id
        )
        
        # 最終結果にセッションIDを追加
        result['session_id'] = session_id
        
        logger.info(f"Phase 2 integration completed: {result.get('completed_count', 0)}/{result.get('total_items', 0)} items in {result.get('total_processing_time', 0):.2f}s")
        
        return result
        
    except Exception as e:
        error_msg = f"Phase 2 integration translation failed: {str(e)}"
        logger.error(error_msg)
        
        # エラー時のSSE送信
        try:
            error_event = IntegrationProgressEvent(
                event_type=IntegrationEventType.INTEGRATION_ERROR,
                timestamp=time.time(),
                batch_id=f"error_{int(time.time())}",
                total_items=len(request.menu_items),
                session_id=session_id,
                error_message=str(e)
            )
            
            communication = Phase2CommunicationLayer(session_manager)
            await communication.send_integration_event(session_id, error_event)
            
        except Exception as send_error:
            logger.error(f"Failed to send error event: {str(send_error)}")
        
        raise HTTPException(status_code=500, detail=error_msg)

@router.get("/stream-phase2-integration/{session_id}")
async def stream_phase2_integration_progress(
    session_id: str,
    request: Request,
    session_manager: SessionManager = Depends(get_session_manager)
):
    """
    Phase 2統合処理進行状況SSEストリーミング
    
    クライアントがこのエンドポイントに接続して統合処理の進行状況をリアルタイム受信
    """
    
    logger.info(f"Starting Phase 2 integration SSE stream for session: {session_id}")
    
    async def event_generator():
        """SSEイベント生成"""
        try:
            # セッション接続
            session_manager.add_session(session_id)
            
            # 接続確認メッセージ送信
            connection_event = {
                'type': 'phase2_connection_established',
                'data': {
                    'session_id': session_id,
                    'timestamp': time.time(),
                    'message': 'Phase 2 integration stream connected'
                }
            }
            
            yield f"data: {json.dumps(connection_event)}\n\n"
            
            # セッションからのメッセージを待機・配信
            while True:
                # クライアント切断チェック
                if await request.is_disconnected():
                    logger.info(f"Client disconnected from Phase 2 integration stream: {session_id}")
                    break
                
                # セッションメッセージの取得
                message = await session_manager.get_session_message(session_id, timeout=1.0)
                
                if message:
                    # SSE形式で送信
                    yield f"data: {json.dumps(message)}\n\n"
                else:
                    # ハートビート送信
                    heartbeat = {
                        'type': 'heartbeat',
                        'data': {'timestamp': time.time()}
                    }
                    yield f"data: {json.dumps(heartbeat)}\n\n"
                
                # 短時間スリープ
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Phase 2 integration SSE stream error: {str(e)}")
            
            # エラーイベント送信
            error_event = {
                'type': 'stream_error',
                'data': {
                    'error': str(e),
                    'timestamp': time.time()
                }
            }
            yield f"data: {json.dumps(error_event)}\n\n"
            
        finally:
            # セッションクリーンアップ
            session_manager.remove_session(session_id)
            logger.info(f"Phase 2 integration session cleaned up: {session_id}")
    
    # SSEレスポンス返却
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )

@router.get("/status")
async def get_phase2_status():
    """Phase 2統合処理ステータス確認"""
    try:
        # Celery接続確認
        from app.tasks.celery_app import celery_app
        
        # 統合処理タスクの存在確認
        from app.tasks.three_item_integration import process_three_items_complete
        
        # サービス初期化テスト
        service = Phase2IntegrationService()
        
        # 必要なサービス可用性チェック
        status_checks = {}
        
        try:
            from app.services.translation.google_translate import GoogleTranslateService
            google_service = GoogleTranslateService()
            status_checks['google_translate'] = google_service.is_available()
        except Exception as e:
            status_checks['google_translate'] = False
            
        try:
            from app.services.description.openai import OpenAIDescriptionService
            description_service = OpenAIDescriptionService()
            status_checks['description_service'] = description_service.is_available()
        except Exception as e:
            status_checks['description_service'] = False
            
        try:
            from app.services.image.imagen3 import Imagen3Service
            image_service = Imagen3Service()
            status_checks['image_service'] = image_service.is_available()
        except Exception as e:
            status_checks['image_service'] = False
        
        # Celeryワーカー状況
        inspect = celery_app.control.inspect()
        active_workers = inspect.active() or {}
        
        return {
            'status': 'operational',
            'phase': 'Phase 2 Integration',
            'timestamp': time.time(),
            'celery_workers': len(active_workers),
            'worker_details': active_workers,
            'service_availability': status_checks,
            'integration_features': [
                'three_item_batches',
                'translation_integration',
                'description_integration', 
                'image_generation_integration',
                'realtime_sse_delivery',
                'responsibility_separation'
            ],
            'batch_configuration': {
                'default_batch_size': service.batch_size,
                'timeout_per_item': service.timeout_per_item,
                'total_timeout': service.total_timeout
            }
        }
        
    except Exception as e:
        logger.error(f"Phase 2 status check failed: {str(e)}")
        return {
            'status': 'error',
            'error': str(e),
            'timestamp': time.time()
        }

# エクスポート
__all__ = ["router"] 
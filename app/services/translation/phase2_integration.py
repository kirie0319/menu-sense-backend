#!/usr/bin/env python3
"""
Phase 2: 統合処理 with 責任分離アーキテクチャ

目標:
- 3つずつ翻訳→詳細説明→画像生成まで統合処理
- Phase 1の責任分離アーキテクチャを活用
- イベント駆動型リアルタイム配信
"""

import time
import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass, asdict

from .base import BaseTranslationService

logger = logging.getLogger(__name__)

class IntegrationEventType(Enum):
    """統合処理イベントタイプ"""
    INTEGRATION_STARTED = "integration_started"
    BATCH_STARTED = "batch_started"
    ITEM_TRANSLATION_STARTED = "item_translation_started"
    ITEM_TRANSLATION_COMPLETED = "item_translation_completed"
    ITEM_DESCRIPTION_STARTED = "item_description_started"
    ITEM_DESCRIPTION_COMPLETED = "item_description_completed"
    ITEM_IMAGE_STARTED = "item_image_started"
    ITEM_IMAGE_COMPLETED = "item_image_completed"
    ITEM_FULLY_COMPLETED = "item_fully_completed"
    BATCH_COMPLETED = "batch_completed"
    INTEGRATION_COMPLETED = "integration_completed"
    INTEGRATION_ERROR = "integration_error"

@dataclass
class IntegrationProgressEvent:
    """統合処理進行イベント"""
    event_type: IntegrationEventType
    timestamp: float
    batch_id: str
    total_items: int
    session_id: Optional[str] = None
    current_item_index: Optional[int] = None
    item_data: Optional[Dict] = None
    processing_step: Optional[str] = None
    progress_percentage: Optional[float] = None
    error_message: Optional[str] = None
    completed_items: Optional[List[Dict]] = None
    processing_times: Optional[Dict] = None

class Phase2IntegrationService(BaseTranslationService):
    """Phase 2統合処理サービス - 責任分離アーキテクチャ準拠"""

    def __init__(self):
        """初期化"""
        super().__init__()
        self.batch_size = 3  # 3つずつ処理
        self.timeout_per_item = 20  # アイテムあたり20秒タイムアウト
        self.total_timeout = 120   # 全体120秒タイムアウト
    
    async def _safe_callback(self, callback: Optional[Callable], event: IntegrationProgressEvent):
        """安全なコールバック実行（同期・非同期両対応）"""
        if not callback:
            return
        
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(event)
            else:
                callback(event)
        except Exception as e:
            logger.warning(f"Callback execution failed: {str(e)}")

    async def translate_menu_integrated(
        self,
        menu_items: List[Dict],
        progress_callback: Optional[Callable[[IntegrationProgressEvent], None]] = None,
        session_id: Optional[str] = None
    ) -> Dict:
        """
        統合処理メニュー翻訳（翻訳→詳細説明→画像生成）
        
        Args:
            menu_items: 処理するメニューアイテムリスト
            progress_callback: 進行状況コールバック
            session_id: セッションID
            
        Returns:
            統合処理結果
        """
        start_time = time.time()
        batch_id = f"phase2_integration_{int(start_time)}"
        
        try:
            logger.info(f"Starting Phase 2 integration processing: {len(menu_items)} items (ID: {batch_id})")
            
            # 統合処理開始イベント
            if progress_callback:
                await self._safe_callback(progress_callback, IntegrationProgressEvent(
                    event_type=IntegrationEventType.INTEGRATION_STARTED,
                    timestamp=time.time(),
                    batch_id=batch_id,
                    total_items=len(menu_items),
                    session_id=session_id,
                    progress_percentage=0
                ))

            # データ抽出・検証
            extracted_items = self._extract_and_validate_items(menu_items)
            
            if not extracted_items:
                error_msg = "No valid items to process"
                logger.warning(error_msg)
                                 
                if progress_callback:
                    await self._safe_callback(progress_callback, IntegrationProgressEvent(
                        event_type=IntegrationEventType.INTEGRATION_ERROR,
                        timestamp=time.time(),
                        batch_id=batch_id,
                        total_items=0,
                        session_id=session_id,
                        error_message=error_msg
                    ))
                
                return {
                    'success': False,
                    'error': error_msg,
                    'batch_id': batch_id,
                    'processing_method': 'phase2_integration'
                }

            # 3つずつバッチ処理
            all_completed_items = []
            batches = [extracted_items[i:i+self.batch_size] for i in range(0, len(extracted_items), self.batch_size)]
            
            for batch_index, batch in enumerate(batches):
                batch_start_time = time.time()
                batch_batch_id = f"{batch_id}_batch_{batch_index}"
                
                # バッチ開始イベント
                if progress_callback:
                    await self._safe_callback(progress_callback, IntegrationProgressEvent(
                        event_type=IntegrationEventType.BATCH_STARTED,
                        timestamp=time.time(),
                        batch_id=batch_batch_id,
                        total_items=len(batch),
                        session_id=session_id,
                        progress_percentage=(batch_index / len(batches)) * 100
                    ))
                
                # バッチ統合処理
                batch_result = await self._process_integration_batch(
                    batch,
                    batch_batch_id,
                    progress_callback,
                    session_id,
                    batch_index * self.batch_size  # 全体での開始インデックス
                )
                
                if batch_result.get('success') and batch_result.get('completed_items'):
                    all_completed_items.extend(batch_result['completed_items'])
                
                # バッチ完了イベント
                batch_processing_time = time.time() - batch_start_time
                if progress_callback:
                    await self._safe_callback(progress_callback, IntegrationProgressEvent(
                        event_type=IntegrationEventType.BATCH_COMPLETED,
                        timestamp=time.time(),
                        batch_id=batch_batch_id,
                        total_items=len(batch),
                        session_id=session_id,
                        completed_items=batch_result.get('completed_items', []),
                        processing_times={'batch_time': batch_processing_time}
                    ))
                
                logger.info(f"Batch {batch_index + 1}/{len(batches)} completed: {len(batch_result.get('completed_items', []))}/{len(batch)} items in {batch_processing_time:.2f}s")

            # 統合処理完了
            total_processing_time = time.time() - start_time
            
            # 統合処理完了イベント
            if progress_callback:
                await self._safe_callback(progress_callback, IntegrationProgressEvent(
                    event_type=IntegrationEventType.INTEGRATION_COMPLETED,
                    timestamp=time.time(),
                    batch_id=batch_id,
                    total_items=len(extracted_items),
                    session_id=session_id,
                    completed_items=all_completed_items,
                    progress_percentage=100,
                    processing_times={
                        'total_time': total_processing_time,
                        'average_per_item': total_processing_time / len(all_completed_items) if all_completed_items else 0,
                        'items_per_second': len(all_completed_items) / total_processing_time if total_processing_time > 0 else 0
                    }
                ))

            result = {
                'success': True,
                'batch_id': batch_id,
                'processing_method': 'phase2_integration',
                'completed_items': all_completed_items,
                'total_items': len(extracted_items),
                'completed_count': len(all_completed_items),
                'failed_count': len(extracted_items) - len(all_completed_items),
                'batches_processed': len(batches),
                'total_processing_time': total_processing_time,
                'integration_features': [
                    'three_item_batches',
                    'translation_integration',
                    'description_integration',
                    'image_generation_integration',
                    'realtime_delivery',
                    'responsibility_separation'
                ],
                'performance_metrics': {
                    'items_per_second': len(all_completed_items) / total_processing_time if total_processing_time > 0 else 0,
                    'average_item_time': total_processing_time / len(all_completed_items) if all_completed_items else 0
                }
            }
            
            logger.info(f"Phase 2 integration completed: {len(all_completed_items)}/{len(extracted_items)} items in {total_processing_time:.2f}s")
            
            return result
            
        except Exception as e:
            total_processing_time = time.time() - start_time
            error_msg = f"Phase 2 integration failed: {str(e)}"
            logger.error(error_msg)
            
            # エラーイベント
            if progress_callback:
                await self._safe_callback(progress_callback, IntegrationProgressEvent(
                    event_type=IntegrationEventType.INTEGRATION_ERROR,
                    timestamp=time.time(),
                    batch_id=batch_id,
                    total_items=len(menu_items),
                    session_id=session_id,
                    error_message=str(e),
                    processing_times={'total_time': total_processing_time}
                ))
            
            return {
                'success': False,
                'batch_id': batch_id,
                'error': str(e),
                'processing_method': 'phase2_integration_failed',
                'total_processing_time': total_processing_time
            }

    async def _process_integration_batch(
        self,
        batch_items: List[Dict],
        batch_id: str,
        progress_callback: Optional[Callable[[IntegrationProgressEvent], None]],
        session_id: Optional[str],
        global_item_index_start: int
    ) -> Dict:
        """統合処理バッチ実行"""
        try:
            from app.tasks.three_item_integration import process_three_items_complete
            
            # Celeryタスク実行（タイムアウト設定）
            task_result = process_three_items_complete.apply_async(
                args=[batch_items],
                expires=self.total_timeout
            )
            
            # タスク状態監視とイベント配信
            completed_items = []
            last_progress = 0
            
            while not task_result.ready():
                try:
                    # タスク状態取得（タイムアウト付き）
                    task_info = task_result.info
                    
                    if isinstance(task_info, dict):
                        # 進行状況に応じたイベント配信
                        current_progress = task_info.get('progress', last_progress)
                        status = task_info.get('status', 'processing')
                        current_item = task_info.get('current_item', '')
                        latest_completed = task_info.get('latest_completed')
                        
                        # 新しいアイテム完了の検出
                        if latest_completed and latest_completed not in [item.get('item_id') for item in completed_items]:
                            completed_items.append(latest_completed)
                            
                            # アイテム完了イベント
                            if progress_callback:
                                await self._safe_callback(progress_callback, IntegrationProgressEvent(
                                    event_type=IntegrationEventType.ITEM_FULLY_COMPLETED,
                                    timestamp=time.time(),
                                    batch_id=batch_id,
                                    total_items=len(batch_items),
                                    session_id=session_id,
                                    current_item_index=global_item_index_start + len(completed_items) - 1,
                                    item_data=latest_completed,
                                    progress_percentage=current_progress
                                ))
                        
                        # ステップ別イベント（翻訳、説明、画像生成）
                        if 'translating' in status and progress_callback:
                            await self._safe_callback(progress_callback, IntegrationProgressEvent(
                                event_type=IntegrationEventType.ITEM_TRANSLATION_STARTED,
                                timestamp=time.time(),
                                batch_id=batch_id,
                                total_items=len(batch_items),
                                session_id=session_id,
                                processing_step='translation',
                                item_data={'name': current_item}
                            ))
                        elif 'describing' in status and progress_callback:
                            await self._safe_callback(progress_callback, IntegrationProgressEvent(
                                event_type=IntegrationEventType.ITEM_DESCRIPTION_STARTED,
                                timestamp=time.time(),
                                batch_id=batch_id,
                                total_items=len(batch_items),
                                session_id=session_id,
                                processing_step='description',
                                item_data={'name': current_item}
                            ))
                        elif 'generating_image' in status and progress_callback:
                            await self._safe_callback(progress_callback, IntegrationProgressEvent(
                                event_type=IntegrationEventType.ITEM_IMAGE_STARTED,
                                timestamp=time.time(),
                                batch_id=batch_id,
                                total_items=len(batch_items),
                                session_id=session_id,
                                processing_step='image_generation',
                                item_data={'name': current_item}
                            ))
                        
                        last_progress = current_progress
                    
                    # 短時間スリープ
                    await asyncio.sleep(0.1)
                    
                except Exception as monitor_error:
                    logger.warning(f"Task monitoring error: {monitor_error}")
                    break
            
            # タスク完了結果取得（タイムアウト付き）
            try:
                result = task_result.get(timeout=self.timeout_per_item * len(batch_items))
                return result
                
            except Exception as get_error:
                logger.error(f"Failed to get task result: {get_error}")
                return {
                    'success': False,
                    'error': f"Task execution failed: {str(get_error)}",
                    'completed_items': completed_items
                }
                
        except Exception as e:
            logger.error(f"Integration batch processing failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'completed_items': []
            }

    def _extract_and_validate_items(self, menu_items: List[Dict]) -> List[Dict]:
        """アイテム抽出・検証（Phase 1と同様）"""
        extracted_items = []
        
        for i, item in enumerate(menu_items):
            try:
                # 日本語名の抽出
                japanese_name = item.get('japanese_name') or item.get('name', '')
                
                if not japanese_name or not japanese_name.strip():
                    logger.warning(f"Skipping item {i}: no japanese_name or name")
                    continue
                
                # 抽出されたアイテム
                extracted_item = {
                    'item_id': item.get('item_id', f'item_{i}'),
                    'japanese_name': japanese_name.strip(),
                    'price': item.get('price', ''),
                    'category': item.get('category', 'Other'),
                    'original_index': i
                }
                
                extracted_items.append(extracted_item)
                
            except Exception as e:
                logger.warning(f"Failed to extract item {i}: {str(e)}")
                continue
        
        logger.info(f"Extracted {len(extracted_items)}/{len(menu_items)} valid items")
        return extracted_items

    # BaseTranslationService抽象メソッドの実装
    async def translate_menu(self, menu_items: List[Dict], **kwargs) -> Dict:
        """統合処理メニュー翻訳（基底クラス互換性）"""
        return await self.translate_menu_integrated(
            menu_items, 
            progress_callback=kwargs.get('progress_callback'),
            session_id=kwargs.get('session_id')
        )
    
    def is_available(self) -> bool:
        """サービス可用性確認"""
        try:
            # 基本的な統合処理に必要なサービスの確認
            from app.tasks.celery_app import celery_app
            
            # Celery接続確認
            inspect = celery_app.control.inspect()
            active_workers = inspect.active()
            
            if not active_workers:
                return False
            
            # 翻訳サービス確認
            try:
                from app.services.translation.google_translate import GoogleTranslateService
                google_service = GoogleTranslateService()
                if google_service.is_available():
                    return True
            except:
                pass
            
            try:
                from app.services.translation.openai import OpenAITranslationService
                openai_service = OpenAITranslationService()
                if openai_service.is_available():
                    return True
            except:
                pass
            
            return False
            
        except Exception:
            return False
    
    def get_service_info(self) -> Dict[str, Any]:
        """サービス情報取得"""
        return {
            "service_name": "Phase2IntegrationService",
            "description": "3つずつ統合処理（翻訳→詳細説明→画像生成）",
            "capabilities": [
                "translation_integration",
                "description_integration", 
                "image_generation_integration",
                "batch_processing",
                "realtime_delivery",
                "responsibility_separation"
            ],
            "supported_languages": {
                "source": ["Japanese"],
                "target": ["English"]
            },
            "batch_size": self.batch_size,
            "timeout_settings": {
                "per_item": self.timeout_per_item,
                "total": self.total_timeout
            },
            "integration_steps": ["translation", "description", "image_generation"]
        }

# エクスポート
__all__ = [
    "Phase2IntegrationService",
    "IntegrationEventType", 
    "IntegrationProgressEvent"
] 
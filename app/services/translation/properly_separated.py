#!/usr/bin/env python3
"""
適切な責任分離を実装したリアルタイム翻訳サービス

FastAPI + Celery の責任分割:
- FastAPI: HTTP/SSE通信、セッション管理、タスクオーケストレーション
- Service Layer: ビジネスロジック、タスク調整（通信なし）
- Celery: 純粋な処理（翻訳処理のみ）
"""

import asyncio
import time
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from app.core.config import settings
from .base import BaseTranslationService, TranslationResult, TranslationProvider

logger = logging.getLogger(__name__)

class EventType(Enum):
    """イベント種類"""
    PROCESSING_STARTED = "processing_started"
    ITEM_COMPLETED = "item_completed"
    BATCH_COMPLETED = "batch_completed"
    PROCESSING_COMPLETED = "processing_completed"
    PROCESSING_FAILED = "processing_failed"
    ERROR = "error"

@dataclass
class TaskProgressEvent:
    """タスク進行状況イベント（通信層への依存なし）"""
    event_type: EventType
    item_data: Optional[Dict] = None
    completed_count: int = 0
    total_items: int = 0
    error_message: Optional[str] = None
    metadata: Optional[Dict] = None
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

class ProperlySeparatedTranslationService(BaseTranslationService):
    """
    適切な責任分離を実装したリアルタイム翻訳サービス
    
    責任:
    - ビジネスロジックの実行
    - タスクの調整とオーケストレーション
    - イベントの発火（通信は行わない）
    
    通信層への直接依存: ❌ なし
    """
    
    def __init__(self):
        super().__init__()
        self.provider = TranslationProvider.GOOGLE_TRANSLATE
        self.service_name = "Properly Separated Translation Service"
        self.max_concurrent_tasks = 4
        self.task_timeout = 15
        self.max_total_timeout = 60
    
    def is_available(self) -> bool:
        """サービスが利用可能かチェック"""
        try:
            from app.tasks.item_level_tasks import translate_single_item
            return True
        except ImportError:
            return False
    
    def create_item_data(self, categorized_data: Dict) -> List[Dict]:
        """カテゴリ分類データをアイテムリストに変換"""
        items = []
        item_counter = 1
        
        for category_name, category_items in categorized_data.items():
            for item in category_items:
                # 改良されたデータ抽出（japanese_nameキーに対応）
                item_name, item_price = self._extract_item_data_improved(item)
                
                if item_name.strip():
                    items.append({
                        "item_id": f"item_{item_counter}",
                        "japanese_name": item_name,
                        "price": item_price,
                        "category": category_name,
                        "original_category": category_name
                    })
                    item_counter += 1
        
        return items
    
    def _extract_item_data_improved(self, item) -> tuple:
        """改良されたメニューアイテムデータ抽出"""
        if isinstance(item, str):
            return item, ""
        elif isinstance(item, dict):
            # japanese_name、name、その他のキーを順に試す
            name = item.get("japanese_name") or item.get("name", "")
            price = item.get("price", "")
            return name, price
        else:
            return "", ""
    
    def translate_category_name(self, japanese_category: str) -> str:
        """カテゴリ名の翻訳（簡易版）"""
        category_mapping = {
            '前菜': 'Appetizers',
            'メイン': 'Main Dishes', 
            'メインディッシュ': 'Main Dishes',
            'スープ': 'Soups',
            'デザート': 'Desserts',
            '飲み物': 'Beverages',
            'サラダ': 'Salads',
            'その他': 'Other'
        }
        return category_mapping.get(japanese_category, japanese_category)
    
    async def process_items_with_events(
        self, 
        items: List[Dict], 
        progress_callback: Optional[Callable[[TaskProgressEvent], None]] = None
    ) -> List[Dict]:
        """
        アイテム処理（イベント駆動、通信層分離）
        
        Args:
            items: 処理するアイテムリスト
            progress_callback: 進行状況コールバック（通信層が設定）
            
        Returns:
            完了したアイテムリスト
        """
        from app.tasks.item_level_tasks import translate_single_item
        
        completed_items = []
        total_items = len(items)
        completed_count = 0
        start_time = time.time()
        
        # アイテムをバッチに分割
        batches = [items[i:i + self.max_concurrent_tasks] for i in range(0, len(items), self.max_concurrent_tasks)]
        
        logger.info(f"🔄 Processing {len(items)} items in {len(batches)} batches with proper separation")
        
        # 開始イベント発火
        if progress_callback:
            await progress_callback(TaskProgressEvent(
                event_type=EventType.PROCESSING_STARTED,
                total_items=total_items,
                metadata={
                    "processing_mode": "properly_separated",
                    "max_concurrent": self.max_concurrent_tasks,
                    "total_batches": len(batches),
                    "batch_strategy": "responsibility_separated"
                }
            ))
        
        for batch_index, batch in enumerate(batches):
            batch_start_time = time.time()
            
            # 全体タイムアウトチェック
            elapsed_total = time.time() - start_time
            if elapsed_total > self.max_total_timeout:
                logger.warning(f"Total timeout exceeded ({elapsed_total:.2f}s), stopping processing")
                break
            
            logger.info(f"Processing batch {batch_index + 1}/{len(batches)} ({len(batch)} items)")
            
            # バッチ内並列処理
            batch_tasks = []
            for item in batch:
                # ✅ 責任分離: session_idを渡さない（通信責任はservice層にない）
                task = translate_single_item.delay(item)
                batch_tasks.append((item, task))
            
            # バッチ完了を待機
            for item_data, task in batch_tasks:
                item_start_time = time.time()
                
                try:
                    # タスク結果取得
                    result = await asyncio.wait_for(
                        asyncio.to_thread(self._get_task_result, task),
                        timeout=self.task_timeout
                    )
                    
                    if result and result.get('success'):
                        completed_count += 1
                        completed_items.append(result)
                        
                        # ✅ 責任分離: イベント発火のみ（SSE送信なし）
                        if progress_callback:
                            event = TaskProgressEvent(
                                event_type=EventType.ITEM_COMPLETED,
                                item_data={
                                    "japanese_name": result['japanese_name'],
                                    "english_name": result['english_name'],
                                    "price": result['price'],
                                    "category": self.translate_category_name(result.get('category', 'その他')),
                                    "original_category": result.get('category', '')
                                },
                                completed_count=completed_count,
                                total_items=total_items,
                                metadata={
                                    "processing_mode": "properly_separated",
                                    "batch_index": batch_index + 1,
                                    "batch_total": len(batches),
                                    "item_processing_time": time.time() - item_start_time
                                }
                            )
                            # 🔄 責任分離: コールバックで通信層に委譲
                            await progress_callback(event)
                        
                        item_time = time.time() - item_start_time
                        logger.info(f"✅ Item {completed_count}/{total_items} completed in {item_time:.2f}s: {result['japanese_name']} → {result['english_name']}")
                    else:
                        logger.warning(f"⚠️ Item failed: {item_data['item_id']}")
                        
                        # エラーイベント発火
                        if progress_callback:
                            await progress_callback(TaskProgressEvent(
                                event_type=EventType.ERROR,
                                error_message=f"Item translation failed: {item_data['item_id']}",
                                metadata={
                                    "failed_item": item_data,
                                    "batch_index": batch_index + 1
                                }
                            ))
                        
                except asyncio.TimeoutError:
                    logger.error(f"❌ Item timeout after {self.task_timeout}s: {item_data['item_id']}")
                    
                    # タイムアウトイベント発火
                    if progress_callback:
                        await progress_callback(TaskProgressEvent(
                            event_type=EventType.ERROR,
                            error_message=f"Item timeout: {item_data['item_id']}",
                            metadata={
                                "timeout_seconds": self.task_timeout,
                                "item_id": item_data['item_id']
                            }
                        ))
                    
                    # タスクキャンセル
                    try:
                        task.revoke(terminate=True)
                    except Exception:
                        pass
                        
                except Exception as e:
                    logger.error(f"❌ Item processing failed: {item_data['item_id']} - {str(e)}")
                    
                    # 例外イベント発火
                    if progress_callback:
                        await progress_callback(TaskProgressEvent(
                            event_type=EventType.ERROR,
                            error_message=f"Processing exception: {str(e)}",
                            metadata={
                                "item_id": item_data['item_id'], 
                                "exception": str(e)
                            }
                        ))
            
            # バッチ完了イベント
            if progress_callback:
                await progress_callback(TaskProgressEvent(
                    event_type=EventType.BATCH_COMPLETED,
                    completed_count=completed_count,
                    total_items=total_items,
                    metadata={
                        "batch_index": batch_index + 1,
                        "total_batches": len(batches),
                        "batch_time": time.time() - batch_start_time,
                        "batch_items": len(batch)
                    }
                ))
            
            # バッチ間の休息
            if batch_index < len(batches) - 1:
                await asyncio.sleep(0.2)
        
        return completed_items
    
    def _get_task_result(self, task):
        """タスク結果取得（純粋なビジネスロジック）"""
        try:
            return task.get(timeout=self.task_timeout, propagate=True)
        except Exception as e:
            logger.error(f"Task result get failed: {str(e)}")
            return None
    
    async def translate_menu(
        self, 
        categorized_data: Dict, 
        session_id: Optional[str] = None
    ) -> TranslationResult:
        """
        基底クラスの抽象メソッド実装（従来のインターフェース用）
        
        Args:
            categorized_data: カテゴリ分類されたメニューデータ
            session_id: セッションID（無視される）
            
        Returns:
            TranslationResult: 翻訳結果
        """
        # デフォルトはコールバックなしで実行
        return await self.translate_menu_separated(categorized_data, None)
    
    async def translate_menu_separated(
        self, 
        categorized_data: Dict, 
        progress_callback: Optional[Callable[[TaskProgressEvent], None]] = None
    ) -> TranslationResult:
        """
        適切な責任分離でメニュー翻訳
        
        Args:
            categorized_data: カテゴリ分類されたメニューデータ
            progress_callback: 進行状況コールバック（通信層が設定）
            
        Returns:
            TranslationResult: 翻訳結果
        """
        start_time = time.time()
        
        logger.info(f"Starting properly separated translation: {len(categorized_data)} categories")
        
        # 入力データの妥当性チェック
        if not self.validate_categorized_data(categorized_data):
            # エラーイベント発火
            if progress_callback:
                await progress_callback(TaskProgressEvent(
                    event_type=EventType.PROCESSING_FAILED,
                    error_message="Invalid categorized data",
                    metadata={"validation_error": True}
                ))
            
            return TranslationResult(
                success=False,
                translation_method="properly_separated",
                error="Invalid categorized data"
            )
        
        try:
            # アイテムリストを作成
            items = self.create_item_data(categorized_data)
            total_items = len(items)
            
            logger.info(f"Created {total_items} items for properly separated processing")
            
            # 🔄 責任分離: 純粋な処理ロジックのみ実行
            completed_items = await self.process_items_with_events(items, progress_callback)
            
            # 結果をカテゴリ別に再構成
            translated_categories = {}
            for item in completed_items:
                english_category = self.translate_category_name(item.get('category', 'その他'))
                
                if english_category not in translated_categories:
                    translated_categories[english_category] = []
                
                translated_categories[english_category].append({
                    "japanese_name": item['japanese_name'],
                    "english_name": item['english_name'],
                    "price": item['price']
                })
            
            # 最終結果
            processing_time = time.time() - start_time
            success = len(completed_items) > 0
            success_rate = len(completed_items) / total_items if total_items > 0 else 0
            
            # 完了イベント発火
            if progress_callback:
                await progress_callback(TaskProgressEvent(
                    event_type=EventType.PROCESSING_COMPLETED,
                    completed_count=len(completed_items),
                    total_items=total_items,
                    metadata={
                        "translated_categories": translated_categories,
                        "success_rate": success_rate,
                        "processing_time": processing_time,
                        "items_per_second": len(completed_items) / processing_time if processing_time > 0 else 0,
                        "responsibility_separation": True
                    }
                ))
            
            return TranslationResult(
                success=success,
                translated_categories=translated_categories,
                translation_method="properly_separated_processing",
                metadata={
                    "total_items": len(completed_items),
                    "total_original_items": total_items,
                    "success_rate": success_rate,
                    "total_categories": len(translated_categories),
                    "processing_mode": "properly_separated",
                    "total_processing_time": processing_time,
                    "items_per_second": len(completed_items) / processing_time if processing_time > 0 else 0,
                    "responsibility_separation": True,
                    "provider": "Properly Separated Translation Service",
                    "features": [
                        "proper_responsibility_separation",
                        "event_driven_architecture", 
                        "no_communication_layer_dependency",
                        "clean_architecture",
                        "testable_design",
                        "scalable_processing"
                    ]
                }
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Properly separated translation failed after {processing_time:.2f}s: {str(e)}")
            
            # エラーイベント発火
            if progress_callback:
                await progress_callback(TaskProgressEvent(
                    event_type=EventType.PROCESSING_FAILED,
                    error_message=str(e),
                    metadata={
                        "processing_time": processing_time,
                        "error_type": "service_layer_error"
                    }
                ))
            
            return TranslationResult(
                success=False,
                translation_method="properly_separated_error",
                error=f"Properly separated translation error: {str(e)}",
                metadata={
                    "error_type": "properly_separated_error",
                    "processing_mode": "properly_separated",
                    "total_processing_time": processing_time,
                    "original_error": str(e),
                    "responsibility_separation": True
                }
            )

# サービスインスタンス化
properly_separated_service = ProperlySeparatedTranslationService()

# 便利な関数
async def translate_menu_properly_separated(
    categorized_data: Dict, 
    progress_callback: Optional[Callable[[TaskProgressEvent], None]] = None
) -> TranslationResult:
    """
    適切な責任分離での翻訳便利関数
    """
    return await properly_separated_service.translate_menu_separated(categorized_data, progress_callback)

# エクスポート
__all__ = [
    "ProperlySeparatedTranslationService",
    "TaskProgressEvent",
    "EventType",
    "properly_separated_service", 
    "translate_menu_properly_separated"
] 
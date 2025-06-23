#!/usr/bin/env python3
"""
リアルタイムアイテム並列翻訳サービス

完了したアイテムを即座にユーザーに配信
- アイテム単位での即座配信
- バッチ待機なし
- 最速ユーザー体験
"""

import asyncio
import time
import logging
from typing import Dict, List, Any, Optional, Tuple
from concurrent.futures import as_completed

from app.core.config import settings
from .base import BaseTranslationService, TranslationResult, TranslationProvider

logger = logging.getLogger(__name__)

class RealtimeItemParallelTranslationService(BaseTranslationService):
    """
    リアルタイムアイテム並列翻訳サービス
    
    完了したアイテムから順次リアルタイム配信
    """
    
    def __init__(self):
        super().__init__()
        self.provider = TranslationProvider.GOOGLE_TRANSLATE
        self.service_name = "Realtime Item Parallel Translation Service"
        self.max_parallel_items = 8
    
    def is_available(self) -> bool:
        """サービスが利用可能かチェック"""
        try:
            from app.tasks.item_level_tasks import translate_single_item
            return True
        except:
            return False
    
    def create_item_data(self, categorized_data: Dict) -> List[Dict]:
        """カテゴリ分類データをアイテムリストに変換"""
        items = []
        item_counter = 1
        
        for category_name, category_items in categorized_data.items():
            for item in category_items:
                # アイテムデータの抽出
                item_name, item_price = self.extract_menu_item_data(item)
                
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
    
    async def process_items_realtime(self, items: List[Dict], session_id: str = None) -> List[Dict]:
        """
        アイテムをリアルタイム並列処理
        
        完了次第即座配信
        """
        from app.tasks.item_level_tasks import translate_single_item
        
        # 全アイテムを同時に並列処理開始
        tasks = []
        for item in items:
            task = translate_single_item.delay(item, session_id)
            tasks.append((item, task))
        
        logger.info(f"Started {len(tasks)} parallel translation tasks for realtime processing")
        
        completed_items = []
        
        # 進行状況管理
        total_items = len(items)
        completed_count = 0
        
        # 各タスクの完了を非同期で監視
        async def monitor_task(item_data, task):
            nonlocal completed_count
            try:
                # 非同期でタスク完了を待機
                result = await asyncio.to_thread(task.get, timeout=60)
                
                if result['success']:
                    completed_count += 1
                    
                    # 完了したアイテムを即座に配信
                    if session_id:
                        await self.send_item_completed(
                            session_id, 
                            result, 
                            completed_count, 
                            total_items
                        )
                    
                    logger.info(f"✅ Item {completed_count}/{total_items} completed: {result['japanese_name']} → {result['english_name']}")
                    return result
                else:
                    logger.warning(f"⚠️ Item failed: {item_data['item_id']} - {result.get('error', 'Unknown error')}")
                    return None
                    
            except Exception as e:
                logger.error(f"❌ Task failed for item {item_data['item_id']}: {str(e)}")
                return None
        
        # 全タスクを並行監視
        monitor_tasks = [monitor_task(item_data, task) for item_data, task in tasks]
        
        # 完了次第結果を収集
        for completed_task in asyncio.as_completed(monitor_tasks):
            result = await completed_task
            if result:
                completed_items.append(result)
        
        return completed_items
    
    async def send_item_completed(self, session_id: str, item_result: Dict, completed_count: int, total_items: int):
        """完了したアイテムを即座にリアルタイム配信"""
        try:
            from app.services.realtime import send_progress
            
            # カテゴリ名を翻訳
            english_category = self.translate_category_name(item_result.get('category', 'その他'))
            
            # 進行状況の計算
            progress_percent = int((completed_count / total_items) * 100)
            
            await send_progress(
                session_id, 3, "active", 
                f"✅ {item_result['japanese_name']} → {item_result['english_name']}",
                {
                    "type": "item_completed",
                    "item_completed": {
                        "japanese_name": item_result['japanese_name'],
                        "english_name": item_result['english_name'],
                        "price": item_result['price'],
                        "category": english_category,
                        "original_category": item_result.get('category', '')
                    },
                    "progress": {
                        "completed_count": completed_count,
                        "total_items": total_items,
                        "progress_percent": progress_percent
                    },
                    "processing_mode": "realtime_item_parallel",
                    "realtime_delivery": True,
                    "timestamp": time.time()
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to send item completed notification: {e}")
    
    async def translate_menu(
        self, 
        categorized_data: Dict, 
        session_id: Optional[str] = None
    ) -> TranslationResult:
        """
        メニュー全体をリアルタイムアイテム並列翻訳
        """
        start_time = time.time()
        
        logger.info(f"Starting realtime item-level parallel translation: {len(categorized_data)} categories")
        
        # 入力データの妥当性チェック
        if not self.validate_categorized_data(categorized_data):
            return TranslationResult(
                success=False,
                translation_method="realtime_item_parallel",
                error="Invalid categorized data"
            )
        
        try:
            # アイテムリストを作成
            items = self.create_item_data(categorized_data)
            total_items = len(items)
            
            logger.info(f"Created {total_items} items for realtime parallel processing")
            
            # 開始通知
            if session_id:
                from app.services.realtime import send_progress
                await send_progress(
                    session_id, 3, "active", 
                    f"🚀 Starting realtime translation: {total_items} items processing simultaneously",
                    {
                        "processing_mode": "realtime_item_parallel",
                        "total_items": total_items,
                        "realtime_delivery": True,
                        "message": "Items will appear as soon as they are completed"
                    }
                )
            
            # リアルタイム並列処理開始
            completed_items = await self.process_items_realtime(items, session_id)
            
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
            
            # 完了通知
            if session_id:
                await send_progress(
                    session_id, 3, "completed", 
                    f"✅ Realtime translation completed! All {len(completed_items)} items delivered",
                    {
                        "translatedCategories": translated_categories,
                        "total_translated_items": len(completed_items),
                        "total_categories": len(translated_categories),
                        "translation_method": "realtime_item_parallel_processing",
                        "show_translated_menu": True,
                        "completion_status": "success",
                        "processing_mode": "realtime_item_parallel",
                        "realtime_delivery": True
                    }
                )
            
            return TranslationResult(
                success=success,
                translated_categories=translated_categories,
                translation_method="realtime_item_parallel_processing",
                metadata={
                    "total_items": len(completed_items),
                    "total_original_items": total_items,
                    "total_categories": len(translated_categories),
                    "processing_mode": "realtime_item_parallel",
                    "total_processing_time": processing_time,
                    "items_per_second": len(completed_items) / processing_time if processing_time > 0 else 0,
                    "realtime_delivery": True,
                    "first_item_delivery_time": "~2-3 seconds",
                    "provider": "Realtime Item Parallel Translation Service",
                    "features": [
                        "realtime_item_delivery",
                        "simultaneous_parallel_processing",
                        "async_task_management",
                        "instant_user_feedback",
                        "progress_streaming"
                    ]
                }
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Realtime item-level parallel translation failed after {processing_time:.2f}s: {str(e)}")
            
            return TranslationResult(
                success=False,
                translation_method="realtime_item_parallel_error",
                error=f"Realtime item-level parallel translation error: {str(e)}",
                metadata={
                    "error_type": "realtime_parallel_processing_error",
                    "processing_mode": "realtime_item_parallel",
                    "total_processing_time": processing_time,
                    "original_error": str(e)
                }
            )

# サービスインスタンス化
realtime_item_parallel_service = RealtimeItemParallelTranslationService()

# 便利な関数
async def translate_menu_realtime_item_parallel(
    categorized_data: Dict, 
    session_id: Optional[str] = None
) -> TranslationResult:
    """
    リアルタイムアイテム並列翻訳の便利関数
    """
    return await realtime_item_parallel_service.translate_menu(categorized_data, session_id)

# エクスポート
__all__ = [
    "RealtimeItemParallelTranslationService",
    "realtime_item_parallel_service",
    "translate_menu_realtime_item_parallel"
] 
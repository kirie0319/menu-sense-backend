#!/usr/bin/env python3
"""
アイテムレベル並列翻訳サービス

正しいCeleryパターンで8個同時翻訳を実現
- FastAPI側でタスク管理
- Celeryワーカーは純粋な処理のみ
"""

import asyncio
import time
import logging
from typing import Dict, List, Any, Optional, Tuple

from app.core.config import settings
from .base import BaseTranslationService, TranslationResult, TranslationProvider

logger = logging.getLogger(__name__)

class ItemLevelParallelTranslationService(BaseTranslationService):
    """
    アイテムレベル並列翻訳サービス
    
    8個のメニューアイテムを同時に翻訳
    FastAPI側でタスク管理、Celeryで並列実行
    """
    
    def __init__(self):
        super().__init__()
        self.provider = TranslationProvider.GOOGLE_TRANSLATE
        self.service_name = "Item Level Parallel Translation Service"
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
                        "category": category_name
                    })
                    item_counter += 1
        
        return items
    
    def create_batches(self, items: List[Dict], batch_size: int = 8) -> List[List[Dict]]:
        """アイテムリストをバッチに分割"""
        batches = []
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batches.append(batch)
        return batches
    
    async def process_item_batch_async(self, batch: List[Dict], session_id: str = None) -> List[Dict]:
        """
        アイテムバッチを非同期で並列処理
        
        Args:
            batch: アイテムバッチ（最大8個）
            session_id: セッションID
            
        Returns:
            List[Dict]: 翻訳済みアイテムリスト
        """
        from app.tasks.item_level_tasks import translate_single_item
        
        # 並列タスクを開始
        tasks = []
        for item in batch:
            task = translate_single_item.delay(item, session_id)
            tasks.append((item["item_id"], task))
        
        logger.info(f"Started {len(tasks)} parallel translation tasks")
        
        # 結果を非同期で収集
        completed_items = []
        
        for item_id, task in tasks:
            try:
                # 非同期でタスク完了を待機
                result = await asyncio.to_thread(task.get, timeout=60)
                
                if result['success']:
                    completed_items.append(result)
                    logger.info(f"✅ Item completed: {result['japanese_name']} → {result['english_name']}")
                else:
                    logger.warning(f"⚠️ Item failed: {item_id} - {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                logger.error(f"❌ Task failed for item {item_id}: {str(e)}")
        
        return completed_items
    
    async def translate_menu(
        self, 
        categorized_data: Dict, 
        session_id: Optional[str] = None
    ) -> TranslationResult:
        """
        メニュー全体をアイテムレベル並列翻訳
        
        Args:
            categorized_data: カテゴリ分類されたメニューデータ
            session_id: セッションID
            
        Returns:
            TranslationResult: 翻訳結果
        """
        start_time = time.time()
        
        logger.info(f"Starting item-level parallel translation: {len(categorized_data)} categories")
        
        # 入力データの妥当性チェック
        if not self.validate_categorized_data(categorized_data):
            return TranslationResult(
                success=False,
                translation_method="item_level_parallel",
                error="Invalid categorized data"
            )
        
        try:
            # アイテムリストを作成
            items = self.create_item_data(categorized_data)
            total_items = len(items)
            
            logger.info(f"Created {total_items} items for parallel processing")
            
            # アイテムをバッチに分割（8個ずつ）
            batches = self.create_batches(items, self.max_parallel_items)
            
            logger.info(f"Created {len(batches)} batches (max {self.max_parallel_items} items each)")
            
            # 進行状況通知
            if session_id:
                from app.services.realtime import send_progress
                await send_progress(
                    session_id, 3, "active", 
                    f"🚀 Starting item-level parallel translation: {total_items} items in {len(batches)} batches",
                    {
                        "processing_mode": "item_level_parallel",
                        "total_items": total_items,
                        "total_batches": len(batches),
                        "max_parallel_items": self.max_parallel_items
                    }
                )
            
            # バッチを順次処理（各バッチ内は並列）
            all_completed_items = []
            
            for batch_index, batch in enumerate(batches):
                logger.info(f"Processing batch {batch_index + 1}/{len(batches)} ({len(batch)} items)")
                
                # 進行状況更新
                if session_id:
                    await send_progress(
                        session_id, 3, "active", 
                        f"🔄 Processing batch {batch_index + 1}/{len(batches)}...",
                        {
                            "processing_mode": "item_level_parallel",
                            "current_batch": batch_index + 1,
                            "total_batches": len(batches),
                            "completed_items": len(all_completed_items)
                        }
                    )
                
                # バッチ内並列処理
                batch_results = await self.process_item_batch_async(batch, session_id)
                all_completed_items.extend(batch_results)
                
                logger.info(f"Batch {batch_index + 1} completed: {len(batch_results)}/{len(batch)} items successful")
            
            # 結果をカテゴリ別に再構成
            translated_categories = {}
            
            for item in all_completed_items:
                category = item.get('category', 'その他')
                
                # カテゴリ名を翻訳（簡易版）
                if category == '前菜':
                    english_category = 'Appetizers'
                elif category == 'メイン' or category == 'メインディッシュ':
                    english_category = 'Main Dishes'
                elif category == 'スープ':
                    english_category = 'Soups'
                elif category == 'デザート':
                    english_category = 'Desserts'
                elif category == '飲み物':
                    english_category = 'Beverages'
                elif category == 'サラダ':
                    english_category = 'Salads'
                else:
                    english_category = 'Other'
                
                if english_category not in translated_categories:
                    translated_categories[english_category] = []
                
                translated_categories[english_category].append({
                    "japanese_name": item['japanese_name'],
                    "english_name": item['english_name'],
                    "price": item['price']
                })
            
            # 最終結果
            processing_time = time.time() - start_time
            success = len(all_completed_items) > 0
            
            # 完了通知
            if session_id:
                await send_progress(
                    session_id, 3, "completed", 
                    f"✅ Item-level parallel translation completed!",
                    {
                        "translatedCategories": translated_categories,
                        "total_translated_items": len(all_completed_items),
                        "total_categories": len(translated_categories),
                        "translation_method": "item_level_parallel_processing",
                        "show_translated_menu": True,
                        "completion_status": "success",
                        "processing_mode": "item_level_parallel"
                    }
                )
            
            return TranslationResult(
                success=success,
                translated_categories=translated_categories,
                translation_method="item_level_parallel_processing",
                metadata={
                    "total_items": len(all_completed_items),
                    "total_original_items": total_items,
                    "total_categories": len(translated_categories),
                    "processing_mode": "item_level_parallel",
                    "max_parallel_items": self.max_parallel_items,
                    "total_batches": len(batches),
                    "total_processing_time": processing_time,
                    "items_per_second": len(all_completed_items) / processing_time if processing_time > 0 else 0,
                    "provider": "Item Level Parallel Translation Service",
                    "features": [
                        "item_level_parallelization",
                        "batch_processing",
                        "async_task_management",
                        "real_time_progress"
                    ]
                }
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Item-level parallel translation failed after {processing_time:.2f}s: {str(e)}")
            
            return TranslationResult(
                success=False,
                translation_method="item_level_parallel_error",
                error=f"Item-level parallel translation error: {str(e)}",
                metadata={
                    "error_type": "parallel_processing_error",
                    "processing_mode": "item_level_parallel",
                    "total_processing_time": processing_time,
                    "original_error": str(e)
                }
            )

# サービスインスタンス化
item_level_parallel_service = ItemLevelParallelTranslationService()

# 便利な関数
async def translate_menu_item_level_parallel(
    categorized_data: Dict, 
    session_id: Optional[str] = None
) -> TranslationResult:
    """
    アイテムレベル並列翻訳の便利関数
    """
    return await item_level_parallel_service.translate_menu(categorized_data, session_id)

# エクスポート
__all__ = [
    "ItemLevelParallelTranslationService",
    "item_level_parallel_service",
    "translate_menu_item_level_parallel"
]

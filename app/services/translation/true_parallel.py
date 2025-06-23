#!/usr/bin/env python3
"""
真の並列翻訳サービス

全アイテムを同時投入、完了順に取得する最高速並列処理
- 43個全て同時実行
- 完了したアイテムから順次配信
- 最初の料理を最速でユーザーに提供
"""

import asyncio
import time
import logging
from typing import Dict, List, Any, Optional

from app.core.config import settings
from .base import BaseTranslationService, TranslationResult, TranslationProvider

logger = logging.getLogger(__name__)

class TrueParallelTranslationService(BaseTranslationService):
    """
    真の並列翻訳サービス
    
    全アイテムを同時実行し、完了順に結果を取得
    最初の料理を最速配信するための設計
    """
    
    def __init__(self):
        super().__init__()
        self.provider = TranslationProvider.GOOGLE_TRANSLATE
        self.service_name = "True Parallel Translation Service"
        self.max_concurrent_tasks = 50  # 同時実行タスク数上限
    
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
    
    async def process_all_items_truly_parallel(
        self, 
        items: List[Dict], 
        session_id: str = None
    ) -> List[Dict]:
        """
        全アイテムを真の並列処理
        
        Args:
            items: 全アイテムリスト
            session_id: セッションID
            
        Returns:
            List[Dict]: 翻訳済みアイテムリスト
        """
        from app.tasks.item_level_tasks import translate_single_item
        
        # 全タスクを同時開始
        tasks = []
        for item in items:
            task = translate_single_item.delay(item, session_id)
            tasks.append({
                "item_id": item["item_id"],
                "japanese_name": item["japanese_name"],
                "category": item["category"],
                "task": task
            })
        
        logger.info(f"🚀 Started {len(tasks)} parallel tasks simultaneously")
        
        # 進行状況追跡
        completed_items = []
        failed_items = []
        
        # 非同期でタスク完了を監視
        async def wait_for_task(task_info):
            """個別タスクの完了を待機"""
            try:
                result = await asyncio.to_thread(task_info["task"].get, timeout=120)
                
                if result['success']:
                    completed_items.append(result)
                    logger.info(f"✅ {len(completed_items)}/{len(tasks)} completed: {result['japanese_name']} → {result['english_name']}")
                    
                    # リアルタイム進行状況配信
                    if session_id:
                        from app.services.realtime import send_progress
                        await send_progress(
                            session_id, 3, "active", 
                            f"⚡ {len(completed_items)}/{len(tasks)} items completed",
                            {
                                "processing_mode": "true_parallel",
                                "completed_count": len(completed_items),
                                "total_items": len(tasks),
                                "latest_completed": {
                                    "japanese_name": result['japanese_name'],
                                    "english_name": result['english_name']
                                },
                                "progress_percent": int((len(completed_items) / len(tasks)) * 100)
                            }
                        )
                else:
                    failed_items.append({
                        'item_id': task_info["item_id"],
                        'japanese_name': task_info["japanese_name"],
                        'error': result.get('error', 'Unknown error')
                    })
                    logger.warning(f"⚠️ Item failed: {task_info['japanese_name']}")
                    
            except Exception as e:
                failed_items.append({
                    'item_id': task_info["item_id"],
                    'japanese_name': task_info["japanese_name"],
                    'error': f"Task execution failed: {str(e)}"
                })
                logger.error(f"❌ Task failed for {task_info['japanese_name']}: {str(e)}")
        
        # 全タスクの完了を並列待機
        await asyncio.gather(*[wait_for_task(task_info) for task_info in tasks])
        
        logger.info(f"🎉 True parallel processing completed: {len(completed_items)}/{len(tasks)} successful")
        
        return completed_items
    
    async def translate_menu(
        self, 
        categorized_data: Dict, 
        session_id: Optional[str] = None
    ) -> TranslationResult:
        """
        メニュー全体を真の並列翻訳
        
        Args:
            categorized_data: カテゴリ分類されたメニューデータ
            session_id: セッションID
            
        Returns:
            TranslationResult: 翻訳結果
        """
        start_time = time.time()
        
        logger.info(f"Starting true parallel translation: {len(categorized_data)} categories")
        
        # 入力データの妥当性チェック
        if not self.validate_categorized_data(categorized_data):
            return TranslationResult(
                success=False,
                translation_method="true_parallel",
                error="Invalid categorized data"
            )
        
        try:
            # アイテムリストを作成
            items = self.create_item_data(categorized_data)
            total_items = len(items)
            
            logger.info(f"Created {total_items} items for true parallel processing")
            
            # 同時実行数の制限チェック
            if total_items > self.max_concurrent_tasks:
                logger.warning(f"Item count ({total_items}) exceeds max concurrent tasks ({self.max_concurrent_tasks})")
                items = items[:self.max_concurrent_tasks]
                total_items = len(items)
            
            # 進行状況通知
            if session_id:
                from app.services.realtime import send_progress
                await send_progress(
                    session_id, 3, "active", 
                    f"🚀 Starting TRUE parallel translation: {total_items} items simultaneously!",
                    {
                        "processing_mode": "true_parallel",
                        "total_items": total_items,
                        "max_concurrent_tasks": self.max_concurrent_tasks,
                        "parallel_strategy": "all_items_simultaneous"
                    }
                )
            
            # 真の並列処理実行
            completed_items = await self.process_all_items_truly_parallel(items, session_id)
            
            # 結果をカテゴリ別に再構成
            translated_categories = {}
            
            for item in completed_items:
                category = item.get('category', 'その他')
                
                # カテゴリ名を翻訳（簡易版）
                category_mapping = {
                    '前菜': 'Appetizers',
                    'メイン': 'Main Dishes',
                    'メインディッシュ': 'Main Dishes',
                    'スープ': 'Soups',
                    'デザート': 'Desserts',
                    '飲み物': 'Beverages',
                    'サラダ': 'Salads'
                }
                english_category = category_mapping.get(category, 'Other')
                
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
            items_per_second = len(completed_items) / processing_time if processing_time > 0 else 0
            
            # 完了通知
            if session_id:
                await send_progress(
                    session_id, 3, "completed", 
                    f"🎉 TRUE parallel translation completed! {len(completed_items)} items in {processing_time:.2f}s",
                    {
                        "translatedCategories": translated_categories,
                        "total_translated_items": len(completed_items),
                        "total_categories": len(translated_categories),
                        "translation_method": "true_parallel_processing",
                        "show_translated_menu": True,
                        "completion_status": "success",
                        "processing_mode": "true_parallel",
                        "items_per_second": items_per_second,
                        "processing_time": processing_time
                    }
                )
            
            return TranslationResult(
                success=success,
                translated_categories=translated_categories,
                translation_method="true_parallel_processing",
                metadata={
                    "total_items": len(completed_items),
                    "total_original_items": total_items,
                    "total_categories": len(translated_categories),
                    "processing_mode": "true_parallel",
                    "max_concurrent_tasks": self.max_concurrent_tasks,
                    "total_processing_time": processing_time,
                    "items_per_second": items_per_second,
                    "parallel_strategy": "all_items_simultaneous",
                    "provider": "True Parallel Translation Service",
                    "features": [
                        "true_parallel_processing",
                        "simultaneous_task_execution",
                        "completion_order_processing",
                        "real_time_progress",
                        "first_item_fastest_delivery"
                    ]
                }
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"True parallel translation failed after {processing_time:.2f}s: {str(e)}")
            
            return TranslationResult(
                success=False,
                translation_method="true_parallel_error",
                error=f"True parallel translation error: {str(e)}",
                metadata={
                    "error_type": "true_parallel_processing_error",
                    "processing_mode": "true_parallel",
                    "total_processing_time": processing_time,
                    "original_error": str(e)
                }
            )

# サービスインスタンス化
true_parallel_service = TrueParallelTranslationService()

# 便利な関数
async def translate_menu_true_parallel(
    categorized_data: Dict, 
    session_id: Optional[str] = None
) -> TranslationResult:
    """
    真の並列翻訳の便利関数
    """
    return await true_parallel_service.translate_menu(categorized_data, session_id)

# エクスポート
__all__ = [
    "TrueParallelTranslationService",
    "true_parallel_service",
    "translate_menu_true_parallel"
]

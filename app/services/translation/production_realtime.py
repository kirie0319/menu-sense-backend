#!/usr/bin/env python3
"""
本番用リアルタイム翻訳サービス

Protocol Error対策済み
- 安定性重視
- 本番環境対応
- エラー耐性強化
"""

import asyncio
import time
import logging
from typing import Dict, List, Any, Optional, Tuple
from concurrent.futures import as_completed

from app.core.config import settings
from .base import BaseTranslationService, TranslationResult, TranslationProvider

logger = logging.getLogger(__name__)

class ProductionRealtimeTranslationService(BaseTranslationService):
    """
    本番用リアルタイム翻訳サービス
    
    Protocol Error対策とエラー耐性を強化
    """
    
    def __init__(self):
        super().__init__()
        self.provider = TranslationProvider.GOOGLE_TRANSLATE
        self.service_name = "Production Realtime Translation Service"
        self.max_concurrent_tasks = 6  # 並列度を制限してエラー対策
        self.task_timeout = 30  # タスクタイムアウト
        self.retry_max = 2  # リトライ回数
    
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
    
    async def process_items_batch_safe(self, items: List[Dict], session_id: str = None) -> List[Dict]:
        """
        安全なバッチ処理（Protocol Error対策）
        
        制限された並列度で安定処理
        """
        from app.tasks.item_level_tasks import translate_single_item
        
        completed_items = []
        total_items = len(items)
        completed_count = 0
        
        # アイテムをバッチに分割（同時実行数制限）
        batches = [items[i:i + self.max_concurrent_tasks] for i in range(0, len(items), self.max_concurrent_tasks)]
        
        logger.info(f"Processing {len(items)} items in {len(batches)} safe batches (max {self.max_concurrent_tasks} concurrent)")
        
        for batch_index, batch in enumerate(batches):
            logger.info(f"Processing batch {batch_index + 1}/{len(batches)} ({len(batch)} items)")
            
            # バッチ内並列処理
            batch_tasks = []
            for item in batch:
                task = translate_single_item.delay(item, session_id)
                batch_tasks.append((item, task))
            
            # バッチ完了を待機（タイムアウト付き）
            for item_data, task in batch_tasks:
                try:
                    # タスク完了を安全に待機
                    result = await asyncio.to_thread(self._safe_task_get, task)
                    
                    if result and result.get('success'):
                        completed_count += 1
                        completed_items.append(result)
                        
                        # 完了したアイテムを即座に配信
                        if session_id:
                            await self.send_item_completed_safe(
                                session_id, 
                                result, 
                                completed_count, 
                                total_items
                            )
                        
                        logger.info(f"✅ Item {completed_count}/{total_items} completed: {result['japanese_name']} → {result['english_name']}")
                    else:
                        logger.warning(f"⚠️ Item failed: {item_data['item_id']}")
                        
                except Exception as e:
                    logger.error(f"❌ Task processing failed for item {item_data['item_id']}: {str(e)}")
            
            # バッチ間の小休止（システム負荷軽減）
            if batch_index < len(batches) - 1:
                await asyncio.sleep(0.1)
        
        return completed_items
    
    def _safe_task_get(self, task, max_retries=3):
        """Protocol Error対策済みのタスク結果取得"""
        for attempt in range(max_retries):
            try:
                return task.get(timeout=self.task_timeout)
            except Exception as e:
                error_str = str(e)
                if "Protocol Error" in error_str:
                    logger.warning(f"Protocol Error attempt {attempt + 1}/{max_retries}: {item_id if 'item_id' in locals() else 'unknown'}")
                    if attempt < max_retries - 1:
                        time.sleep(0.5)  # 短い待機後リトライ
                        continue
                    else:
                        logger.error(f"Protocol Error maximum retries exceeded")
                        return None
                else:
                    logger.error(f"Task get error: {error_str}")
                    return None
        return None
    
    async def send_item_completed_safe(self, session_id: str, item_result: Dict, completed_count: int, total_items: int):
        """安全なアイテム完了通知"""
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
                    "processing_mode": "production_realtime",
                    "realtime_delivery": True,
                    "timestamp": time.time(),
                    "batch_processing": True,
                    "stability_mode": True
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to send safe item completed notification: {e}")
    
    async def translate_menu(
        self, 
        categorized_data: Dict, 
        session_id: Optional[str] = None
    ) -> TranslationResult:
        """
        本番用メニュー翻訳（安定性重視）
        """
        start_time = time.time()
        
        logger.info(f"Starting production realtime translation: {len(categorized_data)} categories")
        
        # 入力データの妥当性チェック
        if not self.validate_categorized_data(categorized_data):
            return TranslationResult(
                success=False,
                translation_method="production_realtime",
                error="Invalid categorized data"
            )
        
        try:
            # アイテムリストを作成
            items = self.create_item_data(categorized_data)
            total_items = len(items)
            
            logger.info(f"Created {total_items} items for production realtime processing")
            
            # 開始通知
            if session_id:
                from app.services.realtime import send_progress
                await send_progress(
                    session_id, 3, "active", 
                    f"🚀 Starting production realtime translation: {total_items} items (safe batches)",
                    {
                        "processing_mode": "production_realtime",
                        "total_items": total_items,
                        "realtime_delivery": True,
                        "stability_mode": True,
                        "max_concurrent": self.max_concurrent_tasks,
                        "message": "Items will appear in safe batches for maximum stability"
                    }
                )
            
            # 安全なバッチ処理
            completed_items = await self.process_items_batch_safe(items, session_id)
            
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
            
            # 完了通知
            if session_id:
                await send_progress(
                    session_id, 3, "completed", 
                    f"✅ Production realtime translation completed! {len(completed_items)}/{total_items} items delivered",
                    {
                        "translatedCategories": translated_categories,
                        "total_translated_items": len(completed_items),
                        "total_original_items": total_items,
                        "success_rate": f"{success_rate:.1%}",
                        "total_categories": len(translated_categories),
                        "translation_method": "production_realtime_processing",
                        "show_translated_menu": True,
                        "completion_status": "success",
                        "processing_mode": "production_realtime",
                        "realtime_delivery": True,
                        "stability_mode": True
                    }
                )
            
            return TranslationResult(
                success=success,
                translated_categories=translated_categories,
                translation_method="production_realtime_processing",
                metadata={
                    "total_items": len(completed_items),
                    "total_original_items": total_items,
                    "success_rate": success_rate,
                    "total_categories": len(translated_categories),
                    "processing_mode": "production_realtime",
                    "total_processing_time": processing_time,
                    "items_per_second": len(completed_items) / processing_time if processing_time > 0 else 0,
                    "realtime_delivery": True,
                    "stability_mode": True,
                    "max_concurrent_tasks": self.max_concurrent_tasks,
                    "first_item_delivery_time": "~1-2 seconds",
                    "provider": "Production Realtime Translation Service",
                    "features": [
                        "realtime_item_delivery",
                        "safe_batch_processing",
                        "protocol_error_resistance",
                        "production_stability",
                        "error_recovery",
                        "progress_streaming"
                    ]
                }
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Production realtime translation failed after {processing_time:.2f}s: {str(e)}")
            
            return TranslationResult(
                success=False,
                translation_method="production_realtime_error",
                error=f"Production realtime translation error: {str(e)}",
                metadata={
                    "error_type": "production_realtime_error",
                    "processing_mode": "production_realtime",
                    "total_processing_time": processing_time,
                    "original_error": str(e)
                }
            )

# サービスインスタンス化
production_realtime_service = ProductionRealtimeTranslationService()

# 便利な関数
async def translate_menu_production_realtime(
    categorized_data: Dict, 
    session_id: Optional[str] = None
) -> TranslationResult:
    """
    本番用リアルタイム翻訳の便利関数
    """
    return await production_realtime_service.translate_menu(categorized_data, session_id)

# エクスポート
__all__ = [
    "ProductionRealtimeTranslationService",
    "production_realtime_service", 
    "translate_menu_production_realtime"
] 
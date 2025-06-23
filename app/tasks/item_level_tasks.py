#!/usr/bin/env python3
"""
アイテムレベル並列処理タスク

目標: 8個のメニューアイテムを同時に翻訳・説明・画像生成
- 既存コードに影響なし
- 段階的テスト可能
- 最速配信重視
"""

import time
import asyncio
import logging
from typing import Dict, List, Any, Optional

from .celery_app import celery_app

# ログ設定
logger = logging.getLogger(__name__)

def await_sync(coro):
    """非同期関数を同期的に実行（Celeryワーカー用）"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

@celery_app.task(bind=True, name="translate_single_item")
def translate_single_item(self, item_data: Dict, session_id: str = None):
    """
    単一アイテムを翻訳（8個同時実行用）
    
    Args:
        item_data: {
            "item_id": "unique_id",
            "japanese_name": "料理名",
            "price": "¥800",
            "category": "カテゴリ名"
        }
        session_id: セッションID
        
    Returns:
        Dict: 翻訳結果
    """
    
    item_id = item_data.get("item_id", "unknown")
    japanese_name = item_data.get("japanese_name", "")
    
    try:
        # 進行状況更新
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'item_translation',
                'item_id': item_id,
                'progress': 0,
                'status': 'starting',
                'japanese_name': japanese_name
            }
        )
        
        logger.info(f"Starting translation for item: {japanese_name} (ID: {item_id})")
        
        # Google Translate API直接呼び出し
        from app.services.translation.google_translate import GoogleTranslateService
        
        google_service = GoogleTranslateService()
        
        if not google_service.is_available():
            # フォールバック: OpenAI
            from app.services.translation.openai import OpenAITranslationService
            translation_service = OpenAITranslationService()
            if not translation_service.is_available():
                raise Exception("No translation services available")
        else:
            translation_service = google_service
        
        # 翻訳実行
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'item_translation',
                'item_id': item_id,
                'progress': 50,
                'status': 'translating'
            }
        )
        
        english_name = await_sync(translation_service.translate_menu_item(japanese_name))
        
        # 完了
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'item_translation',
                'item_id': item_id,
                'progress': 100,
                'status': 'completed'
            }
        )
        
        result = {
            'success': True,
            'item_id': item_id,
            'japanese_name': japanese_name,
            'english_name': english_name,
            'price': item_data.get("price", ""),
            'category': item_data.get("category", ""),
            'translation_method': type(translation_service).__name__,
            'processing_time': time.time()
        }
        
        logger.info(f"Item translation completed: {japanese_name} → {english_name}")
        
        return result
        
    except Exception as e:
        logger.error(f"Item translation failed for {japanese_name}: {str(e)}")
        
        self.update_state(
            state='FAILURE',
            meta={
                'stage': 'item_translation',
                'item_id': item_id,
                'error': str(e),
                'status': 'failed'
            }
        )
        
        return {
            'success': False,
            'item_id': item_id,
            'japanese_name': japanese_name,
            'error': str(e),
            'translation_method': 'failed'
        }

@celery_app.task(bind=True, name="process_items_batch")
def process_items_batch(self, items_batch: List[Dict], session_id: str = None):
    """
    アイテム8個バッチを並列処理
    
    Args:
        items_batch: アイテムリスト（最大8個）
        session_id: セッションID
        
    Returns:
        Dict: バッチ処理結果
    """
    
    batch_id = f"batch_{int(time.time())}"
    
    try:
        logger.info(f"Starting batch processing: {len(items_batch)} items (ID: {batch_id})")
        
        # 進行状況更新
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'batch_processing',
                'batch_id': batch_id,
                'progress': 0,
                'status': 'starting',
                'items_count': len(items_batch)
            }
        )
        
        # 8個のアイテムを同時に翻訳タスク投入
        translation_tasks = []
        
        for item in items_batch:
            task = translate_single_item.delay(item, session_id)
            translation_tasks.append((item.get("item_id", "unknown"), task))
        
        # 進行状況更新
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'batch_processing',
                'batch_id': batch_id,
                'progress': 20,
                'status': 'tasks_created',
                'tasks_count': len(translation_tasks)
            }
        )
        
        # 完了を待機
        completed_items = []
        failed_items = []
        
        for item_id, task in translation_tasks:
            try:
                result = task.get(timeout=60)  # 1分タイムアウト
                
                if result['success']:
                    completed_items.append(result)
                    logger.info(f"✅ Item completed: {result['japanese_name']} → {result['english_name']}")
                else:
                    failed_items.append({
                        'item_id': item_id,
                        'error': result.get('error', 'Unknown error')
                    })
                    logger.warning(f"⚠️ Item failed: {item_id}")
                    
            except Exception as e:
                failed_items.append({
                    'item_id': item_id,
                    'error': f"Task execution failed: {str(e)}"
                })
                logger.error(f"❌ Task failed for item {item_id}: {str(e)}")
        
        # 完了
        success = len(failed_items) == 0
        
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'batch_processing',
                'batch_id': batch_id,
                'progress': 100,
                'status': 'completed',
                'completed_count': len(completed_items),
                'failed_count': len(failed_items)
            }
        )
        
        result = {
            'success': success,
            'batch_id': batch_id,
            'completed_items': completed_items,
            'failed_items': failed_items,
            'total_items': len(items_batch),
            'completed_count': len(completed_items),
            'failed_count': len(failed_items),
            'processing_method': 'item_level_batch_parallel',
            'processing_time': time.time()
        }
        
        logger.info(f"Batch processing completed: {len(completed_items)}/{len(items_batch)} items successful")
        
        return result
        
    except Exception as e:
        logger.error(f"Batch processing failed: {str(e)}")
        
        self.update_state(
            state='FAILURE',
            meta={
                'stage': 'batch_processing',
                'batch_id': batch_id,
                'error': str(e),
                'status': 'failed'
            }
        )
        
        return {
            'success': False,
            'batch_id': batch_id,
            'error': str(e),
            'processing_method': 'item_level_batch_failed'
        }

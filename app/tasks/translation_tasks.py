#!/usr/bin/env python3
"""
翻訳処理 Celeryタスク

Stage 3翻訳の並列化を実現するワーカータスク群
- カテゴリレベルでの並列処理
- フォールバック機能（Google Translate → OpenAI）
- エラー時の部分回復
- フロントエンド互換性の完全保持
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

@celery_app.task(bind=True, name="translate_category_simple")
def translate_category_simple(self, category_name: str, items: List[Dict], session_id: str = None):
    """
    単一カテゴリを翻訳するシンプルなワーカータスク
    
    Args:
        category_name: 日本語カテゴリ名
        items: カテゴリ内のメニューアイテムリスト
        session_id: セッションID
        
    Returns:
        Dict: 翻訳結果
    """
    try:
        # 進行状況更新
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'translation',
                'category': category_name,
                'progress': 0,
                'status': 'starting',
                'items_total': len(items)
            }
        )
        
        logger.info(f"Starting translation for category: {category_name} ({len(items)} items)")
        
        # 翻訳サービスを初期化
        from app.services.translation.google_translate import GoogleTranslateService
        
        google_service = GoogleTranslateService()
        
        if not google_service.is_available():
            raise Exception("Google Translate service not available")
        
        # カテゴリ名の翻訳
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'translation',
                'category': category_name,
                'progress': 10,
                'status': 'translating_category_name'
            }
        )
        
        english_category = await_sync(google_service.translate_category_name(category_name))
        
        # アイテムの翻訳
        translated_items = []
        
        for i, item in enumerate(items):
            # 進行状況更新
            progress = 10 + int((i / len(items)) * 80)  # 10-90%
            self.update_state(
                state='PROGRESS',
                meta={
                    'stage': 'translation',
                    'category': category_name,
                    'progress': progress,
                    'status': 'translating_items',
                    'current_item': i + 1,
                    'items_total': len(items)
                }
            )
            
            # アイテムデータの抽出
            item_name, item_price = google_service.extract_menu_item_data(item)
            
            if item_name.strip():
                # 翻訳実行
                english_name = await_sync(google_service.translate_menu_item(item_name))
                
                translated_items.append({
                    "japanese_name": item_name,
                    "english_name": english_name,
                    "price": item_price
                })
                
                logger.info(f"  Translated: {item_name} → {english_name}")
            
            # レート制限対策
            time.sleep(0.1)
        
        # 完了
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'translation',
                'category': category_name,
                'progress': 100,
                'status': 'completed',
                'items_translated': len(translated_items)
            }
        )
        
        result = {
            'success': True,
            'category_name': category_name,
            'english_category': english_category,
            'translated_items': translated_items,
            'items_processed': len(translated_items),
            'translation_method': 'google_translate_worker',
            'processing_time': time.time()
        }
        
        logger.info(f"Category translation completed: {category_name} → {english_category} ({len(translated_items)} items)")
        
        return result
        
    except Exception as e:
        logger.error(f"Translation failed for category {category_name}: {str(e)}")
        
        # エラー状態更新
        self.update_state(
            state='FAILURE',
            meta={
                'stage': 'translation',
                'category': category_name,
                'error': str(e),
                'status': 'failed',
                'exc_type': type(e).__name__,
                'exc_module': type(e).__module__
            }
        )
        
        return {
            'success': False,
            'category_name': category_name,
            'error': str(e),
            'items_processed': 0,
            'translation_method': 'google_translate_worker'
        }

@celery_app.task(bind=True, name="translate_category_with_fallback")
def translate_category_with_fallback(self, category_name: str, items: List[Dict], session_id: str = None):
    """
    フォールバック機能付きカテゴリ翻訳ワーカー
    Google Translate → OpenAI の順で試行
    
    Args:
        category_name: 日本語カテゴリ名
        items: カテゴリ内のメニューアイテムリスト
        session_id: セッションID
        
    Returns:
        Dict: 翻訳結果
    """
    try:
        # 進行状況更新
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'translation_with_fallback',
                'category': category_name,
                'progress': 0,
                'status': 'starting',
                'items_total': len(items)
            }
        )
        
        logger.info(f"Starting translation with fallback for category: {category_name} ({len(items)} items)")
        
        # Step 1: Google Translate試行
        try:
            from app.services.translation.google_translate import GoogleTranslateService
            
            google_service = GoogleTranslateService()
            
            if google_service.is_available():
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'stage': 'translation_with_fallback',
                        'category': category_name,
                        'progress': 5,
                        'status': 'trying_google_translate'
                    }
                )
                
                # Google Translateで翻訳実行
                result = await_sync(google_service.translate_menu({category_name: items}, session_id))
                
                if result.success and result.translated_categories:
                    # Google Translate成功
                    english_category = list(result.translated_categories.keys())[0]
                    translated_items = result.translated_categories[english_category]
                    
                    self.update_state(
                        state='PROGRESS',
                        meta={
                            'stage': 'translation_with_fallback',
                            'category': category_name,
                            'progress': 100,
                            'status': 'completed_with_google'
                        }
                    )
                    
                    return {
                        'success': True,
                        'category_name': category_name,
                        'english_category': english_category,
                        'translated_items': translated_items,
                        'items_processed': len(translated_items),
                        'translation_method': 'google_translate_primary',
                        'fallback_used': False,
                        'processing_time': time.time()
                    }
                    
            raise Exception("Google Translate failed or unavailable")
            
        except Exception as google_error:
            logger.warning(f"Google Translate failed for {category_name}: {google_error}")
            
            # Step 2: OpenAI フォールバック
            try:
                from app.services.translation.openai import OpenAITranslationService
                
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'stage': 'translation_with_fallback',
                        'category': category_name,
                        'progress': 50,
                        'status': 'trying_openai_fallback'
                    }
                )
                
                openai_service = OpenAITranslationService()
                
                if openai_service.is_available():
                    # OpenAI翻訳実行
                    result = await_sync(openai_service.translate_menu({category_name: items}, session_id))
                    
                    if result.success and result.translated_categories:
                        # OpenAI成功
                        english_category = list(result.translated_categories.keys())[0]
                        translated_items = result.translated_categories[english_category]
                        
                        self.update_state(
                            state='PROGRESS',
                            meta={
                                'stage': 'translation_with_fallback',
                                'category': category_name,
                                'progress': 100,
                                'status': 'completed_with_openai_fallback'
                            }
                        )
                        
                        return {
                            'success': True,
                            'category_name': category_name,
                            'english_category': english_category,
                            'translated_items': translated_items,
                            'items_processed': len(translated_items),
                            'translation_method': 'openai_fallback',
                            'fallback_used': True,
                            'google_error': str(google_error),
                            'processing_time': time.time()
                        }
                
                raise Exception("OpenAI Translation also failed or unavailable")
                
            except Exception as openai_error:
                logger.error(f"Both Google Translate and OpenAI failed for {category_name}")
                
                # 両方失敗
                self.update_state(
                    state='FAILURE',
                    meta={
                        'stage': 'translation_with_fallback',
                        'category': category_name,
                        'error': 'Both translation services failed',
                        'google_error': str(google_error),
                        'openai_error': str(openai_error),
                        'status': 'all_services_failed',
                        'exc_type': type(openai_error).__name__,
                        'exc_module': type(openai_error).__module__
                    }
                )
                
                return {
                    'success': False,
                    'category_name': category_name,
                    'error': 'Both Google Translate and OpenAI translation failed',
                    'google_error': str(google_error),
                    'openai_error': str(openai_error),
                    'items_processed': 0,
                    'translation_method': 'all_failed',
                    'fallback_used': True
                }
                
    except Exception as e:
        logger.error(f"Unexpected error in translation with fallback for {category_name}: {str(e)}")
        
        self.update_state(
            state='FAILURE',
            meta={
                'stage': 'translation_with_fallback',
                'category': category_name,
                'error': str(e),
                'status': 'unexpected_error',
                'exc_type': type(e).__name__,
                'exc_module': type(e).__module__
            }
        )
        
        return {
            'success': False,
            'category_name': category_name,
            'error': f"Unexpected translation error: {str(e)}",
            'items_processed': 0,
            'translation_method': 'worker_error'
        }

@celery_app.task(bind=True, name="translate_menu_parallel")
def translate_menu_parallel(self, categorized_data: Dict, session_id: str = None):
    """
    メニュー全体を並列翻訳する統合ワーカータスク
    
    Args:
        categorized_data: カテゴリ分類されたメニューデータ
        session_id: セッションID
        
    Returns:
        Dict: 翻訳結果（既存形式と互換）
    """
    try:
        # 進行状況更新
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'menu_translation_parallel',
                'progress': 0,
                'status': 'starting',
                'total_categories': len(categorized_data)
            }
        )
        
        logger.info(f"Starting parallel menu translation: {len(categorized_data)} categories")
        
        # カテゴリごとにワーカータスクを作成
        translation_tasks = []
        
        for category_name, items in categorized_data.items():
            if items:  # 空のカテゴリはスキップ
                task = translate_category_with_fallback.delay(category_name, items, session_id)
                translation_tasks.append((category_name, task))
        
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'menu_translation_parallel',
                'progress': 10,
                'status': 'tasks_created',
                'tasks_count': len(translation_tasks)
            }
        )
        
        # 並列実行の結果を収集
        translated_categories = {}
        failed_categories = []
        total_items = 0
        
        for i, (category_name, task) in enumerate(translation_tasks):
            try:
                # タスク完了を待機
                result = task.get(timeout=120)  # 2分タイムアウト
                
                if result['success']:
                    english_category = result['english_category']
                    translated_categories[english_category] = result['translated_items']
                    total_items += len(result['translated_items'])
                    logger.info(f"Category completed: {category_name} → {english_category}")
                else:
                    # 失敗したカテゴリは元データで代替
                    failed_categories.append({
                        'category': category_name,
                        'error': result.get('error', 'Unknown error')
                    })
                    # 翻訳失敗時は元の日本語データを保持
                    translated_categories[category_name] = categorized_data[category_name]
                    logger.warning(f"Category failed, using original data: {category_name}")
                
            except Exception as e:
                # タスク自体が失敗
                failed_categories.append({
                    'category': category_name,
                    'error': f"Task execution failed: {str(e)}"
                })
                # 元の日本語データを保持
                translated_categories[category_name] = categorized_data[category_name]
                logger.error(f"Task failed for category {category_name}: {str(e)}")
            
            # 進行状況更新
            progress = 10 + int(((i + 1) / len(translation_tasks)) * 80)
            self.update_state(
                state='PROGRESS',
                meta={
                    'stage': 'menu_translation_parallel',
                    'progress': progress,
                    'status': 'collecting_results',
                    'completed_categories': i + 1,
                    'total_categories': len(translation_tasks)
                }
            )
        
        # 最終結果
        success = len(failed_categories) == 0
        
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'menu_translation_parallel',
                'progress': 100,
                'status': 'completed',
                'successful_categories': len(translated_categories) - len(failed_categories),
                'failed_categories': len(failed_categories)
            }
        )
        
        result = {
            'success': success,
            'translated_categories': translated_categories,
            'translation_method': 'parallel_worker_processing',
            'total_items': total_items,
            'total_categories': len(translated_categories),
            'failed_categories': failed_categories if failed_categories else None,
            'parallel_processing': True,
            'processing_time': time.time()
        }
        
        logger.info(f"Parallel translation completed: {len(translated_categories)} categories, {len(failed_categories)} failures")
        
        return result
        
    except Exception as e:
        logger.error(f"Parallel menu translation failed: {str(e)}")
        
        self.update_state(
            state='FAILURE',
            meta={
                'stage': 'menu_translation_parallel',
                'error': str(e),
                'status': 'failed',
                'exc_type': type(e).__name__,
                'exc_module': type(e).__module__
            }
        )
        
        return {
            'success': False,
            'error': f"Parallel translation error: {str(e)}",
            'translation_method': 'parallel_worker_failed',
            'translated_categories': {}
        } 
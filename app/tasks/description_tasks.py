#!/usr/bin/env python3
"""
詳細説明処理 Celeryタスク

Stage 4詳細説明の並列化を実現するワーカータスク群
- カテゴリレベルでの並列処理
- チャンクレベルでの細分化処理
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

@celery_app.task(bind=True, name="add_descriptions_to_category")
def add_descriptions_to_category(self, category_name: str, translated_items: List[Dict], session_id: str = None):
    """
    単一カテゴリに詳細説明を追加するワーカータスク
    
    Args:
        category_name: 英語カテゴリ名
        translated_items: 翻訳済みアイテムリスト
        session_id: セッションID
        
    Returns:
        Dict: 詳細説明追加結果
    """
    try:
        # 進行状況更新
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'description',
                'category': category_name,
                'progress': 0,
                'status': 'starting',
                'items_total': len(translated_items)
            }
        )
        
        logger.info(f"Starting description generation for category: {category_name} ({len(translated_items)} items)")
        
        # 詳細説明サービスを初期化
        from app.services.description.openai import OpenAIDescriptionService
        
        openai_service = OpenAIDescriptionService()
        
        if not openai_service.is_available():
            raise Exception("OpenAI Description service not available")
        
        # 詳細説明追加実行
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'description',
                'category': category_name,
                'progress': 10,
                'status': 'processing_descriptions'
            }
        )
        
        # 翻訳データを適切な形式に変換
        translated_data = {category_name: translated_items}
        
        # 詳細説明を並列追加
        result = await_sync(openai_service.add_descriptions(translated_data, session_id))
        
        # 完了
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'description',
                'category': category_name,
                'progress': 100,
                'status': 'completed',
                'items_processed': len(translated_items)
            }
        )
        
        if result.success and result.final_menu and category_name in result.final_menu:
            final_items = result.final_menu[category_name]
            
            response = {
                'success': True,
                'category_name': category_name,
                'final_items': final_items,
                'items_processed': len(final_items),
                'description_method': result.description_method,
                'processing_time': time.time()
            }
            
            logger.info(f"Category description completed: {category_name} ({len(final_items)} items)")
            return response
        else:
            raise Exception(f"Description generation failed: {result.error if result else 'Unknown error'}")
        
    except Exception as e:
        logger.error(f"Description generation failed for category {category_name}: {str(e)}")
        
        # エラー状態更新
        self.update_state(
            state='FAILURE',
            meta={
                'stage': 'description',
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
            'description_method': 'openai_worker'
        }

@celery_app.task(bind=True, name="add_descriptions_to_chunk")
def add_descriptions_to_chunk(self, category_name: str, chunk_items: List[Dict], chunk_info: Dict, session_id: str = None):
    """
    チャンクレベルでの詳細説明追加ワーカータスク
    
    Args:
        category_name: 英語カテゴリ名
        chunk_items: チャンク内のアイテムリスト
        chunk_info: チャンク情報 {"chunk_number": 1, "total_chunks": 3}
        session_id: セッションID
        
    Returns:
        Dict: チャンク処理結果
    """
    try:
        chunk_number = chunk_info.get('chunk_number', 1)
        total_chunks = chunk_info.get('total_chunks', 1)
        
        # 進行状況更新
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'description_chunk',
                'category': category_name,
                'chunk': f"{chunk_number}/{total_chunks}",
                'progress': 0,
                'status': 'starting',
                'items_total': len(chunk_items)
            }
        )
        
        logger.info(f"Starting description generation for chunk {chunk_number}/{total_chunks} in {category_name} ({len(chunk_items)} items)")
        
        # 詳細説明サービスを初期化
        from app.services.description.openai import OpenAIDescriptionService
        
        openai_service = OpenAIDescriptionService()
        
        if not openai_service.is_available():
            raise Exception("OpenAI Description service not available")
        
        # チャンク処理実行
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'description_chunk',
                'category': category_name,
                'chunk': f"{chunk_number}/{total_chunks}",
                'progress': 20,
                'status': 'processing_chunk'
            }
        )
        
        # 直接チャンク処理関数を呼び出し
        final_items = await_sync(openai_service.process_chunk(
            category_name, chunk_items, chunk_number, total_chunks, session_id
        ))
        
        # 完了
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'description_chunk',
                'category': category_name,
                'chunk': f"{chunk_number}/{total_chunks}",
                'progress': 100,
                'status': 'completed',
                'items_processed': len(final_items)
            }
        )
        
        result = {
            'success': True,
            'category_name': category_name,
            'chunk_number': chunk_number,
            'total_chunks': total_chunks,
            'final_items': final_items,
            'items_processed': len(final_items),
            'description_method': 'openai_chunk_worker',
            'processing_time': time.time()
        }
        
        logger.info(f"Chunk description completed: {category_name} chunk {chunk_number}/{total_chunks} ({len(final_items)} items)")
        return result
        
    except Exception as e:
        logger.error(f"Description generation failed for chunk {chunk_number}/{total_chunks} in {category_name}: {str(e)}")
        
        # エラー状態更新
        self.update_state(
            state='FAILURE',
            meta={
                'stage': 'description_chunk',
                'category': category_name,
                'chunk': f"{chunk_number}/{total_chunks}",
                'error': str(e),
                'status': 'failed'
            }
        )
        
        return {
            'success': False,
            'category_name': category_name,
            'chunk_number': chunk_number,
            'total_chunks': total_chunks,
            'error': str(e),
            'items_processed': 0,
            'description_method': 'openai_chunk_worker'
        }

@celery_app.task(bind=True, name="add_descriptions_parallel_menu")
def add_descriptions_parallel_menu(self, translated_data: Dict, session_id: str = None):
    """
    メニュー全体に詳細説明を並列追加する統合ワーカータスク
    
    Args:
        translated_data: 翻訳済みメニューデータ
        session_id: セッションID
        
    Returns:
        Dict: 詳細説明追加結果（既存形式と互換）
    """
    try:
        # 進行状況更新
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'menu_description_parallel',
                'progress': 0,
                'status': 'starting',
                'total_categories': len(translated_data)
            }
        )
        
        logger.info(f"Starting parallel menu description generation: {len(translated_data)} categories")
        
        # カテゴリごとにワーカータスクを作成
        description_tasks = []
        
        for category_name, translated_items in translated_data.items():
            if translated_items:  # 空のカテゴリはスキップ
                task = add_descriptions_to_category.delay(category_name, translated_items, session_id)
                description_tasks.append((category_name, task))
        
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'menu_description_parallel',
                'progress': 10,
                'status': 'tasks_created',
                'tasks_count': len(description_tasks)
            }
        )
        
        # 並列実行の結果を収集
        final_menu = {}
        failed_categories = []
        total_items = 0
        
        # 結果を非同期で収集するため、タスクIDとカテゴリ名をマッピング
        task_map = {task.id: category_name for category_name, task in description_tasks}
        
        # 全タスクの完了を待機（非同期収集）
        from celery import group
        job = group([task for _, task in description_tasks])
        result_group = job.apply_async()
        
        try:
            # グループ全体の結果を取得
            results = result_group.get(timeout=240)
        except Exception as e:
            logger.error(f"Group task execution failed: {str(e)}")
            results = []
        
        # 結果を処理
        for i, result in enumerate(results):
            try:
                if i < len(description_tasks):
                    category_name = description_tasks[i][0]
                
                if result['success']:
                    final_menu[category_name] = result['final_items']
                    total_items += len(result['final_items'])
                    logger.info(f"Category description completed: {category_name}")
                else:
                    # 失敗したカテゴリは元データで代替
                    failed_categories.append({
                        'category': category_name,
                        'error': result.get('error', 'Unknown error')
                    })
                    # フォールバック説明で代替
                    fallback_items = []
                    for item in translated_data[category_name]:
                        fallback_items.append({
                            "japanese_name": item.get("japanese_name", "N/A"),
                            "english_name": item.get("english_name", "N/A"),
                            "description": "Detailed description currently unavailable.",
                            "price": item.get("price", "")
                        })
                    final_menu[category_name] = fallback_items
                    total_items += len(fallback_items)
                    logger.warning(f"Category failed, using fallback descriptions: {category_name}")
                
            except Exception as e:
                # タスク自体が失敗
                failed_categories.append({
                    'category': category_name,
                    'error': f"Task execution failed: {str(e)}"
                })
                # フォールバック説明で代替
                fallback_items = []
                for item in translated_data[category_name]:
                    fallback_items.append({
                        "japanese_name": item.get("japanese_name", "N/A"),
                        "english_name": item.get("english_name", "N/A"),
                        "description": "Detailed description currently unavailable.",
                        "price": item.get("price", "")
                    })
                final_menu[category_name] = fallback_items
                total_items += len(fallback_items)
                logger.error(f"Task failed for category {category_name}: {str(e)}")
            
            # 進行状況更新
            progress = 10 + int(((i + 1) / len(description_tasks)) * 80)
            self.update_state(
                state='PROGRESS',
                meta={
                    'stage': 'menu_description_parallel',
                    'progress': progress,
                    'status': 'collecting_results',
                    'completed_categories': i + 1,
                    'total_categories': len(description_tasks)
                }
            )
        
        # 空のカテゴリを追加
        for category_name, translated_items in translated_data.items():
            if not translated_items and category_name not in final_menu:
                final_menu[category_name] = []
        
        # 最終結果
        success = len(failed_categories) == 0
        
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'menu_description_parallel',
                'progress': 100,
                'status': 'completed',
                'successful_categories': len(final_menu) - len(failed_categories),
                'failed_categories': len(failed_categories)
            }
        )
        
        result = {
            'success': success,
            'final_menu': final_menu,
            'description_method': 'parallel_worker_processing',
            'total_items': total_items,
            'categories_processed': len(final_menu),
            'failed_categories': failed_categories if failed_categories else None,
            'parallel_processing': True,
            'processing_time': time.time()
        }
        
        logger.info(f"Parallel description generation completed: {len(final_menu)} categories, {len(failed_categories)} failures")
        
        return result
        
    except Exception as e:
        logger.error(f"Parallel menu description generation failed: {str(e)}")
        
        self.update_state(
            state='FAILURE',
            meta={
                'stage': 'menu_description_parallel',
                'error': str(e),
                'status': 'failed',
                'exc_type': type(e).__name__,
                'exc_module': type(e).__module__
            }
        )
        
        return {
            'success': False,
            'error': f"Parallel description error: {str(e)}",
            'description_method': 'parallel_worker_failed',
            'final_menu': {}
        }

@celery_app.task(bind=True, name="add_descriptions_ultra_parallel")
def add_descriptions_ultra_parallel(self, translated_data: Dict, session_id: str = None):
    """
    チャンクレベルでの完全並列詳細説明追加（最高速版）
    
    Args:
        translated_data: 翻訳済みメニューデータ
        session_id: セッションID
        
    Returns:
        Dict: 詳細説明追加結果
    """
    try:
        from app.core.config import settings
        
        # 進行状況更新
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'ultra_parallel_description',
                'progress': 0,
                'status': 'starting',
                'total_categories': len(translated_data)
            }
        )
        
        logger.info(f"Starting ULTRA parallel description generation: {len(translated_data)} categories")
        
        # 全チャンクを一度に並列処理するためのタスクリスト
        chunk_tasks = []
        chunk_info_map = {}  # タスクIDとカテゴリ・チャンク情報のマッピング
        
        chunk_size = getattr(settings, 'PROCESSING_CHUNK_SIZE', 3)
        
        for category_name, translated_items in translated_data.items():
            if not translated_items:
                continue
                
            # カテゴリをチャンクに分割
            chunks = []
            for i in range(0, len(translated_items), chunk_size):
                chunk = translated_items[i:i + chunk_size]
                chunk_number = (i // chunk_size) + 1
                total_chunks = (len(translated_items) + chunk_size - 1) // chunk_size
                chunks.append((chunk, chunk_number, total_chunks))
            
            # 各チャンクに対してワーカータスクを作成
            for chunk_items, chunk_number, total_chunks in chunks:
                chunk_info = {
                    'chunk_number': chunk_number,
                    'total_chunks': total_chunks
                }
                task = add_descriptions_to_chunk.delay(category_name, chunk_items, chunk_info, session_id)
                chunk_tasks.append(task)
                chunk_info_map[task.id] = {
                    'category': category_name,
                    'chunk_number': chunk_number,
                    'total_chunks': total_chunks
                }
        
        logger.info(f"Created {len(chunk_tasks)} chunk tasks for ultra-parallel processing")
        
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'ultra_parallel_description',
                'progress': 10,
                'status': 'chunks_created',
                'total_chunks': len(chunk_tasks)
            }
        )
        
        # 全チャンクの完了を並列で待機
        final_menu = {}
        chunk_results = {}  # category -> {chunk_number -> result}
        failed_chunks = []
        
        for i, task in enumerate(chunk_tasks):
            try:
                # チャンク完了を待機
                result = task.get(timeout=180)  # 3分タイムアウト
                
                task_info = chunk_info_map.get(task.id, {})
                category = task_info.get('category', 'unknown')
                chunk_number = task_info.get('chunk_number', 0)
                
                if result['success']:
                    # カテゴリ別結果を整理
                    if category not in chunk_results:
                        chunk_results[category] = {}
                    chunk_results[category][chunk_number] = result['final_items']
                    logger.info(f"Chunk completed: {category} chunk {chunk_number}")
                else:
                    failed_chunks.append({
                        'category': category,
                        'chunk_number': chunk_number,
                        'error': result.get('error', 'Unknown error')
                    })
                    logger.warning(f"Chunk failed: {category} chunk {chunk_number}")
                
            except Exception as e:
                task_info = chunk_info_map.get(task.id, {})
                category = task_info.get('category', 'unknown')
                chunk_number = task_info.get('chunk_number', 0)
                
                failed_chunks.append({
                    'category': category,
                    'chunk_number': chunk_number,
                    'error': f"Task execution failed: {str(e)}"
                })
                logger.error(f"Chunk task failed: {category} chunk {chunk_number}: {str(e)}")
            
            # 進行状況更新
            progress = 10 + int(((i + 1) / len(chunk_tasks)) * 80)
            self.update_state(
                state='PROGRESS',
                meta={
                    'stage': 'ultra_parallel_description',
                    'progress': progress,
                    'status': 'collecting_chunk_results',
                    'completed_chunks': i + 1,
                    'total_chunks': len(chunk_tasks)
                }
            )
        
        # チャンク結果をカテゴリごとに統合
        total_items = 0
        for category_name, translated_items in translated_data.items():
            if category_name in chunk_results:
                # チャンク番号順にソートして結合
                category_chunks = chunk_results[category_name]
                sorted_chunks = sorted(category_chunks.items())
                
                category_items = []
                for chunk_number, chunk_items in sorted_chunks:
                    category_items.extend(chunk_items)
                
                final_menu[category_name] = category_items
                total_items += len(category_items)
            else:
                # 失敗した場合はフォールバック
                fallback_items = []
                for item in translated_items:
                    fallback_items.append({
                        "japanese_name": item.get("japanese_name", "N/A"),
                        "english_name": item.get("english_name", "N/A"),
                        "description": "Detailed description currently unavailable.",
                        "price": item.get("price", "")
                    })
                final_menu[category_name] = fallback_items
                total_items += len(fallback_items)
        
        # 最終結果
        success = len(failed_chunks) == 0
        
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'ultra_parallel_description',
                'progress': 100,
                'status': 'completed',
                'total_chunks_processed': len(chunk_tasks),
                'failed_chunks': len(failed_chunks)
            }
        )
        
        result = {
            'success': success,
            'final_menu': final_menu,
            'description_method': 'ultra_parallel_worker_processing',
            'total_items': total_items,
            'categories_processed': len(final_menu),
            'total_chunks_processed': len(chunk_tasks),
            'failed_chunks': failed_chunks if failed_chunks else None,
            'ultra_parallel_processing': True,
            'processing_time': time.time()
        }
        
        logger.info(f"Ultra-parallel description generation completed: {len(final_menu)} categories, {len(chunk_tasks)} chunks, {len(failed_chunks)} failures")
        
        return result
        
    except Exception as e:
        logger.error(f"Ultra-parallel description generation failed: {str(e)}")
        
        self.update_state(
            state='FAILURE',
            meta={
                'stage': 'ultra_parallel_description',
                'error': str(e),
                'status': 'failed'
            }
        )
        
        return {
            'success': False,
            'error': f"Ultra-parallel description error: {str(e)}",
            'description_method': 'ultra_parallel_worker_failed',
            'final_menu': {}
        } 
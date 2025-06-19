#!/usr/bin/env python3
"""
Stage 2 カテゴライズ並列化 Celeryタスク

Stage 2カテゴライズの並列化を実現するワーカータスク群
- テキスト分割並列処理（チャンク並列カテゴライズ）
- 階層的カテゴライズ（粗分類→詳細分類）
- 複数ワーカー並列実行
- 結果統合・重複排除
- エラー時の自動フォールバック
"""

import time
import asyncio
import logging
import re
from typing import Dict, List, Any, Optional, Tuple

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

@celery_app.task(bind=True, name="categorize_text_chunk")
def categorize_text_chunk(self, text_chunk: str, chunk_info: Dict, session_id: str = None):
    """
    テキストチャンクをカテゴライズするワーカータスク
    
    Args:
        text_chunk: 分割されたメニューテキストチャンク
        chunk_info: チャンク情報（index, total_chunks等）
        session_id: セッションID
        
    Returns:
        Dict: カテゴライズ結果
    """
    try:
        chunk_index = chunk_info.get('index', 0)
        total_chunks = chunk_info.get('total_chunks', 1)
        
        # 進行状況更新
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'categorization_chunk',
                'chunk_index': chunk_index,
                'total_chunks': total_chunks,
                'progress': 0,
                'status': 'starting',
                'text_length': len(text_chunk)
            }
        )
        
        logger.info(f"Starting categorization for chunk {chunk_index + 1}/{total_chunks} ({len(text_chunk)} chars)")
        
        # OpenAIカテゴライズサービスを使用
        from app.services.category.openai import OpenAICategoryService
        
        openai_service = OpenAICategoryService()
        
        if not openai_service.is_available():
            raise Exception("OpenAI categorization service not available")
        
        # チャンクカテゴライズ実行
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'categorization_chunk',
                'chunk_index': chunk_index,
                'progress': 25,
                'status': 'processing',
                'engine': 'openai_function_calling'
            }
        )
        
        result = await_sync(openai_service.categorize_menu(text_chunk, session_id))
        
        # 完了
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'categorization_chunk',
                'chunk_index': chunk_index,
                'progress': 100,
                'status': 'completed'
            }
        )
        
        response = {
            'success': result.success,
            'categories': result.categories if result.success else {},
            'uncategorized': result.uncategorized if result.success else [],
            'error': result.error if not result.success else None,
            'chunk_info': chunk_info,
            'chunk_index': chunk_index,
            'total_chunks': total_chunks,
            'text_length': len(text_chunk),
            'processing_time': time.time(),
            'categorization_method': 'chunk_parallel_openai',
            'metadata': result.metadata
        }
        
        if result.success:
            total_items = sum(len(items) for items in result.categories.values())
            logger.info(f"Chunk {chunk_index + 1}/{total_chunks} completed: {total_items} items categorized")
        else:
            logger.warning(f"Chunk {chunk_index + 1}/{total_chunks} failed: {result.error}")
        
        return response
        
    except Exception as e:
        logger.error(f"Categorization chunk failed: {str(e)}")
        
        # エラー状態更新
        self.update_state(
            state='FAILURE',
            meta={
                'stage': 'categorization_chunk',
                'chunk_index': chunk_info.get('index', 0),
                'error': str(e),
                'status': 'failed',
                'exc_type': type(e).__name__,
                'exc_module': type(e).__module__
            }
        )
        
        return {
            'success': False,
            'categories': {},
            'uncategorized': [],
            'error': str(e),
            'chunk_info': chunk_info,
            'chunk_index': chunk_info.get('index', 0),
            'total_chunks': chunk_info.get('total_chunks', 1),
            'text_length': len(text_chunk) if text_chunk else 0,
            'processing_time': time.time(),
            'categorization_method': 'chunk_parallel_openai_failed'
        }

@celery_app.task(bind=True, name="hierarchical_categorize_coarse")
def hierarchical_categorize_coarse(self, extracted_text: str, session_id: str = None):
    """
    階層的カテゴライズの粗分類ワーカータスク
    
    Args:
        extracted_text: 抽出されたメニューテキスト
        session_id: セッションID
        
    Returns:
        Dict: 粗分類結果
    """
    try:
        # 進行状況更新
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'hierarchical_coarse',
                'progress': 0,
                'status': 'starting',
                'text_length': len(extracted_text)
            }
        )
        
        logger.info(f"Starting hierarchical coarse categorization ({len(extracted_text)} chars)")
        
        # 粗分類用プロンプトでOpenAI実行
        from app.services.category.openai import OpenAICategoryService
        
        openai_service = OpenAICategoryService()
        
        if not openai_service.is_available():
            raise Exception("OpenAI categorization service not available")
        
        # 粗分類プロンプト（大まかな分類のみ）
        coarse_prompt = f"""以下の日本語レストランメニューテキストを大まかに分類してください。
細かい分類は次の段階で行うので、ここでは大カテゴリのみ行ってください。

テキスト:
{extracted_text}

大分類要件:
1. 料理を大まかなカテゴリに分類（前菜系、メイン系、ドリンク系、デザート系）
2. 料理名の抽出は簡単に
3. 価格があれば抽出
4. 不明なものはuncategorizedに
5. 詳細分類は後で行うので、速度重視
"""
        
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'hierarchical_coarse',
                'progress': 30,
                'status': 'processing_coarse_classification'
            }
        )
        
        # OpenAIサービスの categorize_menu を直接使用するが、プロンプトを調整
        # ここでは簡易的に元のメソッドを使用
        result = await_sync(openai_service.categorize_menu(coarse_prompt, session_id))
        
        # 完了
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'hierarchical_coarse',
                'progress': 100,
                'status': 'completed'
            }
        )
        
        response = {
            'success': result.success,
            'coarse_categories': result.categories if result.success else {},
            'uncategorized': result.uncategorized if result.success else [],
            'error': result.error if not result.success else None,
            'processing_time': time.time(),
            'categorization_method': 'hierarchical_coarse_openai',
            'categorization_level': 'coarse',
            'metadata': result.metadata
        }
        
        if result.success:
            total_items = sum(len(items) for items in result.categories.values())
            logger.info(f"Hierarchical coarse categorization completed: {total_items} items in {len(result.categories)} categories")
        else:
            logger.warning(f"Hierarchical coarse categorization failed: {result.error}")
        
        return response
        
    except Exception as e:
        logger.error(f"Hierarchical coarse categorization failed: {str(e)}")
        
        # エラー状態更新
        self.update_state(
            state='FAILURE',
            meta={
                'stage': 'hierarchical_coarse',
                'error': str(e),
                'status': 'failed',
                'exc_type': type(e).__name__,
                'exc_module': type(e).__module__
            }
        )
        
        return {
            'success': False,
            'coarse_categories': {},
            'uncategorized': [],
            'error': str(e),
            'processing_time': time.time(),
            'categorization_method': 'hierarchical_coarse_openai_failed'
        }

@celery_app.task(bind=True, name="hierarchical_categorize_detailed")
def hierarchical_categorize_detailed(self, coarse_categories: Dict, session_id: str = None):
    """
    階層的カテゴライズの詳細分類ワーカータスク
    
    Args:
        coarse_categories: 粗分類結果
        session_id: セッションID
        
    Returns:
        Dict: 詳細分類結果
    """
    try:
        # 進行状況更新
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'hierarchical_detailed',
                'progress': 0,
                'status': 'starting',
                'coarse_categories_count': len(coarse_categories)
            }
        )
        
        logger.info(f"Starting hierarchical detailed categorization for {len(coarse_categories)} coarse categories")
        
        # 各粗分類カテゴリを詳細分類
        detailed_categories = {}
        failed_categories = []
        
        from app.services.category.openai import OpenAICategoryService
        openai_service = OpenAICategoryService()
        
        if not openai_service.is_available():
            raise Exception("OpenAI categorization service not available")
        
        for i, (category_name, items) in enumerate(coarse_categories.items()):
            if not items:  # 空のカテゴリはスキップ
                continue
                
            try:
                # 進行状況更新
                progress = 10 + int((i / len(coarse_categories)) * 80)
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'stage': 'hierarchical_detailed',
                        'progress': progress,
                        'status': 'processing_detailed_classification',
                        'current_category': category_name,
                        'category_items': len(items)
                    }
                )
                
                # カテゴリアイテムを詳細分類用テキストに変換
                items_text = "\n".join([
                    f"- {item.get('name', str(item))} {item.get('price', '')}" if isinstance(item, dict) else f"- {item}"
                    for item in items
                ])
                
                detailed_prompt = f"""以下の{category_name}カテゴリのアイテムをより詳細に分類してください。

カテゴリ: {category_name}
アイテム:
{items_text}

詳細分類要件:
1. より具体的なサブカテゴリに分類
2. 料理名・価格の精度向上
3. 説明があれば抽出
4. 日本語のまま処理
"""
                
                # 詳細分類実行
                result = await_sync(openai_service.categorize_menu(detailed_prompt, session_id))
                
                if result.success:
                    # 詳細分類結果をマージ
                    detailed_categories.update(result.categories)
                    logger.info(f"Detailed categorization completed for {category_name}: {len(result.categories)} subcategories")
                else:
                    # 失敗時は元のカテゴリを保持
                    detailed_categories[category_name] = items
                    failed_categories.append({
                        'category': category_name,
                        'error': result.error
                    })
                    logger.warning(f"Detailed categorization failed for {category_name}, keeping original")
                
            except Exception as e:
                # カテゴリ個別のエラー
                detailed_categories[category_name] = items
                failed_categories.append({
                    'category': category_name,
                    'error': str(e)
                })
                logger.error(f"Detailed categorization error for {category_name}: {str(e)}")
        
        # 完了
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'hierarchical_detailed',
                'progress': 100,
                'status': 'completed'
            }
        )
        
        response = {
            'success': len(failed_categories) == 0,
            'detailed_categories': detailed_categories,
            'failed_categories': failed_categories if failed_categories else None,
            'processing_time': time.time(),
            'categorization_method': 'hierarchical_detailed_openai',
            'categorization_level': 'detailed',
            'total_categories': len(detailed_categories),
            'failed_count': len(failed_categories)
        }
        
        total_items = sum(len(items) for items in detailed_categories.values())
        logger.info(f"Hierarchical detailed categorization completed: {total_items} items in {len(detailed_categories)} categories")
        
        return response
        
    except Exception as e:
        logger.error(f"Hierarchical detailed categorization failed: {str(e)}")
        
        # エラー状態更新
        self.update_state(
            state='FAILURE',
            meta={
                'stage': 'hierarchical_detailed',
                'error': str(e),
                'status': 'failed',
                'exc_type': type(e).__name__,
                'exc_module': type(e).__module__
            }
        )
        
        return {
            'success': False,
            'detailed_categories': {},
            'failed_categories': [],
            'error': str(e),
            'processing_time': time.time(),
            'categorization_method': 'hierarchical_detailed_openai_failed'
        }

@celery_app.task(bind=True, name="categorize_menu_parallel")
def categorize_menu_parallel(self, extracted_text: str, session_id: str = None, options: Dict = None):
    """
    メニュー全体を並列カテゴライズする統合ワーカータスク
    
    Args:
        extracted_text: 抽出されたメニューテキスト
        session_id: セッションID
        options: 処理オプション
        
    Returns:
        Dict: カテゴライズ結果（既存形式と互換）
    """
    try:
        start_time = time.time()
        options = options or {}
        
        # 進行状況更新
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'categorization_parallel',
                'progress': 0,
                'status': 'starting',
                'text_length': len(extracted_text)
            }
        )
        
        logger.info(f"Starting parallel menu categorization ({len(extracted_text)} chars)")
        
        # 並列化戦略の決定
        from app.core.config import settings
        
        parallel_mode = options.get('parallel_mode', settings.PARALLEL_CATEGORIZATION_MODE)
        use_text_chunking = (
            settings.ENABLE_TEXT_CHUNKING and 
            len(extracted_text) >= settings.CATEGORIZATION_TEXT_THRESHOLD
        )
        
        if use_text_chunking and parallel_mode in ["smart", "chunk"]:
            # テキスト分割並列処理
            self.update_state(
                state='PROGRESS',
                meta={
                    'stage': 'categorization_parallel',
                    'progress': 10,
                    'status': 'text_chunking_mode',
                    'parallel_mode': 'text_chunking'
                }
            )
            
            result = _execute_text_chunking_categorization(
                self, extracted_text, session_id, options
            )
            
        else:
            # フォールバック：従来の単一処理
            self.update_state(
                state='PROGRESS',
                meta={
                    'stage': 'categorization_parallel',
                    'progress': 10,
                    'status': 'sequential_fallback',
                    'parallel_mode': 'sequential'
                }
            )
            
            result = _execute_sequential_categorization(
                self, extracted_text, session_id, options
            )
        
        # 最終結果構築
        total_time = time.time() - start_time
        
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'categorization_parallel',
                'progress': 100,
                'status': 'completed',
                'total_processing_time': total_time
            }
        )
        
        final_result = {
            'success': result['success'],
            'categories': result.get('categories', {}),
            'uncategorized': result.get('uncategorized', []),
            'categorization_method': result.get('categorization_method', 'parallel_worker_processing'),
            'parallel_processing': True,
            'parallel_mode': result.get('parallel_mode', 'unknown'),
            'total_processing_time': total_time,
            'text_length': len(extracted_text),
            'error': result.get('error') if not result['success'] else None,
            'metadata': result.get('metadata', {})
        }
        
        if result['success']:
            total_items = sum(len(items) for items in result.get('categories', {}).values())
            final_result.update({
                'total_items': total_items,
                'total_categories': len(result.get('categories', {})),
                'uncategorized_count': len(result.get('uncategorized', []))
            })
            
            logger.info(f"Parallel categorization completed in {total_time:.2f}s: {total_items} items, {len(result.get('categories', {}))} categories")
        
        return final_result
        
    except Exception as e:
        logger.error(f"Parallel menu categorization failed: {str(e)}")
        
        self.update_state(
            state='FAILURE',
            meta={
                'stage': 'categorization_parallel',
                'error': str(e),
                'status': 'failed'
            }
        )
        
        return {
            'success': False,
            'categories': {},
            'uncategorized': [],
            'error': f"Parallel categorization error: {str(e)}",
            'categorization_method': 'parallel_worker_failed',
            'parallel_processing': True,
            'total_processing_time': time.time() - start_time if 'start_time' in locals() else 0
        }

def _execute_text_chunking_categorization(task_self, extracted_text: str, session_id: str, options: Dict) -> Dict:
    """テキスト分割並列カテゴライズを実行"""
    try:
        from app.core.config import settings
        
        # テキストをチャンクに分割
        chunk_size = options.get('chunk_size', settings.CATEGORIZATION_CHUNK_SIZE)
        chunks = _split_text_into_chunks(extracted_text, chunk_size)
        
        logger.info(f"Text split into {len(chunks)} chunks for parallel processing")
        
        # 各チャンクを並列処理
        chunk_tasks = []
        for i, chunk in enumerate(chunks):
            chunk_info = {
                'index': i,
                'total_chunks': len(chunks),
                'chunk_size': len(chunk)
            }
            
            task = categorize_text_chunk.delay(chunk, chunk_info, session_id)
            chunk_tasks.append((i, task))
        
        task_self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'categorization_parallel',
                'progress': 30,
                'status': 'processing_chunks',
                'chunks_created': len(chunk_tasks)
            }
        )
        
        # チャンク結果を収集
        chunk_results = []
        for i, task in chunk_tasks:
            try:
                result = task.get(timeout=settings.CATEGORIZATION_TIMEOUT)
                chunk_results.append(result)
                logger.info(f"Chunk {i + 1}/{len(chunks)} completed")
            except Exception as e:
                logger.error(f"Chunk {i + 1}/{len(chunks)} failed: {str(e)}")
                chunk_results.append({
                    'success': False,
                    'categories': {},
                    'uncategorized': [],
                    'error': str(e),
                    'chunk_index': i
                })
        
        # 結果を統合
        merged_categories = {}
        merged_uncategorized = []
        failed_chunks = []
        
        for result in chunk_results:
            if result['success']:
                # カテゴリをマージ
                for category_name, items in result['categories'].items():
                    if category_name not in merged_categories:
                        merged_categories[category_name] = []
                    merged_categories[category_name].extend(items)
                
                # uncategorizedをマージ
                merged_uncategorized.extend(result['uncategorized'])
            else:
                failed_chunks.append(result)
        
        # 重複排除
        for category_name in merged_categories:
            merged_categories[category_name] = _remove_duplicate_items(merged_categories[category_name])
        
        merged_uncategorized = list(set(merged_uncategorized))
        
        return {
            'success': len(failed_chunks) == 0,
            'categories': merged_categories,
            'uncategorized': merged_uncategorized,
            'categorization_method': 'text_chunking_parallel',
            'parallel_mode': 'text_chunking',
            'chunks_processed': len(chunk_results),
            'failed_chunks': len(failed_chunks),
            'metadata': {
                'chunk_count': len(chunks),
                'successful_chunks': len(chunk_results) - len(failed_chunks),
                'failed_chunks': failed_chunks if failed_chunks else None
            }
        }
        
    except Exception as e:
        logger.error(f"Text chunking categorization failed: {str(e)}")
        raise

def _execute_sequential_categorization(task_self, extracted_text: str, session_id: str, options: Dict) -> Dict:
    """従来の順次カテゴライズを実行（フォールバック）"""
    try:
        from app.services.category.openai import OpenAICategoryService
        
        openai_service = OpenAICategoryService()
        
        if not openai_service.is_available():
            raise Exception("OpenAI categorization service not available")
        
        result = await_sync(openai_service.categorize_menu(extracted_text, session_id))
        
        return {
            'success': result.success,
            'categories': result.categories if result.success else {},
            'uncategorized': result.uncategorized if result.success else [],
            'error': result.error if not result.success else None,
            'categorization_method': 'sequential_fallback',
            'parallel_mode': 'sequential',
            'metadata': result.metadata
        }
        
    except Exception as e:
        logger.error(f"Sequential categorization failed: {str(e)}")
        raise

def _split_text_into_chunks(text: str, chunk_size: int) -> List[str]:
    """テキストをチャンクに分割"""
    # 行ごとに分割してからチャンクサイズに基づいて結合
    lines = text.split('\n')
    chunks = []
    current_chunk = []
    current_size = 0
    
    for line in lines:
        line_size = len(line)
        
        if current_size + line_size > chunk_size * 200 and current_chunk:  # 約200文字/チャンク
            chunks.append('\n'.join(current_chunk))
            current_chunk = [line]
            current_size = line_size
        else:
            current_chunk.append(line)
            current_size += line_size
    
    if current_chunk:
        chunks.append('\n'.join(current_chunk))
    
    return chunks

def _remove_duplicate_items(items: List) -> List:
    """アイテムリストから重複を除去"""
    seen = set()
    unique_items = []
    
    for item in items:
        if isinstance(item, dict):
            item_key = item.get('name', str(item))
        else:
            item_key = str(item)
        
        if item_key not in seen:
            seen.add(item_key)
            unique_items.append(item)
    
    return unique_items 
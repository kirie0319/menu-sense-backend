#!/usr/bin/env python3
"""
完全パイプライン並列化 Celeryタスク

Stage 1-5全体の完全並列化を実現するワーカータスク群
- 完全パイプライン処理（Stage 1→2→3→4→5の最適化された連続実行）
- カテゴリレベルパイプライン処理（カテゴリごとのStage 3→4→5並列実行）
- Stage間オーバーラップ処理（Stage 3完了→即座Stage 5開始）
- 段階的結果ストリーミング（各Stage完了ごとの部分結果配信）
- 複数画像並列パイプライン（複数画像の同時パイプライン実行）
"""

import time
import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

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

@celery_app.task(bind=True, name="full_pipeline_process")
def full_pipeline_process(self, image_path: str, session_id: str = None, options: Dict = None):
    """
    完全パイプライン処理ワーカー（Stage 1-5全体最適化）
    
    Args:
        image_path: 画像ファイルパス
        session_id: セッションID
        options: 処理オプション
        
    Returns:
        Dict: 全Stage完了結果
    """
    try:
        start_time = time.time()
        options = options or {}
        
        # 初期進行状況更新
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'pipeline_full',
                'progress': 0,
                'status': 'initializing',
                'pipeline_mode': 'full_parallel_optimization',
                'current_stage': 1,
                'total_stages': 5
            }
        )
        
        logger.info(f"🚀 Starting FULL PIPELINE processing for: {image_path}")
        
        # パイプライン実行結果を格納
        pipeline_results = {}
        pipeline_metadata = {
            'pipeline_enabled': True,
            'pipeline_mode': 'full_parallel_optimization',
            'start_time': start_time,
            'stage_timing': {},
            'optimizations_applied': []
        }
        
        # === Stage 1: OCR (並列処理版) ===
        stage1_start = time.time()
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'pipeline_full',
                'progress': 5,
                'status': 'stage1_ocr',
                'current_stage': 1,
                'stage_name': 'OCR (Parallel Multi-Engine)'
            }
        )
        
        from app.workflows.stages import stage1_ocr_gemini_exclusive
        stage1_result = await_sync(stage1_ocr_gemini_exclusive(image_path, session_id))
        
        if not stage1_result["success"]:
            raise Exception(f"Stage 1 OCR failed: {stage1_result.get('error', 'Unknown error')}")
        
        pipeline_results['stage1'] = stage1_result
        pipeline_metadata['stage_timing']['stage1'] = time.time() - stage1_start
        pipeline_metadata['optimizations_applied'].append('parallel_ocr')
        
        extracted_text = stage1_result["extracted_text"]
        if not extracted_text.strip():
            return {
                'success': False,
                'error': 'No text extracted from image',
                'pipeline_results': pipeline_results,
                'pipeline_metadata': pipeline_metadata
            }
        
        # === Stage 2: カテゴライズ ===
        stage2_start = time.time()
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'pipeline_full',
                'progress': 25,
                'status': 'stage2_categorize',
                'current_stage': 2,
                'stage_name': 'Categorization (OpenAI Function Calling)'
            }
        )
        
        from app.workflows.stages import stage2_categorize_openai_exclusive
        stage2_result = await_sync(stage2_categorize_openai_exclusive(extracted_text, session_id))
        
        if not stage2_result["success"]:
            raise Exception(f"Stage 2 Categorization failed: {stage2_result.get('error', 'Unknown error')}")
        
        pipeline_results['stage2'] = stage2_result
        pipeline_metadata['stage_timing']['stage2'] = time.time() - stage2_start
        
        categorized_data = stage2_result["categories"]
        
        # カテゴリ数とアイテム数を確認してパイプライン戦略を決定
        total_categories = len(categorized_data)
        total_items = sum(len(items) for items in categorized_data.values())
        
        # パイプライン戦略判定
        from app.core.config import settings
        use_category_pipeline = (
            settings.ENABLE_CATEGORY_PIPELINING and 
            total_categories >= settings.MIN_CATEGORIES_FOR_OVERLAP and
            total_items >= settings.PIPELINE_ITEM_THRESHOLD
        )
        
        use_stage3_to_stage5_overlap = (
            settings.STAGE3_TO_STAGE5_OVERLAP and
            total_items >= 5
        )
        
        if use_category_pipeline:
            pipeline_metadata['optimizations_applied'].append('category_level_pipelining')
            logger.info(f"📋 Using CATEGORY LEVEL PIPELINING: {total_categories} categories, {total_items} items")
            
            # カテゴリレベルパイプライン処理を実行
            pipeline_stage345_result = _execute_category_level_pipeline(
                self, categorized_data, session_id, pipeline_metadata
            )
            
        else:
            pipeline_metadata['optimizations_applied'].append('sequential_stage_processing')
            logger.info(f"📋 Using SEQUENTIAL PROCESSING: {total_categories} categories, {total_items} items")
            
            # 逐次Stage実行
            pipeline_stage345_result = _execute_sequential_stages(
                self, categorized_data, session_id, pipeline_metadata, use_stage3_to_stage5_overlap
            )
        
        # パイプライン結果を統合
        pipeline_results.update(pipeline_stage345_result['results'])
        pipeline_metadata.update(pipeline_stage345_result['metadata'])
        
        # 最終結果構築
        total_time = time.time() - start_time
        pipeline_metadata['total_processing_time'] = total_time
        
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'pipeline_full',
                'progress': 100,
                'status': 'completed',
                'total_processing_time': total_time,
                'optimizations_applied': pipeline_metadata['optimizations_applied']
            }
        )
        
        final_result = {
            'success': True,
            'pipeline_processing': True,
            'pipeline_mode': 'full_parallel_optimization',
            'total_processing_time': total_time,
            'total_categories': total_categories,
            'total_items': total_items,
            'optimizations_applied': pipeline_metadata['optimizations_applied'],
            
            # 各Stage結果
            'extracted_text': extracted_text,
            'categories': categorized_data,
            'translated_categories': pipeline_results.get('stage3', {}).get('translated_categories', {}),
            'final_menu': pipeline_results.get('stage4', {}).get('final_menu', {}),
            'images_generated': pipeline_results.get('stage5', {}).get('images_generated', {}),
            
            # メタデータ
            'pipeline_metadata': pipeline_metadata,
            'stage_timing': pipeline_metadata['stage_timing']
        }
        
        logger.info(f"🎉 FULL PIPELINE completed in {total_time:.2f}s: {total_items} items, {len(pipeline_metadata['optimizations_applied'])} optimizations")
        
        return final_result
        
    except Exception as e:
        logger.error(f"Full pipeline processing failed: {str(e)}")
        
        self.update_state(
            state='FAILURE',
            meta={
                'stage': 'pipeline_full',
                'error': str(e),
                'status': 'failed',
                'exc_type': type(e).__name__,
                'exc_module': type(e).__module__
            }
        )
        
        return {
            'success': False,
            'error': f"Full pipeline error: {str(e)}",
            'pipeline_processing': True,
            'pipeline_mode': 'full_parallel_optimization_failed'
        }

def _execute_category_level_pipeline(task_self, categorized_data: Dict, session_id: str, pipeline_metadata: Dict) -> Dict:
    """カテゴリレベルパイプライン処理を実行"""
    try:
        start_time = time.time()
        
        # === Stage 3: 並列翻訳 ===
        stage3_start = time.time()
        task_self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'pipeline_category',
                'progress': 35,
                'status': 'stage3_parallel_translation',
                'current_stage': 3,
                'stage_name': 'Parallel Translation'
            }
        )
        
        from app.workflows.stages import stage3_translate_with_fallback
        stage3_result = await_sync(stage3_translate_with_fallback(categorized_data, session_id))
        
        if not stage3_result["success"]:
            raise Exception(f"Stage 3 Translation failed: {stage3_result.get('error', 'Unknown error')}")
        
        pipeline_metadata['stage_timing']['stage3'] = time.time() - stage3_start
        translated_categories = stage3_result["translated_categories"]
        
        # === カテゴリレベル並列パイプライン: Stage 4 & 5 ===
        category_pipeline_tasks = []
        
        for category_name, items in translated_categories.items():
            if items:  # 空でないカテゴリのみ
                # カテゴリごとにStage 4→5パイプラインタスクを作成
                task = category_stage45_pipeline.delay(
                    category_name, {category_name: items}, session_id
                )
                category_pipeline_tasks.append((category_name, task))
        
        task_self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'pipeline_category',
                'progress': 55,
                'status': 'stage45_category_pipeline',
                'pipeline_tasks': len(category_pipeline_tasks),
                'stage_name': 'Category Level Pipeline (Stage 4+5)'
            }
        )
        
        # カテゴリパイプライン結果を収集
        final_menu = {}
        images_generated = {}
        category_failures = []
        
        for category_name, task in category_pipeline_tasks:
            try:
                result = task.get(timeout=300)  # 5分タイムアウト
                
                if result['success']:
                    final_menu.update(result['final_menu'])
                    images_generated.update(result['images_generated'])
                    logger.info(f"✅ Category pipeline completed: {category_name}")
                else:
                    category_failures.append({
                        'category': category_name,
                        'error': result.get('error', 'Unknown error')
                    })
                    logger.warning(f"⚠️ Category pipeline failed: {category_name}")
                    
            except Exception as e:
                category_failures.append({
                    'category': category_name,
                    'error': f"Task execution failed: {str(e)}"
                })
                logger.error(f"❌ Category pipeline task failed: {category_name}: {str(e)}")
        
        pipeline_metadata['stage_timing']['stage45_pipeline'] = time.time() - start_time
        pipeline_metadata['category_failures'] = category_failures
        
        return {
            'results': {
                'stage3': stage3_result,
                'stage4': {
                    'success': len(category_failures) == 0,
                    'final_menu': final_menu,
                    'category_failures': category_failures
                },
                'stage5': {
                    'success': len(images_generated) > 0,
                    'images_generated': images_generated
                }
            },
            'metadata': pipeline_metadata
        }
        
    except Exception as e:
        logger.error(f"Category level pipeline failed: {str(e)}")
        raise

def _execute_sequential_stages(task_self, categorized_data: Dict, session_id: str, pipeline_metadata: Dict, use_overlap: bool) -> Dict:
    """逐次Stage処理（必要に応じてStage 3→5オーバーラップ）"""
    try:
        # === Stage 3: 並列翻訳 ===
        stage3_start = time.time()
        task_self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'pipeline_sequential',
                'progress': 35,
                'status': 'stage3_parallel_translation',
                'current_stage': 3
            }
        )
        
        from app.workflows.stages import stage3_translate_with_fallback
        stage3_result = await_sync(stage3_translate_with_fallback(categorized_data, session_id))
        
        if not stage3_result["success"]:
            raise Exception(f"Stage 3 Translation failed: {stage3_result.get('error', 'Unknown error')}")
        
        pipeline_metadata['stage_timing']['stage3'] = time.time() - stage3_start
        translated_categories = stage3_result["translated_categories"]
        
        # Stage 3完了→即座にStage 5開始の処理（オーバーラップ）
        stage5_task = None
        if use_overlap:
            pipeline_metadata['optimizations_applied'].append('stage3_to_stage5_overlap')
            
            try:
                # Stage 5を非同期で開始
                from app.workflows.stages import stage5_generate_images
                stage5_future = asyncio.create_task(stage5_generate_images(translated_categories, session_id))
                logger.info("🔄 Stage 5 started in parallel with Stage 4")
                
            except Exception as e:
                logger.warning(f"Failed to start Stage 5 in parallel: {str(e)}")
                stage5_future = None
        
        # === Stage 4: 並列詳細説明 ===
        stage4_start = time.time()
        task_self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'pipeline_sequential',
                'progress': 65,
                'status': 'stage4_parallel_description',
                'current_stage': 4
            }
        )
        
        from app.workflows.stages import stage4_add_descriptions
        stage4_result = await_sync(stage4_add_descriptions(translated_categories, session_id))
        
        if not stage4_result["success"]:
            raise Exception(f"Stage 4 Description failed: {stage4_result.get('error', 'Unknown error')}")
        
        pipeline_metadata['stage_timing']['stage4'] = time.time() - stage4_start
        final_menu = stage4_result["final_menu"]
        
        # === Stage 5: 画像生成 ===
        stage5_start = time.time()
        task_self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'pipeline_sequential',
                'progress': 85,
                'status': 'stage5_images',
                'current_stage': 5
            }
        )
        
        if use_overlap and 'stage5_future' in locals() and stage5_future:
            # オーバーラップStage 5の結果を取得
            try:
                stage5_result = await_sync(stage5_future)
                logger.info("✅ Overlapped Stage 5 completed")
                
            except Exception as e:
                logger.warning(f"Overlapped Stage 5 failed, falling back to sequential: {str(e)}")
                # フォールバック：通常のStage 5実行
                from app.workflows.stages import stage5_generate_images
                stage5_result = await_sync(stage5_generate_images(final_menu, session_id))
        
        else:
            # 通常のStage 5実行
            from app.workflows.stages import stage5_generate_images
            stage5_result = await_sync(stage5_generate_images(final_menu, session_id))
        
        pipeline_metadata['stage_timing']['stage5'] = time.time() - stage5_start
        
        return {
            'results': {
                'stage3': stage3_result,
                'stage4': stage4_result,
                'stage5': stage5_result
            },
            'metadata': pipeline_metadata
        }
        
    except Exception as e:
        logger.error(f"Sequential stages execution failed: {str(e)}")
        raise

@celery_app.task(bind=True, name="category_stage45_pipeline")
def category_stage45_pipeline(self, category_name: str, category_data: Dict, session_id: str = None):
    """
    単一カテゴリのStage 4→5パイプライン処理ワーカー
    
    Args:
        category_name: カテゴリ名
        category_data: カテゴリデータ {category_name: items}
        session_id: セッションID
        
    Returns:
        Dict: Stage 4+5完了結果
    """
    try:
        start_time = time.time()
        
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'category_pipeline',
                'category': category_name,
                'progress': 0,
                'status': 'starting_stage4'
            }
        )
        
        logger.info(f"🔄 Starting Category Pipeline for: {category_name}")
        
        # === Stage 4: カテゴリ詳細説明 ===
        from app.workflows.stages import stage4_add_descriptions
        stage4_result = await_sync(stage4_add_descriptions(category_data, session_id))
        
        if not stage4_result["success"]:
            raise Exception(f"Stage 4 failed for category {category_name}: {stage4_result.get('error', 'Unknown error')}")
        
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'category_pipeline',
                'category': category_name,
                'progress': 50,
                'status': 'starting_stage5'
            }
        )
        
        final_menu = stage4_result["final_menu"]
        
        # === Stage 5: カテゴリ画像生成 ===
        from app.workflows.stages import stage5_generate_images
        stage5_result = await_sync(stage5_generate_images(final_menu, session_id))
        
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'category_pipeline',
                'category': category_name,
                'progress': 100,
                'status': 'completed'
            }
        )
        
        total_time = time.time() - start_time
        
        result = {
            'success': True,
            'category': category_name,
            'final_menu': final_menu,
            'images_generated': stage5_result.get('images_generated', {}),
            'processing_time': total_time,
            'pipeline_mode': 'category_stage45_pipeline'
        }
        
        logger.info(f"✅ Category Pipeline completed: {category_name} in {total_time:.2f}s")
        
        return result
        
    except Exception as e:
        logger.error(f"Category pipeline failed for {category_name}: {str(e)}")
        
        self.update_state(
            state='FAILURE',
            meta={
                'stage': 'category_pipeline',
                'category': category_name,
                'error': str(e),
                'status': 'failed',
                'exc_type': type(e).__name__,
                'exc_module': type(e).__module__
            }
        )
        
        return {
            'success': False,
            'category': category_name,
            'error': f"Category pipeline error: {str(e)}",
            'pipeline_mode': 'category_stage45_pipeline_failed'
        }

@celery_app.task(bind=True, name="multiple_images_pipeline")
def multiple_images_pipeline(self, image_paths: List[str], session_id: str = None, options: Dict = None):
    """
    複数画像並列パイプライン処理ワーカー
    
    Args:
        image_paths: 画像ファイルパスのリスト
        session_id: セッションID
        options: 処理オプション
        
    Returns:
        Dict: 全画像パイプライン完了結果
    """
    try:
        start_time = time.time()
        options = options or {}
        
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'multi_image_pipeline',
                'progress': 0,
                'status': 'initializing',
                'total_images': len(image_paths),
                'pipeline_mode': 'multiple_images_parallel'
            }
        )
        
        logger.info(f"🚀 Starting MULTIPLE IMAGES PIPELINE: {len(image_paths)} images")
        
        # 画像ごとにフルパイプラインタスクを並列実行
        pipeline_tasks = []
        
        for i, image_path in enumerate(image_paths):
            task = full_pipeline_process.delay(image_path, f"{session_id}_img{i}", options)
            pipeline_tasks.append((f"image_{i}", image_path, task))
        
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'multi_image_pipeline',
                'progress': 10,
                'status': 'parallel_processing',
                'tasks_created': len(pipeline_tasks)
            }
        )
        
        # 全パイプライン結果を収集
        all_results = {}
        failed_images = []
        
        for image_name, image_path, task in pipeline_tasks:
            try:
                result = task.get(timeout=1200)  # 20分タイムアウト
                
                if result['success']:
                    all_results[image_name] = result
                    logger.info(f"✅ Image pipeline completed: {image_name}")
                else:
                    failed_images.append({
                        'image': image_name,
                        'path': image_path,
                        'error': result.get('error', 'Unknown error')
                    })
                    logger.warning(f"⚠️ Image pipeline failed: {image_name}")
                    
            except Exception as e:
                failed_images.append({
                    'image': image_name,
                    'path': image_path,
                    'error': f"Task execution failed: {str(e)}"
                })
                logger.error(f"❌ Image pipeline task failed: {image_name}: {str(e)}")
        
        total_time = time.time() - start_time
        
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'multi_image_pipeline',
                'progress': 100,
                'status': 'completed',
                'successful_images': len(all_results),
                'failed_images': len(failed_images)
            }
        )
        
        result = {
            'success': len(failed_images) == 0,
            'pipeline_processing': True,
            'pipeline_mode': 'multiple_images_parallel',
            'total_processing_time': total_time,
            'total_images': len(image_paths),
            'successful_images': len(all_results),
            'failed_images': len(failed_images),
            'all_results': all_results,
            'failed_images': failed_images if failed_images else None
        }
        
        logger.info(f"🎉 MULTIPLE IMAGES PIPELINE completed in {total_time:.2f}s: {len(all_results)}/{len(image_paths)} images")
        
        return result
        
    except Exception as e:
        logger.error(f"Multiple images pipeline failed: {str(e)}")
        
        self.update_state(
            state='FAILURE',
            meta={
                'stage': 'multi_image_pipeline',
                'error': str(e),
                'status': 'failed',
                'exc_type': type(e).__name__,
                'exc_module': type(e).__module__
            }
        )
        
        return {
            'success': False,
            'error': f"Multiple images pipeline error: {str(e)}",
            'pipeline_processing': True,
            'pipeline_mode': 'multiple_images_parallel_failed'
        } 
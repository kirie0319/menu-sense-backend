#!/usr/bin/env python3
"""
パイプライン統合サービス

完全パイプライン並列化の統合サービス:
- 完全パイプライン処理（Stage 1-5最適化）
- カテゴリレベルパイプライン処理
- Stage間オーバーラップ処理
- 段階的結果ストリーミング
- 適応的リソース配分
"""

import time
import logging
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass

# 設定とワーカーの取得
from app.core.config import settings

logger = logging.getLogger(__name__)

@dataclass
class PipelineResult:
    """パイプライン処理結果"""
    success: bool
    pipeline_mode: str
    total_processing_time: float
    total_categories: int
    total_items: int
    optimizations_applied: List[str]
    
    # 各Stage結果
    extracted_text: str
    categories: Dict
    translated_categories: Dict
    final_menu: Dict
    images_generated: Dict
    
    # メタデータ
    metadata: Dict
    error: Optional[str] = None

class PipelineProcessingService:
    """パイプライン統合処理サービス"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # パイプライン設定の読み込み
        self.pipeline_enabled = settings.ENABLE_FULL_PIPELINE_PARALLEL
        self.pipeline_mode = settings.PIPELINE_PARALLEL_MODE
        self.max_workers = settings.MAX_PIPELINE_WORKERS
        self.category_threshold = settings.PIPELINE_CATEGORY_THRESHOLD
        self.item_threshold = settings.PIPELINE_ITEM_THRESHOLD
        
        # 最適化フラグ
        self.early_stage5_enabled = settings.ENABLE_EARLY_STAGE5_START
        self.category_pipelining_enabled = settings.ENABLE_CATEGORY_PIPELINING
        self.streaming_enabled = settings.ENABLE_STREAMING_RESULTS
        
        self.logger.info("Pipeline Processing Service initialized:")
        self.logger.info(f"  - Pipeline enabled: {self.pipeline_enabled}")
        self.logger.info(f"  - Pipeline mode: {self.pipeline_mode}")
        self.logger.info(f"  - Max workers: {self.max_workers}")
        self.logger.info(f"  - Category threshold: {self.category_threshold}")
        self.logger.info(f"  - Item threshold: {self.item_threshold}")
    
    def is_available(self) -> bool:
        """パイプライン処理が利用可能かチェック"""
        try:
            # Celeryワーカーの確認
            from app.tasks.celery_app import celery_app
            
            # 基本設定の確認
            if not self.pipeline_enabled:
                return False
                
            # 依存サービスの確認
            from app.workflows.stages import (
                stage1_ocr_gemini_exclusive,
                stage2_categorize_openai_exclusive,
                stage3_translate_with_fallback,
                stage4_add_descriptions,
                stage5_generate_images
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Pipeline service availability check failed: {e}")
            return False
    
    async def process_full_pipeline(
        self, 
        image_path: str, 
        session_id: str = None, 
        options: Dict = None
    ) -> PipelineResult:
        """
        完全パイプライン処理を実行
        
        Args:
            image_path: 画像ファイルパス
            session_id: セッションID
            options: 処理オプション
            
        Returns:
            PipelineResult: パイプライン処理結果
        """
        start_time = time.time()
        options = options or {}
        
        try:
            self.logger.info(f"Starting full pipeline processing: {image_path}")
            
            # パイプライン戦略の決定
            pipeline_strategy = self._determine_pipeline_strategy(options)
            
            if pipeline_strategy == "worker_pipeline":
                # Celeryワーカーでパイプライン処理
                result = await self._execute_worker_pipeline(image_path, session_id, options)
                
            elif pipeline_strategy == "category_pipeline":
                # カテゴリレベルパイプライン処理
                result = await self._execute_category_pipeline(image_path, session_id, options)
                
            else:
                # 順次処理（フォールバック）
                result = await self._execute_sequential_pipeline(image_path, session_id, options)
            
            # 処理時間の記録
            total_time = time.time() - start_time
            
            if result.success:
                result.total_processing_time = total_time
                result.metadata['total_processing_time'] = total_time
                
                self.logger.info(f"Full pipeline completed in {total_time:.2f}s:")
                self.logger.info(f"  - Mode: {result.pipeline_mode}")
                self.logger.info(f"  - Categories: {result.total_categories}")
                self.logger.info(f"  - Items: {result.total_items}")
                self.logger.info(f"  - Optimizations: {', '.join(result.optimizations_applied)}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Full pipeline processing failed: {str(e)}")
            
            return PipelineResult(
                success=False,
                pipeline_mode="full_pipeline_failed",
                total_processing_time=time.time() - start_time,
                total_categories=0,
                total_items=0,
                optimizations_applied=[],
                extracted_text="",
                categories={},
                translated_categories={},
                final_menu={},
                images_generated={},
                metadata={"error": str(e)},
                error=str(e)
            )
    
    def _determine_pipeline_strategy(self, options: Dict) -> str:
        """パイプライン戦略を決定"""
        # 強制モードの確認
        if settings.FORCE_SEQUENTIAL_PIPELINE:
            return "sequential_pipeline"
        
        # オプションによる指定
        if options.get("force_worker_pipeline"):
            return "worker_pipeline"
        
        if options.get("force_category_pipeline"):
            return "category_pipeline"
        
        # パイプラインモードに基づく判定
        if self.pipeline_mode == "aggressive":
            return "worker_pipeline"
        elif self.pipeline_mode == "smart":
            return "category_pipeline"
        else:  # conservative
            return "sequential_pipeline"
    
    async def _execute_worker_pipeline(self, image_path: str, session_id: str, options: Dict) -> PipelineResult:
        """Celeryワーカーでパイプライン処理を実行"""
        try:
            from app.tasks.pipeline_tasks import full_pipeline_process
            
            # ワーカータスクを実行
            task = full_pipeline_process.delay(image_path, session_id, options)
            
            # 結果を待機（タイムアウト付き）
            result_data = task.get(timeout=settings.PIPELINE_TOTAL_TIMEOUT)
            
            if result_data['success']:
                return PipelineResult(
                    success=True,
                    pipeline_mode=result_data['pipeline_mode'],
                    total_processing_time=result_data['total_processing_time'],
                    total_categories=result_data['total_categories'],
                    total_items=result_data['total_items'],
                    optimizations_applied=result_data['optimizations_applied'],
                    extracted_text=result_data['extracted_text'],
                    categories=result_data['categories'],
                    translated_categories=result_data['translated_categories'],
                    final_menu=result_data['final_menu'],
                    images_generated=result_data['images_generated'],
                    metadata=result_data['pipeline_metadata']
                )
            else:
                raise Exception(result_data.get('error', 'Worker pipeline failed'))
                
        except Exception as e:
            self.logger.error(f"Worker pipeline execution failed: {str(e)}")
            raise
    
    async def _execute_category_pipeline(self, image_path: str, session_id: str, options: Dict) -> PipelineResult:
        """カテゴリレベルパイプライン処理を実行"""
        try:
            start_time = time.time()
            
            # Stage 1-2を実行してカテゴリデータを取得
            stage12_result = await self._execute_stage12(image_path, session_id)
            
            if not stage12_result['success']:
                raise Exception(f"Stage 1-2 failed: {stage12_result.get('error')}")
            
            categorized_data = stage12_result['categories']
            total_categories = len(categorized_data)
            total_items = sum(len(items) for items in categorized_data.values())
            
            # カテゴリパイプライン戦略の判定
            if (total_categories >= self.category_threshold and 
                total_items >= self.item_threshold):
                
                # カテゴリレベル並列パイプライン実行
                pipeline_result = await self._execute_parallel_category_stages(
                    categorized_data, session_id
                )
                
                optimizations = ['category_level_pipelining', 'parallel_stage_execution']
                pipeline_mode = 'category_parallel_pipeline'
                
            else:
                # 通常のStage 3-5実行
                pipeline_result = await self._execute_sequential_stages345(
                    categorized_data, session_id
                )
                
                optimizations = ['sequential_stage_execution']
                pipeline_mode = 'category_sequential_pipeline'
            
            return PipelineResult(
                success=pipeline_result['success'],
                pipeline_mode=pipeline_mode,
                total_processing_time=time.time() - start_time,
                total_categories=total_categories,
                total_items=total_items,
                optimizations_applied=optimizations,
                extracted_text=stage12_result['extracted_text'],
                categories=categorized_data,
                translated_categories=pipeline_result.get('translated_categories', {}),
                final_menu=pipeline_result.get('final_menu', {}),
                images_generated=pipeline_result.get('images_generated', {}),
                metadata={
                    'stage12_timing': stage12_result.get('timing', {}),
                    'stage345_timing': pipeline_result.get('timing', {}),
                    'strategy': 'category_pipeline'
                }
            )
            
        except Exception as e:
            self.logger.error(f"Category pipeline execution failed: {str(e)}")
            raise
    
    async def _execute_sequential_pipeline(self, image_path: str, session_id: str, options: Dict) -> PipelineResult:
        """順次パイプライン処理を実行（フォールバック）"""
        try:
            start_time = time.time()
            
            # 各Stageを順次実行
            from app.workflows.stages import (
                stage1_ocr_gemini_exclusive,
                stage2_categorize_openai_exclusive,
                stage3_translate_with_fallback,
                stage4_add_descriptions,
                stage5_generate_images
            )
            
            # Stage 1: OCR
            stage1_result = await stage1_ocr_gemini_exclusive(image_path, session_id)
            if not stage1_result["success"]:
                raise Exception(f"Stage 1 failed: {stage1_result.get('error')}")
            
            # Stage 2: カテゴライズ
            stage2_result = await stage2_categorize_openai_exclusive(stage1_result["extracted_text"], session_id)
            if not stage2_result["success"]:
                raise Exception(f"Stage 2 failed: {stage2_result.get('error')}")
            
            # Stage 3: 翻訳
            stage3_result = await stage3_translate_with_fallback(stage2_result["categories"], session_id)
            if not stage3_result["success"]:
                raise Exception(f"Stage 3 failed: {stage3_result.get('error')}")
            
            # Stage 4: 詳細説明
            stage4_result = await stage4_add_descriptions(stage3_result["translated_categories"], session_id)
            if not stage4_result["success"]:
                raise Exception(f"Stage 4 failed: {stage4_result.get('error')}")
            
            # Stage 5: 画像生成
            stage5_result = await stage5_generate_images(stage4_result["final_menu"], session_id)
            
            total_categories = len(stage2_result["categories"])
            total_items = sum(len(items) for items in stage2_result["categories"].values())
            
            return PipelineResult(
                success=True,
                pipeline_mode="sequential_pipeline",
                total_processing_time=time.time() - start_time,
                total_categories=total_categories,
                total_items=total_items,
                optimizations_applied=['sequential_processing'],
                extracted_text=stage1_result["extracted_text"],
                categories=stage2_result["categories"],
                translated_categories=stage3_result["translated_categories"],
                final_menu=stage4_result["final_menu"],
                images_generated=stage5_result.get("images_generated", {}),
                metadata={
                    'strategy': 'sequential_pipeline',
                    'stage_results': {
                        'stage1': stage1_result,
                        'stage2': stage2_result,
                        'stage3': stage3_result,
                        'stage4': stage4_result,
                        'stage5': stage5_result
                    }
                }
            )
            
        except Exception as e:
            self.logger.error(f"Sequential pipeline execution failed: {str(e)}")
            raise
    
    async def _execute_stage12(self, image_path: str, session_id: str) -> Dict:
        """Stage 1-2を実行してカテゴリデータを取得"""
        try:
            stage12_start = time.time()
            
            # Stage 1: OCR
            from app.workflows.stages import stage1_ocr_gemini_exclusive
            stage1_result = await stage1_ocr_gemini_exclusive(image_path, session_id)
            
            if not stage1_result["success"]:
                return {
                    'success': False,
                    'error': f"Stage 1 OCR failed: {stage1_result.get('error')}"
                }
            
            # Stage 2: カテゴライズ
            from app.workflows.stages import stage2_categorize_openai_exclusive
            stage2_result = await stage2_categorize_openai_exclusive(stage1_result["extracted_text"], session_id)
            
            if not stage2_result["success"]:
                return {
                    'success': False,
                    'error': f"Stage 2 Categorization failed: {stage2_result.get('error')}"
                }
            
            return {
                'success': True,
                'extracted_text': stage1_result["extracted_text"],
                'categories': stage2_result["categories"],
                'timing': {
                    'stage1': stage1_result.get('processing_time', 0),
                    'stage2': stage2_result.get('processing_time', 0),
                    'total_stage12': time.time() - stage12_start
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Stage 1-2 execution failed: {str(e)}"
            }
    
    async def _execute_parallel_category_stages(self, categorized_data: Dict, session_id: str) -> Dict:
        """カテゴリレベル並列Stage 3-5を実行"""
        try:
            # Stage 3: 並列翻訳
            from app.workflows.stages import stage3_translate_with_fallback
            stage3_result = await stage3_translate_with_fallback(categorized_data, session_id)
            
            if not stage3_result["success"]:
                return {
                    'success': False,
                    'error': f"Stage 3 failed: {stage3_result.get('error')}"
                }
            
            translated_categories = stage3_result["translated_categories"]
            
            # カテゴリごとにStage 4+5パイプラインを並列実行
            from app.tasks.pipeline_tasks import category_stage45_pipeline
            
            category_tasks = []
            for category_name, items in translated_categories.items():
                if items:  # 空でないカテゴリのみ
                    task = category_stage45_pipeline.delay(
                        category_name, {category_name: items}, session_id
                    )
                    category_tasks.append((category_name, task))
            
            # カテゴリパイプライン結果を収集
            final_menu = {}
            images_generated = {}
            failed_categories = []
            
            for category_name, task in category_tasks:
                try:
                    result = task.get(timeout=300)  # 5分タイムアウト
                    
                    if result['success']:
                        final_menu.update(result['final_menu'])
                        images_generated.update(result['images_generated'])
                    else:
                        failed_categories.append({
                            'category': category_name,
                            'error': result.get('error', 'Unknown error')
                        })
                        
                except Exception as e:
                    failed_categories.append({
                        'category': category_name,
                        'error': f"Task execution failed: {str(e)}"
                    })
            
            return {
                'success': len(failed_categories) == 0,
                'translated_categories': translated_categories,
                'final_menu': final_menu,
                'images_generated': images_generated,
                'failed_categories': failed_categories if failed_categories else None,
                'timing': {
                    'stage3': stage3_result.get('processing_time', 0)
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Parallel category stages failed: {str(e)}"
            }
    
    async def _execute_sequential_stages345(self, categorized_data: Dict, session_id: str) -> Dict:
        """順次Stage 3-5を実行"""
        try:
            from app.workflows.stages import (
                stage3_translate_with_fallback,
                stage4_add_descriptions,
                stage5_generate_images
            )
            
            # Stage 3: 翻訳
            stage3_result = await stage3_translate_with_fallback(categorized_data, session_id)
            if not stage3_result["success"]:
                return {
                    'success': False,
                    'error': f"Stage 3 failed: {stage3_result.get('error')}"
                }
            
            # Stage 4: 詳細説明
            stage4_result = await stage4_add_descriptions(stage3_result["translated_categories"], session_id)
            if not stage4_result["success"]:
                return {
                    'success': False,
                    'error': f"Stage 4 failed: {stage4_result.get('error')}"
                }
            
            # Stage 5: 画像生成
            stage5_result = await stage5_generate_images(stage4_result["final_menu"], session_id)
            
            return {
                'success': True,
                'translated_categories': stage3_result["translated_categories"],
                'final_menu': stage4_result["final_menu"],
                'images_generated': stage5_result.get("images_generated", {}),
                'timing': {
                    'stage3': stage3_result.get('processing_time', 0),
                    'stage4': stage4_result.get('processing_time', 0),
                    'stage5': stage5_result.get('processing_time', 0)
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Sequential stages 3-5 failed: {str(e)}"
            }

# 便利関数
async def process_full_pipeline(
    image_path: str,
    session_id: str = None,
    options: Dict = None
) -> PipelineResult:
    """完全パイプライン処理の便利関数"""
    service = PipelineProcessingService()
    return await service.process_full_pipeline(image_path, session_id, options)

async def process_pipeline_with_streaming(
    image_path: str,
    session_id: str = None,
    options: Dict = None
) -> PipelineResult:
    """ストリーミング付きパイプライン処理の便利関数"""
    # ストリーミング機能は将来の実装
    return await process_full_pipeline(image_path, session_id, options) 
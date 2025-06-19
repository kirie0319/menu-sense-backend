"""
Stage 2 並列カテゴライズ統合サービス

カテゴライズ処理の並列化を統合管理するサービス
- テキスト分割並列処理
- 階層的カテゴライズ
- 適応的並列化戦略選択
- エラー時フォールバック
- 既存システムとの完全互換性
"""

import time
import asyncio
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from app.core.config import settings
from .base import CategoryResult

# ログ設定
logger = logging.getLogger(__name__)

@dataclass
class ParallelCategorizationResult:
    """並列カテゴライズ結果データクラス"""
    success: bool
    categories: Dict[str, List[Dict]] = None
    uncategorized: List[str] = None
    parallel_mode: str = "unknown"
    processing_time: float = 0.0
    workers_used: int = 0
    error: str = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.categories is None:
            self.categories = {}
        if self.uncategorized is None:
            self.uncategorized = []
        if self.metadata is None:
            self.metadata = {}

class ParallelCategorizationService:
    """並列カテゴライズ統合サービス"""
    
    def __init__(self):
        self.service_name = "Parallel Categorization Service"
        self.supported_modes = ["smart", "text_chunking", "sequential"]
        
    def is_available(self) -> bool:
        """サービスが利用可能かチェック"""
        try:
            # 基本設定チェック
            if not settings.ENABLE_PARALLEL_CATEGORIZATION:
                return False
            
            # OpenAIサービスの利用可能性チェック
            from .openai import OpenAICategoryService
            openai_service = OpenAICategoryService()
            
            return openai_service.is_available()
            
        except Exception as e:
            logger.error(f"Parallel categorization service availability check failed: {e}")
            return False
    
    def get_service_info(self) -> Dict[str, Any]:
        """サービス情報を取得"""
        return {
            "service_name": self.service_name,
            "supported_modes": self.supported_modes,
            "capabilities": [
                "text_chunking_parallel",
                "adaptive_strategy_selection",
                "error_fallback", 
                "openai_function_calling",
                "result_merging",
                "duplicate_removal"
            ],
            "configuration": {
                "enabled": settings.ENABLE_PARALLEL_CATEGORIZATION,
                "parallel_mode": settings.PARALLEL_CATEGORIZATION_MODE,
                "chunk_size": settings.CATEGORIZATION_CHUNK_SIZE,
                "parallel_limit": settings.CATEGORIZATION_PARALLEL_LIMIT,
                "text_threshold": settings.CATEGORIZATION_TEXT_THRESHOLD,
                "timeout": settings.CATEGORIZATION_TIMEOUT,
                "max_workers": settings.MAX_CATEGORIZATION_WORKERS
            }
        }
    
    async def categorize_menu_parallel(
        self, 
        extracted_text: str, 
        session_id: Optional[str] = None,
        options: Optional[Dict] = None
    ) -> ParallelCategorizationResult:
        """
        メニューテキストを並列カテゴライズ
        
        Args:
            extracted_text: OCRで抽出されたメニューテキスト
            session_id: セッションID（進行状況通知用）
            options: 処理オプション
            
        Returns:
            ParallelCategorizationResult: 並列カテゴライズ結果
        """
        start_time = time.time()
        options = options or {}
        
        logger.info(f"Starting parallel menu categorization ({len(extracted_text)} chars)")
        
        # サービス利用可能性チェック
        if not self.is_available():
            return ParallelCategorizationResult(
                success=False,
                error="Parallel categorization service is not available",
                metadata={
                    "error_type": "service_unavailable",
                    "suggestions": [
                        "Enable ENABLE_PARALLEL_CATEGORIZATION setting",
                        "Check OpenAI API availability",
                        "Verify categorization configuration"
                    ]
                }
            )
        
        # 入力検証
        if not extracted_text or len(extracted_text.strip()) < 5:
            return ParallelCategorizationResult(
                success=False,
                error="Invalid input text for categorization",
                metadata={
                    "error_type": "invalid_input",
                    "text_length": len(extracted_text),
                    "suggestions": [
                        "Provide menu text with at least 5 characters",
                        "Check OCR extraction results"
                    ]
                }
            )
        
        try:
            # 並列化戦略を決定
            strategy = self._determine_parallel_strategy(extracted_text, options)
            
            logger.info(f"Selected parallel categorization strategy: {strategy}")
            
            # 戦略に基づいて実行
            if strategy == "text_chunking" and not settings.FORCE_SEQUENTIAL_CATEGORIZATION:
                result = await self._execute_text_chunking_strategy(
                    extracted_text, session_id, options
                )
            else:
                result = await self._execute_sequential_strategy(
                    extracted_text, session_id, options
                )
            
            # 処理時間を記録
            total_time = time.time() - start_time
            result.processing_time = total_time
            
            # メタデータを強化
            if result.success:
                total_items = sum(len(items) for items in result.categories.values())
                result.metadata.update({
                    "total_items": total_items,
                    "total_categories": len(result.categories),
                    "uncategorized_count": len(result.uncategorized),
                    "processing_time": total_time,
                    "text_length": len(extracted_text),
                    "parallel_strategy": strategy,
                    "service": "ParallelCategorizationService"
                })
                
                logger.info(f"Parallel categorization completed in {total_time:.2f}s: {total_items} items, {len(result.categories)} categories, strategy: {strategy}")
            else:
                logger.warning(f"Parallel categorization failed with strategy {strategy}: {result.error}")
            
            return result
            
        except Exception as e:
            logger.error(f"Parallel categorization error: {str(e)}")
            
            # フォールバック実行を試行
            if settings.CATEGORIZATION_FALLBACK_ENABLED:
                try:
                    logger.info("Attempting fallback to sequential categorization")
                    fallback_result = await self._execute_sequential_strategy(
                        extracted_text, session_id, options
                    )
                    
                    if fallback_result.success:
                        fallback_result.metadata.update({
                            "fallback_used": True,
                            "original_error": str(e),
                            "fallback_reason": "parallel_processing_failed"
                        })
                        return fallback_result
                    
                except Exception as fallback_error:
                    logger.error(f"Fallback also failed: {str(fallback_error)}")
            
            return ParallelCategorizationResult(
                success=False,
                error=f"Parallel categorization failed: {str(e)}",
                processing_time=time.time() - start_time,
                metadata={
                    "error_type": "parallel_processing_error",
                    "original_error": str(e),
                    "fallback_attempted": settings.CATEGORIZATION_FALLBACK_ENABLED,
                    "suggestions": [
                        "Check Celery workers are running",
                        "Verify OpenAI API access",
                        "Try enabling FORCE_SEQUENTIAL_CATEGORIZATION for testing"
                    ]
                }
            )
    
    def _determine_parallel_strategy(self, extracted_text: str, options: Dict) -> str:
        """並列化戦略を決定"""
        try:
            # オプションで戦略が指定されている場合
            if options.get('parallel_mode'):
                return options['parallel_mode']
            
            # 設定から戦略を取得
            mode = settings.PARALLEL_CATEGORIZATION_MODE
            
            # テキスト長による自動選択
            text_length = len(extracted_text)
            
            if mode == "smart":
                # スマートモード：テキスト長に基づく自動選択
                if text_length >= settings.CATEGORIZATION_TEXT_THRESHOLD:
                    if settings.ENABLE_TEXT_CHUNKING:
                        return "text_chunking"
                    else:
                        return "sequential"
                else:
                    return "sequential"
            
            elif mode == "chunk" and settings.ENABLE_TEXT_CHUNKING:
                return "text_chunking"
            
            elif mode == "parallel":
                return "sequential"
            
            else:
                return "sequential"
                
        except Exception as e:
            logger.warning(f"Strategy determination failed, using sequential: {e}")
            return "sequential"
    
    async def _execute_text_chunking_strategy(
        self, 
        extracted_text: str, 
        session_id: str, 
        options: Dict
    ) -> ParallelCategorizationResult:
        """テキスト分割並列処理戦略を実行"""
        try:
            logger.info("Executing text chunking parallel strategy")
            
            # Celeryワーカーで並列処理
            from app.tasks.categorization_tasks import categorize_menu_parallel
            
            # オプション設定
            parallel_options = {
                "parallel_mode": "chunk",
                "chunk_size": options.get('chunk_size', settings.CATEGORIZATION_CHUNK_SIZE),
                **options
            }
            
            # 非同期タスクを開始
            task = categorize_menu_parallel.delay(extracted_text, session_id, parallel_options)
            
            # 結果を待機
            result = task.get(timeout=settings.CATEGORIZATION_TIMEOUT)
            
            return ParallelCategorizationResult(
                success=result['success'],
                categories=result.get('categories', {}),
                uncategorized=result.get('uncategorized', []),
                parallel_mode="text_chunking",
                workers_used=result.get('chunks_processed', 0),
                error=result.get('error'),
                metadata=result.get('metadata', {})
            )
            
        except Exception as e:
            logger.error(f"Text chunking strategy failed: {str(e)}")
            raise
    
    async def _execute_sequential_strategy(
        self, 
        extracted_text: str, 
        session_id: str, 
        options: Dict
    ) -> ParallelCategorizationResult:
        """順次処理戦略を実行（フォールバック）"""
        try:
            logger.info("Executing sequential strategy (fallback)")
            
            # 直接OpenAIサービスを使用
            from .openai import OpenAICategoryService
            
            openai_service = OpenAICategoryService()
            
            if not openai_service.is_available():
                raise Exception("OpenAI categorization service not available")
            
            result = await openai_service.categorize_menu(extracted_text, session_id)
            
            return ParallelCategorizationResult(
                success=result.success,
                categories=result.categories if result.success else {},
                uncategorized=result.uncategorized if result.success else [],
                parallel_mode="sequential",
                workers_used=0,
                error=result.error if not result.success else None,
                metadata=result.metadata
            )
            
        except Exception as e:
            logger.error(f"Sequential strategy failed: {str(e)}")
            raise

    def get_parallel_status(self) -> Dict[str, Any]:
        """並列カテゴライズサービスの状態を取得"""
        try:
            is_available = self.is_available()
            
            # OpenAI サービス状態
            from .openai import OpenAICategoryService
            openai_service = OpenAICategoryService()
            openai_available = openai_service.is_available()
            
            # Celery ワーカー状態（簡易チェック）
            celery_available = True
            try:
                from app.tasks.celery_app import celery_app
                inspect = celery_app.control.inspect()
                active_workers = inspect.active()
                celery_available = active_workers is not None and len(active_workers) > 0
            except Exception:
                celery_available = False
            
            return {
                "service_available": is_available,
                "parallel_categorization_enabled": settings.ENABLE_PARALLEL_CATEGORIZATION,
                "openai_available": openai_available,
                "celery_workers_available": celery_available,
                "configuration": {
                    "parallel_mode": settings.PARALLEL_CATEGORIZATION_MODE,
                    "text_chunking_enabled": settings.ENABLE_TEXT_CHUNKING,
                    "chunk_size": settings.CATEGORIZATION_CHUNK_SIZE,
                    "parallel_limit": settings.CATEGORIZATION_PARALLEL_LIMIT,
                    "text_threshold": settings.CATEGORIZATION_TEXT_THRESHOLD,
                    "timeout": settings.CATEGORIZATION_TIMEOUT,
                    "max_workers": settings.MAX_CATEGORIZATION_WORKERS,
                    "fallback_enabled": settings.CATEGORIZATION_FALLBACK_ENABLED
                },
                "supported_strategies": self.supported_modes,
                "recommendations": self._get_status_recommendations(is_available, openai_available, celery_available)
            }
            
        except Exception as e:
            return {
                "service_available": False,
                "error": f"Status check failed: {str(e)}",
                "recommendations": [
                    "Check service configuration",
                    "Verify dependencies are installed",
                    "Check logs for detailed error information"
                ]
            }
    
    def _get_status_recommendations(self, is_available: bool, openai_available: bool, celery_available: bool) -> List[str]:
        """状態に基づく推奨事項を生成"""
        recommendations = []
        
        if not is_available:
            recommendations.append("Enable ENABLE_PARALLEL_CATEGORIZATION setting")
        
        if not openai_available:
            recommendations.extend([
                "Set OPENAI_API_KEY environment variable",
                "Install openai package: pip install openai",
                "Check OpenAI API access permissions"
            ])
        
        if not celery_available:
            recommendations.extend([
                "Start Celery workers: celery -A app.tasks.celery_app worker --loglevel=info",
                "Check Redis/RabbitMQ broker connectivity",
                "Verify Celery configuration"
            ])
        
        if is_available and openai_available and celery_available:
            recommendations.extend([
                "Parallel categorization is ready for use",
                "Use smart mode for adaptive strategy selection",
                "Monitor processing times and adjust chunk sizes as needed"
            ])
        
        return recommendations

# グローバルサービスインスタンス
_parallel_categorization_service = None

def get_parallel_categorization_service() -> ParallelCategorizationService:
    """並列カテゴライズサービスのグローバルインスタンスを取得"""
    global _parallel_categorization_service
    if _parallel_categorization_service is None:
        _parallel_categorization_service = ParallelCategorizationService()
    return _parallel_categorization_service

async def categorize_menu_with_parallel(
    extracted_text: str, 
    session_id: Optional[str] = None,
    options: Optional[Dict] = None
) -> CategoryResult:
    """
    並列カテゴライズを使用してメニューテキストをカテゴリ分類
    
    Args:
        extracted_text: OCRで抽出されたメニューテキスト
        session_id: セッションID（進行状況通知用）
        options: 処理オプション
        
    Returns:
        CategoryResult: 既存システムと互換性のある分類結果
    """
    service = get_parallel_categorization_service()
    
    result = await service.categorize_menu_parallel(extracted_text, session_id, options)
    
    # 既存のCategoryResult形式に変換
    return CategoryResult(
        success=result.success,
        categories=result.categories,
        uncategorized=result.uncategorized,
        error=result.error,
        metadata=result.metadata
    ) 
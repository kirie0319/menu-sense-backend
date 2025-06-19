#!/usr/bin/env python3
"""
詳細説明並列処理統合サービス

Stage 4詳細説明の並列化統合管理
- 既存詳細説明サービスとの完全互換性
- 段階的な並列処理への移行
- 自動的な処理方式選択
- フロントエンド連携の完全保持
"""

import time
import logging
from typing import Dict, List, Any, Optional

from app.core.config import settings
from .base import DescriptionResult

logger = logging.getLogger(__name__)

class ParallelDescriptionService:
    """詳細説明並列処理統合サービス"""
    
    def __init__(self):
        self.service_name = "Parallel Description Service"
        logger.info("🚀 Parallel Description Service initialized")
    
    def is_available(self) -> bool:
        """並列詳細説明サービスが利用可能かチェック"""
        try:
            # 基本的な詳細説明サービスの可用性をチェック
            from app.services.description.openai import OpenAIDescriptionService
            openai_service = OpenAIDescriptionService()
            return openai_service.is_available()
        except Exception as e:
            logger.error(f"Parallel description service availability check failed: {e}")
            return False
    
    def should_use_parallel_processing(self, translated_data: Dict) -> bool:
        """並列処理を使用すべきかを判定"""
        if not getattr(settings, 'ENABLE_PARALLEL_DESCRIPTION', True):
            logger.info("📋 Parallel description processing disabled by configuration")
            return False
        
        # カテゴリ数とアイテム数を確認
        categories = [cat for cat, items in translated_data.items() if items]
        total_items = sum(len(items) for items in translated_data.values())
        
        # 設定値を取得（デフォルト値付き）
        category_threshold = getattr(settings, 'PARALLEL_DESCRIPTION_CATEGORY_THRESHOLD', 2)
        item_threshold = getattr(settings, 'PARALLEL_DESCRIPTION_ITEM_THRESHOLD', 5)
        
        use_parallel = len(categories) >= category_threshold or total_items >= item_threshold
        
        logger.info(f"📊 Description processing decision: {len(categories)} categories, {total_items} items")
        logger.info(f"🎯 Using {'PARALLEL' if use_parallel else 'SEQUENTIAL'} processing mode")
        
        return use_parallel
    
    async def add_descriptions_with_parallel(
        self, 
        translated_data: Dict, 
        session_id: Optional[str] = None
    ) -> DescriptionResult:
        """
        並列ワーカーを使用した詳細説明追加
        
        Args:
            translated_data: 翻訳されたメニューデータ
            session_id: セッションID
            
        Returns:
            DescriptionResult: 詳細説明追加結果
        """
        start_time = time.time()
        
        try:
            logger.info("🚀 Starting parallel description generation...")
            
            # 並列詳細説明タスクを実行
            from app.tasks.description_tasks import add_descriptions_parallel_menu
            
            # 並列タスクを開始
            task = add_descriptions_parallel_menu.delay(translated_data, session_id)
            
            # タスク完了を待機
            timeout = getattr(settings, 'PARALLEL_DESCRIPTION_TIMEOUT', 300)  # 5分
            result = task.get(timeout=timeout)
            
            # 処理時間計算
            processing_time = time.time() - start_time
            
            if result['success']:
                logger.info(f"✅ Parallel description generation completed in {processing_time:.2f}s")
                
                return DescriptionResult(
                    success=True,
                    final_menu=result['final_menu'],
                    description_method="parallel_worker",
                    metadata={
                        "total_items": result['total_items'],
                        "categories_processed": result['categories_processed'],
                        "processing_time": processing_time,
                        "processing_mode": "parallel_worker",
                        "parallel_enabled": True,
                        "provider": "OpenAI API (Parallel Workers)",
                        "features": [
                            "parallel_worker_processing",
                            "category_level_parallelization",
                            "detailed_descriptions",
                            "cultural_context",
                            "tourist_friendly_language",
                            "real_time_progress",
                            "error_resilience"
                        ],
                        "failed_categories": result.get('failed_categories')
                    }
                )
            else:
                error_msg = result.get('error', 'Unknown parallel processing error')
                logger.error(f"❌ Parallel description generation failed: {error_msg}")
                
                return DescriptionResult(
                    success=False,
                    description_method="parallel_worker",
                    error=error_msg,
                    metadata={
                        "error_type": "parallel_processing_failed",
                        "processing_time": processing_time,
                        "processing_mode": "parallel_worker_failed",
                        "suggestions": [
                            "Check Celery worker availability",
                            "Verify OpenAI API configuration",
                            "Check for timeout issues",
                            "Try sequential processing as fallback"
                        ]
                    }
                )
                
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"❌ Parallel description service error: {str(e)}")
            
            return DescriptionResult(
                success=False,
                description_method="parallel_worker",
                error=f"Parallel description service error: {str(e)}",
                metadata={
                    "error_type": "service_exception",
                    "processing_time": processing_time,
                    "processing_mode": "parallel_worker_exception",
                    "original_error": str(e),
                    "suggestions": [
                        "Check Celery broker connection",
                        "Verify worker processes are running",
                        "Check system resources",
                        "Ensure all dependencies are available"
                    ]
                }
            )
    
    async def add_descriptions_sequential_fallback(
        self, 
        translated_data: Dict, 
        session_id: Optional[str] = None
    ) -> DescriptionResult:
        """
        逐次処理によるフォールバック詳細説明追加
        
        Args:
            translated_data: 翻訳されたメニューデータ
            session_id: セッションID
            
        Returns:
            DescriptionResult: 詳細説明追加結果
        """
        try:
            logger.info("🔄 Using sequential description processing as fallback...")
            
            # 既存のOpenAI詳細説明サービスを使用
            from app.services.description.openai import OpenAIDescriptionService
            
            openai_service = OpenAIDescriptionService()
            result = await openai_service.add_descriptions(translated_data, session_id)
            
            # メタデータに処理方式を追加
            if result.metadata:
                result.metadata.update({
                    "processing_mode": "sequential_fallback",
                    "parallel_enabled": False,
                    "fallback_reason": "parallel_processing_unavailable"
                })
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Sequential fallback also failed: {str(e)}")
            
            return DescriptionResult(
                success=False,
                description_method="sequential_fallback",
                error=f"Sequential fallback error: {str(e)}",
                metadata={
                    "error_type": "fallback_failed",
                    "processing_mode": "fallback_failed",
                    "suggestions": [
                        "Check OpenAI API configuration",
                        "Verify API key and permissions",
                        "Check network connectivity",
                        "Review system resources"
                    ]
                }
            )

async def add_descriptions_with_parallel(
    translated_data: Dict, 
    session_id: Optional[str] = None
) -> DescriptionResult:
    """
    並列詳細説明追加の便利関数（適応的処理選択）
    
    Args:
        translated_data: 翻訳されたメニューデータ
        session_id: セッションID
        
    Returns:
        DescriptionResult: 詳細説明追加結果
    """
    parallel_service = ParallelDescriptionService()
    
    # サービス利用可能性チェック
    if not parallel_service.is_available():
        logger.warning("⚠️ Parallel description service not available")
        return DescriptionResult(
            success=False,
            description_method="unavailable",
            error="Parallel description service is not available",
            metadata={
                "error_type": "service_unavailable",
                "suggestions": [
                    "Check OpenAI API configuration",
                    "Verify Celery worker status",
                    "Ensure all dependencies are installed"
                ]
            }
        )
    
    # 並列処理の必要性を判定
    if parallel_service.should_use_parallel_processing(translated_data):
        logger.info("🚀 Using parallel description processing")
        
        # 並列処理を試行
        result = await parallel_service.add_descriptions_with_parallel(translated_data, session_id)
        
        # 並列処理が失敗した場合のフォールバック
        if not result.success and getattr(settings, 'ENABLE_DESCRIPTION_FALLBACK', True):
            logger.warning("⚠️ Parallel processing failed, falling back to sequential...")
            result = await parallel_service.add_descriptions_sequential_fallback(translated_data, session_id)
        
        return result
    else:
        # 逐次処理を使用
        logger.info("📋 Using sequential description processing")
        return await parallel_service.add_descriptions_sequential_fallback(translated_data, session_id)

# エクスポート
__all__ = [
    "ParallelDescriptionService",
    "add_descriptions_with_parallel"
] 
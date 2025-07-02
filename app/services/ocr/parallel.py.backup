#!/usr/bin/env python3
"""
OCR並列処理統合サービス

Stage 1 OCRの並列化統合管理
- マルチエンジン並列OCR（Gemini + Google Vision）
- 結果品質の自動判定・選択
- 既存OCRサービスとの完全互換性
- 自動的な処理方式選択
- フロントエンド連携の完全保持
"""

import time
import logging
from typing import Dict, List, Any, Optional

from app.core.config import settings
from .base import OCRResult

logger = logging.getLogger(__name__)

class ParallelOCRService:
    """OCR並列処理統合サービス"""
    
    def __init__(self):
        self.service_name = "Parallel OCR Service"
        logger.info("🚀 Parallel OCR Service initialized")
    
    def is_available(self) -> bool:
        """並列OCRサービスが利用可能かチェック"""
        try:
            # 基本的なOCRサービスの可用性をチェック
            from app.services.ocr.gemini import GeminiOCRService
            
            gemini_service = GeminiOCRService()
            return gemini_service.is_available()
        except Exception as e:
            logger.error(f"Parallel OCR service availability check failed: {e}")
            return False
    
    def should_use_parallel_processing(self, image_path: str) -> bool:
        """並列処理を使用すべきかを判定"""
        if not getattr(settings, 'ENABLE_PARALLEL_OCR', True):
            logger.info("📋 Parallel OCR processing disabled by configuration")
            return False
        
        # 画像サイズや複雑さを確認（今回は簡略化）
        use_parallel = True  # デフォルトで並列処理を使用
        
        logger.info(f"📊 OCR processing decision for {image_path}")
        logger.info(f"🎯 Using {'PARALLEL' if use_parallel else 'SEQUENTIAL'} processing mode")
        
        return use_parallel
    
    async def extract_text_with_parallel(
        self, 
        image_path: str, 
        session_id: Optional[str] = None
    ) -> OCRResult:
        """
        並列ワーカーを使用したマルチエンジンOCR
        
        Args:
            image_path: 画像ファイルパス
            session_id: セッションID
            
        Returns:
            OCRResult: OCR結果
        """
        start_time = time.time()
        
        try:
            logger.info("🚀 Starting parallel multi-engine OCR...")
            
            # 並列OCRタスクを実行
            from app.tasks.ocr_tasks import ocr_parallel_multi_engine
            
            # 並列タスクを開始
            task = ocr_parallel_multi_engine.delay(image_path, session_id)
            
            # タスク完了を待機
            timeout = getattr(settings, 'PARALLEL_OCR_TIMEOUT', 90)  # 90秒
            result = task.get(timeout=timeout)
            
            # 処理時間計算
            processing_time = time.time() - start_time
            
            if result['success']:
                logger.info(f"✅ Parallel OCR completed in {processing_time:.2f}s")
                
                return OCRResult(
                    success=True,
                    extracted_text=result['extracted_text'],
                    metadata={
                        "text_length": result['text_length'],
                        "processing_time": processing_time,
                        "processing_mode": "parallel_multi_engine",
                        "parallel_enabled": True,
                        "selected_engine": result.get('engine', 'unknown'),
                        "engines_used": result.get('engines_used', []),
                        "all_results": result.get('all_results', {}),
                        "selection_reason": result.get('selection_reason', ''),
                        "provider": "Parallel OCR Service",
                        "features": [
                            "multi_engine_parallel",
                            "automatic_best_selection",
                            "gemini_2.0_flash",
                            "google_vision_api",
                            "quality_optimization",
                            "error_resilience"
                        ]
                    }
                )
            else:
                error_msg = result.get('error', 'Unknown parallel processing error')
                logger.error(f"❌ Parallel OCR failed: {error_msg}")
                
                return OCRResult(
                    success=False,
                    error=error_msg,
                    metadata={
                        "error_type": "parallel_processing_failed",
                        "processing_time": processing_time,
                        "processing_mode": "parallel_multi_engine_failed",
                        "all_results": result.get('all_results', {}),
                        "suggestions": [
                            "Check Celery worker availability",
                            "Verify Gemini API and Google Vision API configuration",
                            "Check for timeout issues",
                            "Try sequential processing as fallback"
                        ]
                    }
                )
                
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"❌ Parallel OCR service error: {str(e)}")
            
            return OCRResult(
                success=False,
                error=f"Parallel OCR service error: {str(e)}",
                metadata={
                    "error_type": "service_exception",
                    "processing_time": processing_time,
                    "processing_mode": "parallel_ocr_exception",
                    "original_error": str(e),
                    "suggestions": [
                        "Check Celery broker connection",
                        "Verify worker processes are running",
                        "Check system resources",
                        "Ensure all dependencies are available"
                    ]
                }
            )
    
    async def extract_text_sequential_fallback(
        self, 
        image_path: str, 
        session_id: Optional[str] = None
    ) -> OCRResult:
        """
        逐次処理によるフォールバックOCR
        
        Args:
            image_path: 画像ファイルパス
            session_id: セッションID
            
        Returns:
            OCRResult: OCR結果
        """
        try:
            logger.info("🔄 Using sequential OCR processing as fallback...")
            
            # 既存のGemini OCRサービスを使用
            from app.services.ocr.gemini import GeminiOCRService
            
            gemini_service = GeminiOCRService()
            result = await gemini_service.extract_text(image_path, session_id)
            
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
            
            return OCRResult(
                success=False,
                error=f"Sequential fallback error: {str(e)}",
                metadata={
                    "error_type": "fallback_failed",
                    "processing_mode": "fallback_failed",
                    "suggestions": [
                        "Check Gemini API configuration",
                        "Verify API key and permissions",
                        "Check network connectivity",
                        "Review image file accessibility"
                    ]
                }
            )

async def extract_text_with_parallel(
    image_path: str, 
    session_id: Optional[str] = None
) -> OCRResult:
    """
    並列OCRの便利関数（適応的処理選択）
    
    Args:
        image_path: 画像ファイルパス
        session_id: セッションID
        
    Returns:
        OCRResult: OCR結果
    """
    parallel_service = ParallelOCRService()
    
    # サービス利用可能性チェック
    if not parallel_service.is_available():
        logger.warning("⚠️ Parallel OCR service not available")
        return OCRResult(
            success=False,
            error="Parallel OCR service is not available",
            metadata={
                "error_type": "service_unavailable",
                "suggestions": [
                    "Check Gemini API configuration",
                    "Verify Celery worker status",
                    "Ensure all dependencies are installed"
                ]
            }
        )
    
    # 並列処理の必要性を判定
    if parallel_service.should_use_parallel_processing(image_path):
        logger.info("🚀 Using parallel OCR processing")
        
        # 並列処理を試行
        result = await parallel_service.extract_text_with_parallel(image_path, session_id)
        
        # 並列処理が失敗した場合のフォールバック
        if not result.success and getattr(settings, 'ENABLE_OCR_FALLBACK', True):
            logger.warning("⚠️ Parallel processing failed, falling back to sequential...")
            result = await parallel_service.extract_text_sequential_fallback(image_path, session_id)
        
        return result
    else:
        # 逐次処理を使用
        logger.info("📋 Using sequential OCR processing")
        return await parallel_service.extract_text_sequential_fallback(image_path, session_id)

# エクスポート
__all__ = [
    "ParallelOCRService",
    "extract_text_with_parallel"
] 
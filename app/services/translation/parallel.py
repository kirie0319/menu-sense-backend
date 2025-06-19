#!/usr/bin/env python3
"""
並列翻訳統合サービス

Stage 3翻訳の並列化を実現する統合サービス
- 既存翻訳サービスとの完全互換
- 段階的な並列処理への移行
- フロントエンド影響ゼロ
- フォールバック機能の保持
"""

import asyncio
import time
import logging
from typing import Dict, List, Any, Optional, Union

from app.core.config import settings
from .base import BaseTranslationService, TranslationResult, TranslationProvider

# ログ設定
logger = logging.getLogger(__name__)

class ParallelTranslationService(BaseTranslationService):
    """
    並列翻訳統合サービス
    
    既存の翻訳サービスと完全互換を保ちながら、
    カテゴリレベルでの並列処理を実現
    """
    
    def __init__(self):
        super().__init__()
        self.provider = TranslationProvider.GOOGLE_TRANSLATE
        self.service_name = "Parallel Translation Service"
        
        # 設定値の取得
        self.enable_parallel = getattr(settings, 'ENABLE_PARALLEL_TRANSLATION', True)
        self.parallel_limit = getattr(settings, 'PARALLEL_TRANSLATION_LIMIT', 6)
        self.category_threshold = getattr(settings, 'PARALLEL_CATEGORY_THRESHOLD', 2)
        
        logger.info(f"Parallel Translation Service initialized:")
        logger.info(f"  - Parallel enabled: {self.enable_parallel}")
        logger.info(f"  - Parallel limit: {self.parallel_limit}")
        logger.info(f"  - Category threshold: {self.category_threshold}")
    
    def is_available(self) -> bool:
        """サービスが利用可能かチェック"""
        # Google TranslateまたはOpenAIのいずれかが利用可能であればOK
        try:
            from .google_translate import GoogleTranslateService
            google_service = GoogleTranslateService()
            if google_service.is_available():
                return True
        except:
            pass
        
        try:
            from .openai import OpenAITranslationService
            openai_service = OpenAITranslationService()
            if openai_service.is_available():
                return True
        except:
            pass
        
        return False
    
    def should_use_parallel(self, categorized_data: Dict) -> bool:
        """
        並列処理を使用すべきかを判定
        
        Args:
            categorized_data: カテゴリ分類されたメニューデータ
            
        Returns:
            bool: 並列処理を使用すべきかどうか
        """
        if not self.enable_parallel:
            logger.info("Parallel processing disabled by configuration")
            return False
        
        # カテゴリ数が閾値以下の場合は逐次処理
        if len(categorized_data) <= self.category_threshold:
            logger.info(f"Category count ({len(categorized_data)}) <= threshold ({self.category_threshold}), using sequential processing")
            return False
        
        # アイテム数の確認
        total_items = sum(len(items) for items in categorized_data.values())
        if total_items < 10:  # アイテム数が少ない場合は逐次処理
            logger.info(f"Total items ({total_items}) too small for parallel processing")
            return False
        
        logger.info(f"Using parallel processing: {len(categorized_data)} categories, {total_items} items")
        return True
    
    async def translate_menu_sequential(
        self, 
        categorized_data: Dict, 
        session_id: Optional[str] = None
    ) -> TranslationResult:
        """
        従来の逐次翻訳処理（フォールバック用）
        
        Args:
            categorized_data: カテゴリ分類されたメニューデータ
            session_id: セッションID
            
        Returns:
            TranslationResult: 翻訳結果
        """
        logger.info("Using sequential translation processing")
        
        # 既存の翻訳マネージャーを使用
        from . import translation_manager
        
        try:
            result = await translation_manager.translate_with_fallback(categorized_data, session_id)
            
            # メタデータに処理方式を追加
            if result.metadata is None:
                result.metadata = {}
            result.metadata.update({
                "processing_mode": "sequential",
                "parallel_attempted": False,
                "service": "ParallelTranslationService"
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Sequential translation failed: {str(e)}")
            return TranslationResult(
                success=False,
                translation_method="sequential_failed",
                error=f"Sequential translation error: {str(e)}",
                metadata={
                    "processing_mode": "sequential",
                    "parallel_attempted": False,
                    "error_type": "sequential_processing_error"
                }
            )
    
    async def translate_menu_parallel(
        self, 
        categorized_data: Dict, 
        session_id: Optional[str] = None
    ) -> TranslationResult:
        """
        並列翻訳処理（改良版）
        
        Celeryタスク内での同期待機を避けて、メイン処理で直接並列タスクを管理
        
        Args:
            categorized_data: カテゴリ分類されたメニューデータ
            session_id: セッションID
            
        Returns:
            TranslationResult: 翻訳結果
        """
        logger.info("Using parallel translation processing (improved)")
        
        try:
            # Celeryタスクをインポート
            from app.tasks.translation_tasks import translate_category_with_fallback
            
            # 進行状況通知（オプション）
            if session_id:
                from app.services.realtime import send_progress
                await send_progress(
                    session_id, 3, "active", 
                    "🚀 Starting parallel translation processing...",
                    {
                        "processing_mode": "parallel_direct",
                        "total_categories": len(categorized_data),
                        "parallel_limit": self.parallel_limit
                    }
                )
            
            # カテゴリごとにワーカータスクを作成
            translation_tasks = []
            
            for category_name, items in categorized_data.items():
                if items:  # 空のカテゴリはスキップ
                    task = translate_category_with_fallback.delay(category_name, items, session_id)
                    translation_tasks.append((category_name, task))
            
            logger.info(f"Started {len(translation_tasks)} parallel translation tasks")
            
            # 並列実行の結果を収集（非同期的に）
            translated_categories = {}
            failed_categories = []
            total_items = 0
            
            # タスク完了を待機（個別にタイムアウト処理）
            for i, (category_name, task) in enumerate(translation_tasks):
                try:
                    # カテゴリあたりのタイムアウト
                    timeout = getattr(settings, 'TRANSLATION_TIMEOUT_PER_CATEGORY', 30)
                    
                    # 進行状況更新
                    if session_id:
                        await send_progress(
                            session_id, 3, "active", 
                            f"🔄 Waiting for {category_name}...",
                            {
                                "processing_mode": "parallel_direct", 
                                "completed_categories": i,
                                "total_categories": len(translation_tasks),
                                "current_category": category_name
                            }
                        )
                    
                    # タスク完了を待機
                    result = task.get(timeout=timeout)
                    
                    if result['success']:
                        english_category = result['english_category']
                        translated_categories[english_category] = result['translated_items']
                        total_items += len(result['translated_items'])
                        logger.info(f"✅ Category completed: {category_name} → {english_category}")
                    else:
                        # 失敗したカテゴリは元データで代替
                        failed_categories.append({
                            'category': category_name,
                            'error': result.get('error', 'Unknown error')
                        })
                        # 翻訳失敗時は元の日本語データを保持
                        translated_categories[category_name] = categorized_data[category_name]
                        logger.warning(f"⚠️ Category failed, using original data: {category_name}")
                    
                except Exception as e:
                    # タスク自体が失敗
                    failed_categories.append({
                        'category': category_name,
                        'error': f"Task execution failed: {str(e)}"
                    })
                    # 元の日本語データを保持
                    translated_categories[category_name] = categorized_data[category_name]
                    logger.error(f"❌ Task failed for category {category_name}: {str(e)}")
            
            # 最終結果判定
            success = len(failed_categories) == 0
            
            # 最終的な完了通知
            if session_id:
                await send_progress(
                    session_id, 3, "completed", 
                    "✅ Parallel translation completed!",
                    {
                        "translatedCategories": translated_categories,
                        "total_translated_items": total_items,
                        "total_categories": len(translated_categories),
                        "translation_method": "parallel_direct_processing",
                        "show_translated_menu": True,
                        "completion_status": "success",
                        "processing_mode": "parallel_direct",
                        "failed_categories": failed_categories if failed_categories else None
                    }
                )
            
            return TranslationResult(
                success=success,
                translated_categories=translated_categories,
                translation_method="parallel_direct_processing",
                metadata={
                    "total_items": total_items,
                    "total_categories": len(translated_categories),
                    "processing_mode": "parallel_direct",
                    "parallel_limit": self.parallel_limit,
                    "failed_categories": failed_categories if failed_categories else None,
                    "successful_categories": len(translated_categories) - len(failed_categories),
                    "provider": "Parallel Translation Service (Direct)",
                    "features": [
                        "parallel_processing",
                        "direct_task_management",
                        "category_level_parallelization",
                        "fallback_support",
                        "error_recovery"
                    ]
                }
            )
                    
        except Exception as e:
            logger.error(f"Parallel translation initialization failed: {str(e)}")
            
            # 並列処理の初期化に失敗、逐次処理にフォールバック
            logger.warning("Parallel translation initialization failed, falling back to sequential processing")
            return await self.translate_menu_sequential(categorized_data, session_id)
    
    async def translate_menu(
        self, 
        categorized_data: Dict, 
        session_id: Optional[str] = None
    ) -> TranslationResult:
        """
        メニュー翻訳のメインエントリーポイント
        
        カテゴリ数と設定に基づいて、並列処理または逐次処理を選択
        
        Args:
            categorized_data: カテゴリ分類されたメニューデータ
            session_id: セッションID
            
        Returns:
            TranslationResult: 翻訳結果
        """
        start_time = time.time()
        
        # サービス利用可能性チェック
        if not self.is_available():
            return TranslationResult(
                success=False,
                translation_method="parallel_service",
                error="No translation services available",
                metadata={
                    "error_type": "service_unavailable",
                    "processing_mode": "none",
                    "suggestions": [
                        "Check Google Translate API configuration",
                        "Check OpenAI API configuration",
                        "Ensure at least one translation service is available"
                    ]
                }
            )
        
        # 入力データの妥当性チェック
        if not self.validate_categorized_data(categorized_data):
            return TranslationResult(
                success=False,
                translation_method="parallel_service",
                error="Invalid categorized data",
                metadata={
                    "error_type": "invalid_input",
                    "processing_mode": "none"
                }
            )
        
        logger.info(f"Starting menu translation: {len(categorized_data)} categories")
        
        # 処理方式の決定
        use_parallel = self.should_use_parallel(categorized_data)
        
        try:
            if use_parallel:
                # 並列処理を実行
                result = await self.translate_menu_parallel(categorized_data, session_id)
            else:
                # 逐次処理を実行
                result = await self.translate_menu_sequential(categorized_data, session_id)
            
            # 処理時間の記録
            processing_time = time.time() - start_time
            
            if result.metadata is None:
                result.metadata = {}
            result.metadata.update({
                "total_processing_time": processing_time,
                "service": "ParallelTranslationService",
                "timestamp": start_time
            })
            
            logger.info(f"Translation completed in {processing_time:.2f}s (mode: {result.metadata.get('processing_mode', 'unknown')})")
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Translation service failed after {processing_time:.2f}s: {str(e)}")
            
            return TranslationResult(
                success=False,
                translation_method="parallel_service_error",
                error=f"Translation service error: {str(e)}",
                metadata={
                    "error_type": "service_error",
                    "processing_mode": "failed",
                    "total_processing_time": processing_time,
                    "original_error": str(e)
                }
            )
    
    def get_service_info(self) -> Dict[str, Any]:
        """サービス情報を取得"""
        return {
            "service_name": self.service_name,
            "provider": "parallel_translation",
            "capabilities": [
                "parallel_processing",
                "sequential_fallback", 
                "category_level_parallelization",
                "automatic_mode_selection",
                "error_recovery",
                "progress_tracking"
            ],
            "configuration": {
                "parallel_enabled": self.enable_parallel,
                "parallel_limit": self.parallel_limit,
                "category_threshold": self.category_threshold
            },
            "supported_languages": {
                "source": ["Japanese"],
                "target": ["English"]
            }
        }

# 並列翻訳サービスのインスタンス化
parallel_translation_service = ParallelTranslationService()

# 便利な関数をエクスポート
async def translate_menu_with_parallel(
    categorized_data: Dict, 
    session_id: Optional[str] = None
) -> TranslationResult:
    """
    並列翻訳を使用したメニュー翻訳の便利関数
    
    Args:
        categorized_data: カテゴリ分類されたメニューデータ
        session_id: セッションID
        
    Returns:
        TranslationResult: 翻訳結果
    """
    return await parallel_translation_service.translate_menu(categorized_data, session_id)

def get_parallel_translation_status() -> Dict[str, Any]:
    """並列翻訳サービスの状態を取得"""
    return {
        "available": parallel_translation_service.is_available(),
        "service_info": parallel_translation_service.get_service_info(),
        "configuration": {
            "parallel_enabled": parallel_translation_service.enable_parallel,
            "parallel_limit": parallel_translation_service.parallel_limit,
            "category_threshold": parallel_translation_service.category_threshold
        }
    }

# エクスポート
__all__ = [
    "ParallelTranslationService",
    "parallel_translation_service",
    "translate_menu_with_parallel",
    "get_parallel_translation_status"
] 
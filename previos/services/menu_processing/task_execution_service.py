"""
🚀 TaskExecutionService - タスク実行管理サービス

タスク層からビジネスロジックを分離し、実行管理のみに特化させます。
プロバイダーサービスの統合とフォールバック処理を含む実行ロジックを提供。
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from app.services.providers.google import GoogleProviderService
from app.services.providers.openai import OpenAIProviderService
from app.core.config.ai import ai_settings

logger = logging.getLogger(__name__)


class ExecutionMode(Enum):
    """実行モード"""
    REAL = "real"
    TEST = "test"


class TaskStage(Enum):
    """タスクステージ"""
    TRANSLATION = "translation"
    DESCRIPTION = "description"
    IMAGE = "image"
    OCR = "ocr"


@dataclass
class TaskExecutionRequest:
    """タスク実行リクエスト"""
    session_id: str
    item_id: int
    item_text: str
    stage: TaskStage
    category: str = "Other"
    execution_mode: ExecutionMode = ExecutionMode.REAL
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskExecutionResult:
    """タスク実行結果"""
    success: bool
    session_id: str
    item_id: int
    stage: TaskStage
    result_data: Dict[str, Any]
    provider_used: str
    execution_time: float
    fallback_used: bool = False
    error: Optional[str] = None
    quality_score: Optional[float] = None
    confidence: Optional[float] = None


class TaskExecutionService:
    """
    タスク実行管理サービス
    
    プロバイダーサービスを統合し、フォールバック処理を含む
    ビジネスロジックを提供する。
    """
    
    def __init__(self):
        """サービス初期化"""
        self.google_provider = GoogleProviderService()
        self.openai_provider = OpenAIProviderService()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    
    async def execute_translation(self, request: TaskExecutionRequest) -> TaskExecutionResult:
        """
        翻訳実行（ビジネスロジック付き）
        
        Args:
            request: 翻訳実行リクエスト
            
        Returns:
            TaskExecutionResult: 翻訳結果
        """
        start_time = time.time()
        
        try:
            if request.execution_mode == ExecutionMode.TEST:
                return await self._execute_test_translation(request, start_time)
            else:
                return await self._execute_real_translation(request, start_time)
                
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Translation execution failed: {e}")
            
            return TaskExecutionResult(
                success=False,
                session_id=request.session_id,
                item_id=request.item_id,
                stage=request.stage,
                result_data={},
                provider_used="none",
                execution_time=execution_time,
                error=str(e)
            )
    
    
    async def execute_description_generation(self, request: TaskExecutionRequest) -> TaskExecutionResult:
        """
        説明生成実行（ビジネスロジック付き）
        
        Args:
            request: 説明生成実行リクエスト
            
        Returns:
            TaskExecutionResult: 説明生成結果
        """
        start_time = time.time()
        
        try:
            if request.execution_mode == ExecutionMode.TEST:
                return await self._execute_test_description(request, start_time)
            else:
                return await self._execute_real_description(request, start_time)
                
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Description generation failed: {e}")
            
            return TaskExecutionResult(
                success=False,
                session_id=request.session_id,
                item_id=request.item_id,
                stage=request.stage,
                result_data={},
                provider_used="none",
                execution_time=execution_time,
                error=str(e)
            )
    
    
    async def execute_image_generation(self, request: TaskExecutionRequest) -> TaskExecutionResult:
        """
        画像生成実行（ビジネスロジック付き）
        
        Args:
            request: 画像生成実行リクエスト
            
        Returns:
            TaskExecutionResult: 画像生成結果
        """
        start_time = time.time()
        
        try:
            if request.execution_mode == ExecutionMode.TEST:
                return await self._execute_test_image(request, start_time)
            else:
                return await self._execute_real_image(request, start_time)
                
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Image generation failed: {e}")
            
            return TaskExecutionResult(
                success=False,
                session_id=request.session_id,
                item_id=request.item_id,
                stage=request.stage,
                result_data={},
                provider_used="none",
                execution_time=execution_time,
                error=str(e)
            )
    
    
    async def execute_ocr(self, request: TaskExecutionRequest) -> TaskExecutionResult:
        """
        OCR実行（ビジネスロジック付き）
        
        Args:
            request: OCR実行リクエスト
            
        Returns:
            TaskExecutionResult: OCR結果
        """
        start_time = time.time()
        
        try:
            # OCR processing logic will be implemented here
            # For now, return a placeholder
            execution_time = time.time() - start_time
            
            return TaskExecutionResult(
                success=True,
                session_id=request.session_id,
                item_id=request.item_id,
                stage=request.stage,
                result_data={"ocr_text": "placeholder"},
                provider_used="google_vision",
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"OCR execution failed: {e}")
            
            return TaskExecutionResult(
                success=False,
                session_id=request.session_id,
                item_id=request.item_id,
                stage=request.stage,
                result_data={},
                provider_used="none",
                execution_time=execution_time,
                error=str(e)
            )
    
    
    # ==========================================
    # Private Implementation Methods
    # ==========================================
    
    async def _execute_real_translation(self, request: TaskExecutionRequest, start_time: float) -> TaskExecutionResult:
        """実際の翻訳実行"""
        try:
            # Primary: Google Translate
            translated_text = await self.google_provider.translate_menu_item(request.item_text)
            
            execution_time = time.time() - start_time
            
            return TaskExecutionResult(
                success=True,
                session_id=request.session_id,
                item_id=request.item_id,
                stage=request.stage,
                result_data={
                    "translated_text": result.translated_text,
                    "confidence": result.confidence,
                    "source_language": result.source_language
                },
                provider_used="google_translate",
                execution_time=execution_time,
                quality_score=result.quality_score,
                confidence=result.confidence
            )
            
        except Exception as e:
            # Fallback: OpenAI
            self.logger.warning(f"Google Translate failed, trying OpenAI fallback: {e}")
            
            try:
                fallback_result = await self.openai_provider.translate_text(
                    text=request.item_text,
                    target_language="English",
                    source_language="Japanese"
                )
                
                execution_time = time.time() - start_time
                
                return TaskExecutionResult(
                    success=True,
                    session_id=request.session_id,
                    item_id=request.item_id,
                    stage=request.stage,
                    result_data={
                        "translated_text": fallback_result.translated_text,
                        "confidence": fallback_result.confidence
                    },
                    provider_used="openai_gpt",
                    execution_time=execution_time,
                    fallback_used=True,
                    quality_score=fallback_result.quality_score,
                    confidence=fallback_result.confidence
                )
                
            except Exception as fallback_error:
                execution_time = time.time() - start_time
                raise Exception(f"Both translation providers failed. Google: {e}, OpenAI: {fallback_error}")
    
    
    async def _execute_test_translation(self, request: TaskExecutionRequest, start_time: float) -> TaskExecutionResult:
        """テスト翻訳実行"""
        # Simulate processing time
        await asyncio.sleep(0.1)
        
        execution_time = time.time() - start_time
        
        return TaskExecutionResult(
            success=True,
            session_id=request.session_id,
            item_id=request.item_id,
            stage=request.stage,
            result_data={
                "translated_text": f"Test translation of: {request.item_text}",
                "confidence": 0.95
            },
            provider_used="test_provider",
            execution_time=execution_time,
            quality_score=0.95,
            confidence=0.95
        )
    
    
    async def _execute_real_description(self, request: TaskExecutionRequest, start_time: float) -> TaskExecutionResult:
        """実際の説明生成実行"""
        try:
            # Extract translated text from metadata
            translated_text = request.metadata.get("translated_text", request.item_text)
            
            # Generate description using OpenAI
            result = await self.openai_provider.generate_description(
                japanese_text=request.item_text,
                english_text=translated_text,
                category=request.category
            )
            
            execution_time = time.time() - start_time
            
            return TaskExecutionResult(
                success=True,
                session_id=request.session_id,
                item_id=request.item_id,
                stage=request.stage,
                result_data={
                    "description": result.description,
                    "ingredients": result.ingredients,
                    "preparation": result.preparation
                },
                provider_used="openai_gpt",
                execution_time=execution_time,
                quality_score=result.quality_score,
                confidence=result.confidence
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            raise Exception(f"Description generation failed: {e}")
    
    
    async def _execute_test_description(self, request: TaskExecutionRequest, start_time: float) -> TaskExecutionResult:
        """テスト説明生成実行"""
        # Simulate processing time
        await asyncio.sleep(0.1)
        
        execution_time = time.time() - start_time
        
        return TaskExecutionResult(
            success=True,
            session_id=request.session_id,
            item_id=request.item_id,
            stage=request.stage,
            result_data={
                "description": f"Test description for: {request.item_text}",
                "ingredients": ["test ingredient 1", "test ingredient 2"],
                "preparation": "Test preparation method"
            },
            provider_used="test_provider",
            execution_time=execution_time,
            quality_score=0.90,
            confidence=0.90
        )
    
    
    async def _execute_real_image(self, request: TaskExecutionRequest, start_time: float) -> TaskExecutionResult:
        """実際の画像生成実行"""
        try:
            # Extract description from metadata
            description = request.metadata.get("description", f"Japanese dish: {request.item_text}")
            
            # Generate image using Google Imagen
            result = await self.google_provider.generate_image(
                prompt=description,
                category=request.category
            )
            
            execution_time = time.time() - start_time
            
            return TaskExecutionResult(
                success=True,
                session_id=request.session_id,
                item_id=request.item_id,
                stage=request.stage,
                result_data={
                    "image_url": result.image_url,
                    "image_path": result.image_path,
                    "prompt_used": result.prompt_used
                },
                provider_used="google_imagen",
                execution_time=execution_time,
                quality_score=result.quality_score,
                confidence=result.confidence
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            raise Exception(f"Image generation failed: {e}")
    
    
    async def _execute_test_image(self, request: TaskExecutionRequest, start_time: float) -> TaskExecutionResult:
        """テスト画像生成実行"""
        # Simulate processing time
        await asyncio.sleep(0.1)
        
        execution_time = time.time() - start_time
        
        return TaskExecutionResult(
            success=True,
            session_id=request.session_id,
            item_id=request.item_id,
            stage=request.stage,
            result_data={
                "image_url": f"https://test.example.com/image_{request.item_id}.jpg",
                "image_path": f"/test/images/item_{request.item_id}.jpg",
                "prompt_used": f"Test image for: {request.item_text}"
            },
            provider_used="test_provider",
            execution_time=execution_time,
            quality_score=0.85,
            confidence=0.85
        )
    
    
    # ==========================================
    # Statistics and Health Methods
    # ==========================================
    
    def get_execution_statistics(self) -> Dict[str, Any]:
        """実行統計取得"""
        return {
            "service_status": "active",
            "providers_available": {
                "google": hasattr(self, 'google_provider') and self.google_provider is not None,
                "openai": hasattr(self, 'openai_provider') and self.openai_provider is not None
            },
            "supported_stages": [stage.value for stage in TaskStage],
            "supported_modes": [mode.value for mode in ExecutionMode]
        }
    
    
    async def health_check(self) -> Dict[str, Any]:
        """ヘルスチェック"""
        try:
            # Test provider availability
            google_healthy = await self._check_provider_health(self.google_provider)
            openai_healthy = await self._check_provider_health(self.openai_provider)
            
            return {
                "status": "healthy",
                "providers": {
                    "google": google_healthy,
                    "openai": openai_healthy
                },
                "overall_health": google_healthy or openai_healthy  # At least one provider should work
            }
            
        except Exception as e:
            return {
                "status": "degraded",
                "error": str(e),
                "providers": {
                    "google": False,
                    "openai": False
                },
                "overall_health": False
            }
    
    
    async def _check_provider_health(self, provider) -> bool:
        """プロバイダーヘルスチェック"""
        try:
            # Simple health check - just verify the provider exists and is initialized
            return provider is not None and hasattr(provider, 'translate_text')
        except Exception:
            return False


# ==========================================
# Export
# ==========================================

__all__ = [
    "TaskExecutionService",
    "TaskExecutionRequest", 
    "TaskExecutionResult",
    "ExecutionMode",
    "TaskStage"
]
"""
🚀 WorkflowOrchestrator - OCR統合ワークフロー管理

このサービスはOCR → カテゴリ分類 → 並列処理の統合フローを管理します。
複雑なワークフローをエンドポイントから分離し、再利用可能なサービスとして提供します。
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from fastapi import UploadFile

from .menu_processing_service import MenuProcessingService, ProcessingResult
from .file_handler import FileHandler, FileInfo


@dataclass
class OCRResult:
    """OCR結果"""
    success: bool
    extracted_text: str
    provider: str
    error: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_summary(self) -> Dict[str, Any]:
        """サマリー形式に変換"""
        if self.success:
            return {
                "success": True,
                "extracted_text_length": len(self.extracted_text),
                "provider": self.provider,
                "preview": self.extracted_text[:200] + "..." if len(self.extracted_text) > 200 else self.extracted_text
            }
        else:
            return {
                "success": False,
                "error": self.error,
                "provider": self.provider
            }


@dataclass
class CategoryResult:
    """カテゴリ分類結果"""
    success: bool
    categories: Dict[str, list]
    provider: str
    error: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_summary(self) -> Dict[str, Any]:
        """サマリー形式に変換"""
        if self.success:
            return {
                "success": True,
                "categories": list(self.categories.keys()),
                "total_items": sum(len(items) for items in self.categories.values()),
                "provider": self.provider
            }
        else:
            return {
                "success": False,
                "error": self.error,
                "provider": self.provider
            }


@dataclass
class WorkflowResult:
    """ワークフロー結果"""
    success: bool
    session_id: str
    ocr_result: OCRResult
    category_result: CategoryResult
    processing_result: ProcessingResult
    file_info: FileInfo
    message: str
    streaming_url: str
    status_url: str
    error: Optional[str] = None


class WorkflowOrchestrator:
    """
    OCR統合ワークフロー管理サービス
    
    責任:
    - OCR → カテゴリ分類 → 並列処理フローの統合
    - ファイル管理と各サービスの調整
    - エラー処理と回復
    - ワークフロー状態管理
    """

    def __init__(
        self,
        menu_processing_service: MenuProcessingService,
        file_handler: FileHandler
    ):
        self.menu_processing_service = menu_processing_service
        self.file_handler = file_handler

    async def process_ocr_to_parallel(
        self, 
        file: UploadFile, 
        use_real_apis: bool = True
    ) -> WorkflowResult:
        """
        OCR → カテゴリ分類 → 並列処理の完全統合フロー
        
        Args:
            file: アップロードされた画像ファイル
            use_real_apis: 実際のAPI統合を使用するかどうか
            
        Returns:
            WorkflowResult: ワークフロー結果
        """
        file_info = None
        
        try:
            # セッションID生成（一時的）
            import time
            import uuid
            session_id = f"ocr_parallel_{int(time.time())}_{str(uuid.uuid4())[:8]}"
            
            # Step 1: ファイル処理
            file_info = await self._process_file(file, session_id)
            
            # Step 2: OCR処理
            ocr_result = await self._process_ocr(file_info)
            
            if not ocr_result.success:
                raise Exception(f"OCR failed: {ocr_result.error}")
            
            # Step 3: カテゴリ分類
            category_result = await self._process_categorization(ocr_result.extracted_text, session_id)
            
            if not category_result.success:
                raise Exception(f"Categorization failed: {category_result.error}")
            
            # Step 4: 並列処理開始
            processing_result = await self._start_parallel_processing(
                category_result.categories, not use_real_apis
            )
            
            if not processing_result.success:
                raise Exception(f"Parallel processing failed: {processing_result.error}")
            
            # Step 5: 成功レスポンス構築
            workflow_result = WorkflowResult(
                success=True,
                session_id=processing_result.session.session_id,
                ocr_result=ocr_result,
                category_result=category_result,
                processing_result=processing_result,
                file_info=file_info,
                message=self._build_success_message(ocr_result, category_result, processing_result),
                streaming_url=processing_result.streaming_url,
                status_url=processing_result.status_url
            )
            
            return workflow_result
            
        except Exception as e:
            # エラー時の結果構築
            error_result = WorkflowResult(
                success=False,
                session_id="",
                ocr_result=OCRResult(False, "", "", str(e)),
                category_result=CategoryResult(False, {}, "", str(e)),
                processing_result=ProcessingResult(False, None, None, "", "", "", str(e)),
                file_info=file_info,
                message="OCR to parallel processing failed",
                streaming_url="",
                status_url="",
                error=str(e)
            )
            
            return error_result
            
        finally:
            # ファイルクリーンアップ
            if file_info:
                await self.file_handler.cleanup_file(file_info.file_id)

    async def process_standalone_ocr(self, file: UploadFile) -> Dict[str, Any]:
        """
        単体OCR処理
        
        Args:
            file: アップロードファイル
            
        Returns:
            Dict: OCR結果
        """
        file_info = None
        
        try:
            # ファイル保存
            file_info = await self.file_handler.save_temp_file(file, prefix="standalone_ocr")
            
            # OCR処理
            ocr_result = await self._process_ocr(file_info)
            
            if ocr_result.success:
                return {
                    "status": "success",
                    "extracted_text": ocr_result.extracted_text,
                    "file_name": file.filename,
                    "provider": ocr_result.provider
                }
            else:
                return {
                    "status": "error",
                    "message": f"OCR processing failed: {ocr_result.error}",
                    "file_name": file.filename
                }
        
        except Exception as e:
            return {
                "status": "error",
                "message": f"OCR processing failed: {str(e)}",
                "file_name": file.filename if file else "unknown"
            }
        
        finally:
            # ファイルクリーンアップ
            if file_info:
                await self.file_handler.cleanup_file(file_info.file_id)

    def get_ocr_service_status(self) -> Dict[str, Any]:
        """
        OCRサービス状態取得
        
        Returns:
            Dict: サービス状態
        """
        try:
            # 直接Google Providerの状態確認
            from app.services.providers.google import GoogleProviderService
            google_provider = GoogleProviderService()
            
            # Geminiサービスの状態確認
            gemini_available = google_provider.is_gemini_available()
            vision_available = google_provider.is_vision_available()
            is_healthy = gemini_available or vision_available
            
            response = {
                "status": "healthy" if is_healthy else "degraded",
                "ocr_engine": "gemini-2.0-flash",
                "mode": "unified_integration",
                "gemini_available": gemini_available,
                "vision_available": vision_available,
                "service_details": {
                    "gemini_available": gemini_available,
                    "vision_available": vision_available,
                    "provider": "google"
                },
                "integration_features": {
                    "standalone_ocr": True,
                    "integrated_flow": True,
                    "category_classification": True,
                    "parallel_processing": True
                },
                "features": [
                    "japanese_menu_optimized",
                    "high_precision_ocr", 
                    "context_aware_extraction",
                    "multimodal_understanding"
                ] if is_healthy else [],
                "recommendations": []
            }
            
            if not is_healthy:
                response["recommendations"].extend([
                    "Check Google API credentials",
                    "Verify GEMINI_API_KEY is set",
                    "Ensure Google Cloud Vision API is enabled"
                ])
            
            return response
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "ocr_engine": "gemini-2.0-flash",
                "mode": "unified_integration",
                "recommendations": [
                    "Check Google Provider service initialization",
                    "Verify API credentials",
                    "Check service dependencies"
                ]
            }

    async def _process_file(self, file: UploadFile, session_id: str) -> FileInfo:
        """ファイル処理"""
        return await self.file_handler.save_ocr_temp_file(file, session_id)

    async def _process_ocr(self, file_info: FileInfo) -> OCRResult:
        """OCR処理（フォールバック機能付き）"""
        try:
            from app.services.providers.google import GoogleProviderService
            
            print(f"🔍 [OCR] Starting OCR with Gemini 2.0 Flash: {file_info.original_name}")
            
            google_provider = GoogleProviderService()
            
            # まずGemini 2.0 Flashで試行
            try:
                ocr_result = await google_provider.extract_text_gemini(
                    image_path=file_info.saved_path, 
                    session_id=file_info.session_id
                )
                
                if ocr_result.success:
                    print(f"✅ [OCR] Gemini extracted {len(ocr_result.extracted_text)} characters")
                    return OCRResult(
                        success=True,
                        extracted_text=ocr_result.extracted_text,
                        provider="Gemini 2.0 Flash",
                        metadata={
                            "file_info": file_info.to_dict(),
                            "processing_time": getattr(ocr_result, 'processing_time', None)
                        }
                    )
                else:
                    print(f"⚠️ [OCR] Gemini failed: {ocr_result.error}, trying Google Vision fallback...")
            except Exception as gemini_error:
                print(f"⚠️ [OCR] Gemini exception: {gemini_error}, trying Google Vision fallback...")
            
            # Gemini失敗時のGoogle Visionフォールバック
            try:
                print(f"🔄 [OCR] Fallback to Google Vision API: {file_info.original_name}")
                vision_result = await google_provider.extract_text(
                    image_path=file_info.saved_path,
                    session_id=file_info.session_id
                )
                
                if vision_result.success:
                    print(f"✅ [OCR] Google Vision extracted {len(vision_result.extracted_text)} characters")
                    return OCRResult(
                        success=True,
                        extracted_text=vision_result.extracted_text,
                        provider="Google Vision API (Fallback)",
                        metadata={
                            "file_info": file_info.to_dict(),
                            "fallback_used": True,
                            "processing_time": getattr(vision_result, 'processing_time', None)
                        }
                    )
                else:
                    return OCRResult(
                        success=False,
                        extracted_text="",
                        provider="Google Vision API (Fallback)",
                        error=vision_result.error
                    )
            except Exception as vision_error:
                return OCRResult(
                    success=False,
                    extracted_text="",
                    provider="All OCR Engines",
                    error=f"Both Gemini and Vision failed: {vision_error}"
                )
        
        except Exception as e:
            return OCRResult(
                success=False,
                extracted_text="",
                provider="Gemini 2.0 Flash",
                error=str(e)
            )

    async def _process_categorization(self, extracted_text: str, session_id: str) -> CategoryResult:
        """カテゴリ分類処理"""
        try:
            # 直接OpenAI Providerを使用（category serviceラッパーを削除）
            from app.services.providers.openai import OpenAIProviderService
            
            print(f"🏷️ [CATEGORY] Starting categorization with OpenAI Function Calling")
            
            openai_provider = OpenAIProviderService()
            category_result = await openai_provider.categorize_menu(
                extracted_text=extracted_text, 
                session_id=session_id
            )
            
            if category_result.success:
                print(f"✅ [CATEGORY] Categorized into {len(category_result.categories)} categories")
                return CategoryResult(
                    success=True,
                    categories=category_result.categories,
                    provider="OpenAI Function Calling",
                    metadata={
                        "extracted_text_length": len(extracted_text),
                        "processing_time": getattr(category_result, 'processing_time', None)
                    }
                )
            else:
                return CategoryResult(
                    success=False,
                    categories={},
                    provider="OpenAI Function Calling",
                    error=category_result.error
                )
        
        except Exception as e:
            return CategoryResult(
                success=False,
                categories={},
                provider="OpenAI Function Calling",
                error=str(e)
            )

    async def _start_parallel_processing(
        self, 
        categories: Dict[str, list], 
        test_mode: bool
    ) -> ProcessingResult:
        """並列処理開始"""
        try:
            print(f"🚀 [PARALLEL] Starting parallel task processing")
            
            processing_result = await self.menu_processing_service.start_categorized_processing(
                categories=categories,
                test_mode=test_mode
            )
            
            if processing_result.success:
                total_items = sum(len(items) for items in categories.values())
                print(f"✅ [PARALLEL] Queued {total_items} items for parallel processing")
            
            return processing_result
            
        except Exception as e:
            return ProcessingResult(
                success=False,
                session=None,
                task_batch=None,
                message="Parallel processing failed",
                streaming_url="",
                status_url="",
                error=str(e)
            )

    def _build_success_message(
        self, 
        ocr_result: OCRResult, 
        category_result: CategoryResult, 
        processing_result: ProcessingResult
    ) -> str:
        """成功メッセージ構築"""
        total_items = sum(len(items) for items in category_result.categories.values())
        category_count = len(category_result.categories)
        api_mode = processing_result.session.api_mode
        
        return (
            f"🎉 Complete OCR → Categorization → Parallel Processing pipeline started! "
            f"{total_items} items in {category_count} categories queued with {api_mode}. "
            f"APIs: Gemini OCR + OpenAI Categorization + Google Translate + OpenAI Description + Google Imagen 3"
        )
"""
Enhanced OCR Service - 強化版OCRサービス
新しい基盤クラスを使用した高度なOCRサービス実装

新機能:
- 統一されたエラーハンドリング
- 詳細な品質指標
- パフォーマンス測定
- 既存システムとの完全互換性
"""
import os
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field

from app.services.base import (
    BaseResult, BaseService, ErrorType,
    ValidationError, FileError, APIError, ServiceUnavailableError
)
from app.services.ocr.base import OCRResult, BaseOCRService
from app.core.config import settings


class EnhancedOCRResult(BaseResult):
    """
    強化版OCR結果クラス
    
    BaseResultを継承し、OCR固有の機能を追加
    既存のOCRResultとの完全互換性を維持
    """
    
    # OCR固有フィールド
    extracted_text: str = Field(default="", description="抽出されたテキスト")
    
    # 新しい高度な機能
    language_detected: Optional[str] = Field(default=None, description="検出された言語")
    text_regions: List[Dict[str, Any]] = Field(default_factory=list, description="テキスト領域情報")
    ocr_engine: Optional[str] = Field(default=None, description="使用されたOCRエンジン")
    
    # 品質指標（OCR特化）
    text_clarity_score: Optional[float] = Field(default=None, description="テキスト明瞭度")
    character_count: Optional[int] = Field(default=None, description="文字数")
    word_count: Optional[int] = Field(default=None, description="単語数")
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換（OCR特化情報含む）"""
        result = super().to_dict()
        
        # OCR固有の情報を追加
        result["extracted_text"] = self.extracted_text
        
        if self.language_detected:
            result["language_detected"] = self.language_detected
        if self.text_regions:
            result["text_regions"] = self.text_regions
        if self.ocr_engine:
            result["ocr_engine"] = self.ocr_engine
        if self.text_clarity_score is not None:
            result["text_clarity_score"] = self.text_clarity_score
        if self.character_count is not None:
            result["character_count"] = self.character_count
        if self.word_count is not None:
            result["word_count"] = self.word_count
            
        return result
    
    def get_text_statistics(self) -> Dict[str, Any]:
        """テキスト統計を取得"""
        text = self.extracted_text
        
        stats = {
            "character_count": len(text),
            "word_count": len(text.split()) if text else 0,
            "line_count": len(text.splitlines()) if text else 0,
            "has_japanese": any('\u3040' <= char <= '\u309F' or '\u30A0' <= char <= '\u30FF' or '\u4E00' <= char <= '\u9FAF' for char in text),
            "has_numbers": any(char.isdigit() for char in text),
            "has_symbols": any(char in '¥円$€£' for char in text)
        }
        
        # 既存フィールドを更新
        self.character_count = stats["character_count"]
        self.word_count = stats["word_count"]
        
        return stats


class EnhancedOCRService(BaseService):
    """
    強化版OCRサービス
    
    BaseServiceを継承し、統一されたエラーハンドリング、
    パフォーマンス測定、品質指標を提供
    """
    
    def __init__(self):
        super().__init__()
        self.provider = "enhanced_ocr"
        self._ocr_stats = {
            "total_images_processed": 0,
            "successful_extractions": 0,
            "average_text_length": 0.0,
            "languages_detected": set()
        }
    
    def is_available(self) -> bool:
        """サービス利用可能性チェック"""
        # 必要な設定が存在するかチェック
        required_settings = ["GEMINI_API_KEY", "GOOGLE_CREDENTIALS_JSON"]
        return all(hasattr(settings, key) and getattr(settings, key) for key in required_settings)
    
    def get_capabilities(self) -> List[str]:
        """OCRサービスの機能一覧"""
        return [
            "text_extraction",
            "image_processing", 
            "japanese_text_recognition",
            "menu_text_parsing",
            "quality_assessment",
            "performance_monitoring",
            "error_recovery",
            "language_detection",
            "text_region_analysis"
        ]
    
    async def extract_text(
        self, 
        image_path: str, 
        session_id: Optional[str] = None
    ) -> EnhancedOCRResult:
        """
        画像からテキストを抽出（強化版）
        
        エラーハンドリング、パフォーマンス測定、品質評価を含む
        """
        start_time = datetime.now()
        
        try:
            # 入力検証
            self._validate_image_input(image_path)
            
            # OCR実行
            result = await self._perform_extraction_with_monitoring(
                image_path, 
                session_id, 
                start_time
            )
            
            # 統計更新
            self._update_ocr_stats(result)
            
            return result
            
        except ValidationError as e:
            # バリデーションエラーを適切にハンドル
            processing_time = (datetime.now() - start_time).total_seconds()
            self._update_performance_stats(processing_time, False)
            
            return self._create_error_result(
                str(e),
                EnhancedOCRResult,
                ErrorType.VALIDATION_ERROR,
                e.suggestions,
                context={
                    "image_path": image_path,
                    "session_id": session_id,
                    "field_name": getattr(e, 'field_name', None)
                }
            )
            
        except FileError as e:
            # ファイルエラーを適切にハンドル
            processing_time = (datetime.now() - start_time).total_seconds()
            self._update_performance_stats(processing_time, False)
            
            return self._create_error_result(
                str(e),
                EnhancedOCRResult,
                ErrorType.FILE_ERROR,
                e.suggestions,
                context={
                    "image_path": image_path,
                    "session_id": session_id,
                    "file_path": getattr(e, 'file_path', None)
                }
            )
            
        except APIError as e:
            # APIエラーを適切にハンドル
            processing_time = (datetime.now() - start_time).total_seconds()
            self._update_performance_stats(processing_time, False)
            
            return self._create_error_result(
                str(e),
                EnhancedOCRResult,
                ErrorType.API_ERROR,
                e.suggestions,
                context={
                    "image_path": image_path,
                    "session_id": session_id,
                    "api_service": getattr(e, 'api_service', None),
                    "status_code": getattr(e, 'status_code', None)
                }
            )
            
        except ServiceUnavailableError as e:
            # サービス利用不可エラーを適切にハンドル
            processing_time = (datetime.now() - start_time).total_seconds()
            self._update_performance_stats(processing_time, False)
            
            return self._create_error_result(
                str(e),
                EnhancedOCRResult,
                ErrorType.SERVICE_UNAVAILABLE,
                e.suggestions,
                context={
                    "image_path": image_path,
                    "session_id": session_id,
                    "service_name": getattr(e, 'service_name', None)
                }
            )
            
        except Exception as e:
            # その他の予期しない例外を適切にハンドル
            processing_time = (datetime.now() - start_time).total_seconds()
            self._update_performance_stats(processing_time, False)
            
            return self._create_error_result(
                f"OCR processing failed: {str(e)}",
                EnhancedOCRResult,
                ErrorType.PROCESSING_ERROR,
                suggestions=[
                    "システム管理者に連絡してください",
                    "しばらく時間をおいて再試行してください",
                    "ログを確認してください"
                ],
                context={
                    "image_path": image_path,
                    "session_id": session_id,
                    "exception_type": type(e).__name__,
                    "exception_details": str(e)
                }
            )
    
    def _validate_image_input(self, image_path: str) -> None:
        """入力画像の検証（強化版）"""
        if not image_path or not image_path.strip():
            raise ValidationError(
                "Invalid image path: empty or None",
                field_name="image_path",
                suggestions=[
                    "有効な画像ファイルパスを指定してください",
                    "パスが空でないか確認してください"
                ]
            )
        
        if not os.path.exists(image_path):
            raise FileError(
                f"Image file not found: {image_path}",
                file_path=image_path,
                suggestions=[
                    "ファイルパスが正しいか確認してください",
                    "ファイルが存在するか確認してください",
                    "アクセス権限を確認してください"
                ]
            )
        
        # ファイルサイズチェック
        try:
            file_size = os.path.getsize(image_path)
            if file_size == 0:
                raise FileError(
                    "Image file is empty",
                    file_path=image_path,
                    suggestions=["有効な画像ファイルを選択してください"]
                )
            
            max_size = getattr(settings, 'MAX_FILE_SIZE', 10 * 1024 * 1024)  # 10MB デフォルト
            if file_size > max_size:
                max_mb = max_size // (1024 * 1024)
                raise FileError(
                    f"Image file too large: {file_size} bytes (max: {max_mb}MB)",
                    file_path=image_path,
                    suggestions=[
                        f"ファイルサイズを{max_mb}MB以下にしてください",
                        "画像を圧縮してください"
                    ]
                )
        except OSError as e:
            raise FileError(
                f"Unable to access image file: {str(e)}",
                file_path=image_path,
                suggestions=["ファイルアクセス権限を確認してください"]
            )
    
    async def _perform_extraction_with_monitoring(
        self,
        image_path: str,
        session_id: Optional[str],
        start_time: datetime
    ) -> EnhancedOCRResult:
        """監視機能付きOCR実行"""
        
        try:
            # 実際のOCR処理（サブクラスで実装）
            result = await self._perform_extraction(image_path, session_id)
            
            # 処理時間設定
            result.set_processing_time(start_time)
            
            # テキスト統計計算
            text_stats = result.get_text_statistics()
            
            # 品質評価
            quality_metrics = self._assess_quality(result, text_stats)
            result.set_quality_metrics(**quality_metrics)
            
            # 言語検出
            if text_stats["has_japanese"]:
                result.language_detected = "japanese"
            
            # OCRエンジン情報設定
            result.ocr_engine = "enhanced_ocr_v2"
            
            # メタデータ強化
            result.add_metadata("text_statistics", text_stats)
            result.add_metadata("processing_details", {
                "image_path": os.path.basename(image_path),
                "session_id": session_id,
                "processing_timestamp": datetime.now().isoformat()
            })
            
            return result
            
        except Exception as e:
            # OCR固有のエラーハンドリング
            if "API" in str(e) or "quota" in str(e).lower():
                raise APIError(
                    f"OCR API error: {str(e)}",
                    api_service="gemini_vision",
                    suggestions=[
                        "APIキーを確認してください",
                        "API利用制限を確認してください",
                        "しばらく時間をおいて再試行してください"
                    ]
                )
            else:
                raise Exception(f"OCR processing failed: {str(e)}")
    
    async def _perform_extraction(
        self, 
        image_path: str, 
        session_id: Optional[str] = None
    ) -> EnhancedOCRResult:
        """
        実際のOCR処理（サブクラスでオーバーライド）
        
        このメソッドは具体的なOCRエンジン（Gemini、Google Vision等）
        で実装される
        """
        # デフォルト実装（テスト用）
        return self._create_success_result(
            EnhancedOCRResult,
            extracted_text=f"Enhanced OCR extracted text from {os.path.basename(image_path)}"
        )
    
    def _assess_quality(
        self, 
        result: EnhancedOCRResult, 
        text_stats: Dict[str, Any]
    ) -> Dict[str, float]:
        """OCR結果の品質を評価"""
        
        quality_score = 0.0
        confidence = 0.0
        
        # 文字数ベースの評価
        char_count = text_stats["character_count"]
        if char_count > 0:
            quality_score += 0.3  # テキストが抽出された
            
            if char_count > 20:
                quality_score += 0.2  # 十分な長さ
            
            if text_stats["has_japanese"]:
                quality_score += 0.2  # 日本語検出
            
            if text_stats["has_numbers"]:
                quality_score += 0.1  # 数字検出（価格等）
            
            if text_stats["has_symbols"]:
                quality_score += 0.1  # 通貨記号等
            
            # 行数による評価
            if text_stats["line_count"] > 1:
                quality_score += 0.1  # 複数行
        
        # 信頼度は品質スコアを基に計算
        confidence = min(quality_score, 1.0)
        
        # テキスト明瞭度の仮計算
        text_clarity = min(char_count / 100.0, 1.0) if char_count > 0 else 0.0
        result.text_clarity_score = text_clarity
        
        return {
            "quality_score": quality_score,
            "confidence": confidence
        }
    
    def _update_ocr_stats(self, result: EnhancedOCRResult) -> None:
        """OCR統計を更新"""
        self._ocr_stats["total_images_processed"] += 1
        
        if result.success:
            self._ocr_stats["successful_extractions"] += 1
            
            # 平均テキスト長を更新
            text_length = len(result.extracted_text)
            total_extractions = self._ocr_stats["successful_extractions"]
            current_avg = self._ocr_stats["average_text_length"]
            self._ocr_stats["average_text_length"] = (
                (current_avg * (total_extractions - 1) + text_length) / total_extractions
            )
            
            # 検出言語を追加
            if result.language_detected:
                self._ocr_stats["languages_detected"].add(result.language_detected)
    
    def create_compatible_result(self, enhanced_result: EnhancedOCRResult) -> OCRResult:
        """既存OCRResultとの互換性のため変換"""
        return OCRResult(
            success=enhanced_result.success,
            extracted_text=enhanced_result.extracted_text,
            error=enhanced_result.error,
            metadata=enhanced_result.metadata
        )
    
    def get_ocr_statistics(self) -> Dict[str, Any]:
        """OCR固有の統計を取得"""
        stats = self._ocr_stats.copy()
        stats["languages_detected"] = list(stats["languages_detected"])
        
        if stats["total_images_processed"] > 0:
            stats["success_rate"] = stats["successful_extractions"] / stats["total_images_processed"]
        else:
            stats["success_rate"] = 0.0
        
        return stats 
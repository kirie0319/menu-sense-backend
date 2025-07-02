from abc import ABC, abstractmethod
from typing import Dict, Optional, Union, List, Any
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
import os
import re
from app.core.config import settings

class OCRProvider(Enum):
    """OCRプロバイダーの列挙型"""
    GEMINI = "gemini"
    GOOGLE_VISION = "google_vision"
    ENHANCED = "enhanced"

class OCRResult(BaseModel):
    """
    OCR処理結果を格納するクラス
    
    Enhanced機能統合版：
    - 既存APIとの完全互換性を維持
    - 品質指標・統計機能を追加
    - パフォーマンス測定機能を追加
    """
    
    # 既存フィールド（互換性維持）
    success: bool
    extracted_text: str = ""
    error: Optional[str] = None
    metadata: Dict = {}
    
    # Enhanced機能追加フィールド（オプション）
    processing_time: Optional[float] = Field(default=None, description="処理時間（秒）")
    ocr_engine: Optional[str] = Field(default=None, description="使用されたOCRエンジン")
    language_detected: Optional[str] = Field(default=None, description="検出された言語")
    
    # 品質指標（Enhanced機能）
    quality_score: Optional[float] = Field(default=None, description="品質スコア (0-1)")
    confidence: Optional[float] = Field(default=None, description="信頼度 (0-1)")
    text_clarity_score: Optional[float] = Field(default=None, description="テキスト明瞭度")
    character_count: Optional[int] = Field(default=None, description="文字数")
    word_count: Optional[int] = Field(default=None, description="単語数")
    line_count: Optional[int] = Field(default=None, description="行数")
    
    # 統計情報（Enhanced機能）
    text_regions: List[Dict[str, Any]] = Field(default_factory=list, description="テキスト領域情報")
    extraction_stats: Dict[str, Any] = Field(default_factory=dict, description="抽出統計")
    
    def to_dict(self) -> Dict:
        """辞書形式に変換（既存互換性維持）"""
        result = {
            "success": self.success,
            "extracted_text": self.extracted_text
        }
        if self.error:
            result["error"] = self.error
        if self.metadata:
            result.update(self.metadata)
        return result
    
    def get_text_statistics(self) -> Dict[str, Any]:
        """テキスト統計を取得（Enhanced機能）"""
        text = self.extracted_text
        
        # 基本統計
        char_count = len(text)
        word_count = len(text.split()) if text else 0
        line_count = len(text.splitlines()) if text else 0
        
        # 日本語文字の検出（ひらがな、カタカナ、漢字のUnicode範囲）
        has_japanese = bool(re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', text))
        has_numbers = bool(re.search(r'\d', text))
        has_symbols = bool(re.search(r'[￥¥$€£]', text))
        
        stats = {
            "character_count": char_count,
            "word_count": word_count,
            "line_count": line_count,
            "has_japanese": has_japanese,
            "has_numbers": has_numbers,
            "has_symbols": has_symbols,
            "text_length_category": self._categorize_text_length(char_count),
            "processing_time": self.processing_time,
            "quality_score": self.quality_score,
            "confidence": self.confidence,
            "language_detected": self.language_detected
        }
        
        # 既存フィールドを更新
        self.character_count = char_count
        self.word_count = word_count
        self.line_count = line_count
        
        return stats
    
    def _categorize_text_length(self, char_count: int) -> str:
        """文字数に基づくカテゴリ分類"""
        if char_count == 0:
            return "empty"
        elif char_count < 20:
            return "short"
        elif char_count < 100:
            return "medium"
        elif char_count < 500:
            return "long"
        else:
            return "very_long"
    
    def set_quality_metrics(self, quality_score: float, confidence: float, **kwargs) -> None:
        """品質メトリクスを設定（Enhanced機能）"""
        self.quality_score = quality_score
        self.confidence = confidence
        
        # 追加のメトリクス
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def set_processing_time(self, start_time: datetime) -> None:
        """処理時間を設定（Enhanced機能）"""
        self.processing_time = (datetime.now() - start_time).total_seconds()
    
    def add_metadata(self, key: str, value: Any) -> None:
        """メタデータを追加（Enhanced機能）"""
        self.metadata[key] = value


class BaseOCRService(ABC):
    """
    OCRサービスの基底クラス
    
    Enhanced機能統合版：
    - 既存APIとの完全互換性を維持
    - 統計機能・品質評価を追加
    - エラーハンドリングを強化
    """
    
    def __init__(self):
        self.service_name = self.__class__.__name__
        self.provider = None
        
        # Enhanced機能：統計管理
        self._ocr_stats = {
            "total_images_processed": 0,
            "successful_extractions": 0,
            "average_text_length": 0.0,
            "average_processing_time": 0.0,
            "languages_detected": set()
        }
    
    def validate_image_file(self, image_path: str) -> None:
        """画像ファイルの検証（既存互換）"""
        # ファイル存在チェック
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"画像ファイルが見つかりません: {image_path}")
        
        # ファイルサイズチェック
        file_size = os.path.getsize(image_path)
        if file_size == 0:
            raise ValueError("画像ファイルが空です")
        
        if file_size > settings.MAX_FILE_SIZE:
            max_size_mb = settings.MAX_FILE_SIZE // (1024*1024)
            raise ValueError(f"画像ファイルが大きすぎます（{max_size_mb}MB以下にしてください）")
    
    def _create_error_result(self, error_message: str, error_type: str = "unknown_error", suggestions: list = None) -> OCRResult:
        """エラー結果を作成（既存互換）"""
        return OCRResult(
            success=False,
            error=error_message,
            metadata={
                "error_type": error_type,
                "suggestions": suggestions or [],
                "service": self.service_name
            }
        )
    
    def _create_success_result(self, extracted_text: str, metadata: Dict = None) -> OCRResult:
        """成功結果を作成（既存互換）"""
        return OCRResult(
            success=True,
            extracted_text=extracted_text,
            metadata={
                **(metadata or {}),
                "service": self.service_name
            }
        )
    
    @abstractmethod
    async def extract_text(self, image_path: str, session_id: str = None) -> OCRResult:
        """
        画像からテキストを抽出する抽象メソッド
        
        Args:
            image_path: 画像ファイルのパス
            session_id: セッションID（進行状況通知用）
            
        Returns:
            OCRResult: 抽出結果
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """サービスが利用可能かどうかを確認"""
        pass
    
    def get_service_info(self) -> Dict:
        """サービス情報を取得（Enhanced機能追加）"""
        base_info = {
            "service_name": self.service_name,
            "available": self.is_available(),
            "capabilities": self.get_capabilities(),
            "supported_formats": ["jpg", "jpeg", "png", "gif", "bmp", "webp"],
            "max_file_size": getattr(settings, 'MAX_FILE_SIZE', 10*1024*1024)  # 10MB default
        }
        
        # Enhanced機能：統計情報追加
        if hasattr(self, '_ocr_stats'):
            base_info["statistics"] = self.get_ocr_statistics()
        
        return base_info
    
    def get_capabilities(self) -> List[str]:
        """サービス機能一覧を取得（Enhanced機能）"""
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
    
    # ========================================
    # Enhanced機能：品質評価・統計管理
    # ========================================
    
    def assess_ocr_quality(
        self, 
        result: OCRResult
    ) -> Dict[str, float]:
        """OCR結果の品質を評価（Enhanced機能）"""
        
        quality_score = 0.0
        confidence = 0.0
        
        text_stats = result.get_text_statistics()
        char_count = text_stats["character_count"]
        
        # 文字数ベースの評価
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
    
    def update_ocr_stats(self, result: OCRResult) -> None:
        """OCR統計を更新（Enhanced機能）"""
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
            
            # 平均処理時間を更新
            if result.processing_time:
                total_extractions = self._ocr_stats["successful_extractions"]
                current_avg = self._ocr_stats["average_processing_time"]
                self._ocr_stats["average_processing_time"] = (
                    (current_avg * (total_extractions - 1) + result.processing_time) / total_extractions
                )
            
            # 検出言語を追加
            if result.language_detected:
                self._ocr_stats["languages_detected"].add(result.language_detected)
    
    def get_ocr_statistics(self) -> Dict[str, Any]:
        """OCR固有の統計を取得（Enhanced機能）"""
        stats = self._ocr_stats.copy()
        stats["languages_detected"] = list(stats["languages_detected"])
        
        if stats["total_images_processed"] > 0:
            stats["success_rate"] = stats["successful_extractions"] / stats["total_images_processed"]
        else:
            stats["success_rate"] = 0.0
        
        return stats
    
    def create_enhanced_result(
        self,
        success: bool,
        extracted_text: str = "",
        error: str = None,
        **kwargs
    ) -> OCRResult:
        """Enhanced機能付きの結果を作成"""
        result = OCRResult(
            success=success,
            extracted_text=extracted_text,
            error=error,
            **kwargs
        )
        
        # 処理時間設定
        if 'start_time' in kwargs:
            result.set_processing_time(kwargs['start_time'])
        
        return result

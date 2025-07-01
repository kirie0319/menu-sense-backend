from typing import Dict, Optional, Any, List
from pydantic import BaseModel, Field
from datetime import datetime
from .exceptions import ErrorType

class BaseResult(BaseModel):
    """
    全サービス結果の基底クラス（強化版）
    
    このクラスは新しいリファクタリング用で、既存のサービスには影響しません。
    段階的に移行していくために使用されます。
    
    新機能:
    - 処理時間の自動追跡
    - 品質指標（信頼度、スコア）
    - 詳細なエラー情報
    - 統一されたメタデータ構造
    """
    
    success: bool
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # 新しい品質指標フィールド
    processing_time: Optional[float] = Field(default=None, description="処理時間（秒）")
    quality_score: Optional[float] = Field(default=None, description="品質スコア（0.0-1.0）")
    confidence: Optional[float] = Field(default=None, description="信頼度（0.0-1.0）")
    suggestions: List[str] = Field(default_factory=list, description="改善提案")
    
    # エラー詳細情報
    error_type: Optional[str] = Field(default=None, description="エラータイプ")
    error_context: Dict[str, Any] = Field(default_factory=dict, description="エラーコンテキスト")
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換（後方互換性あり）"""
        result = {
            "success": self.success
        }
        
        # エラー情報
        if self.error:
            result["error"] = self.error
        
        # 新しい品質指標（利用可能な場合のみ）
        if self.processing_time is not None:
            result["processing_time"] = self.processing_time
        if self.quality_score is not None:
            result["quality_score"] = self.quality_score
        if self.confidence is not None:
            result["confidence"] = self.confidence
        if self.suggestions:
            result["suggestions"] = self.suggestions
        if self.error_type:
            result["error_type"] = self.error_type
        if self.error_context:
            result["error_context"] = self.error_context
        
        # メタデータを追加（既存の動作を維持）
        if self.metadata:
            result.update(self.metadata)
            
        return result
    
    def add_metadata(self, key: str, value: Any) -> None:
        """メタデータを追加"""
        self.metadata[key] = value
    
    def set_processing_time(self, start_time: datetime) -> None:
        """処理時間を自動計算して設定"""
        end_time = datetime.now()
        self.processing_time = (end_time - start_time).total_seconds()
        self.add_metadata("start_time", start_time.isoformat())
        self.add_metadata("end_time", end_time.isoformat())
    
    def set_quality_metrics(
        self, 
        quality_score: Optional[float] = None,
        confidence: Optional[float] = None
    ) -> None:
        """品質指標を設定"""
        if quality_score is not None:
            self.quality_score = max(0.0, min(1.0, quality_score))  # 0.0-1.0に制限
        if confidence is not None:
            self.confidence = max(0.0, min(1.0, confidence))  # 0.0-1.0に制限
    
    def add_suggestion(self, suggestion: str) -> None:
        """改善提案を追加"""
        if suggestion and suggestion not in self.suggestions:
            self.suggestions.append(suggestion)
    
    def add_suggestions(self, suggestions: List[str]) -> None:
        """複数の改善提案を追加"""
        for suggestion in suggestions:
            self.add_suggestion(suggestion)
    
    def set_error_details(
        self, 
        error_type: ErrorType,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """詳細なエラー情報を設定"""
        self.error_type = error_type.value
        if context:
            self.error_context.update(context)
    
    def is_success(self) -> bool:
        """成功かどうかを判定"""
        return self.success and not self.error
    
    def is_high_quality(self, threshold: float = 0.8) -> bool:
        """高品質な結果かどうかを判定"""
        if not self.is_success():
            return False
        
        # 品質スコアがあればそれを使用
        if self.quality_score is not None:
            return self.quality_score >= threshold
        
        # 信頼度があればそれを使用
        if self.confidence is not None:
            return self.confidence >= threshold
        
        # どちらもない場合は成功していれば高品質とみなす
        return True
    
    def get_error_details(self) -> Dict[str, Any]:
        """エラー詳細を取得"""
        return {
            "has_error": bool(self.error),
            "error_message": self.error,
            "error_type": self.error_type,
            "error_context": self.error_context,
            "suggestions": self.suggestions
        }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """パフォーマンス概要を取得"""
        return {
            "success": self.success,
            "processing_time": self.processing_time,
            "quality_score": self.quality_score,
            "confidence": self.confidence,
            "is_high_quality": self.is_high_quality(),
            "suggestion_count": len(self.suggestions)
        } 
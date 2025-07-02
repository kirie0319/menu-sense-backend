from abc import ABC, abstractmethod
from typing import Dict, Optional, List, Any
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
import re
from app.core.config import settings

class CategoryProvider(Enum):
    """カテゴリ分類プロバイダーの列挙型"""
    OPENAI = "openai"
    GOOGLE_TRANSLATE = "google_translate"
    ENHANCED = "enhanced"

class CategoryResult(BaseModel):
    """
    カテゴリ分類結果を格納するクラス
    
    Enhanced機能統合版：
    - 既存APIとの完全互換性を維持
    - 品質指標・統計機能を追加
    - パフォーマンス測定機能を追加
    """
    
    # 既存フィールド（互換性維持）
    success: bool
    categories: Dict[str, List[Dict]] = {}
    uncategorized: List[str] = []
    error: Optional[str] = None
    metadata: Dict = {}
    
    # Enhanced機能追加フィールド（オプション）
    total_items: Optional[int] = Field(default=None, description="総アイテム数")
    categorized_items: Optional[int] = Field(default=None, description="分類済みアイテム数")
    processing_time: Optional[float] = Field(default=None, description="処理時間（秒）")
    categorization_method: Optional[str] = Field(default=None, description="分類手法")
    
    # 品質指標（Enhanced機能）
    quality_score: Optional[float] = Field(default=None, description="品質スコア (0-1)")
    confidence: Optional[float] = Field(default=None, description="信頼度 (0-1)")
    coverage_score: Optional[float] = Field(default=None, description="分類カバレッジ")
    balance_score: Optional[float] = Field(default=None, description="カテゴリバランス")
    accuracy_estimate: Optional[float] = Field(default=None, description="精度推定")
    
    # 統計情報（Enhanced機能）
    category_confidence: Dict[str, float] = Field(default_factory=dict, description="カテゴリごとの信頼度")
    extraction_stats: Dict[str, Any] = Field(default_factory=dict, description="抽出統計")
    
    def to_dict(self) -> Dict:
        """辞書形式に変換（既存互換性維持）"""
        result = {
            "success": self.success,
            "categories": self.categories,
            "uncategorized": self.uncategorized
        }
        if self.error:
            result["error"] = self.error
        if self.metadata:
            result.update(self.metadata)
        return result
    
    def get_categorization_statistics(self) -> Dict[str, Any]:
        """カテゴリ分類統計を取得（Enhanced機能）"""
        total_items = sum(len(items) for items in self.categories.values())
        uncategorized_count = len(self.uncategorized)
        
        stats = {
            "total_items": total_items + uncategorized_count,
            "categorized_items": total_items,
            "uncategorized_items": uncategorized_count,
            "categories_count": len(self.categories),
            "categorization_rate": total_items / (total_items + uncategorized_count) if (total_items + uncategorized_count) > 0 else 0,
            "categories_distribution": {
                category: len(items) 
                for category, items in self.categories.items()
            },
            "average_items_per_category": total_items / len(self.categories) if len(self.categories) > 0 else 0,
            "processing_time": self.processing_time,
            "quality_score": self.quality_score,
            "confidence": self.confidence,
            "coverage_score": self.coverage_score,
            "balance_score": self.balance_score
        }
        
        # 既存フィールドを更新
        self.total_items = total_items + uncategorized_count
        self.categorized_items = total_items
        
        return stats
    
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


class BaseCategoryService(ABC):
    """
    カテゴリ分類サービスの基底抽象クラス
    
    Enhanced機能統合版：
    - 既存APIとの完全互換性を維持
    - 統計機能・品質評価を追加
    - エラーハンドリングを強化
    """
    
    def __init__(self):
        self.service_name = self.__class__.__name__
        self.provider = None
        
        # Enhanced機能：統計管理
        self._category_stats = {
            "total_categorizations": 0,
            "successful_categorizations": 0,
            "average_items_per_categorization": 0.0,
            "average_processing_time": 0.0,
            "categories_used": set(),
            "most_common_category": None
        }
    
    @abstractmethod
    def is_available(self) -> bool:
        """サービスが利用可能かチェック"""
        pass
    
    @abstractmethod
    async def categorize_menu(
        self, 
        extracted_text: str, 
        session_id: Optional[str] = None
    ) -> CategoryResult:
        """
        メニューテキストをカテゴリ分類
        
        Args:
            extracted_text: OCRで抽出されたメニューテキスト
            session_id: セッションID（進行状況通知用）
            
        Returns:
            CategoryResult: 分類結果
        """
        pass
    
    def get_default_categories(self) -> List[str]:
        """デフォルトのカテゴリリストを取得（既存互換）"""
        return ["前菜", "メイン", "ドリンク", "デザート", "サイド", "スープ"]
    
    def validate_text_input(self, extracted_text: str) -> bool:
        """入力テキストの妥当性をチェック（既存互換）"""
        if not extracted_text or not extracted_text.strip():
            return False
        
        # 最小文字数チェック
        if len(extracted_text.strip()) < 5:
            return False
            
        return True
    
    def get_service_info(self) -> Dict:
        """サービス情報を取得（Enhanced機能追加）"""
        base_info = {
            "service_name": self.service_name,
            "available": self.is_available(),
            "capabilities": self.get_capabilities(),
            "supported_languages": ["Japanese"],
            "default_categories": self.get_default_categories()
        }
        
        # Enhanced機能：統計情報追加
        if hasattr(self, '_category_stats'):
            base_info["statistics"] = self.get_category_statistics()
        
        return base_info
    
    def get_capabilities(self) -> List[str]:
        """サービス機能一覧を取得（Enhanced機能）"""
        return [
            "japanese_menu_categorization",
            "menu_item_extraction", 
            "price_detection",
            "structured_output",
            "quality_assessment",
            "performance_monitoring",
            "error_recovery",
            "confidence_scoring",
            "coverage_analysis",
            "balance_evaluation"
        ]
    
    # ========================================
    # Enhanced機能：品質評価・統計管理
    # ========================================
    
    def assess_categorization_quality(
        self, 
        result: CategoryResult, 
        original_text: str
    ) -> Dict[str, float]:
        """カテゴリ分類結果の品質を評価（Enhanced機能）"""
        
        quality_score = 0.0
        confidence = 0.0
        
        category_stats = result.get_categorization_statistics()
        total_items = category_stats["total_items"]
        categorization_rate = category_stats["categorization_rate"]
        categories_count = category_stats["categories_count"]
        
        # カバレッジ評価
        coverage_score = categorization_rate  # 分類率
        
        # バランス評価
        if categories_count > 0:
            items_per_category = [len(items) for items in result.categories.values()]
            max_items = max(items_per_category) if items_per_category else 0
            min_items = min(items_per_category) if items_per_category else 0
            
            # バランススコア（最大と最小の差が少ないほど高い）
            if max_items > 0:
                balance_score = 1.0 - (max_items - min_items) / max_items
            else:
                balance_score = 1.0
        else:
            balance_score = 0.0
        
        # 総合品質スコア
        if total_items > 0:
            quality_score += 0.4 * coverage_score  # カバレッジ重視
            quality_score += 0.2 * balance_score   # バランス
            
            if categories_count > 0:
                quality_score += 0.2  # カテゴリが存在
            
            if categories_count >= 2:
                quality_score += 0.1  # 複数カテゴリ
            
            if len(original_text) > 100:
                quality_score += 0.1  # 十分なテキスト量
        
        # 信頼度は品質スコアを基に計算
        confidence = min(quality_score, 1.0)
        
        # 結果に品質指標を設定
        result.coverage_score = coverage_score
        result.balance_score = balance_score
        result.accuracy_estimate = quality_score
        
        return {
            "quality_score": quality_score,
            "confidence": confidence
        }
    
    def update_category_stats(self, result: CategoryResult) -> None:
        """カテゴリ分類統計を更新（Enhanced機能）"""
        self._category_stats["total_categorizations"] += 1
        
        if result.success:
            self._category_stats["successful_categorizations"] += 1
            
            # 平均アイテム数を更新
            if result.total_items:
                total_categorizations = self._category_stats["successful_categorizations"]
                current_avg = self._category_stats["average_items_per_categorization"]
                self._category_stats["average_items_per_categorization"] = (
                    (current_avg * (total_categorizations - 1) + result.total_items) / total_categorizations
                )
            
            # 平均処理時間を更新
            if result.processing_time:
                total_categorizations = self._category_stats["successful_categorizations"]
                current_avg = self._category_stats["average_processing_time"]
                self._category_stats["average_processing_time"] = (
                    (current_avg * (total_categorizations - 1) + result.processing_time) / total_categorizations
                )
            
            # 使用されたカテゴリを追加
            for category in result.categories.keys():
                self._category_stats["categories_used"].add(category)
            
            # 最も多いカテゴリを更新
            if result.categories:
                largest_category = max(result.categories.keys(), key=lambda k: len(result.categories[k]))
                self._category_stats["most_common_category"] = largest_category
    
    def get_category_statistics(self) -> Dict[str, Any]:
        """カテゴリ分類固有の統計を取得（Enhanced機能）"""
        stats = self._category_stats.copy()
        stats["categories_used"] = list(stats["categories_used"])
        
        if stats["total_categorizations"] > 0:
            stats["success_rate"] = stats["successful_categorizations"] / stats["total_categorizations"]
        else:
            stats["success_rate"] = 0.0
        
        return stats
    
    def create_enhanced_result(
        self,
        success: bool,
        categories: Dict[str, List[Dict]] = None,
        uncategorized: List[str] = None,
        error: str = None,
        **kwargs
    ) -> CategoryResult:
        """Enhanced機能付きの結果を作成"""
        result = CategoryResult(
            success=success,
            categories=categories or {},
            uncategorized=uncategorized or [],
            error=error,
            **kwargs
        )
        
        # 処理時間設定
        if 'start_time' in kwargs:
            result.set_processing_time(kwargs['start_time'])
        
        return result

from abc import ABC, abstractmethod
from typing import Dict, Optional, List, Any
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
import re

class TranslationProvider(str, Enum):
    """翻訳プロバイダーの定義"""
    GOOGLE_TRANSLATE = "google_translate"
    OPENAI = "openai"
    ENHANCED = "enhanced"

class TranslationResult(BaseModel):
    """
    翻訳結果を格納するクラス
    
    Enhanced機能統合版：
    - 既存APIとの完全互換性を維持
    - 品質指標・統計機能を追加
    - パフォーマンス測定機能を追加
    """
    
    # 既存フィールド（互換性維持）
    success: bool
    translated_categories: Dict[str, List[Dict]] = {}
    translation_method: str = ""
    error: Optional[str] = None
    metadata: Dict = {}
    
    # Enhanced機能追加フィールド（オプション）
    total_items: Optional[int] = Field(default=None, description="総アイテム数")
    translated_items: Optional[int] = Field(default=None, description="翻訳済みアイテム数")
    processing_time: Optional[float] = Field(default=None, description="処理時間（秒）")
    
    # 品質指標（Enhanced機能）
    quality_score: Optional[float] = Field(default=None, description="品質スコア (0-1)")
    confidence: Optional[float] = Field(default=None, description="信頼度 (0-1)")
    translation_coverage: Optional[float] = Field(default=None, description="翻訳カバレッジ")
    consistency_score: Optional[float] = Field(default=None, description="翻訳一貫性")
    
    # 統計情報（Enhanced機能）
    fallback_used: bool = Field(default=False, description="フォールバック使用フラグ")
    untranslated_items: List[str] = Field(default_factory=list, description="翻訳失敗アイテム")
    category_mapping_used: Dict[str, str] = Field(default_factory=dict, description="使用されたカテゴリマッピング")
    
    def to_dict(self) -> Dict:
        """辞書形式に変換（既存互換性維持）"""
        result = {
            "success": self.success,
            "translated_categories": self.translated_categories,
            "translation_method": self.translation_method
        }
        if self.error:
            result["error"] = self.error
        if self.metadata:
            result.update(self.metadata)
        return result
    
    def get_translation_statistics(self) -> Dict[str, Any]:
        """翻訳統計を取得（Enhanced機能）"""
        total_items = sum(len(items) for items in self.translated_categories.values())
        untranslated_count = len(self.untranslated_items)
        
        stats = {
            "total_items": total_items,
            "translated_items": total_items - untranslated_count,
            "untranslated_items": untranslated_count,
            "categories_count": len(self.translated_categories),
            "translation_rate": (total_items - untranslated_count) / total_items if total_items > 0 else 0,
            "categories_distribution": {
                category: len(items) 
                for category, items in self.translated_categories.items()
            },
            "category_mappings_used": len(self.category_mapping_used),
            "fallback_used": self.fallback_used,
            "processing_time": self.processing_time,
            "quality_score": self.quality_score,
            "confidence": self.confidence
        }
        
        # 既存フィールドを更新
        self.total_items = total_items
        self.translated_items = total_items - untranslated_count
        
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


class BaseTranslationService(ABC):
    """
    翻訳サービスの基底抽象クラス
    
    Enhanced機能統合版：
    - 既存APIとの完全互換性を維持
    - 統計機能・品質評価を追加
    - エラーハンドリングを強化
    """
    
    def __init__(self):
        self.service_name = self.__class__.__name__
        self.provider = None
        
        # Enhanced機能：統計管理
        self._translation_stats = {
            "total_translations": 0,
            "successful_translations": 0,
            "fallback_usage_count": 0,
            "average_items_per_translation": 0.0,
            "average_processing_time": 0.0,
            "most_common_source_language": "japanese",
            "most_common_target_language": "english"
        }
    
    @abstractmethod
    def is_available(self) -> bool:
        """サービスが利用可能かチェック"""
        pass
    
    @abstractmethod
    async def translate_menu(
        self, 
        categorized_data: Dict[str, List], 
        session_id: Optional[str] = None
    ) -> TranslationResult:
        """
        カテゴリ分類されたメニューを英語に翻訳
        
        Args:
            categorized_data: カテゴリ分類されたメニューデータ
            session_id: セッションID（進行状況通知用）
            
        Returns:
            TranslationResult: 翻訳結果
        """
        pass
    
    def get_category_mapping(self) -> Dict[str, str]:
        """カテゴリ名のマッピング辞書を取得（日本語→英語）"""
        return {
            "前菜": "Appetizers",
            "メイン": "Main Dishes", 
            "ドリンク": "Drinks",
            "デザート": "Desserts",
            "飲み物": "Beverages",
            "お酒": "Alcoholic Beverages",
            "サラダ": "Salads",
            "スープ": "Soups",
            "パスタ": "Pasta",
            "ピザ": "Pizza",
            "肉料理": "Meat Dishes",
            "魚料理": "Seafood",
            "鍋料理": "Hot Pot",
            "揚げ物": "Fried Foods",
            "焼き物": "Grilled Foods",
            "サイド": "Side Dishes",
            "その他": "Others"
        }
    
    def validate_categorized_data(self, categorized_data: Dict) -> bool:
        """カテゴリデータの妥当性をチェック（既存互換）"""
        if not categorized_data or not isinstance(categorized_data, dict):
            return False
        
        # 少なくとも1つのカテゴリにアイテムがあることを確認
        has_items = any(
            isinstance(items, list) and len(items) > 0 
            for items in categorized_data.values()
        )
        
        return has_items
    
    def extract_menu_item_data(self, item) -> tuple:
        """メニューアイテムからデータを抽出（既存互換）"""
        if isinstance(item, str):
            return item, ""
        elif isinstance(item, dict):
            return item.get("name", ""), item.get("price", "")
        else:
            return "", ""
    
    def get_service_info(self) -> Dict:
        """サービス情報を取得（Enhanced機能追加）"""
        base_info = {
            "service_name": self.service_name,
            "provider": self.provider.value if self.provider else "unknown",
            "available": self.is_available(),
            "capabilities": self.get_capabilities(),
            "supported_languages": {
                "source": ["Japanese"],
                "target": ["English"]
            },
            "category_mapping": self.get_category_mapping()
        }
        
        # Enhanced機能：統計情報追加
        if hasattr(self, '_translation_stats'):
            base_info["statistics"] = self.get_translation_statistics()
        
        return base_info
    
    def get_capabilities(self) -> List[str]:
        """サービス機能一覧を取得（Enhanced機能）"""
        return [
            "menu_translation",
            "category_mapping", 
            "japanese_to_english",
            "price_preservation",
            "quality_assessment",
            "performance_monitoring",
            "error_recovery",
            "consistency_evaluation"
        ]
    
    def clean_translated_text(self, text: str) -> str:
        """翻訳されたテキストをクリーンアップ（既存互換）"""
        if not text:
            return text
            
        import html
        # HTMLエンティティをデコード
        cleaned = html.unescape(text)
        
        # 不要な空白を除去
        cleaned = cleaned.strip()
        
        return cleaned
    
    # ========================================
    # Enhanced機能：品質評価・統計管理
    # ========================================
    
    def assess_translation_quality(
        self, 
        result: TranslationResult, 
        original_data: Dict[str, List]
    ) -> Dict[str, float]:
        """翻訳結果の品質を評価（Enhanced機能）"""
        
        quality_score = 0.0
        confidence = 0.0
        
        translation_stats = result.get_translation_statistics()
        total_items = translation_stats["total_items"]
        translation_rate = translation_stats["translation_rate"]
        categories_count = translation_stats["categories_count"]
        
        # 翻訳カバレッジ評価
        translation_coverage = translation_rate
        
        # 一貫性スコア評価
        consistency_score = self._evaluate_translation_consistency(result)
        
        # 総合品質スコア
        if total_items > 0:
            quality_score += 0.5 * translation_coverage    # カバレッジ重視
            quality_score += 0.3 * consistency_score       # 一貫性
            quality_score += 0.2 * (1.0 if categories_count >= len(original_data) else 0.5)  # カテゴリ完全性
        
        # 信頼度は品質スコアを基に計算
        confidence = min(quality_score, 1.0)
        
        # 結果に品質指標を設定
        result.translation_coverage = translation_coverage
        result.consistency_score = consistency_score
        
        return {
            "quality_score": quality_score,
            "confidence": confidence
        }
    
    def _evaluate_translation_consistency(self, result: TranslationResult) -> float:
        """翻訳一貫性を評価（Enhanced機能）"""
        # 同じ日本語名が異なる英語名に翻訳されていないかチェック
        translation_map = {}
        inconsistencies = 0
        total_items = 0
        
        for category, items in result.translated_categories.items():
            for item in items:
                japanese_name = item.get("japanese_name", "")
                english_name = item.get("english_name", "")
                
                if japanese_name and english_name:
                    total_items += 1
                    
                    if japanese_name in translation_map:
                        if translation_map[japanese_name] != english_name:
                            inconsistencies += 1
                    else:
                        translation_map[japanese_name] = english_name
        
        consistency_rate = 1.0 - (inconsistencies / total_items) if total_items > 0 else 1.0
        return max(0.0, consistency_rate)
    
    def update_translation_stats(self, result: TranslationResult) -> None:
        """翻訳統計を更新（Enhanced機能）"""
        self._translation_stats["total_translations"] += 1
        
        if result.success:
            self._translation_stats["successful_translations"] += 1
            
            # 平均アイテム数を更新
            if result.total_items:
                total_translations = self._translation_stats["successful_translations"]
                current_avg = self._translation_stats["average_items_per_translation"]
                self._translation_stats["average_items_per_translation"] = (
                    (current_avg * (total_translations - 1) + result.total_items) / total_translations
                )
            
            # 平均処理時間を更新
            if result.processing_time:
                total_translations = self._translation_stats["successful_translations"]
                current_avg = self._translation_stats["average_processing_time"]
                self._translation_stats["average_processing_time"] = (
                    (current_avg * (total_translations - 1) + result.processing_time) / total_translations
                )
            
            # フォールバック使用回数
            if result.fallback_used:
                self._translation_stats["fallback_usage_count"] += 1
    
    def get_translation_statistics(self) -> Dict[str, Any]:
        """翻訳固有の統計を取得（Enhanced機能）"""
        stats = self._translation_stats.copy()
        
        if stats["total_translations"] > 0:
            stats["success_rate"] = stats["successful_translations"] / stats["total_translations"]
            stats["fallback_usage_rate"] = stats["fallback_usage_count"] / stats["total_translations"]
        else:
            stats["success_rate"] = 0.0
            stats["fallback_usage_rate"] = 0.0
        
        return stats
    
    def create_enhanced_result(
        self,
        success: bool,
        translated_categories: Dict[str, List[Dict]] = None,
        translation_method: str = "",
        error: str = None,
        **kwargs
    ) -> TranslationResult:
        """Enhanced機能付きの結果を作成"""
        result = TranslationResult(
            success=success,
            translated_categories=translated_categories or {},
            translation_method=translation_method,
            error=error,
            **kwargs
        )
        
        # 処理時間設定
        if 'start_time' in kwargs:
            result.set_processing_time(kwargs['start_time'])
        
        return result

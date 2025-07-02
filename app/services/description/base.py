from abc import ABC, abstractmethod
from typing import Dict, Optional, List, Any
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
import re

class DescriptionProvider(str, Enum):
    """詳細説明プロバイダーの定義"""
    OPENAI = "openai"
    ENHANCED = "enhanced"

class DescriptionResult(BaseModel):
    """
    詳細説明生成結果を格納するクラス
    
    Enhanced機能統合版：
    - 既存APIとの完全互換性を維持
    - 品質指標・統計機能を追加
    - パフォーマンス測定機能を追加
    """
    
    # 既存フィールド（互換性維持）
    success: bool
    final_menu: Dict[str, List[Dict]] = {}
    description_method: str = ""
    error: Optional[str] = None
    metadata: Dict = {}
    
    # Enhanced機能追加フィールド（オプション）
    total_items: Optional[int] = Field(default=None, description="総アイテム数")
    described_items: Optional[int] = Field(default=None, description="説明追加済みアイテム数")
    processing_time: Optional[float] = Field(default=None, description="処理時間（秒）")
    
    # 品質指標（Enhanced機能）
    quality_score: Optional[float] = Field(default=None, description="品質スコア (0-1)")
    confidence: Optional[float] = Field(default=None, description="信頼度 (0-1)")
    description_coverage: Optional[float] = Field(default=None, description="説明カバレッジ")
    description_quality: Optional[float] = Field(default=None, description="説明品質")
    cultural_accuracy: Optional[float] = Field(default=None, description="文化的正確性")
    
    # 統計情報（Enhanced機能）
    failed_descriptions: List[str] = Field(default_factory=list, description="説明生成失敗アイテム")
    description_stats: Dict[str, Any] = Field(default_factory=dict, description="説明統計")
    fallback_used: bool = Field(default=False, description="フォールバック使用フラグ")
    
    def to_dict(self) -> Dict:
        """辞書形式に変換（既存互換性維持）"""
        result = {
            "success": self.success,
            "final_menu": self.final_menu,
            "description_method": self.description_method
        }
        if self.error:
            result["error"] = self.error
        if self.metadata:
            result.update(self.metadata)
        return result
    
    def get_description_statistics(self) -> Dict[str, Any]:
        """詳細説明統計を取得（Enhanced機能）"""
        total_items = sum(len(items) for items in self.final_menu.values())
        
        # 説明が追加されたアイテム数をカウント
        described_count = sum(
            1 for items in self.final_menu.values() 
            for item in items 
            if item.get("description") and len(item.get("description", "").strip()) > 0
        )
        
        # 説明の長さ統計
        description_lengths = [
            len(item.get("description", ""))
            for items in self.final_menu.values()
            for item in items
            if item.get("description")
        ]
        
        avg_description_length = sum(description_lengths) / len(description_lengths) if description_lengths else 0
        
        stats = {
            "total_items": total_items,
            "described_items": described_count,
            "failed_items": len(self.failed_descriptions),
            "categories_count": len(self.final_menu),
            "description_rate": described_count / total_items if total_items > 0 else 0,
            "categories_distribution": {
                category: len(items) 
                for category, items in self.final_menu.items()
            },
            "average_description_length": avg_description_length,
            "processing_time": self.processing_time,
            "quality_score": self.quality_score,
            "confidence": self.confidence,
            "fallback_used": self.fallback_used
        }
        
        # 既存フィールドを更新
        self.total_items = total_items
        self.described_items = described_count
        
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


class BaseDescriptionService(ABC):
    """
    詳細説明サービスの基底抽象クラス
    
    Enhanced機能統合版：
    - 既存APIとの完全互換性を維持
    - 統計機能・品質評価を追加
    - エラーハンドリングを強化
    """
    
    def __init__(self):
        self.service_name = self.__class__.__name__
        self.provider = None
        
        # Enhanced機能：統計管理
        self._description_stats = {
            "total_descriptions": 0,
            "successful_descriptions": 0,
            "fallback_usage_count": 0,
            "average_items_per_description": 0.0,
            "average_processing_time": 0.0,
            "average_description_length": 0.0
        }
    
    @abstractmethod
    def is_available(self) -> bool:
        """サービスが利用可能かチェック"""
        pass
    
    @abstractmethod
    async def add_descriptions(
        self, 
        translated_data: Dict[str, List], 
        session_id: Optional[str] = None
    ) -> DescriptionResult:
        """
        翻訳されたメニューに詳細説明を追加
        
        Args:
            translated_data: 翻訳されたメニューデータ
            session_id: セッションID（進行状況通知用）
            
        Returns:
            DescriptionResult: 詳細説明生成結果
        """
        pass
    
    def validate_translated_data(self, translated_data: Dict) -> bool:
        """翻訳データの妥当性をチェック（既存互換）"""
        if not translated_data or not isinstance(translated_data, dict):
            return False
        
        # 少なくとも1つのカテゴリにアイテムがあることを確認
        has_items = any(
            isinstance(items, list) and len(items) > 0 
            for items in translated_data.values()
        )
        
        return has_items
    
    def validate_menu_item(self, item: Dict) -> bool:
        """メニューアイテムの妥当性をチェック（既存互換）"""
        if not isinstance(item, dict):
            return False
        
        # 必須フィールドの確認
        required_fields = ["japanese_name", "english_name"]
        return all(
            field in item and isinstance(item[field], str) and item[field].strip()
            for field in required_fields
        )
    
    def create_fallback_description(self, item: Dict) -> str:
        """フォールバック用のシンプルな説明を生成（既存互換）"""
        english_name = item.get("english_name", "This dish")
        japanese_name = item.get("japanese_name", "")
        
        if japanese_name and japanese_name != "N/A":
            return f"Traditional Japanese dish '{japanese_name}' ({english_name}). A popular menu item with authentic Japanese flavors and careful preparation."
        else:
            return f"Traditional Japanese dish. {english_name} is a popular menu item with authentic Japanese flavors."
    
    def get_example_descriptions(self) -> Dict[str, str]:
        """説明例のマッピングを取得（既存互換）"""
        return {
            "Yakitori": "Traditional Japanese grilled chicken skewers, marinated in savory tare sauce and grilled over charcoal for a smoky flavor",
            "Tempura": "Light and crispy battered and deep-fried seafood and vegetables, served with tentsuyu dipping sauce",
            "Sushi": "Fresh raw fish and seafood served over seasoned sushi rice, showcasing the chef's skill and the finest ingredients",
            "Ramen": "Japanese noodle soup with rich broth, featuring wheat noodles in various flavorful broths topped with vegetables, meat, and seasonings",
            "Miso Soup": "Traditional Japanese soup made with fermented soybean paste, often containing tofu, seaweed, and vegetables",
            "Tonkatsu": "Breaded and deep-fried pork cutlet, served crispy on the outside and tender inside, typically with tonkatsu sauce",
            "Gyoza": "Pan-fried dumplings filled with seasoned ground pork and vegetables, crispy on one side and steamed on the other",
            "Edamame": "Young soybeans boiled and lightly salted, served as a healthy and traditional Japanese appetizer"
        }
    
    def get_service_info(self) -> Dict:
        """サービス情報を取得（Enhanced機能追加）"""
        base_info = {
            "service_name": self.service_name,
            "provider": self.provider.value if self.provider else "unknown",
            "available": self.is_available(),
            "capabilities": self.get_capabilities(),
            "supported_categories": [
                "Appetizers", "Main Dishes", "Drinks", "Desserts",
                "前菜", "メイン", "ドリンク", "デザート"
            ],
            "description_features": [
                "cooking_methods",
                "ingredients",
                "flavor_profiles", 
                "cultural_background",
                "serving_suggestions"
            ]
        }
        
        # Enhanced機能：統計情報追加
        if hasattr(self, '_description_stats'):
            base_info["statistics"] = self.get_description_statistics()
        
        return base_info
    
    def get_capabilities(self) -> List[str]:
        """サービス機能一覧を取得（Enhanced機能）"""
        return [
            "detailed_description_generation",
            "japanese_cuisine_expertise",
            "cultural_context_explanation",
            "tourist_friendly_descriptions",
            "chunked_processing",
            "quality_assessment",
            "performance_monitoring",
            "error_recovery",
            "fallback_management",
            "cultural_accuracy_evaluation"
        ]
    
    def extract_processing_statistics(self, translated_data: Dict, final_menu: Dict) -> Dict:
        """処理統計を抽出（既存互換）"""
        input_stats = {
            "total_categories": len(translated_data),
            "total_items": sum(len(items) for items in translated_data.values()),
            "items_per_category": {
                category: len(items) 
                for category, items in translated_data.items()
            }
        }
        
        output_stats = {
            "processed_categories": len(final_menu),
            "processed_items": sum(len(items) for items in final_menu.values()),
            "descriptions_added": sum(
                1 for items in final_menu.values() 
                for item in items 
                if item.get("description")
            )
        }
        
        return {
            "input_statistics": input_stats,
            "output_statistics": output_stats,
            "processing_completeness": output_stats["processed_items"] / input_stats["total_items"] if input_stats["total_items"] > 0 else 0
        }
    
    def clean_description_text(self, description: str) -> str:
        """説明テキストをクリーンアップ（既存互換）"""
        if not description:
            return description
        
        # 不要な空白や改行を除去
        cleaned = description.strip()
        
        # 複数の空白を単一の空白に変換
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # 文の最初を大文字にする
        if cleaned and cleaned[0].islower():
            cleaned = cleaned[0].upper() + cleaned[1:]
        
        # 文末にピリオドがない場合は追加
        if cleaned and not cleaned.endswith('.'):
            cleaned += '.'
        
        return cleaned
    
    # ========================================
    # Enhanced機能：品質評価・統計管理
    # ========================================
    
    def assess_description_quality(
        self, 
        result: DescriptionResult, 
        original_data: Dict[str, List]
    ) -> Dict[str, float]:
        """詳細説明結果の品質を評価（Enhanced機能）"""
        
        quality_score = 0.0
        confidence = 0.0
        
        description_stats = result.get_description_statistics()
        total_items = description_stats["total_items"]
        description_rate = description_stats["description_rate"]
        avg_length = description_stats["average_description_length"]
        
        # 説明カバレッジ評価
        description_coverage = description_rate
        
        # 説明品質評価
        description_quality = 0.0
        if avg_length > 0:
            if avg_length >= 50:  # 十分な長さ
                description_quality += 0.4
            elif avg_length >= 20:  # 最小限の長さ
                description_quality += 0.2
            
            if avg_length <= 200:  # 適度な長さ（長すぎない）
                description_quality += 0.3
            
            # 文化的正確性の仮評価（実装で詳細化可能）
            cultural_accuracy = 0.7  # デフォルト値
            description_quality += 0.3 * cultural_accuracy
        
        # 総合品質スコア
        if total_items > 0:
            quality_score += 0.4 * description_coverage  # カバレッジ重視
            quality_score += 0.4 * description_quality   # 品質重視
            quality_score += 0.2 * (1.0 if len(result.final_menu) >= len(original_data) else 0.5)  # カテゴリ完全性
        
        # 信頼度は品質スコアを基に計算
        confidence = min(quality_score, 1.0)
        
        # 結果に品質指標を設定
        result.description_coverage = description_coverage
        result.description_quality = description_quality
        result.cultural_accuracy = cultural_accuracy if 'cultural_accuracy' in locals() else 0.7
        
        return {
            "quality_score": quality_score,
            "confidence": confidence
        }
    
    def update_description_stats(self, result: DescriptionResult) -> None:
        """詳細説明統計を更新（Enhanced機能）"""
        self._description_stats["total_descriptions"] += 1
        
        if result.success:
            self._description_stats["successful_descriptions"] += 1
            
            # 平均アイテム数を更新
            if result.total_items:
                total_descriptions = self._description_stats["successful_descriptions"]
                current_avg = self._description_stats["average_items_per_description"]
                self._description_stats["average_items_per_description"] = (
                    (current_avg * (total_descriptions - 1) + result.total_items) / total_descriptions
                )
            
            # 平均処理時間を更新
            if result.processing_time:
                total_descriptions = self._description_stats["successful_descriptions"]
                current_avg = self._description_stats["average_processing_time"]
                self._description_stats["average_processing_time"] = (
                    (current_avg * (total_descriptions - 1) + result.processing_time) / total_descriptions
                )
            
            # 平均説明長を更新
            description_stats = result.get_description_statistics()
            if description_stats["average_description_length"] > 0:
                total_descriptions = self._description_stats["successful_descriptions"]
                current_avg = self._description_stats["average_description_length"]
                self._description_stats["average_description_length"] = (
                    (current_avg * (total_descriptions - 1) + description_stats["average_description_length"]) / total_descriptions
                )
            
            # フォールバック使用回数
            if result.fallback_used:
                self._description_stats["fallback_usage_count"] += 1
    
    def get_description_statistics(self) -> Dict[str, Any]:
        """詳細説明固有の統計を取得（Enhanced機能）"""
        stats = self._description_stats.copy()
        
        if stats["total_descriptions"] > 0:
            stats["success_rate"] = stats["successful_descriptions"] / stats["total_descriptions"]
            stats["fallback_usage_rate"] = stats["fallback_usage_count"] / stats["total_descriptions"]
        else:
            stats["success_rate"] = 0.0
            stats["fallback_usage_rate"] = 0.0
        
        return stats
    
    def create_enhanced_result(
        self,
        success: bool,
        final_menu: Dict[str, List[Dict]] = None,
        description_method: str = "",
        error: str = None,
        **kwargs
    ) -> DescriptionResult:
        """Enhanced機能付きの結果を作成"""
        result = DescriptionResult(
            success=success,
            final_menu=final_menu or {},
            description_method=description_method,
            error=error,
            **kwargs
        )
        
        # 処理時間設定
        if 'start_time' in kwargs:
            result.set_processing_time(kwargs['start_time'])
        
        return result

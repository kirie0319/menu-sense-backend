from abc import ABC, abstractmethod
from typing import Dict, Optional, List, Any
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
import re

class ImageProvider(str, Enum):
    """画像生成プロバイダーの定義"""
    IMAGEN3 = "imagen3"
    ENHANCED = "enhanced"

class ImageResult(BaseModel):
    """
    画像生成結果を格納するクラス
    
    Enhanced機能統合版：
    - 既存APIとの完全互換性を維持
    - 品質指標・統計機能を追加
    - パフォーマンス測定機能を追加
    """
    
    # 既存フィールド（互換性維持）
    success: bool
    images_generated: Dict[str, List[Dict]] = {}
    total_images: int = 0
    total_items: int = 0
    image_method: str = ""
    error: Optional[str] = None
    metadata: Dict = {}
    
    # Enhanced機能追加フィールド（オプション）
    processing_time: Optional[float] = Field(default=None, description="処理時間（秒）")
    generated_items: Optional[int] = Field(default=None, description="画像生成済みアイテム数")
    
    # 品質指標（Enhanced機能）
    quality_score: Optional[float] = Field(default=None, description="品質スコア (0-1)")
    confidence: Optional[float] = Field(default=None, description="信頼度 (0-1)")
    generation_success_rate: Optional[float] = Field(default=None, description="生成成功率")
    visual_quality: Optional[float] = Field(default=None, description="視覚品質")
    prompt_effectiveness: Optional[float] = Field(default=None, description="プロンプト効果")
    
    # 統計情報（Enhanced機能）
    failed_generations: List[str] = Field(default_factory=list, description="生成失敗アイテム")
    generation_stats: Dict[str, Any] = Field(default_factory=dict, description="生成統計")
    fallback_used: bool = Field(default=False, description="フォールバック使用フラグ")
    storage_stats: Dict[str, Any] = Field(default_factory=dict, description="ストレージ統計")
    
    def to_dict(self) -> Dict:
        """辞書形式に変換（既存互換性維持）"""
        result = {
            "success": self.success,
            "images_generated": self.images_generated,
            "total_images": self.total_images,
            "total_items": self.total_items,
            "image_method": self.image_method
        }
        if self.error:
            result["error"] = self.error
        if self.metadata:
            result.update(self.metadata)
        return result
    
    def get_image_statistics(self) -> Dict[str, Any]:
        """画像生成統計を取得（Enhanced機能）"""
        total_attempted = sum(len(items) for items in self.images_generated.values())
        
        # 成功した画像生成数をカウント
        successful_count = sum(
            1 for items in self.images_generated.values() 
            for item in items 
            if item.get("image_url") and item.get("generation_success", True)
        )
        
        # ストレージタイプ別の統計
        storage_types = {}
        for items in self.images_generated.values():
            for item in items:
                storage_type = item.get("storage_type", "unknown")
                storage_types[storage_type] = storage_types.get(storage_type, 0) + 1
        
        stats = {
            "total_items": self.total_items,
            "total_attempted": total_attempted,
            "successful_generations": successful_count,
            "failed_generations": len(self.failed_generations),
            "categories_count": len(self.images_generated),
            "generation_rate": successful_count / total_attempted if total_attempted > 0 else 0,
            "categories_distribution": {
                category: len(items) 
                for category, items in self.images_generated.items()
            },
            "storage_distribution": storage_types,
            "processing_time": self.processing_time,
            "quality_score": self.quality_score,
            "confidence": self.confidence,
            "fallback_used": self.fallback_used
        }
        
        # 既存フィールドを更新
        self.generated_items = successful_count
        self.generation_success_rate = stats["generation_rate"]
        
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


class BaseImageService(ABC):
    """
    画像生成サービスの基底抽象クラス
    
    Enhanced機能統合版：
    - 既存APIとの完全互換性を維持
    - 統計機能・品質評価を追加
    - エラーハンドリングを強化
    """
    
    def __init__(self):
        self.service_name = self.__class__.__name__
        self.provider = None
        
        # Enhanced機能：統計管理
        self._image_stats = {
            "total_generations": 0,
            "successful_generations": 0,
            "fallback_usage_count": 0,
            "average_items_per_generation": 0.0,
            "average_processing_time": 0.0,
            "average_success_rate": 0.0,
            "storage_types_used": set()
        }
    
    @abstractmethod
    def is_available(self) -> bool:
        """サービスが利用可能かチェック"""
        pass
    
    @abstractmethod
    async def generate_images(
        self, 
        final_menu: Dict[str, List], 
        session_id: Optional[str] = None
    ) -> ImageResult:
        """
        メニューアイテムの画像を生成
        
        Args:
            final_menu: 詳細説明付きメニューデータ
            session_id: セッションID（進行状況通知用）
            
        Returns:
            ImageResult: 画像生成結果
        """
        pass
    
    def validate_menu_data(self, final_menu: Dict) -> bool:
        """メニューデータの妥当性をチェック（既存互換）"""
        if not final_menu or not isinstance(final_menu, dict):
            return False
        
        # 少なくとも1つのカテゴリにアイテムがあることを確認
        has_items = any(
            isinstance(items, list) and len(items) > 0 
            for items in final_menu.values()
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
    
    def create_image_prompt(self, japanese_name: str, english_name: str, description: str, category: str) -> str:
        """メニューアイテム用の画像生成プロンプトを作成（既存互換）"""
        
        # カテゴリに応じた基本的なスタイル指定
        category_styles = {
            "Appetizers": "elegant plating, small portions, artistic presentation",
            "Main Dishes": "generous portions, main course presentation, satisfying appearance", 
            "Drinks": "beautiful glassware, refreshing appearance, perfect lighting",
            "Desserts": "sweet presentation, delicate plating, tempting appearance",
            "前菜": "elegant plating, small portions, artistic presentation",
            "メイン": "generous portions, main course presentation, satisfying appearance",
            "ドリンク": "beautiful glassware, refreshing appearance, perfect lighting", 
            "デザート": "sweet presentation, delicate plating, tempting appearance"
        }
        
        style = category_styles.get(category, "beautiful food photography")
        
        # 基本プロンプト構成
        base_prompt = f"Professional food photography of {english_name}"
        
        # 日本語名が意味のある場合は追加
        if japanese_name and japanese_name != "N/A":
            base_prompt += f" ({japanese_name})"
        
        # 説明から重要なキーワードを抽出
        if description and len(description) > 10:
            keywords = self.extract_keywords_from_description(description)
            if keywords:
                base_prompt += f", featuring {', '.join(keywords[:3])}"  # 最大3つのキーワード
        
        # 最終プロンプト
        final_prompt = f"{base_prompt}, {style}, professional lighting, appetizing appearance, high quality restaurant photography, clean white background or elegant table setting"
        
        return final_prompt
    
    def extract_keywords_from_description(self, description: str) -> List[str]:
        """説明から重要なキーワードを抽出（既存互換）"""
        keywords = []
        cooking_methods = [
            "grilled", "fried", "steamed", "boiled", "roasted", "sautéed", 
            "tempura", "yakitori", "teriyaki", "miso", "katsu", "curry",
            "sushi", "sashimi", "ramen", "udon", "soba"
        ]
        ingredients = [
            "chicken", "beef", "pork", "fish", "seafood", "vegetables", 
            "rice", "noodles", "tofu", "miso", "soy sauce", "sake",
            "shrimp", "salmon", "tuna", "scallop", "mushroom", "cucumber"
        ]
        
        desc_lower = description.lower()
        for method in cooking_methods:
            if method in desc_lower:
                keywords.append(method)
        for ingredient in ingredients:
            if ingredient in desc_lower:
                keywords.append(ingredient)
        
        return keywords
    
    def create_safe_filename(self, english_name: str, timestamp: str) -> str:
        """安全なファイル名を作成（既存互換）"""
        # ファイル名を安全にする
        safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '' for c in english_name)
        safe_name = safe_name.replace(' ', '_').lower()[:30]  # 30文字に制限
        
        filename = f"menu_image_{safe_name}_{timestamp}.png"
        return filename
    
    def get_category_styles(self) -> Dict[str, str]:
        """カテゴリ別スタイル定義を取得（既存互換）"""
        return {
            "Appetizers": {
                "style": "elegant plating, small portions, artistic presentation",
                "description": "Small, beautifully presented dishes that start the meal"
            },
            "Main Dishes": {
                "style": "generous portions, main course presentation, satisfying appearance",
                "description": "Hearty, substantial dishes that form the centerpiece of the meal"
            },
            "Drinks": {
                "style": "beautiful glassware, refreshing appearance, perfect lighting",
                "description": "Beverages presented in appropriate glassware with appealing colors"
            },
            "Desserts": {
                "style": "sweet presentation, delicate plating, tempting appearance",
                "description": "Sweet treats with elegant presentation and appealing colors"
            },
            "前菜": {
                "style": "elegant plating, small portions, artistic presentation",
                "description": "Japanese-style appetizers with traditional presentation"
            },
            "メイン": {
                "style": "generous portions, main course presentation, satisfying appearance",
                "description": "Japanese main dishes with authentic presentation"
            },
            "ドリンク": {
                "style": "beautiful glassware, refreshing appearance, perfect lighting",
                "description": "Japanese beverages including traditional and modern options"
            },
            "デザート": {
                "style": "sweet presentation, delicate plating, tempting appearance",
                "description": "Japanese desserts with traditional aesthetic"
            }
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
            "image_features": [
                "professional_lighting",
                "appetizing_appearance",
                "clean_background",
                "high_quality_photography",
                "category_specific_styling"
            ]
        }
        
        # Enhanced機能：統計情報追加
        if hasattr(self, '_image_stats'):
            base_info["statistics"] = self.get_image_statistics()
        
        return base_info
    
    def get_capabilities(self) -> List[str]:
        """サービス機能一覧を取得（Enhanced機能）"""
        return [
            "menu_item_image_generation",
            "category_specific_styling",
            "japanese_cuisine_focus",
            "professional_food_photography",
            "prompt_optimization",
            "quality_assessment",
            "performance_monitoring",
            "error_recovery",
            "storage_management",
            "visual_quality_evaluation"
        ]
    
    def extract_generation_statistics(self, final_menu: Dict, images_generated: Dict) -> Dict:
        """画像生成統計を抽出（既存互換）"""
        input_stats = {
            "total_categories": len(final_menu),
            "total_items": sum(len(items) for items in final_menu.values()),
            "items_per_category": {
                category: len(items) 
                for category, items in final_menu.items()
            }
        }
        
        output_stats = {
            "processed_categories": len(images_generated),
            "total_images_attempted": sum(len(items) for items in images_generated.values()),
            "successful_images": sum(
                1 for items in images_generated.values() 
                for item in items 
                if item.get("image_url")
            ),
            "failed_images": sum(
                1 for items in images_generated.values() 
                for item in items 
                if item.get("error")
            )
        }
        
        success_rate = (
            output_stats["successful_images"] / output_stats["total_images_attempted"] 
            if output_stats["total_images_attempted"] > 0 else 0
        )
        
        return {
            "input_statistics": input_stats,
            "output_statistics": output_stats,
            "success_rate": round(success_rate * 100, 2),
            "processing_completeness": output_stats["total_images_attempted"] / input_stats["total_items"] if input_stats["total_items"] > 0 else 0
        }
    
    def combine_menu_with_images(self, final_menu: Dict, images_generated: Dict) -> Dict:
        """最終メニューと生成された画像を統合（既存互換）"""
        combined_menu = {}
        
        for category, items in final_menu.items():
            combined_items = []
            category_images = images_generated.get(category, [])
            
            # 画像データをマッピング用の辞書に変換
            image_map = {}
            for img_data in category_images:
                english_name = img_data.get("english_name", "")
                if english_name:
                    image_map[english_name] = img_data
            
            # メニューアイテムと画像を統合
            for item in items:
                combined_item = item.copy()  # 元のメニューアイテムをコピー
                
                english_name = item.get("english_name", "")
                if english_name in image_map:
                    # 対応する画像が見つかった場合
                    img_data = image_map[english_name]
                    combined_item["image_url"] = img_data.get("image_url")
                    combined_item["image_generated"] = True
                    combined_item["image_prompt"] = img_data.get("prompt_used")
                    combined_item["image_error"] = img_data.get("error")
                else:
                    # 画像が見つからない場合
                    combined_item["image_url"] = None
                    combined_item["image_generated"] = False
                    combined_item["image_prompt"] = None
                    combined_item["image_error"] = "Image not generated"
                
                combined_items.append(combined_item)
            
            combined_menu[category] = combined_items
        
        return combined_menu
    
    def validate_prompt_content(self, prompt: str) -> bool:
        """プロンプト内容の妥当性をチェック（既存互換）"""
        if not prompt or len(prompt.strip()) < 10:
            return False
        
        # 必要な要素が含まれているかチェック
        essential_terms = ["food", "photography", "professional"]
        return any(term in prompt.lower() for term in essential_terms)
    
    # ========================================
    # Enhanced機能：品質評価・統計管理
    # ========================================
    
    def assess_image_quality(
        self, 
        result: ImageResult, 
        original_data: Dict[str, List]
    ) -> Dict[str, float]:
        """画像生成結果の品質を評価（Enhanced機能）"""
        
        quality_score = 0.0
        confidence = 0.0
        
        image_stats = result.get_image_statistics()
        total_items = image_stats["total_items"]
        generation_rate = image_stats["generation_rate"]
        successful_generations = image_stats["successful_generations"]
        
        # 生成成功率評価
        generation_success_rate = generation_rate
        
        # 視覚品質評価（プロンプト効果と仮定）
        visual_quality = 0.0
        prompt_effectiveness = 0.0
        
        if successful_generations > 0:
            # プロンプトの複雑さと多様性を仮評価
            total_prompts = sum(
                1 for items in result.images_generated.values()
                for item in items
                if item.get("prompt_used")
            )
            
            if total_prompts > 0:
                # プロンプトが作成されている = 基本的な品質
                visual_quality += 0.5
                prompt_effectiveness += 0.5
                
                # 成功率に基づく品質評価
                if generation_rate >= 0.8:
                    visual_quality += 0.3
                    prompt_effectiveness += 0.3
                elif generation_rate >= 0.5:
                    visual_quality += 0.2
                    prompt_effectiveness += 0.2
                
                # ストレージの多様性（S3使用等）
                storage_types = image_stats.get("storage_distribution", {})
                if "s3" in storage_types:
                    visual_quality += 0.2
                    prompt_effectiveness += 0.2
        
        # 総合品質スコア
        if total_items > 0:
            quality_score += 0.4 * generation_success_rate  # 成功率重視
            quality_score += 0.3 * visual_quality          # 視覚品質
            quality_score += 0.2 * prompt_effectiveness    # プロンプト効果
            quality_score += 0.1 * (1.0 if len(result.images_generated) >= len(original_data) else 0.5)  # カテゴリ完全性
        
        # 信頼度は品質スコアを基に計算
        confidence = min(quality_score, 1.0)
        
        # 結果に品質指標を設定
        result.generation_success_rate = generation_success_rate
        result.visual_quality = visual_quality
        result.prompt_effectiveness = prompt_effectiveness
        
        return {
            "quality_score": quality_score,
            "confidence": confidence
        }
    
    def update_image_stats(self, result: ImageResult) -> None:
        """画像生成統計を更新（Enhanced機能）"""
        self._image_stats["total_generations"] += 1
        
        if result.success:
            self._image_stats["successful_generations"] += 1
            
            # 平均アイテム数を更新
            if result.total_items:
                total_generations = self._image_stats["successful_generations"]
                current_avg = self._image_stats["average_items_per_generation"]
                self._image_stats["average_items_per_generation"] = (
                    (current_avg * (total_generations - 1) + result.total_items) / total_generations
                )
            
            # 平均処理時間を更新
            if result.processing_time:
                total_generations = self._image_stats["successful_generations"]
                current_avg = self._image_stats["average_processing_time"]
                self._image_stats["average_processing_time"] = (
                    (current_avg * (total_generations - 1) + result.processing_time) / total_generations
                )
            
            # 平均成功率を更新
            if result.generation_success_rate:
                total_generations = self._image_stats["successful_generations"]
                current_avg = self._image_stats["average_success_rate"]
                self._image_stats["average_success_rate"] = (
                    (current_avg * (total_generations - 1) + result.generation_success_rate) / total_generations
                )
            
            # 使用されたストレージタイプを追加
            storage_stats = result.storage_stats
            for storage_type in storage_stats.get("storage_distribution", {}):
                self._image_stats["storage_types_used"].add(storage_type)
            
            # フォールバック使用回数
            if result.fallback_used:
                self._image_stats["fallback_usage_count"] += 1
    
    def get_image_statistics(self) -> Dict[str, Any]:
        """画像生成固有の統計を取得（Enhanced機能）"""
        stats = self._image_stats.copy()
        stats["storage_types_used"] = list(stats["storage_types_used"])
        
        if stats["total_generations"] > 0:
            stats["success_rate"] = stats["successful_generations"] / stats["total_generations"]
            stats["fallback_usage_rate"] = stats["fallback_usage_count"] / stats["total_generations"]
        else:
            stats["success_rate"] = 0.0
            stats["fallback_usage_rate"] = 0.0
        
        return stats
    
    def create_enhanced_result(
        self,
        success: bool,
        images_generated: Dict[str, List[Dict]] = None,
        total_images: int = 0,
        total_items: int = 0,
        image_method: str = "",
        error: str = None,
        **kwargs
    ) -> ImageResult:
        """Enhanced機能付きの結果を作成"""
        result = ImageResult(
            success=success,
            images_generated=images_generated or {},
            total_images=total_images,
            total_items=total_items,
            image_method=image_method,
            error=error,
            **kwargs
        )
        
        # 処理時間設定
        if 'start_time' in kwargs:
            result.set_processing_time(kwargs['start_time'])
        
        return result

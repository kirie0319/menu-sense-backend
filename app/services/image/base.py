from abc import ABC, abstractmethod
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import re
from app.services.base_result import BaseServiceResult

class ImageProvider(str, Enum):
    """画像生成プロバイダーの定義"""
    IMAGEN3 = "imagen3"

@dataclass
class ImageResult(BaseServiceResult):
    """画像生成結果を格納するクラス"""
    images_generated: Dict[str, List[Dict]] = field(default_factory=dict)
    total_images: int = 0
    total_items: int = 0
    image_method: str = ""
    
    def to_dict(self) -> Dict:
        """辞書形式に変換"""
        result = super().to_dict()
        result["images_generated"] = self.images_generated
        result["total_images"] = self.total_images
        result["total_items"] = self.total_items
        result["image_method"] = self.image_method
        return result

class BaseImageService(ABC):
    """画像生成サービスの基底抽象クラス"""
    
    def __init__(self):
        self.service_name = self.__class__.__name__
        self.provider = None
    
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
        """メニューデータの妥当性をチェック"""
        if not final_menu or not isinstance(final_menu, dict):
            return False
        
        # 少なくとも1つのカテゴリにアイテムがあることを確認
        has_items = any(
            isinstance(items, list) and len(items) > 0 
            for items in final_menu.values()
        )
        
        return has_items
    
    def validate_menu_item(self, item: Dict) -> bool:
        """メニューアイテムの妥当性をチェック"""
        if not isinstance(item, dict):
            return False
        
        # 必須フィールドの確認
        required_fields = ["japanese_name", "english_name"]
        return all(
            field in item and isinstance(item[field], str) and item[field].strip()
            for field in required_fields
        )
    
    def create_image_prompt(self, japanese_name: str, english_name: str, description: str, category: str) -> str:
        """メニューアイテム用の画像生成プロンプトを作成"""
        
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
        """説明から重要なキーワードを抽出"""
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
        """安全なファイル名を作成"""
        # ファイル名を安全にする
        safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '' for c in english_name)
        safe_name = safe_name.replace(' ', '_').lower()[:30]  # 30文字に制限
        
        filename = f"menu_image_{safe_name}_{timestamp}.png"
        return filename
    
    def get_category_styles(self) -> Dict[str, str]:
        """カテゴリ別スタイル定義を取得"""
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
        """サービス情報を取得"""
        return {
            "service_name": self.service_name,
            "provider": self.provider.value if self.provider else "unknown",
            "available": self.is_available(),
            "capabilities": [
                "menu_item_image_generation",
                "category_specific_styling",
                "japanese_cuisine_focus",
                "professional_food_photography",
                "prompt_optimization"
            ],
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
    
    def extract_generation_statistics(self, final_menu: Dict, images_generated: Dict) -> Dict:
        """画像生成統計を抽出"""
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
        """最終メニューと生成された画像を統合"""
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
        """プロンプト内容の妥当性をチェック"""
        if not prompt or len(prompt.strip()) < 10:
            return False
        
        # 必要な要素が含まれているかチェック
        essential_terms = ["food", "photography", "professional"]
        return any(term in prompt.lower() for term in essential_terms)

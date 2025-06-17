from abc import ABC, abstractmethod
from typing import Dict, Optional, List
from pydantic import BaseModel
from enum import Enum

class DescriptionProvider(str, Enum):
    """詳細説明プロバイダーの定義"""
    OPENAI = "openai"

class DescriptionResult(BaseModel):
    """詳細説明生成結果を格納するクラス"""
    
    success: bool
    final_menu: Dict[str, List[Dict]] = {}
    description_method: str = ""
    error: Optional[str] = None
    metadata: Dict = {}
    
    def to_dict(self) -> Dict:
        """辞書形式に変換"""
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

class BaseDescriptionService(ABC):
    """詳細説明サービスの基底抽象クラス"""
    
    def __init__(self):
        self.service_name = self.__class__.__name__
        self.provider = None
    
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
        """翻訳データの妥当性をチェック"""
        if not translated_data or not isinstance(translated_data, dict):
            return False
        
        # 少なくとも1つのカテゴリにアイテムがあることを確認
        has_items = any(
            isinstance(items, list) and len(items) > 0 
            for items in translated_data.values()
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
    
    def create_fallback_description(self, item: Dict) -> str:
        """フォールバック用のシンプルな説明を生成"""
        english_name = item.get("english_name", "This dish")
        japanese_name = item.get("japanese_name", "")
        
        if japanese_name and japanese_name != "N/A":
            return f"Traditional Japanese dish '{japanese_name}' ({english_name}). A popular menu item with authentic Japanese flavors and careful preparation."
        else:
            return f"Traditional Japanese dish. {english_name} is a popular menu item with authentic Japanese flavors."
    
    def get_example_descriptions(self) -> Dict[str, str]:
        """説明例のマッピングを取得"""
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
        """サービス情報を取得"""
        return {
            "service_name": self.service_name,
            "provider": self.provider.value if self.provider else "unknown",
            "available": self.is_available(),
            "capabilities": [
                "detailed_description_generation",
                "japanese_cuisine_expertise",
                "cultural_context_explanation",
                "tourist_friendly_descriptions",
                "chunked_processing"
            ],
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
    
    def extract_processing_statistics(self, translated_data: Dict, final_menu: Dict) -> Dict:
        """処理統計を抽出"""
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
        """説明テキストをクリーンアップ"""
        if not description:
            return description
        
        # 不要な空白や改行を除去
        cleaned = description.strip()
        
        # 複数の空白を単一の空白に変換
        import re
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # 文の最初を大文字にする
        if cleaned and cleaned[0].islower():
            cleaned = cleaned[0].upper() + cleaned[1:]
        
        # 文末にピリオドがない場合は追加
        if cleaned and not cleaned.endswith('.'):
            cleaned += '.'
        
        return cleaned

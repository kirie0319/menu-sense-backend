from abc import ABC, abstractmethod
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from app.services.base_result import BaseServiceResult

class TranslationProvider(str, Enum):
    """翻訳プロバイダーの定義"""
    GOOGLE_TRANSLATE = "google_translate"
    OPENAI = "openai"

@dataclass
class TranslationResult(BaseServiceResult):
    """翻訳結果を格納するクラス"""
    translated_categories: Dict[str, List[Dict]] = field(default_factory=dict)
    translation_method: str = ""
    
    def to_dict(self) -> Dict:
        """辞書形式に変換"""
        result = super().to_dict()
        result["translated_categories"] = self.translated_categories
        result["translation_method"] = self.translation_method
        return result

class BaseTranslationService(ABC):
    """翻訳サービスの基底抽象クラス"""
    
    def __init__(self):
        self.service_name = self.__class__.__name__
        self.provider = None
    
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
            "その他": "Others"
        }
    
    def validate_categorized_data(self, categorized_data: Dict) -> bool:
        """カテゴリデータの妥当性をチェック"""
        if not categorized_data or not isinstance(categorized_data, dict):
            return False
        
        # 少なくとも1つのカテゴリにアイテムがあることを確認
        has_items = any(
            isinstance(items, list) and len(items) > 0 
            for items in categorized_data.values()
        )
        
        return has_items
    
    def extract_menu_item_data(self, item) -> tuple:
        """メニューアイテムからデータを抽出"""
        if isinstance(item, str):
            return item, ""
        elif isinstance(item, dict):
            return item.get("name", ""), item.get("price", "")
        else:
            return "", ""
    
    def get_service_info(self) -> Dict:
        """サービス情報を取得"""
        return {
            "service_name": self.service_name,
            "provider": self.provider.value if self.provider else "unknown",
            "available": self.is_available(),
            "capabilities": [
                "menu_translation",
                "category_mapping", 
                "japanese_to_english",
                "price_preservation"
            ],
            "supported_languages": {
                "source": ["Japanese"],
                "target": ["English"]
            },
            "category_mapping": self.get_category_mapping()
        }
    
    def clean_translated_text(self, text: str) -> str:
        """翻訳されたテキストをクリーンアップ"""
        if not text:
            return text
            
        import html
        # HTMLエンティティをデコード
        cleaned = html.unescape(text)
        
        # 不要な空白を除去
        cleaned = cleaned.strip()
        
        return cleaned

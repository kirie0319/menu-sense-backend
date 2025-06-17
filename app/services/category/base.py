from abc import ABC, abstractmethod
from typing import Dict, Optional, List
from pydantic import BaseModel
from app.core.config import settings

class CategoryResult(BaseModel):
    """カテゴリ分類結果を格納するクラス"""
    
    success: bool
    categories: Dict[str, List[Dict]] = {}
    uncategorized: List[str] = []
    error: Optional[str] = None
    metadata: Dict = {}
    
    def to_dict(self) -> Dict:
        """辞書形式に変換"""
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

class BaseCategoryService(ABC):
    """カテゴリ分類サービスの基底抽象クラス"""
    
    def __init__(self):
        self.service_name = self.__class__.__name__
    
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
        """デフォルトのカテゴリリストを取得"""
        return ["前菜", "メイン", "ドリンク", "デザート"]
    
    def validate_text_input(self, extracted_text: str) -> bool:
        """入力テキストの妥当性をチェック"""
        if not extracted_text or not extracted_text.strip():
            return False
        
        # 最小文字数チェック
        if len(extracted_text.strip()) < 5:
            return False
            
        return True
    
    def get_service_info(self) -> Dict:
        """サービス情報を取得"""
        return {
            "service_name": self.service_name,
            "available": self.is_available(),
            "capabilities": [
                "japanese_menu_categorization",
                "menu_item_extraction", 
                "price_detection",
                "structured_output"
            ],
            "supported_languages": ["Japanese"],
            "default_categories": self.get_default_categories()
        }

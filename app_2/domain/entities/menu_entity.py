"""
Menu Entity - Domain Layer
Business entity definition for menu processing
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class MenuEntity:
    """
    メニューエンティティ
    
    ビジネス上のメニューオブジェクトを表現
    外部依存なし、純粋なビジネスロジック
    """
    id: str
    name: str
    translation: str
    category: Optional[str] = None
    category_translation: Optional[str] = None
    price: Optional[str] = None
    description: Optional[str] = None
    allergy: Optional[str] = None
    ingredient: Optional[str] = None
    search_engine: Optional[str] = None
    gen_image: Optional[str] = None
    
    def is_complete(self) -> bool:
        """
        メニュー情報が完全か判定
        
        Returns:
            bool: 必須項目が揃っているか
        """
        return bool(self.id and self.name and self.translation)
    
    def has_generated_content(self) -> bool:
        """
        AI生成コンテンツが存在するか判定
        
        Returns:
            bool: 説明・アレルゲン・含有物のいずれかが存在するか
        """
        return bool(self.description or self.allergy or self.ingredient)

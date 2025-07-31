"""
Menu Repository Interface - Domain Layer
Abstract repository for menu data access
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from app_2.domain.entities.menu_entity import MenuEntity


class MenuRepositoryInterface(ABC):
    """
    メニューリポジトリ抽象化
    
    データアクセスの抽象化インターフェース
    Infrastructure層で具体実装される
    """
    
    @abstractmethod
    async def save(self, menu: MenuEntity) -> MenuEntity:
        """
        メニューを保存
        
        Args:
            menu: 保存するメニューエンティティ
            
        Returns:
            MenuEntity: 保存されたメニューエンティティ
        """
        pass
    
    @abstractmethod
    async def save_with_session(self, menu: MenuEntity, session_id: str) -> MenuEntity:
        """
        セッションID付きでメニューを保存
        
        Args:
            menu: 保存するメニューエンティティ
            session_id: セッションID
            
        Returns:
            MenuEntity: 保存されたメニューエンティティ
        """
        pass
    
    @abstractmethod
    async def bulk_save_with_session(self, menus: List[MenuEntity], session_id: str) -> List[MenuEntity]:
        """
        複数メニューの一括保存（パフォーマンス最適化版）
        
        Args:
            menus: 保存するメニューエンティティのリスト
            session_id: セッションID
            
        Returns:
            List[MenuEntity]: 保存されたメニューエンティティのリスト
        """
        pass
    
    @abstractmethod
    async def get_by_id(self, menu_id: str) -> Optional[MenuEntity]:
        """
        IDでメニューを取得
        
        Args:
            menu_id: メニューID
            
        Returns:
            Optional[MenuEntity]: 見つかったメニューエンティティ
        """
        pass
    
    @abstractmethod
    async def update(self, menu: MenuEntity) -> MenuEntity:
        """
        メニューを更新
        
        Args:
            menu: 更新するメニューエンティティ
            
        Returns:
            MenuEntity: 更新されたメニューエンティティ
        """
        pass

    @abstractmethod
    async def update_partial(self, menu_id: str, fields: dict) -> Optional[MenuEntity]:
        """
        メニューの部分更新（特定フィールドのみ更新）
        
        Args:
            menu_id: メニューID
            fields: 更新するフィールドの辞書
            
        Returns:
            Optional[MenuEntity]: 更新されたメニューエンティティ
        """
        pass
    
    @abstractmethod
    async def delete(self, menu_id: str) -> bool:
        """
        メニューを削除
        
        Args:
            menu_id: 削除するメニューID
            
        Returns:
            bool: 削除が成功したか
        """
        pass
    
    @abstractmethod
    async def get_menu_image_urls(self, menu_id: str) -> Optional[List[str]]:
        """
        メニューの画像URLリストを取得
        
        Args:
            menu_id: メニューID
            
        Returns:
            Optional[List[str]]: 画像URLリスト（見つからない場合はNone）
        """
        pass
    
    @abstractmethod
    async def get_session_menu_images(self, session_id: str) -> List[dict]:
        """
        セッション内の全メニューの画像URLリストを取得
        
        Args:
            session_id: セッションID
            
        Returns:
            List[dict]: メニューIDと画像URLリストのマッピング
        """
        pass

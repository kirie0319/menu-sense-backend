"""
Search Image Service - Menu Processor v2
Google画像検索を使用したメニュー画像検索サービス
"""
from typing import List, Dict, Optional
from functools import lru_cache

from app_2.infrastructure.integrations.google.google_search_client import get_google_search_client
from app_2.utils.logger import get_logger

logger = get_logger("search_image_service")


class SearchImageService:
    """
    画像検索サービス
    
    メニュー項目に関連する画像を検索（シンプル版）
    """
    
    def __init__(self):
        """初期化"""
        self.search_client = get_google_search_client()
        logger.info("SearchImageService initialized")
    
    async def search_menu_images(
        self, 
        menu_item: str, 
        category: Optional[str] = None,
        num_results: int = 10
    ) -> List[Dict[str, str]]:
        """
        メニュー項目に関連する画像を検索
        
        Args:
            menu_item: メニュー項目名（翻訳前の原文）
            category: メニューカテゴリ（任意）
            num_results: 取得する画像数（デフォルト: 10）
            
        Returns:
            List[Dict]: 画像情報のリスト
                - title: 画像タイトル
                - link: 画像URL
                - thumbnail: サムネイルURL
                - width: 画像の幅（取得可能な場合）
                - height: 画像の高さ（取得可能な場合）
        """
        if not menu_item or not menu_item.strip():
            logger.warning("Empty menu item provided for image search")
            return []
            
        try:
            # シンプルな検索クエリの構築
            search_query = self._build_search_query(menu_item, category)
            logger.info(f"Searching images for: {search_query}")
            
            # Google画像検索実行
            results = await self.search_client.search_images(
                query=search_query,
                num_results=num_results
            )
            
            # 結果をそのまま返す（簡略化版）
            logger.info(f"Found {len(results)} images for: {menu_item}")
            return results
            
        except Exception as e:
            logger.error(f"Image search failed for {menu_item}: {e}")
            return []
    
    def _build_search_query(self, menu_item: str, category: Optional[str] = None) -> str:
        """
        検索クエリを構築
        
        Args:
            menu_item: メニュー項目名
            category: メニューカテゴリ
            
        Returns:
            str: 検索クエリ
        """
        # 基本的にはmenu_itemをそのまま使用
        query = menu_item.strip()
        
        # カテゴリが指定されている場合は追加
        if category and category.strip():
            query = f"{query} {category.strip()}"
        
        return query



@lru_cache(maxsize=1)
def get_search_image_service() -> SearchImageService:
    """
    SearchImageServiceインスタンスを取得（シングルトン）
    
    Returns:
        SearchImageService: 画像検索サービス
    """
    return SearchImageService() 
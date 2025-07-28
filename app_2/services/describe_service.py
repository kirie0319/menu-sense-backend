"""
Describe Service - Menu Processor v2
OpenAI API を使用したメニュー詳細説明生成サービス
"""
from functools import lru_cache
from typing import Optional, Dict, Any
from app_2.infrastructure.integrations.openai import DescriptionClient, get_description_client
from app_2.utils.logger import get_logger

logger = get_logger("describe_service")


class DescribeService:
    """詳細説明生成サービス"""
    
    def __init__(self, description_client: Optional[DescriptionClient] = None):
        """
        詳細説明サービスを初期化
        
        Args:
            description_client: DescriptionClientインスタンス（テスト用）
                              Noneの場合はシングルトンクライアンスを使用
        """
        self.description_client = description_client or get_description_client()
        logger.info("DescribeService initialized")
    
    async def generate_menu_description(
        self, 
        menu_item: str,
        category: str = ""
    ) -> Dict[str, Any]:
        """
        メニュー項目の詳細説明を生成
        
        Args:
            menu_item: メニュー項目名
            category: カテゴリ（オプション）
            
        Returns:
            Dict[str, Any]: 詳細説明データ
            
        Raises:
            ValueError: 入力メニュー項目が無効な場合
            Exception: 説明生成処理が失敗した場合
        """
        if not menu_item or not menu_item.strip():
            logger.warning("Empty or whitespace-only menu item provided for description")
            raise ValueError("Menu item cannot be empty")
        
        try:
            logger.info(f"Generating detailed description for: {menu_item}")
            
            # DescriptionClientで詳細説明を生成
            description_result = await self.description_client.generate_description(
                menu_item=menu_item, 
                category=category
            )
            
            logger.info(f"Description generation completed for: {menu_item}")
            return description_result
            
        except Exception as e:
            logger.error(f"Failed to generate description for '{menu_item}': {e}")
            raise


@lru_cache(maxsize=1)
def get_describe_service() -> DescribeService:
    """
    DescribeServiceのシングルトンインスタンスを取得
    
    Returns:
        DescribeService: 詳細説明サービスシングルトンインスタンス
    """
    return DescribeService() 
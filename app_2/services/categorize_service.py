"""
Categorize Service - Menu Categorization Logic
OpenAI APIを使用したメニューカテゴライズサービス
"""
from functools import lru_cache
from typing import Dict, Any
from app_2.infrastructure.integrations.openai.categorize_client import get_categorize_client
from app_2.utils.logger import get_logger

logger = get_logger("categorize_service")


class CategorizeService:
    """
    メニューカテゴライズサービス
    
    OpenAI APIを使用してメニューデータを分析・カテゴライズ
    """
    
    def __init__(self):
        """サービスを初期化"""
        self.categorize_client = get_categorize_client()
        logger.info("CategorizeService initialized")

    async def categorize_menu_structure(self, mapping_data: str, level: str) -> Dict[str, Any]:
        """
        マッピングデータをカテゴライズ（categorize_clientに委譲）
        
        Args:
            mapping_data: 整形済みマッピングデータ
            level: データレベル
            
        Returns:
            Dict[str, Any]: カテゴライズ結果
        """
        try:
            # categorize_clientに委譲
            result = await self.categorize_client.categorize_menu_structure(mapping_data, level)
            logger.info("Menu structure categorization completed via categorize_client")
            return result
            
        except Exception as e:
            logger.error(f"Menu structure categorization failed: {e}")
            raise


# ファクトリー関数（シングルトンパターン）
@lru_cache(maxsize=1)
def get_categorize_service() -> CategorizeService:
    """
    CategorizeService のインスタンスを取得（シングルトン）
    
    Returns:
        CategorizeService: カテゴライズサービス
    """
    return CategorizeService()

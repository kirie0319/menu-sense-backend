"""
Description Client - Infrastructure Layer
Specialized client for menu item description generation using prompts
"""
from functools import lru_cache
from typing import Dict, Any
from app_2.utils.logger import get_logger
from .openai_base_client import OpenAIBaseClient

logger = get_logger("description_client")


class DescriptionClient(OpenAIBaseClient):
    """
    詳細説明生成専用クライアント（プロンプトベース）
    
    メニュー項目の詳細で魅力的な説明を生成
    """

    async def generate_description(self, menu_item: str, category: str = "") -> Dict[str, Any]:
        """
        メニュー項目の詳細説明を生成（プロンプトベース）
        
        Args:
            menu_item: メニュー項目名
            category: カテゴリ（オプション）
            
        Returns:
            Dict[str, Any]: 説明情報
            {
                "description": "生成された詳細説明",
                "confidence": 0.9
            }
        """
        try:
            # デバッグ用ログ
            logger.debug(f"generate_description called with menu_item='{menu_item}', category='{category}'")
            
            # description.yamlのプロンプトを使用
            system_prompt, user_prompt = self._get_prompts("description", menu_item, category)
            
            logger.info(f"Generating description for: {menu_item} (category: {category})")
            
            result = await self._make_completion_request(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.7,
                max_tokens=800
            )
            
            description = result.strip() if result else ""
            
            logger.info(f"Generated description for: {menu_item}")
            return {
                "description": description
            }
            
        except Exception as e:
            logger.error(f"Failed to generate description for {menu_item}: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # フォールバック: 基本的な説明を返す
            return {
                "description": f"{menu_item}は、厳選された食材を使用して丁寧に調理された料理です。独特の風味と食感をお楽しみいただけます。"
            }

@lru_cache(maxsize=1)
def get_description_client() -> DescriptionClient:
    """
    DescriptionClient のインスタンスを取得（シングルトン）
    
    Returns:
        DescriptionClient: 詳細説明生成クライアント（キャッシュ済み）
    """
    return DescriptionClient() 
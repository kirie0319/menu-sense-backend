"""
Categorize Client - Infrastructure Layer
Specialized client for menu structure categorization using Function Calling
"""
from functools import lru_cache
from typing import Dict, List, Any
from app_2.utils.logger import get_logger
from app_2.prompt_loader import PromptLoader
from .openai_base_client import OpenAIBaseClient

logger = get_logger("categorize_client")


class CategorizeClient(OpenAIBaseClient):
    """
    カテゴライズ専用クライアント（Function Calling対応）
    
    メニュー全体構造を適切にカテゴリ分析し、構造化されたJSONでレスポンス
    """

    def __init__(self):
        """カテゴライズクライアントを初期化"""
        super().__init__()
        self.prompt_loader = PromptLoader(base_path="app_2/prompts")
        logger.info("CategorizeClient initialized with PromptLoader")

    def _get_menu_structure_categorize_function_schema(self) -> List[Dict[str, Any]]:
        """
        メニュー構造カテゴライズ用のFunction Callingスキーマを取得（YAMLファイルから読み込み）
        
        Returns:
            List[Dict[str, Any]]: Function Callingのスキーマ定義
        """
        schema = self.prompt_loader.get_function_schema(
            provider="openai",
            category="menu_analysis", 
            schema_name="categorize",
            function_name="menu_structure"
        )
        return [schema]

    async def categorize_menu_structure(self, mapping_data: str, level: str) -> Dict[str, Any]:
        """
        OpenAI APIを使用してマッピングデータをカテゴライズ（Function Calling使用）
        
        Args:
            mapping_data: 整形済みマッピングデータ
            level: データレベル
            
        Returns:
            Dict[str, Any]: カテゴライズ結果
        """
        # YAMLファイルからプロンプトを読み込み
        prompts = self.prompt_loader.load_prompt("openai", "menu_analysis", "categorize")
        menu_structure_prompts = prompts["menu_structure"]
        
        system_prompt = menu_structure_prompts["system"]
        user_prompt = menu_structure_prompts["user"].format(
            mapping_data=mapping_data,
            level=level
        )
        
        try:
            result = await self._make_function_call_request(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                functions=self._get_menu_structure_categorize_function_schema(),
                function_call={"name": "categorize_menu_structure"}
            )
            
            logger.info("Menu structure categorization successful - structured JSON returned")
            return result
            
        except Exception as e:
            logger.error(f"Menu structure categorization failed: {e}")
            # フォールバック: エラー時は基本構造を返す
            return {
                "menu": {
                    "overall_summary": {
                        "main_categories": [],
                        "note": f"分析エラーが発生しました: {str(e)}"
                    },
                    "categories": [],
                    "other_texts": [],
                    "summary_table": []
                },
                "error": str(e),
                "fallback_used": True
            }


@lru_cache(maxsize=1)
def get_categorize_client() -> CategorizeClient:
    """
    CategorizeClientのシングルトンインスタンスを取得
    
    Returns:
        CategorizeClient: カテゴライズクライアント（キャッシュ済み）
    """
    return CategorizeClient() 
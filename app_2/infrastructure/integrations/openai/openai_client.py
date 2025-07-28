"""
OpenAI Client - Infrastructure Layer
Unified client for all OpenAI-based menu analysis features with Function Calling support
"""
from functools import lru_cache
from typing import Dict, Any
from app_2.utils.logger import get_logger
from .description_client import get_description_client
from .allergen_client import get_allergen_client
from .ingredient_client import get_ingredient_client

logger = get_logger("openai_client")


class OpenAIClient:
    """
    OpenAI API 統合クライアント（Function Calling対応版）
    
    メニュー解析の機能を提供（内部では専用クライアントを使用）
    Function Callingによる構造化されたデータと従来互換性の両方をサポート
    """
    
    def __init__(self):
        """
        OpenAI API 統合クライアントを初期化（シングルトンクライアント使用）
        """
        self._description_client = get_description_client()
        self._allergen_client = get_allergen_client()
        self._ingredient_client = get_ingredient_client()

    # ===== Function Calling対応メソッド（新機能） =====

    async def extract_allergens_detailed(self, menu_item: str) -> Dict[str, Any]:
        """
        アレルゲン抽出（Function Calling使用、構造化データ）
        
        Args:
            menu_item: メニュー項目名
            
        Returns:
            Dict[str, Any]: アレルゲン情報の構造化データ
        """
        return await self._allergen_client.extract_allergens(menu_item)

    async def extract_ingredients_detailed(self, menu_item: str) -> Dict[str, Any]:
        """
        含有物抽出（Function Calling使用、構造化データ）
        
        Args:
            menu_item: メニュー項目名
            
        Returns:
            Dict[str, Any]: 含有物情報の構造化データ
        """
        return await self._ingredient_client.extract_ingredients(menu_item)

    async def generate_description_detailed(self, menu_item: str, category: str = "") -> Dict[str, Any]:
        """
        詳細説明生成（プロンプトベース、構造化データ）
        
        Args:
            menu_item: メニュー項目名
            category: カテゴリ（オプション）
            
        Returns:
            Dict[str, Any]: 説明情報の構造化データ
        """
        return await self._description_client.generate_description(menu_item, category)

    async def analyze_menu_item_comprehensive(self, menu_item: str, category: str = "") -> Dict[str, Any]:
        """
        メニュー項目の包括的分析（Function Calling使用、一部機能統合）
        
        Args:
            menu_item: メニュー項目名
            category: カテゴリ（オプション）
            
        Returns:
            Dict[str, Any]: 包括的分析結果の構造化データ
        """
        try:
            logger.info(f"Starting comprehensive analysis for: {menu_item}")
            
            # 並列で分析を実行（カテゴライズは除外）
            import asyncio
            allergen_task = self.extract_allergens_detailed(menu_item)
            ingredient_task = self.extract_ingredients_detailed(menu_item)
            description_task = self.generate_description_detailed(menu_item, category)
            
            allergen_result, ingredient_result, description_result = await asyncio.gather(
                allergen_task, ingredient_task, description_task,
                return_exceptions=True
            )
            
            # 結果を統合
            analysis_result = {
                "menu_item": menu_item,
                "category": category if category else "未指定",
                "allergens": allergen_result if not isinstance(allergen_result, Exception) else None,
                "ingredients": ingredient_result if not isinstance(ingredient_result, Exception) else None,
                "description": description_result if not isinstance(description_result, Exception) else None,
                "analysis_timestamp": "2024-01-01T00:00:00Z",  # 実際のタイムスタンプ
                "analysis_status": "completed"
            }
            
            # エラーがあった場合の処理
            errors = []
            for task_name, result in [
                ("allergens", allergen_result),
                ("ingredients", ingredient_result), 
                ("description", description_result)
            ]:
                if isinstance(result, Exception):
                    errors.append(f"{task_name}: {str(result)}")
                    logger.error(f"Error in {task_name} analysis for {menu_item}: {result}")
            
            if errors:
                analysis_result["errors"] = errors
                analysis_result["analysis_status"] = "completed_with_errors"
            
            logger.info(f"Comprehensive analysis completed for: {menu_item}")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Comprehensive analysis failed for {menu_item}: {e}")
            return {
                "menu_item": menu_item,
                "category": category if category else "未指定",
                "allergens": None,
                "ingredients": None,
                "description": None,
                "analysis_timestamp": "2024-01-01T00:00:00Z",
                "analysis_status": "failed",
                "error": str(e)
            }

    # ===== 従来互換性メソッド（文字列レスポンス） =====

    async def extract_allergens(self, menu_item: str) -> str:
        """
        アレルゲン抽出（従来互換性のため、文字列で返す）
        
        Args:
            menu_item: メニュー項目名
            
        Returns:
            str: アレルゲン情報（文字列）
        """
        result = await self._allergen_client.extract_allergens(menu_item)
        return ", ".join(result.get("allergens", [])) if result.get("allergens") else "特定のアレルゲンは検出されませんでした"

    async def extract_ingredients(self, menu_item: str) -> str:
        """
        含有物抽出（従来互換性のため、文字列で返す）
        
        Args:
            menu_item: メニュー項目名
            
        Returns:
            str: 含有物情報（文字列）
        """
        result = await self._ingredient_client.extract_ingredients(menu_item)
        return ", ".join(result.get("ingredients", [])) if result.get("ingredients") else "主要な材料情報は取得できませんでした"

    async def generate_description(self, menu_item: str, category: str = "") -> str:
        """
        詳細説明生成（従来互換性のため、文字列で返す）
        
        Args:
            menu_item: メニュー項目名
            category: カテゴリ（オプション）
            
        Returns:
            str: 生成された詳細説明
        """
        result = await self._description_client.generate_description(menu_item, category)
        return result.get("description", f"{menu_item}の美味しい一品です。")


@lru_cache(maxsize=1)
def get_openai_client() -> OpenAIClient:
    """
    OpenAIClient のインスタンスを取得（シングルトン）
    
    Returns:
        OpenAIClient: OpenAI API 統合クライアント（キャッシュ済み）
    """
    return OpenAIClient() 
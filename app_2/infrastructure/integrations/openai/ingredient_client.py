"""
Ingredient Client - Infrastructure Layer
Specialized client for ingredient information extraction using Function Calling
"""
from functools import lru_cache
from typing import Dict, List, Any
from app_2.utils.logger import get_logger
from .openai_base_client import OpenAIBaseClient

logger = get_logger("ingredient_client")


class IngredientClient(OpenAIBaseClient):
    """
    Ingredient extraction specialized client (Function Calling support)
    
    Extracts main ingredients and components from menu items in structured JSON format
    """

    def __init__(self):
        """Initialize ingredient client"""
        super().__init__()
        logger.info("IngredientClient initialized")

    def _get_ingredient_function_schema(self) -> List[Dict[str, Any]]:
        """
        Get Function Calling schema for ingredient extraction (loaded from YAML file)
        
        Returns:
            List[Dict[str, Any]]: Function Calling schema definition
        """
        # Use base class prompt_loader for consistency
        schema = self.prompt_loader.get_function_schema(
            provider="openai",
            category="menu_analysis",
            schema_name="ingredient",
            function_name="extract_ingredients"
        )
        return [schema]

    async def extract_ingredients(self, menu_item: str, category: str = "") -> Dict[str, Any]:
        """
        Extract ingredients from menu item
        """
        try:
            # Use base class _get_prompts method for consistency
            system_prompt, user_prompt = self._get_prompts("ingredient", menu_item, category)
            
            result = await self._make_function_call_request(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                functions=self._get_ingredient_function_schema(),
                function_call={"name": "extract_ingredients"}
            )
            
            ingredient_count = len(result.get("main_ingredients", []))
            category_info = f" (category: {category})" if category else ""
            logger.info(f"Extracted ingredients for: {menu_item}{category_info} -> {ingredient_count} ingredients found")
            return result
            
        except Exception as e:
            logger.error(f"Failed to extract ingredients for {menu_item} (category: {category}): {e}")
            # Fallback: return basic ingredient information
            return {
                "main_ingredients": [],
                "cooking_method": [],
                "cuisine_category": "unknown",
                "flavor_profile": {
                    "taste": [],
                    "texture": "unknown",
                    "intensity": "unknown"
                },
                "dietary_info": {
                    "vegetarian": False,
                    "vegan": False,
                    "gluten_free": False,
                    "dairy_free": False,
                    "low_carb": False,
                    "keto_friendly": False
                },
                "confidence": 0.0
            }


@lru_cache(maxsize=1)
def get_ingredient_client() -> IngredientClient:
    """
    Get IngredientClient instance (singleton)
    
    Returns:
        IngredientClient: Ingredient extraction client (cached)
    """
    return IngredientClient() 
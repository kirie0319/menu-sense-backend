"""
Allergen Client - Infrastructure Layer
Specialized client for allergen information extraction using Function Calling
"""
from functools import lru_cache
from typing import Dict, List, Any
from app_2.utils.logger import get_logger
from .openai_base_client import OpenAIBaseClient

logger = get_logger("allergen_client")


class AllergenClient(OpenAIBaseClient):
    """
    Allergen extraction specialized client (Function Calling support)
    
    Extracts allergen information from menu items in structured JSON format
    """

    def __init__(self):
        """Initialize allergen client"""
        super().__init__()
        logger.info("AllergenClient initialized")

    def _get_allergen_function_schema(self) -> List[Dict[str, Any]]:
        """
        Get Function Calling schema for allergen extraction (loaded from YAML file)
        
        Returns:
            List[Dict[str, Any]]: Function Calling schema definition
        """
        # Use base class prompt_loader for consistency
        schema = self.prompt_loader.get_function_schema(
            provider="openai",
            category="menu_analysis",
            schema_name="allergen",
            function_name="extract_allergens"
        )
        return [schema]

    async def extract_allergens(self, menu_item: str, category: str = "") -> Dict[str, Any]:
        try:
            # Use base class _get_prompts method for consistency
            system_prompt, user_prompt = self._get_prompts("allergen", menu_item, category)
            
            result = await self._make_function_call_request(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                functions=self._get_allergen_function_schema(),
                function_call={"name": "extract_allergens"}
            )
            
            allergen_count = len(result.get("allergens", []))
            category_info = f" (category: {category})" if category else ""
            logger.info(f"Extracted allergens for: {menu_item}{category_info} -> {allergen_count} allergens found")
            return result
            
        except Exception as e:
            logger.error(f"Failed to extract allergens for {menu_item} (category: {category}): {e}")
            # Fallback: return basic allergen information
            return {
                "allergens": [],
                "allergen_free": False,
                "notes": f"Unable to retrieve allergen information due to analysis error: {str(e)}",
                "confidence": 0.0
            }


@lru_cache(maxsize=1)
def get_allergen_client() -> AllergenClient:
    """
    Get AllergenClient instance (singleton)
    
    Returns:
        AllergenClient: Allergen extraction client (cached)
    """
    return AllergenClient() 
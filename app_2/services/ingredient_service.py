"""
Ingredient Service - Menu Processor v2
Simple ingredient analysis service for menu items
"""
from functools import lru_cache
from typing import Optional, Dict, Any, List
from app_2.infrastructure.integrations.openai import IngredientClient, get_ingredient_client
from app_2.utils.logger import get_logger

logger = get_logger("ingredient_service")


class IngredientService:
    """
    Simple ingredient analysis service
    
    Provides basic ingredient information extraction for menu items
    """
    
    def __init__(self, ingredient_client: Optional[IngredientClient] = None):
        """
        Initialize ingredient service
        
        Args:
            ingredient_client: IngredientClient instance (for testing)
                             None uses singleton client
        """
        self.ingredient_client = ingredient_client or get_ingredient_client()
        logger.info("IngredientService initialized")
    
    async def analyze_ingredients(self, menu_item: str, category: str = "") -> Dict[str, Any]:
        """
        Analyze ingredients in a menu item
        
        Args:
            menu_item: Menu item name
            category: Menu category (optional)
            
        Returns:
            Dict[str, Any]: Ingredient analysis result
        """
        if not menu_item or not menu_item.strip():
            logger.warning("Empty menu item provided for ingredient analysis")
            raise ValueError("Menu item cannot be empty")
        
        try:
            logger.info(f"Analyzing ingredients for: {menu_item}" + (f" (category: {category})" if category else ""))
            
            # Get ingredient information from client
            result = await self.ingredient_client.extract_ingredients(menu_item, category)
            
            logger.info(f"Ingredient analysis completed for: {menu_item}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to analyze ingredients for '{menu_item}': {e}")
            raise
    
    async def get_main_ingredients(self, menu_item: str, category: str = "") -> List[str]:
        """
        Get list of main ingredients
        
        Args:
            menu_item: Menu item name
            category: Menu category (optional)
            
        Returns:
            List[str]: List of main ingredient names
        """
        try:
            result = await self.analyze_ingredients(menu_item, category)
            ingredients = result.get("main_ingredients", [])
            
            # Extract ingredient names
            ingredient_names = [
                ing.get("ingredient", "") 
                for ing in ingredients 
                if ing.get("ingredient")
            ]
            
            return ingredient_names
            
        except Exception as e:
            logger.error(f"Failed to get main ingredients for '{menu_item}': {e}")
            return []
    
    async def is_vegetarian(self, menu_item: str, category: str = "") -> bool:
        """
        Check if menu item is vegetarian
        
        Args:
            menu_item: Menu item name
            category: Menu category (optional)
            
        Returns:
            bool: True if vegetarian
        """
        try:
            result = await self.analyze_ingredients(menu_item, category)
            dietary_info = result.get("dietary_info", {})
            return dietary_info.get("vegetarian", False)
            
        except Exception as e:
            logger.error(f"Failed to check vegetarian status for '{menu_item}': {e}")
            return False
    
    async def is_vegan(self, menu_item: str, category: str = "") -> bool:
        """
        Check if menu item is vegan
        
        Args:
            menu_item: Menu item name
            category: Menu category (optional)
            
        Returns:
            bool: True if vegan
        """
        try:
            result = await self.analyze_ingredients(menu_item, category)
            dietary_info = result.get("dietary_info", {})
            return dietary_info.get("vegan", False)
            
        except Exception as e:
            logger.error(f"Failed to check vegan status for '{menu_item}': {e}")
            return False
    
    async def is_gluten_free(self, menu_item: str, category: str = "") -> bool:
        """
        Check if menu item is gluten-free
        
        Args:
            menu_item: Menu item name
            category: Menu category (optional)
            
        Returns:
            bool: True if gluten-free
        """
        try:
            result = await self.analyze_ingredients(menu_item, category)
            dietary_info = result.get("dietary_info", {})
            return dietary_info.get("gluten_free", False)
            
        except Exception as e:
            logger.error(f"Failed to check gluten-free status for '{menu_item}': {e}")
            return False


@lru_cache(maxsize=1)
def get_ingredient_service() -> IngredientService:
    """
    Get IngredientService singleton instance
    
    Returns:
        IngredientService: Ingredient service singleton instance
    """
    return IngredientService() 
"""
Allergen Service - Menu Processor v2
Simple allergen analysis service for menu items
"""
from functools import lru_cache
from typing import Optional, Dict, Any
from app_2.infrastructure.integrations.openai import AllergenClient, get_allergen_client
from app_2.utils.logger import get_logger

logger = get_logger("allergen_service")


class AllergenService:
    """
    Simple allergen analysis service
    
    Provides basic allergen information extraction for menu items
    """
    
    def __init__(self, allergen_client: Optional[AllergenClient] = None):
        """
        Initialize allergen service
        
        Args:
            allergen_client: AllergenClient instance (for testing)
                           None uses singleton client
        """
        self.allergen_client = allergen_client or get_allergen_client()
        logger.info("AllergenService initialized")
    
    async def analyze_allergens(self, menu_item: str, category: str = "") -> Dict[str, Any]:
        """
        Analyze allergens in a menu item
        
        Args:
            menu_item: Menu item name
            category: Menu category (optional)
            
        Returns:
            Dict[str, Any]: Allergen analysis result
        """
        if not menu_item or not menu_item.strip():
            logger.warning("Empty menu item provided for allergen analysis")
            raise ValueError("Menu item cannot be empty")
        
        try:
            logger.info(f"Analyzing allergens for: {menu_item}" + (f" (category: {category})" if category else ""))
            
            # Get allergen information from client
            result = await self.allergen_client.extract_allergens(menu_item, category)
            
            logger.info(f"Allergen analysis completed for: {menu_item}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to analyze allergens for '{menu_item}': {e}")
            raise



@lru_cache(maxsize=1)
def get_allergen_service() -> AllergenService:
    """
    Get AllergenService singleton instance
    
    Returns:
        AllergenService: Allergen service singleton instance
    """
    return AllergenService() 
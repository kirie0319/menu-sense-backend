"""
Tasks package - Celery task imports for autodiscovery
"""

# Import all Celery tasks for autodiscovery
from .translate_task import translate_menu_task
from .describe_task import describe_menu_task
from .allergen_task import allergen_menu_task
from .ingredient_task import ingredient_menu_task
from .search_image_task import search_image_menu_task

__all__ = [
    "translate_menu_task",
    "describe_menu_task",
    "allergen_menu_task", 
    "ingredient_menu_task",
    "search_image_menu_task",
] 
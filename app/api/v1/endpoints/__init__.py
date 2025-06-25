"""
API v1 endpoints
"""

# OCRエンドポイントをエクスポート
from . import ocr

__all__ = ["ocr", "system", "menu_item_parallel", "images"]

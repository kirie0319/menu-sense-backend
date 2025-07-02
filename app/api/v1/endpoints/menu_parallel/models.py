"""
🎯 メニュー並列処理API用のPydanticモデル

このファイルは menu_item_parallel.py から分割されたモデル定義集です。
全てのAPI関連のリクエスト・レスポンスモデルを統一管理します。
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class MenuItemsRequest(BaseModel):
    """メニューアイテムリクエスト"""
    menu_items: List[str]  # 日本語メニューテキストのリスト
    test_mode: Optional[bool] = False  # Phase 2では実際のAPI統合がデフォルト


class MenuItemsResponse(BaseModel):
    """メニューアイテムレスポンス"""
    success: bool
    session_id: str
    total_items: int
    message: str
    test_mode: bool
    api_integration: str


class ItemStatusResponse(BaseModel):
    """アイテム状況レスポンス"""
    success: bool
    session_id: str
    item_id: int
    translation: Dict[str, Any]
    description: Dict[str, Any]
    image: Dict[str, Any]


class SessionStatusResponse(BaseModel):
    """セッション全体の状況レスポンス"""
    success: bool
    session_id: str
    total_items: int
    completed_items: int
    progress_percentage: float
    items_status: List[Dict[str, Any]]
    api_integration: str


class OCRToParallelRequest(BaseModel):
    """OCR → カテゴリ分類 → 並列処理統合リクエスト"""
    use_real_apis: Optional[bool] = True  # 実際のAPI統合を使用


class OCRToParallelResponse(BaseModel):
    """OCR → カテゴリ分類 → 並列処理統合レスポンス"""
    success: bool
    session_id: str
    ocr_result: Dict[str, Any]
    categorization_result: Dict[str, Any] 
    parallel_processing: Dict[str, Any]
    streaming_url: str
    message: str


# エクスポート用（インポート時の明確化）
__all__ = [
    "MenuItemsRequest",
    "MenuItemsResponse", 
    "ItemStatusResponse",
    "SessionStatusResponse",
    "OCRToParallelRequest",
    "OCRToParallelResponse"
] 
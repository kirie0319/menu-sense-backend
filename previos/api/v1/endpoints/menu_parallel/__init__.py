"""
🎯 メニュー並列処理API統合ルーター

このファイルは分割されたメニュー並列処理APIの全サブルーターを統合し、
既存のインポートとの完全な互換性を提供します。

分割構成:
- models.py: Pydanticモデル
- shared_state.py: 共有状態管理
- streaming.py: SSEストリーミング
- processing.py: メイン処理API
- testing.py: テスト・デバッグ
- ocr_integration.py: OCR統合処理

監視機能は統一監視システム（/api/v1/monitoring/）に統合されました。

元の menu_item_parallel.py との完全互換を維持。
"""

from fastapi import APIRouter

# 各サブモジュールのインポート
from . import models
from .streaming import router as streaming_router
from .processing import router as processing_router  
from .testing import router as testing_router
from .ocr_integration import router as ocr_router

# 統合ルーター作成
router = APIRouter()

# 各サブルーターをマウント
router.include_router(streaming_router, tags=["SSE Streaming"])
router.include_router(processing_router, tags=["Processing"])
router.include_router(testing_router, tags=["Testing"])
router.include_router(ocr_router, tags=["OCR Integration"])


# ====================================
# 🔄 後方互換性: 直接インポート対応
# ====================================

# モデルクラスの直接インポート対応（既存コードとの互換性）
from .models import (
    MenuItemsRequest,
    MenuItemsResponse,
    ItemStatusResponse,
    SessionStatusResponse
)

# 共有状態の直接インポート対応
from .shared_state import (
    _progress_streams,
    _active_sessions,
    send_sse_event,
    cleanup_session_state,
    get_sse_statistics,
    initialize_session
)


# ====================================
# 📊 統合API情報エンドポイント
# ====================================

@router.get("/")
async def get_api_info():
    """メニュー並列処理API統合情報"""
    return {
        "name": "Menu Item Parallel Processing API",
        "version": "2.2.0-unified-monitoring",
        "description": "Complete menu item processing with real API integration and SSE streaming",
        "architecture": "Split into specialized modules with unified monitoring",
        "modules": {
            "streaming": "SSE real-time progress streaming",
            "processing": "Core menu item processing APIs",
            "testing": "Debug and test endpoints",
            "ocr_integration": "OCR → Categorization → Parallel processing flow"
        },
        "features": [
            "Real API Integration (Google Translate + OpenAI + Imagen3)",
            "SSE Real-time Streaming",
            "Redis State Management",
            "Celery Parallel Processing",
            "OCR Text Extraction",
            "AI-powered Categorization",
            "Unified Health Monitoring"
        ],
        "endpoints": {
            "streaming": ["/stream/{session_id}", "/notify/{session_id}"],
            "processing": ["/process-menu-items", "/status/{session_id}/item/{item_id}", "/status/{session_id}"],
            "testing": ["/test/redis", "/test/single-item", "/cleanup/{session_id}", "/test/system-info", "/test/bulk-cleanup"],
            "ocr_integration": ["/ocr-to-parallel"]
        },
        "monitoring_migration": {
            "old_paths": [
                "/menu-parallel/stats/system",
                "/menu-parallel/stats/api-health", 
                "/menu-parallel/stats/sse",
                "/menu-parallel/stats/performance"
            ],
            "new_paths": [
                "/monitoring/stats/system",
                "/monitoring/health/apis",
                "/monitoring/stats/sse", 
                "/monitoring/stats/performance"
            ],
            "note": "Monitoring functionality migrated to unified monitoring system"
        },
        "backward_compatibility": True,
        "migration_notes": "Monitoring endpoints moved to /api/v1/monitoring/* for better organization"
    }


# ====================================
# 🔗 エクスポート（既存インポートとの互換性）
# ====================================

__all__ = [
    # メインルーター
    "router",
    
    # モデルクラス
    "MenuItemsRequest",
    "MenuItemsResponse", 
    "ItemStatusResponse",
    "SessionStatusResponse",
    
    # 共有状態
    "_progress_streams",
    "_active_sessions",
    "send_sse_event",
    "cleanup_session_state",
    "get_sse_statistics",
    "initialize_session",
    
    # モジュール参照
    "models"
] 
"""
API v1 ルーター
"""
from fastapi import APIRouter

from .endpoints import menu_translation_db, images, monitoring
from .endpoints.menu_parallel import router as menu_parallel_router

# APIルーターの作成
api_router = APIRouter()

# ===== NEW: 統一監視システムによる完全置き換え =====
# 古い system.py を新しい monitoring.py で完全に置き換え
api_router.include_router(monitoring.router, prefix="/system", tags=["System"])  # 🔄 Path compatibility
api_router.include_router(monitoring.router, prefix="/monitoring", tags=["Monitoring"])  # 🆕 New enhanced path

# エンドポイントの追加
api_router.include_router(menu_translation_db.router, prefix="/menu-translation", tags=["Menu Translation"])
api_router.include_router(images.router, prefix="/images", tags=["Images"])

# 並列処理エンドポイント（統合ルーター）
api_router.include_router(menu_parallel_router, prefix="/menu-parallel", tags=["Menu Parallel Processing"])

from fastapi import APIRouter
from fastapi.staticfiles import StaticFiles
import os

from .endpoints import ocr, system, menu_parallel, images, menu_translation_db
from app.core.config import settings

# APIルーターの作成
api_router = APIRouter()

# 静的ファイル配信を最初に追加（ルーティング優先度のため）
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
api_router.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="api_uploads")

# システム・診断エンドポイントを追加
api_router.include_router(system.router, prefix="", tags=["System"])

# OCRエンドポイントを追加
api_router.include_router(ocr.router, prefix="/ocr", tags=["OCR"])

# メニューアイテム並列処理エンドポイントを追加（分割アーキテクチャ版）
api_router.include_router(menu_parallel.router, prefix="/menu-parallel", tags=["Menu Item Parallel Processing"])

# S3画像管理エンドポイントを追加
api_router.include_router(images.router, prefix="/images", tags=["S3 Images"])

# Database-integrated menu translation endpoints
api_router.include_router(menu_translation_db.router, prefix="/menu-translation", tags=["Menu Translation Database"])

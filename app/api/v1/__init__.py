from fastapi import APIRouter

from .endpoints import ocr, category, translation, description, image, ui, menu, session, system

# APIルーターの作成
api_router = APIRouter()

# UIエンドポイントを追加（main.pyから移行）
api_router.include_router(ui.router, prefix="", tags=["UI"])

# メニュー処理エンドポイントを追加（main.pyから移行）
api_router.include_router(menu.router, prefix="", tags=["Menu"])

# セッション・進行状況エンドポイントを追加（main.pyから移行）
api_router.include_router(session.router, prefix="", tags=["Session"])

# システム・診断エンドポイントを追加（main.pyから移行）
api_router.include_router(system.router, prefix="", tags=["System"])

# OCRエンドポイントを追加
api_router.include_router(ocr.router, prefix="/ocr", tags=["OCR"])

# カテゴリ分類エンドポイントを追加
api_router.include_router(category.router, prefix="/category", tags=["Category"])

# 翻訳エンドポイントを追加
api_router.include_router(translation.router, prefix="/translation", tags=["Translation"])

# 詳細説明エンドポイントを追加
api_router.include_router(description.router, prefix="/description", tags=["Description"])

# 画像生成エンドポイントを追加
api_router.include_router(image.router, prefix="/image", tags=["Image Generation"])

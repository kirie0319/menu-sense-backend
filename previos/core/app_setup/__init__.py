"""
アプリケーション設定統合サービス

このモジュールは以下の機能を提供します：
- FastAPIアプリケーションの作成と設定
- ミドルウェア、ルーター、静的ファイルの統合設定
"""

from fastapi import FastAPI
import logging

from app.core.config import validate_settings
from app.core.config.base import base_settings
from .middleware import setup_middleware
from .router_manager import setup_routers
from .static_files import setup_static_files

logger = logging.getLogger(__name__)

def create_app() -> FastAPI:
    """
    設定済みFastAPIアプリケーションを作成する
    
    Returns:
        FastAPI: 完全に設定されたFastAPIアプリケーションインスタンス
    """
    
    # 設定値の検証
    issues = validate_settings()
    if issues:
        logger.warning("⚠️ Configuration issues detected:")
        for issue in issues:
            logger.warning(f"   - {issue}")
        logger.warning("   Some features may not be available.")
    
    # FastAPIアプリケーション作成
    app = FastAPI(
        title=base_settings.app_title,
        version=base_settings.app_version,
        description=base_settings.app_description
    )
    
    # 設定の適用（順序重要）
    setup_static_files(app)  # 静的ファイル設定
    setup_routers(app)       # ルーター設定
    setup_middleware(app)    # ミドルウェア設定（最後に適用）
    
    logger.info(f"✅ FastAPI application created: {base_settings.app_title} v{base_settings.app_version}")
    
    return app

# 公開API
__all__ = [
    'create_app'
] 
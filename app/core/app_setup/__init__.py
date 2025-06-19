"""
アプリケーション設定統合サービス

このモジュールは以下の機能を提供します：
- FastAPIアプリケーションの作成
- ミドルウェア設定
- ルーター統合
- 静的ファイル配信設定
- 後方互換性レイヤー
"""

from fastapi import FastAPI
from typing import Dict, Any

# 個別サービスのインポート
from .app_factory import create_app
from .middleware import setup_middleware
from .router_manager import setup_routers
from .static_files import setup_static_files
from .compatibility import setup_compatibility_layer

class ApplicationSetup:
    """アプリケーション全体の設定を管理するクラス"""
    
    @staticmethod
    def create_and_configure_app() -> tuple[FastAPI, Dict[str, Any]]:
        """アプリケーションを作成し、すべての設定を適用する"""
        
        # 1. FastAPIアプリ作成
        app = create_app()
        
        # 2. 静的ファイル設定
        setup_static_files(app)
        
        # 3. ルーター設定
        setup_routers(app)
        
        # 4. ミドルウェア設定
        setup_middleware(app)
        
        # 5. 後方互換性レイヤー設定
        compatibility_vars = setup_compatibility_layer()
        
        return app, compatibility_vars

# 便利な関数
def create_configured_app() -> tuple[FastAPI, Dict[str, Any]]:
    """設定済みFastAPIアプリケーションを作成する便利関数"""
    return ApplicationSetup.create_and_configure_app()

# 個別機能も直接利用可能
__all__ = [
    # メイン機能
    'ApplicationSetup',
    'create_configured_app',
    
    # 個別機能
    'create_app',
    'setup_middleware', 
    'setup_routers',
    'setup_static_files',
    'setup_compatibility_layer'
] 
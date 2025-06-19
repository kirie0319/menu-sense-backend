"""
ルーター管理サービス
"""
from fastapi import FastAPI

class RouterManager:
    """APIルーターとハンドラーの統合を管理するクラス"""
    
    @staticmethod
    def setup_api_routers(app: FastAPI) -> None:
        """APIルーターを設定する"""
        # APIルーターのインポート
        from app.api.v1 import api_router
        
        # APIルーターを統合
        app.include_router(api_router, prefix="/api/v1")
    
    @staticmethod
    def setup_handlers(app: FastAPI) -> None:
        """ハンドラーを設定する"""
        # ハンドラーのインポート
        from app.handlers.health import router as health_router
        from app.handlers.progress import router as progress_router
        from app.handlers.translate import router as translate_router
        
        # ハンドラーを統合
        app.include_router(health_router)
        app.include_router(progress_router)
        app.include_router(translate_router)
    
    @staticmethod
    def setup_all_routers(app: FastAPI) -> None:
        """すべてのルーターを設定する"""
        RouterManager.setup_api_routers(app)
        RouterManager.setup_handlers(app)

# 便利な関数
def setup_routers(app: FastAPI) -> None:
    """アプリケーションにルーターを設定する便利関数"""
    RouterManager.setup_all_routers(app) 
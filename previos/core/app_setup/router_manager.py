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
    def setup_all_routers(app: FastAPI) -> None:
        """すべてのルーターを設定する"""
        RouterManager.setup_api_routers(app)

# 便利な関数
def setup_routers(app: FastAPI) -> None:
    """アプリケーションにルーターを設定する便利関数"""
    RouterManager.setup_all_routers(app) 
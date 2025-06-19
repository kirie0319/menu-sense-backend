"""
ミドルウェア設定サービス
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

class MiddlewareManager:
    """ミドルウェアの設定を管理するクラス"""
    
    @staticmethod
    def setup_cors(app: FastAPI) -> None:
        """CORS設定をアプリケーションに追加する"""
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
            allow_methods=settings.CORS_ALLOW_METHODS,
            allow_headers=settings.CORS_ALLOW_HEADERS,
            expose_headers=settings.CORS_EXPOSE_HEADERS,
        )
    
    @staticmethod
    def setup_all_middleware(app: FastAPI) -> None:
        """すべてのミドルウェアを設定する"""
        MiddlewareManager.setup_cors(app)

# 便利な関数
def setup_middleware(app: FastAPI) -> None:
    """アプリケーションにミドルウェアを設定する便利関数"""
    MiddlewareManager.setup_all_middleware(app) 
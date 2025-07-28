"""
ミドルウェア設定
FastAPIアプリケーション用のミドルウェアを設定
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config.cors import cors_settings

class MiddlewareManager:
    """ミドルウェアの設定を管理するクラス"""
    
    @staticmethod
    def setup_cors(app: FastAPI) -> None:
        """CORS設定をアプリケーションに追加する"""
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_settings.origins,
            allow_credentials=cors_settings.allow_credentials,
            allow_methods=cors_settings.allow_methods,
            allow_headers=cors_settings.allow_headers,
            expose_headers=cors_settings.expose_headers,
        )
    
    @staticmethod
    def setup_all_middleware(app: FastAPI) -> None:
        """すべてのミドルウェアを設定する"""
        MiddlewareManager.setup_cors(app)

# 便利な関数
def setup_middleware(app: FastAPI) -> None:
    """アプリケーションにミドルウェアを設定する便利関数"""
    MiddlewareManager.setup_all_middleware(app) 
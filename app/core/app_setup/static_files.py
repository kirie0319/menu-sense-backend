"""
静的ファイル設定サービス
"""
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.core.config import settings

class StaticFilesManager:
    """静的ファイル配信の設定を管理するクラス"""
    
    @staticmethod
    def ensure_upload_directory() -> None:
        """アップロードディレクトリの存在を確認し、必要に応じて作成する"""
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    @staticmethod
    def setup_static_files(app: FastAPI) -> None:
        """静的ファイル配信を設定する"""
        # アップロードディレクトリの作成
        StaticFilesManager.ensure_upload_directory()
        
        # 静的ファイル配信の設定（画像アクセス用）
        app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")
    
    @staticmethod
    def setup_all_static_files(app: FastAPI) -> None:
        """すべての静的ファイル配信を設定する"""
        StaticFilesManager.setup_static_files(app)

# 便利な関数
def setup_static_files(app: FastAPI) -> None:
    """アプリケーションに静的ファイル配信を設定する便利関数"""
    StaticFilesManager.setup_all_static_files(app) 
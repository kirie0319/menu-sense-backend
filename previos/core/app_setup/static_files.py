"""
静的ファイル設定
FastAPIアプリケーション用の静的ファイル配信を設定
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.core.config.base import base_settings
import os


def setup_static_files(app: FastAPI):
    """静的ファイル配信を設定"""
    
    # アップロードディレクトリが存在しない場合は作成
    os.makedirs(base_settings.upload_dir, exist_ok=True)
    
    # アップロードファイル用の静的ファイル配信
    app.mount("/uploads", StaticFiles(directory=base_settings.upload_dir), name="uploads")
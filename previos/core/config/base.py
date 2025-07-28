"""
アプリケーション基本設定
アプリケーション情報、サーバー設定、ファイル設定を管理
"""
from pydantic import BaseModel
from typing import List
import os
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()


class BaseSettings(BaseModel):
    """アプリケーション基本設定クラス"""
    
    # ===== アプリケーション情報 =====
    app_title: str = "Menu Processor MVP"
    app_version: str = "1.0.0"
    app_description: str = "Transform Japanese restaurant menus into detailed English descriptions for international visitors"
    
    # ===== サーバー設定 =====
    host: str = "0.0.0.0"
    port: int = int(os.getenv("PORT", 8000))
    
    # ===== ファイル設定 =====
    upload_dir: str = "uploads"
    max_file_size: int = 20 * 1024 * 1024  # 20MB
    allowed_file_types: List[str] = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    
    class Config:
        env_file = ".env"
    
    def get_server_config(self) -> dict:
        """サーバー設定辞書を取得"""
        return {
            "host": self.host,
            "port": self.port,
            "title": self.app_title,
            "version": self.app_version,
            "description": self.app_description
        }
    
    def get_file_config(self) -> dict:
        """ファイル設定辞書を取得"""
        return {
            "upload_dir": self.upload_dir,
            "max_file_size": self.max_file_size,
            "allowed_file_types": self.allowed_file_types
        }


# グローバルインスタンス
base_settings = BaseSettings()


# 後方互換性のための関数（移行期間中のみ使用）
def get_base_settings():
    """基本設定を取得（後方互換性用）"""
    return base_settings

"""
FastAPI アプリケーションファクトリー
"""
from fastapi import FastAPI
from app.core.config import settings, validate_settings

class AppFactory:
    """FastAPIアプリケーションの作成と設定を管理するファクトリークラス"""
    
    @staticmethod
    def create_app() -> FastAPI:
        """FastAPIアプリケーションを作成する"""
        
        # 起動時の設定検証
        config_issues = validate_settings()
        if config_issues:
            print("⚠️ Configuration issues detected:")
            for issue in config_issues:
                print(f"   - {issue}")
            print("   Some features may not be available.")
        
        # FastAPIアプリケーション作成
        app = FastAPI(
            title=settings.APP_TITLE, 
            version=settings.APP_VERSION,
            description=settings.APP_DESCRIPTION
        )
        
        return app

# 便利な関数
def create_app() -> FastAPI:
    """FastAPIアプリケーションを作成する便利関数"""
    return AppFactory.create_app() 
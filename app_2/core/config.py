"""
このファイルは以下の設定を統合管理します:
- アプリケーション基本設定
- AI/API設定 (OpenAI, Gemini, Imagen)
- AWS設定 (S3, Secrets Manager)
- Redis/Celery設定
- CORS設定
"""

from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
from dotenv import load_dotenv

load_dotenv()


# ==========================================
# Base Settings
# ==========================================

class BaseSettings(BaseModel):
    """アプリケーション基本設定"""
    
    # アプリケーション情報
    app_title: str = "Menu Processor v2"
    app_version: str = "2.0.0"
    app_description: str = "Clean Architecture-based menu processing system with pipeline architecture"
    
    # サーバー設定
    host: str = os.getenv("HOST")
    port: int = int(os.getenv("PORT"))
    
    # デバッグ設定
    debug_mode: bool = os.getenv("DEBUG_MODE", "false").lower() == "true"
    
    # データベース自動リセット設定
    auto_reset_database: bool = os.getenv("AUTO_RESET_DATABASE", "false").lower() == "true"
    
    max_file_size: int = 20 * 1024 * 1024  # 20MB
    allowed_file_types: List[str] = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    
    # データベース設定
    database_url: Optional[str] = os.getenv("DATABASE_URL")
    db_host: str = os.getenv("DB_HOST")
    db_port: int = int(os.getenv("DB_PORT"))
    db_user: str = os.getenv("DB_USER") 
    db_password: str = os.getenv("DB_PASSWORD")
    db_name: str = os.getenv("DB_NAME")
    
    class Config:
        env_file = ".env"


# ==========================================
# AI/API Settings
# ==========================================

class AISettings(BaseModel):
    """AI/API設定"""
    
    # API認証キー
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    gemini_api_key: Optional[str] = os.getenv("GEMINI_API_KEY")
    
    # Google Cloud設定
    google_cloud_project_id: Optional[str] = os.getenv("GOOGLE_CLOUD_PROJECT_ID")
    google_search_engine_id: Optional[str] = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
    
    # OpenAI設定
    openai_model_name: str = "gpt-4.1-mini"
    openai_timeout: float = float(os.getenv("OPENAI_TIMEOUT", 120.0))
    openai_max_retries: int = int(os.getenv("OPENAI_MAX_RETRIES", 3))
    
    # Gemini設定
    gemini_model: str = "gemini-2.0-flash-exp"
    
    # Imagen設定
    imagen_model: str = "imagen-3.0-generate-002"
    imagen_aspect_ratio: str = "1:1"
    imagen_number_of_images: int = 1
    
    def is_openai_api_key_available(self) -> bool:
        return bool(self.openai_api_key)
    
    def is_gemini_api_key_available(self) -> bool:
        return bool(self.gemini_api_key)


# ==========================================
# AWS Settings
# ==========================================

class AWSSettings(BaseModel):
    """AWS関連設定"""
    
    # 認証情報
    access_key_id: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
    secret_access_key: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")
    session_token: Optional[str] = os.getenv("AWS_SESSION_TOKEN")
    region: str = os.getenv("AWS_REGION")
    
    # S3設定
    s3_bucket_name: str = os.getenv("S3_BUCKET_NAME")
    s3_region: str = os.getenv("S3_REGION")
    s3_image_prefix: str = os.getenv("S3_IMAGE_PREFIX")
    s3_public_url_template: str = os.getenv("S3_PUBLIC_URL_TEMPLATE")
    secret_name: str = os.getenv("AWS_SECRET_NAME")
    
    def is_credentials_available(self) -> bool:
        return bool(self.access_key_id and self.secret_access_key)


# ==========================================
# Redis/Celery Settings (MVP Simplified)
# ==========================================

class CelerySettings(BaseModel):
    """Redis/Celery設定（MVP簡素版）"""
    
    # 🎯 MVP必須設定のみ
    redis_url: str = os.getenv("REDIS_URL")
    sse_channel_prefix: str = os.getenv("SSE_CHANNEL_PREFIX", "sse:")
    
    def get_sse_channel(self, session_id: str) -> str:
        """SSE用チャンネル名を生成"""
        return f"{self.sse_channel_prefix}{session_id}"
    
    def is_redis_available(self) -> bool:
        """Redis接続可能性チェック（同期版・互換性維持）"""
        try:
            import redis
            client = redis.from_url(self.redis_url, socket_connect_timeout=3, socket_timeout=3)
            client.ping()
            client.close()
            return True
        except Exception:
            return False
    
    async def async_is_redis_available(self) -> bool:
        """Redis接続可能性チェック（非同期版・推奨）"""
        try:
            import redis.asyncio as redis
            client = redis.from_url(self.redis_url)
            try:
                await client.ping()
                return True
            finally:
                await client.aclose()
        except Exception:
            return False


# ==========================================
# CORS Settings
# ==========================================

class CORSSettings(BaseModel):
    """CORS設定"""
    
    # 環境変数から読み込み、カンマ区切りで複数指定可能
    origins: List[str] = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    allow_credentials: bool = os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true"
    allow_methods: List[str] = os.getenv("CORS_ALLOW_METHODS", "*").split(",")
    allow_headers: List[str] = os.getenv("CORS_ALLOW_HEADERS", "*").split(",")
    expose_headers: List[str] = os.getenv("CORS_EXPOSE_HEADERS", "*").split(",")
    
    def get_cors_config(self) -> dict:
        return {
            "allow_origins": self.origins,
            "allow_credentials": self.allow_credentials,
            "allow_methods": self.allow_methods,
            "allow_headers": self.allow_headers,
            "expose_headers": self.expose_headers
        }


# ==========================================
# Unified Configuration Management
# ==========================================

class Settings:
    """統合設定管理クラス"""
    
    def __init__(self):
        self.base = BaseSettings()
        self.ai = AISettings()
        self.aws = AWSSettings()
        self.celery = CelerySettings()
        self.cors = CORSSettings()
    
    def validate_all(self) -> Dict[str, List[str]]:
        """全設定の妥当性を検証"""
        issues = {}
        
        # AI設定の検証
        ai_issues = []
        if not self.ai.openai_api_key:
            ai_issues.append("OPENAI_API_KEY not set")
        if not self.ai.gemini_api_key:
            ai_issues.append("GEMINI_API_KEY not set")
        if self.ai.openai_timeout <= 0:
            ai_issues.append("OPENAI_TIMEOUT must be positive")
        
        if ai_issues:
            issues["ai"] = ai_issues
        
        # AWS設定の検証（簡素化）
        aws_issues = []
        if self.aws.access_key_id and not self.aws.secret_access_key:
            aws_issues.append("AWS_SECRET_ACCESS_KEY required when AWS_ACCESS_KEY_ID is set")
        if self.aws.secret_access_key and not self.aws.access_key_id:
            aws_issues.append("AWS_ACCESS_KEY_ID required when AWS_SECRET_ACCESS_KEY is set")
        
        if aws_issues:
            issues["aws"] = aws_issues
        
        # Celery設定の検証
        celery_issues = []
        if not self.celery.redis_url:
            celery_issues.append("REDIS_URL is required")
        if not self.celery.is_redis_available():
            celery_issues.append("Redis connection failed")
        
        if celery_issues:
            issues["celery"] = celery_issues
        return issues
    
    async def async_validate_all(self) -> Dict[str, List[str]]:
        """全設定の妥当性を検証（非同期版・Redis接続チェック含む）"""
        issues = {}
        
        # AI設定の検証
        ai_issues = []
        if not self.ai.openai_api_key:
            ai_issues.append("OPENAI_API_KEY not set")
        if not self.ai.gemini_api_key:
            ai_issues.append("GEMINI_API_KEY not set")
        if self.ai.openai_timeout <= 0:
            ai_issues.append("OPENAI_TIMEOUT must be positive")
        
        if ai_issues:
            issues["ai"] = ai_issues
        
        # AWS設定の検証（簡素化）
        aws_issues = []
        if self.aws.access_key_id and not self.aws.secret_access_key:
            aws_issues.append("AWS_SECRET_ACCESS_KEY required when AWS_ACCESS_KEY_ID is set")
        if self.aws.secret_access_key and not self.aws.access_key_id:
            aws_issues.append("AWS_ACCESS_KEY_ID required when AWS_SECRET_ACCESS_KEY is set")
        
        if aws_issues:
            issues["aws"] = aws_issues
        
        # Celery設定の検証（非同期Redis接続チェック使用）
        celery_issues = []
        if not self.celery.redis_url:
            celery_issues.append("REDIS_URL is required")
        if not await self.celery.async_is_redis_available():
            celery_issues.append("Redis connection failed")
        
        if celery_issues:
            issues["celery"] = celery_issues
        return issues
    
    def get_availability_status(self) -> Dict[str, bool]:
        """各サービスの可用性ステータスを取得"""
        return {
            "openai": self.ai.is_openai_api_key_available(),
            "gemini": self.ai.is_gemini_api_key_available(),
            "aws_credentials": self.aws.is_credentials_available(),
            "redis": self.celery.is_redis_available(),
        }
    
    async def async_get_availability_status(self) -> Dict[str, bool]:
        """各サービスの可用性ステータスを取得（非同期版・Redis接続チェック含む）"""
        return {
            "openai": self.ai.is_openai_api_key_available(),
            "gemini": self.ai.is_gemini_api_key_available(),
            "aws_credentials": self.aws.is_credentials_available(),
            "redis": await self.celery.async_is_redis_available(),
        }


# ==========================================
# Global Instance
# ==========================================

# グローバル設定インスタンス
settings = Settings()


# 後方互換性のためのエイリアス
base_settings = settings.base
ai_settings = settings.ai
aws_settings = settings.aws
celery_settings = settings.celery
cors_settings = settings.cors


# ==========================================
# Validation Functions
# ==========================================

def validate_settings() -> List[str]:
    """設定値の妥当性を検証（フラットリスト版）"""
    all_issues = []
    issues_by_category = settings.validate_all()
    
    for category, issues in issues_by_category.items():
        for issue in issues:
            all_issues.append(f"[{category.upper()}] {issue}")
    
    return all_issues

def get_configuration_summary() -> Dict[str, Any]:
    """設定サマリーを取得"""
    return {
        "app_info": {
            "title": settings.base.app_title,
            "version": settings.base.app_version,
            "host": settings.base.host,
            "port": settings.base.port
        },
        "services_available": settings.get_availability_status(),
        "validation_issues": len(validate_settings())
    }


# ==========================================
# Export
# ==========================================

__all__ = [
    # Main settings class
    "settings",
    
    # Individual setting classes
    "BaseSettings",
    "AISettings", 
    "AWSSettings",
    "CelerySettings",
    "CORSSettings",
    "Settings",
    
    # Compatibility aliases
    "base_settings",
    "ai_settings",
    "aws_settings", 
    "celery_settings",
    "cors_settings",
    
    # Utility functions
    "validate_settings",
    "get_configuration_summary"
] 
"""
設定管理パッケージ
"""
from .aws import aws_settings, AWSSettings
from .base import base_settings, BaseSettings
from .cors import cors_settings, CORS
from .ai import ai_settings, AISettings
from .processing import processing_settings, ProcessingSettings
from .celery import celery_settings, CelerySettings
from .sse import sse_settings, SSESettings

# アップロードディレクトリの作成
import os
os.makedirs(base_settings.upload_dir, exist_ok=True)

# config.pyから関数をインポート
import sys
import os
sys.path.append(os.path.dirname(__file__))

# config.pyの関数を動的にインポート
def check_api_availability():
    """各APIの利用可能性をチェック"""
    availability = {
        "openai": ai_settings.is_openai_available(),
        "gemini": ai_settings.is_gemini_available(),
        "aws_secrets_manager": aws_settings.use_secrets_manager,
        "redis": celery_settings.is_redis_available(),
        "celery": celery_settings.is_celery_configured()
    }
    return availability

def validate_settings():
    """設定値の妥当性を検証"""
    issues = []
    
    # AI設定の検証
    ai_issues = ai_settings.validate_configuration()
    issues.extend(ai_issues)
    
    # 並列処理設定の検証
    processing_issues = processing_settings.validate_configuration()
    issues.extend(processing_issues)
    
    # Celery設定の検証
    celery_issues = celery_settings.validate_configuration()
    issues.extend(celery_issues)
    
    # SSE設定の検証
    sse_issues = sse_settings.validate_configuration()
    issues.extend(sse_issues)
        
    # Google認証情報の検証
    if aws_settings.use_secrets_manager:
        aws_issues = aws_settings.validate_configuration()
        issues.extend(aws_issues)
    
    return issues

__all__ = [
    "aws_settings", "AWSSettings",
    "base_settings", "BaseSettings", 
    "cors_settings", "CORS",
    "ai_settings", "AISettings",
    "processing_settings", "ProcessingSettings",
    "celery_settings", "CelerySettings",
    "sse_settings", "SSESettings",
    "check_api_availability",
    "validate_settings"
] 
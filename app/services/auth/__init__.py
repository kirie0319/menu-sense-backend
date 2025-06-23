"""
API認証・クライアント管理サービス

このモジュールは以下の機能を提供します：
- Google Cloud認証情報管理
- 各種APIクライアントの初期化と管理
- OpenAI API リトライ機能
- 後方互換性API
"""

# 主要クラス
from .unified_auth import UnifiedAuthManager, get_unified_auth_manager
from .credentials import CredentialsManager, get_credentials_manager
from .clients import APIClientsManager, get_api_clients_manager
from .openai_retry import OpenAIRetryService, get_openai_retry_service, call_openai_with_retry

# 便利な関数をエクスポート（後方互換性のため）
def get_google_credentials():
    """Google Cloud認証情報を取得（後方互換性）"""
    return get_unified_auth_manager().get_credentials()

def get_vision_client():
    """Google Vision APIクライアントを取得（後方互換性）"""
    return get_api_clients_manager().get_vision_client()

def get_translate_client():
    """Google Translate APIクライアントを取得（後方互換性）"""
    return get_api_clients_manager().get_translate_client()

def get_openai_client():
    """OpenAI APIクライアントを取得（後方互換性）"""
    return get_api_clients_manager().get_openai_client()

def get_gemini_model():
    """Gemini APIモデルを取得（後方互換性）"""
    return get_api_clients_manager().get_gemini_model()

def get_imagen_client():
    """Imagen 3 APIクライアントを取得（後方互換性）"""
    return get_api_clients_manager().get_imagen_client()

# 可用性フラグを取得する関数
def get_api_availability():
    """すべてのAPIの可用性ステータスを取得"""
    return get_api_clients_manager().get_availability_status()

def is_vision_available():
    """Google Vision APIが利用可能かチェック"""
    return get_api_clients_manager().is_vision_available()

def is_translate_available():
    """Google Translate APIが利用可能かチェック"""
    return get_api_clients_manager().is_translate_available()

def is_openai_available():
    """OpenAI APIが利用可能かチェック"""
    return get_api_clients_manager().is_openai_available()

def is_gemini_available():
    """Gemini APIが利用可能かチェック"""
    return get_api_clients_manager().is_gemini_available()

def is_imagen_available():
    """Imagen 3 APIが利用可能かチェック"""
    return get_api_clients_manager().is_imagen_available()

# 統一認証システムの直接インターフェース
from .unified_auth import (
    get_google_credentials as get_unified_google_credentials,
    is_google_auth_available,
    get_auth_status,
    get_auth_troubleshooting
)

# 後方互換性のための変数エクスポート
def get_compatibility_variables():
    """main.pyで使用されている変数の後方互換性版を取得"""
    clients_manager = get_api_clients_manager()
    availability = clients_manager.get_availability_status()
    
    return {
        "google_credentials": clients_manager.get_google_credentials(),
        "vision_client": clients_manager.get_vision_client(),
        "translate_client": clients_manager.get_translate_client(),
        "openai_client": clients_manager.get_openai_client(),
        "gemini_model": clients_manager.get_gemini_model(),
        "imagen_client": clients_manager.get_imagen_client(),
        "VISION_AVAILABLE": availability["VISION_AVAILABLE"],
        "TRANSLATE_AVAILABLE": availability["TRANSLATE_AVAILABLE"],
        "OPENAI_AVAILABLE": availability["OPENAI_AVAILABLE"],
        "GEMINI_AVAILABLE": availability["GEMINI_AVAILABLE"],
        "IMAGEN_AVAILABLE": availability["IMAGEN_AVAILABLE"]
    }

# 統計情報取得
def get_auth_stats():
    """認証・API管理サービスの統計情報を取得"""
    clients_manager = get_api_clients_manager()
    credentials_manager = get_credentials_manager()
    
    return {
        "service": "auth_api_management",
        "version": "1.0.0",
        "google_credentials_loaded": credentials_manager.has_google_credentials(),
        "api_availability": clients_manager.get_availability_status(),
        "initialized_clients": [
            name for name, available in clients_manager.get_availability_status().items()
            if available
        ],
        "features": [
            "Google Cloud credentials management",
            "Multi-API client initialization",
            "OpenAI retry with exponential backoff",
            "Centralized availability status",
            "Backward compatibility"
        ]
    }

__all__ = [
    # クラス
    'UnifiedAuthManager', 'CredentialsManager', 'APIClientsManager', 'OpenAIRetryService',
    
    # インスタンス取得関数
    'get_unified_auth_manager', 'get_credentials_manager', 'get_api_clients_manager', 'get_openai_retry_service',
    
    # 統一認証システム関数
    'get_unified_google_credentials', 'is_google_auth_available', 'get_auth_status', 'get_auth_troubleshooting',
    
    # 後方互換性関数
    'get_google_credentials', 'get_vision_client', 'get_translate_client',
    'get_openai_client', 'get_gemini_model', 'get_imagen_client',
    'get_api_availability', 'is_vision_available', 'is_translate_available',
    'is_openai_available', 'is_gemini_available', 'is_imagen_available',
    'get_compatibility_variables', 'call_openai_with_retry',
    
    # ユーティリティ
    'get_auth_stats'
] 
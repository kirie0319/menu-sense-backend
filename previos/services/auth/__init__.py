"""
API認証管理サービス

このモジュールは以下の機能を提供します：
- Google Cloud認証情報管理 (AWS Secrets Manager統合)
- 統一認証インターフェース
- 後方互換性API
"""

# 主要クラス - 統合認証マネージャーから導入
from .auth_manager import (
    UnifiedAuthManager, 
    CredentialsManager,
    get_unified_auth_manager, 
    get_credentials_manager,
    get_auth_status,
    get_auth_troubleshooting
)

# 便利な関数をエクスポート（後方互換性のため）
def get_google_credentials():
    """Google Cloud認証情報を取得（後方互換性）"""
    return get_unified_auth_manager().get_credentials()

def get_vision_client():
    """Google Vision APIクライアント取得（スタブ - 後方互換性のみ）"""
    try:
        from google.cloud import vision
        credentials = get_google_credentials()
        return vision.ImageAnnotatorClient(credentials=credentials) if credentials else None
    except ImportError:
        return None

def get_translate_client():
    """Google Translate APIクライアント取得（スタブ - 後方互換性のみ）"""
    try:
        from google.cloud import translate_v2 as translate
        credentials = get_google_credentials()
        return translate.Client(credentials=credentials) if credentials else None
    except ImportError:
        return None

def get_openai_client():
    """OpenAI APIクライアント取得（スタブ - 後方互換性のみ）"""
    try:
        import openai
        return openai.OpenAI()
    except ImportError:
        return None

# 統一認証システムの関数は上記で既に導入済み

# 統計情報取得
def get_auth_stats():
    """認証管理サービスの統計情報を取得"""
    auth_manager = get_unified_auth_manager()
    
    return {
        "service": "unified_auth_management",
        "version": "1.0.0",
        "auth_available": auth_manager.is_available(),
        "auth_method": auth_manager.auth_method,
        "auth_source": auth_manager.auth_source,
        "features": [
            "AWS Secrets Manager integration",
            "Google Cloud credentials management",
            "Unified authentication interface",
            "Troubleshooting support"
        ]
    }

__all__ = [
    # クラス
    'UnifiedAuthManager', 'CredentialsManager',
    
    # インスタンス取得関数
    'get_unified_auth_manager', 'get_credentials_manager',
    
    # 統一認証システム関数
    'get_auth_status', 'get_auth_troubleshooting',
    
    # 後方互換性関数
    'get_google_credentials', 'get_vision_client', 'get_translate_client', 'get_openai_client',
    
    # ユーティリティ
    'get_auth_stats'
] 
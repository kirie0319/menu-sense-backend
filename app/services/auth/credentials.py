"""
API認証情報管理サービス
（統一認証システムのラッパー - 後方互換性のため）
"""
from typing import Optional
from google.oauth2 import service_account
from .unified_auth import get_unified_auth_manager

class CredentialsManager:
    """認証情報を管理するクラス（後方互換性のため維持）"""
    
    _instance: Optional['CredentialsManager'] = None
    
    def __new__(cls) -> 'CredentialsManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        # 統一認証マネージャーを使用
        self.unified_auth = get_unified_auth_manager()
        self._initialized = True
    
    def get_google_credentials(self) -> Optional[service_account.Credentials]:
        """Google Cloud認証情報を取得"""
        return self.unified_auth.get_credentials()
    
    def has_google_credentials(self) -> bool:
        """Google Cloud認証情報が利用可能かチェック"""
        return self.unified_auth.is_available()

# シングルトンインスタンスを取得する関数
def get_credentials_manager() -> CredentialsManager:
    """CredentialsManagerのシングルトンインスタンスを取得"""
    return CredentialsManager() 
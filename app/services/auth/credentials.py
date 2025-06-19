"""
API認証情報管理サービス
"""
import json
from typing import Optional
from google.oauth2 import service_account

class CredentialsManager:
    """認証情報を管理するクラス"""
    
    _instance: Optional['CredentialsManager'] = None
    
    def __new__(cls) -> 'CredentialsManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        self.google_credentials = None
        self._load_google_credentials()
        self._initialized = True
    
    def _load_google_credentials(self) -> None:
        """Google Cloud認証情報を読み込み"""
        from app.core.config import settings
        
        google_credentials_json = settings.GOOGLE_CREDENTIALS_JSON
        
        if google_credentials_json:
            try:
                # JSON文字列をパース
                credentials_info = json.loads(google_credentials_json)
                self.google_credentials = service_account.Credentials.from_service_account_info(credentials_info)
                print("✅ Google Cloud credentials loaded from environment variable")
            except json.JSONDecodeError as e:
                print(f"⚠️ Failed to parse Google credentials JSON: {e}")
                print(f"   First 100 chars: {google_credentials_json[:100]}...")
                self.google_credentials = None
            except Exception as e:
                print(f"⚠️ Failed to load Google credentials: {e}")
                self.google_credentials = None
        else:
            print("⚠️ GOOGLE_CREDENTIALS_JSON not found in environment variables")
            self.google_credentials = None
    
    def get_google_credentials(self) -> Optional[service_account.Credentials]:
        """Google Cloud認証情報を取得"""
        return self.google_credentials
    
    def has_google_credentials(self) -> bool:
        """Google Cloud認証情報が利用可能かチェック"""
        return self.google_credentials is not None

# シングルトンインスタンスを取得する関数
def get_credentials_manager() -> CredentialsManager:
    """CredentialsManagerのシングルトンインスタンスを取得"""
    return CredentialsManager() 
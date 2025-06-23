"""
統一認証管理インターフェース

すべての認証情報取得を一元化し、AWS Secrets Manager、環境変数、ファイルベースの
認証方法を統一的に管理します。
"""

from typing import Optional, Dict, Any, List
from google.oauth2 import service_account
from app.core.config import settings
import json
import os


class UnifiedAuthManager:
    """統一認証管理クラス"""
    
    _instance: Optional['UnifiedAuthManager'] = None
    
    def __new__(cls) -> 'UnifiedAuthManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        self.google_credentials = None
        self.auth_method = None
        self.auth_source = None
        self._load_credentials()
        self._initialized = True
    
    def _load_credentials(self) -> None:
        """認証情報を統一的に読み込み"""
        
        # 優先順位1: AWS Secrets Manager
        if settings.USE_AWS_SECRETS_MANAGER:
            if self._load_from_aws_secrets_manager():
                return
        
        # 優先順位2: 環境変数のJSON文字列
        if settings.GOOGLE_CREDENTIALS_JSON and not os.path.isfile(settings.GOOGLE_CREDENTIALS_JSON):
            if self._load_from_env_json():
                return
        
        # 優先順位3: ファイルパス
        if settings.GOOGLE_CREDENTIALS_JSON and os.path.isfile(settings.GOOGLE_CREDENTIALS_JSON):
            if self._load_from_file():
                return
        
        # 優先順位4: GOOGLE_APPLICATION_CREDENTIALS環境変数
        if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            if self._load_from_google_app_credentials():
                return
        
        # すべて失敗した場合
        self._handle_auth_failure()
    
    def _load_from_aws_secrets_manager(self) -> bool:
        """AWS Secrets Managerから認証情報を読み込み"""
        try:
            from .aws_secrets import get_google_credentials_from_aws
            
            print("🔄 Loading credentials from AWS Secrets Manager...")
            credentials_info = get_google_credentials_from_aws()
            
            if credentials_info:
                self.google_credentials = service_account.Credentials.from_service_account_info(credentials_info)
                self.auth_method = "aws_secrets_manager"
                self.auth_source = f"AWS Secrets: {settings.AWS_SECRET_NAME}"
                print("✅ Google Cloud credentials loaded from AWS Secrets Manager")
                return True
            else:
                print("❌ Failed to load credentials from AWS Secrets Manager")
                return False
                
        except Exception as e:
            print(f"❌ AWS Secrets Manager error: {e}")
            return False
    
    def _load_from_env_json(self) -> bool:
        """環境変数のJSON文字列から認証情報を読み込み"""
        try:
            credentials_info = json.loads(settings.GOOGLE_CREDENTIALS_JSON)
            self.google_credentials = service_account.Credentials.from_service_account_info(credentials_info)
            self.auth_method = "environment_json"
            self.auth_source = "Environment variable (JSON)"
            print("✅ Google Cloud credentials loaded from environment JSON")
            return True
            
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse environment JSON: {e}")
            return False
        except Exception as e:
            print(f"❌ Environment JSON error: {e}")
            return False
    
    def _load_from_file(self) -> bool:
        """ファイルパスから認証情報を読み込み"""
        try:
            self.google_credentials = service_account.Credentials.from_service_account_file(settings.GOOGLE_CREDENTIALS_JSON)
            self.auth_method = "service_account_file"
            self.auth_source = f"File: {settings.GOOGLE_CREDENTIALS_JSON}"
            print(f"✅ Google Cloud credentials loaded from file: {settings.GOOGLE_CREDENTIALS_JSON}")
            return True
            
        except FileNotFoundError:
            print(f"❌ Credentials file not found: {settings.GOOGLE_CREDENTIALS_JSON}")
            return False
        except Exception as e:
            print(f"❌ File loading error: {e}")
            return False
    
    def _load_from_google_app_credentials(self) -> bool:
        """GOOGLE_APPLICATION_CREDENTIALS環境変数から認証情報を読み込み"""
        try:
            credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            self.google_credentials = service_account.Credentials.from_service_account_file(credentials_path)
            self.auth_method = "google_application_credentials"
            self.auth_source = f"GOOGLE_APPLICATION_CREDENTIALS: {credentials_path}"
            print(f"✅ Google Cloud credentials loaded from GOOGLE_APPLICATION_CREDENTIALS: {credentials_path}")
            return True
            
        except Exception as e:
            print(f"❌ GOOGLE_APPLICATION_CREDENTIALS error: {e}")
            return False
    
    def _handle_auth_failure(self) -> None:
        """認証情報読み込み失敗時の処理"""
        self.google_credentials = None
        self.auth_method = "none"
        self.auth_source = "No valid credentials found"
        print("❌ No valid Google Cloud credentials found")
    
    def get_credentials(self) -> Optional[service_account.Credentials]:
        """Google Cloud認証情報を取得"""
        return self.google_credentials
    
    def is_available(self) -> bool:
        """認証情報が利用可能かチェック"""
        return self.google_credentials is not None
    
    def get_auth_info(self) -> Dict[str, Any]:
        """認証情報の詳細を取得"""
        return {
            "available": self.is_available(),
            "method": self.auth_method,
            "source": self.auth_source,
            "use_aws_secrets_manager": settings.USE_AWS_SECRETS_MANAGER
        }
    
    def get_troubleshooting_suggestions(self) -> List[str]:
        """問題解決のサジェスチョンを取得"""
        if self.is_available():
            return ["Google Cloud credentials are working correctly"]
        
        suggestions = []
        
        if settings.USE_AWS_SECRETS_MANAGER:
            suggestions.extend([
                "AWS Secrets Manager mode is enabled. Check the following:",
                f"- AWS credentials are configured (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)",
                f"- Secret exists in AWS Secrets Manager: {settings.AWS_SECRET_NAME}",
                f"- AWS region is correct: {settings.AWS_REGION}",
                "- IAM permissions include secretsmanager:GetSecretValue",
                "",
                "Alternative options:"
            ])
        
        suggestions.extend([
            "1. Use AWS Secrets Manager (recommended for production):",
            "   - Set USE_AWS_SECRETS_MANAGER=true",
            "   - Configure AWS credentials",
            "   - Store Google credentials in AWS Secrets Manager",
            "",
            "2. Use environment variable (JSON):",
            "   - Set GOOGLE_CREDENTIALS_JSON with full JSON content",
            "   - Ensure JSON is valid and contains required fields",
            "",
            "3. Use service account file:",
            "   - Set GOOGLE_CREDENTIALS_JSON with file path",
            "   - Ensure file exists and is readable",
            "",
            "4. Use GOOGLE_APPLICATION_CREDENTIALS:",
            "   - Set GOOGLE_APPLICATION_CREDENTIALS environment variable",
            "   - Point to valid service account key file",
            "",
            "Required Google Cloud setup:",
            "- Enable Vision API and Translate API",
            "- Create service account with appropriate permissions",
            "- Generate and download service account key"
        ])
        
        return suggestions


# シングルトンインスタンスを取得する関数
def get_unified_auth_manager() -> UnifiedAuthManager:
    """統一認証マネージャーのシングルトンインスタンスを取得"""
    return UnifiedAuthManager()


# 便利な関数
def get_google_credentials() -> Optional[service_account.Credentials]:
    """Google Cloud認証情報を取得（便利関数）"""
    return get_unified_auth_manager().get_credentials()


def is_google_auth_available() -> bool:
    """Google Cloud認証が利用可能かチェック（便利関数）"""
    return get_unified_auth_manager().is_available()


def get_auth_status() -> Dict[str, Any]:
    """認証状態の詳細情報を取得（便利関数）"""
    return get_unified_auth_manager().get_auth_info()


def get_auth_troubleshooting() -> List[str]:
    """認証問題のトラブルシューティング情報を取得（便利関数）"""
    return get_unified_auth_manager().get_troubleshooting_suggestions() 
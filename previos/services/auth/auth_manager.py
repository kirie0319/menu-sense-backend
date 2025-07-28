"""
統一認証管理システム

AWS Secrets Managerを使用したGoogle Cloud認証情報の統合管理と
後方互換性インターフェースを提供します。
"""

from typing import Optional, Dict, Any, List
from google.oauth2 import service_account
import logging
from app.core.config.aws import aws_settings

logger = logging.getLogger(__name__)


class UnifiedAuthManager:
    """統一認証管理クラス - AWS Secrets Manager統合"""
    
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
        """AWS Secrets Managerから認証情報を読み込み"""
        if self._load_from_aws_secrets():
            return
        self._handle_auth_failure()
    
    def _load_from_aws_secrets(self) -> bool:
        """AWS Secrets Managerから認証情報を取得"""
        try:
            from .aws_secrets import get_google_credentials_from_aws
            
            logger.info("🔐 Attempting to load Google credentials from AWS Secrets Manager...")
            
            credentials_dict = get_google_credentials_from_aws()
            if not credentials_dict:
                logger.warning("⚠️ Failed to retrieve credentials from AWS Secrets Manager")
                return False
            
            # Google認証情報オブジェクトを作成
            self.google_credentials = service_account.Credentials.from_service_account_info(
                credentials_dict,
                scopes=['https://www.googleapis.com/auth/cloud-platform']
            )
            
            self.auth_method = "aws_secrets_manager"
            self.auth_source = f"AWS Secrets: {aws_settings.secret_name}"
            
            logger.info(f"✅ Google credentials loaded from AWS Secrets Manager")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load from AWS Secrets Manager: {e}")
            return False
    
    def _handle_auth_failure(self) -> None:
        """認証情報読み込み失敗時の処理"""
        self.google_credentials = None
        self.auth_method = "none"
        self.auth_source = "No valid credentials found"
        logger.error("❌ No valid Google Cloud credentials found")
    
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
            "use_aws_secrets_manager": aws_settings.use_secrets_manager
        }
    
    def get_troubleshooting_suggestions(self) -> List[str]:
        """問題解決のサジェスチョンを取得"""
        if self.is_available():
            return ["Google Cloud credentials are working correctly"]
        
        return [
            "AWS Secrets Manager authentication failed. Check the following:",
            f"- AWS credentials are configured (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)",
            f"- Secret exists in AWS Secrets Manager: {aws_settings.secret_name}",
            f"- AWS region is correct: {aws_settings.region}",
            "- IAM permissions include secretsmanager:GetSecretValue",
            "",
            "Required Google Cloud setup:",
            "- Enable Vision API and Translate API",
            "- Create service account with appropriate permissions"
        ]


class CredentialsManager:
    """認証情報管理クラス - 後方互換性インターフェース"""
    
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


# ===== シングルトンインスタンス取得関数 =====

def get_unified_auth_manager() -> UnifiedAuthManager:
    """統一認証マネージャーのシングルトンインスタンスを取得"""
    return UnifiedAuthManager()


def get_credentials_manager() -> CredentialsManager:
    """認証情報マネージャーのシングルトンインスタンスを取得"""
    return CredentialsManager()


# ===== 便利関数 =====

def get_auth_status() -> Dict[str, Any]:
    """認証状態の詳細情報を取得"""
    return get_unified_auth_manager().get_auth_info()


def get_auth_troubleshooting() -> List[str]:
    """認証問題のトラブルシューティング情報を取得"""
    return get_unified_auth_manager().get_troubleshooting_suggestions()


# ===== エクスポート =====

__all__ = [
    # メインクラス
    'UnifiedAuthManager',
    'CredentialsManager',
    
    # インスタンス取得関数
    'get_unified_auth_manager',
    'get_credentials_manager',
    
    # 便利関数
    'get_auth_status',
    'get_auth_troubleshooting'
]
"""
AWS関連設定
S3ストレージとSecrets Manager設定を管理
"""
from pydantic import BaseModel
from typing import Optional
import os
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()


class AWSSettings(BaseModel):
    """AWS関連設定クラス"""
    
    # ===== 認証情報 =====
    access_key_id: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID") # need to set in .env
    secret_access_key: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY") # need to set in .env
    session_token: Optional[str] = os.getenv("AWS_SESSION_TOKEN")  # need to set in .env
    region: str = os.getenv("AWS_REGION", "us-east-1") # need to set in .env
    
    # ===== S3設定（画像保存用） =====
    s3_bucket_name: str = os.getenv("S3_BUCKET_NAME", "menu-sense")
    s3_region: str = os.getenv("S3_REGION", "ap-northeast-1")
    s3_image_prefix: str = os.getenv("S3_IMAGE_PREFIX", "generated-images")
    use_s3_storage: bool = os.getenv("USE_S3_STORAGE", "true").lower() == "true"
    s3_public_url_template: str = os.getenv(
        "S3_PUBLIC_URL_TEMPLATE", 
        "https://{bucket}.s3.{region}.amazonaws.com/{key}"
    )
    
    # ===== Secrets Manager設定 =====
    secret_name: str = os.getenv("AWS_SECRET_NAME", "prod/menu-sense/google-credentials")
    use_secrets_manager: bool = os.getenv("USE_AWS_SECRETS_MANAGER", "false").lower() == "true"
    
    class Config:
        env_file = ".env"
    
    def is_credentials_available(self) -> bool:
        """AWS認証情報が利用可能かチェック"""
        return bool(self.access_key_id and self.secret_access_key)
    
    def is_s3_enabled(self) -> bool:
        """S3ストレージが有効かチェック"""
        return self.use_s3_storage
    
    def is_secrets_manager_enabled(self) -> bool:
        """Secrets Managerが有効かチェック"""
        return self.use_secrets_manager
    
    def get_s3_config(self) -> dict:
        """S3設定辞書を取得"""
        return {
            "bucket_name": self.s3_bucket_name,
            "region": self.s3_region,
            "image_prefix": self.s3_image_prefix,
            "use_storage": self.use_s3_storage,
            "public_url_template": self.s3_public_url_template
        }
    
    def get_secrets_manager_config(self) -> dict:
        """Secrets Manager設定辞書を取得"""
        return {
            "secret_name": self.secret_name,
            "region": self.region,
            "use_secrets_manager": self.use_secrets_manager
        }
    
    def validate_configuration(self) -> list:
        """AWS設定の妥当性を検証"""
        issues = []
        
        # Secrets Manager設定の検証
        if self.use_secrets_manager:
            if not self.secret_name:
                issues.append("AWS_SECRET_NAME not set (required when USE_AWS_SECRETS_MANAGER=true)")
            if not self.region:
                issues.append("AWS_REGION not set (required when USE_AWS_SECRETS_MANAGER=true)")
        
        # S3設定の検証
        if self.use_s3_storage:
            if not self.s3_bucket_name:
                issues.append("S3_BUCKET_NAME not set (required when USE_S3_STORAGE=true)")
            if not self.s3_region:
                issues.append("S3_REGION not set (required when USE_S3_STORAGE=true)")
        
        return issues


# グローバルインスタンス
aws_settings = AWSSettings()


# 後方互換性のための関数（移行期間中のみ使用）
def get_aws_settings():
    """AWS設定を取得（後方互換性用）"""
    return aws_settings

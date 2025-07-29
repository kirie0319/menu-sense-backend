"""
AWS Secrets Manager Client - Infrastructure Layer
Secret management service using AWS Secrets Manager
"""

import json
from typing import Dict, Any, Optional
from functools import lru_cache
import boto3
from botocore.exceptions import ClientError

from app_2.core.config import settings
from app_2.utils.logger import get_logger

logger = get_logger("secrets_manager")


class SecretsManager:
    """
    AWS Secrets Manager クライアント
    
    APIキーや機密情報の管理を担当
    """
    
    def __init__(self):
        """
        AWS Secrets Manager クライアントを初期化
        """
        self.client = boto3.client(
            'secretsmanager',
            aws_access_key_id=settings.aws.access_key_id,
            aws_secret_access_key=settings.aws.secret_access_key,
            region_name=settings.aws.region
        )

    async def get_secret(self, secret_name: str) -> Dict[str, Any]:
        """
        シークレットを取得
        
        Args:
            secret_name: シークレット名
            
        Returns:
            Dict[str, Any]: シークレットデータ
        """
        try:
            response = self.client.get_secret_value(SecretId=secret_name)
            
            # JSON形式のシークレットをパース
            if 'SecretString' in response:
                secret_data = json.loads(response['SecretString'])
            else:
                # バイナリシークレットの場合
                secret_data = response['SecretBinary']
            
            logger.info(f"Retrieved secret: {secret_name}")
            return secret_data
            
        except ClientError as e:
            logger.error(f"Failed to get secret {secret_name}: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse secret JSON {secret_name}: {e}")
            raise

    async def get_api_keys(self) -> Dict[str, str]:
        """
        API키들을 일괄 취득
        
        Returns:
            Dict[str, str]: API키 딕셔너리
        """
        try:
            # 메뉴 처리 시스템용 API키들
            secret_name = "menu-processor-api-keys"
            api_keys = await self.get_secret(secret_name)
            
            logger.info("Retrieved all API keys")
            return api_keys
            
        except Exception as e:
            logger.error(f"Failed to get API keys: {e}")
            # 환경변수 폴백
            fallback_keys = {
                "openai_api_key": settings.ai.openai_api_key,
                "google_api_key": settings.ai.gemini_api_key,
            }
            logger.info("Using fallback API keys from environment variables")
            return fallback_keys

    async def update_secret(
        self, 
        secret_name: str, 
        secret_data: Dict[str, Any]
    ) -> bool:
        """
        シークレットを更新
        
        Args:
            secret_name: シークレット名
            secret_data: 更新するシークレットデータ
            
        Returns:
            bool: 更新が成功したか
        """
        try:
            secret_string = json.dumps(secret_data)
            
            self.client.update_secret(
                SecretId=secret_name,
                SecretString=secret_string
            )
            
            logger.info(f"Updated secret: {secret_name}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to update secret {secret_name}: {e}")
            return False

    async def create_secret(
        self, 
        secret_name: str, 
        secret_data: Dict[str, Any],
        description: Optional[str] = None
    ) -> bool:
        """
        新しいシークレットを作成
        
        Args:
            secret_name: シークレット名
            secret_data: シークレットデータ
            description: シークレットの説明
            
        Returns:
            bool: 作成が成功したか
        """
        try:
            secret_string = json.dumps(secret_data)
            
            params = {
                'Name': secret_name,
                'SecretString': secret_string
            }
            
            if description:
                params['Description'] = description
            
            self.client.create_secret(**params)
            
            logger.info(f"Created secret: {secret_name}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to create secret {secret_name}: {e}")
            return False 


@lru_cache(maxsize=1)
def get_secrets_manager() -> SecretsManager:
    """
    SecretsManager のシングルトンインスタンスを取得
    
    Returns:
        SecretsManager: シングルトンインスタンス
    """
    return SecretsManager() 
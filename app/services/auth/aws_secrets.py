"""
AWS Secrets Manager認証情報取得サービス
"""
import json
import boto3
from botocore.exceptions import ClientError
from typing import Optional, Dict, Any
from app.core.config import settings


def get_secret() -> Optional[str]:
    """
    AWS Secrets Managerから秘密情報を取得
    
    Returns:
        Optional[str]: 取得した秘密情報（JSON文字列）、失敗時はNone
    """
    secret_name = settings.AWS_SECRET_NAME
    region_name = settings.AWS_REGION

    # Create a Secrets Manager client with explicit credentials
    session_kwargs = {}
    
    # 環境変数から認証情報を明示的に設定
    if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
        session_kwargs.update({
            'aws_access_key_id': settings.AWS_ACCESS_KEY_ID,
            'aws_secret_access_key': settings.AWS_SECRET_ACCESS_KEY,
        })
        
        if settings.AWS_SESSION_TOKEN:
            session_kwargs['aws_session_token'] = settings.AWS_SESSION_TOKEN
            
        print("🔐 Using explicit AWS credentials from environment variables")
    else:
        print("🔐 Using default AWS credentials (IAM Role or shared credentials)")
    
    session = boto3.session.Session(**session_kwargs)
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
        secret = get_secret_value_response['SecretString']
        return secret
        
    except ClientError as e:
        # For a list of exceptions thrown, see
        # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
        error_code = e.response['Error']['Code']
        
        if error_code == 'DecryptionFailureException':
            # Secrets Manager can't decrypt the protected secret text using the provided KMS key.
            print(f"❌ AWS Secrets Manager - Decryption failure: {e}")
        elif error_code == 'InternalServiceErrorException':
            # An error occurred on the server side.
            print(f"❌ AWS Secrets Manager - Internal service error: {e}")
        elif error_code == 'InvalidParameterException':
            # You provided an invalid value for a parameter.
            print(f"❌ AWS Secrets Manager - Invalid parameter: {e}")
        elif error_code == 'InvalidRequestException':
            # You provided a parameter value that is not valid for the current state of the resource.
            print(f"❌ AWS Secrets Manager - Invalid request: {e}")
        elif error_code == 'ResourceNotFoundException':
            # We can't find the resource that you asked for.
            print(f"❌ AWS Secrets Manager - Resource not found: {secret_name}")
        else:
            print(f"❌ AWS Secrets Manager - Unknown error: {e}")
            
        return None
    
    except Exception as e:
        print(f"❌ AWS Secrets Manager - Unexpected error: {e}")
        return None


def get_google_credentials_from_aws() -> Optional[Dict[str, Any]]:
    """
    AWS Secrets ManagerからGoogle認証情報を取得し、辞書として返す
    
    Returns:
        Optional[Dict[str, Any]]: Google認証情報辞書、失敗時はNone
    """
    secret_string = get_secret()
    
    if not secret_string:
        return None
    
    try:
        # JSON文字列をパース
        credentials_dict = json.loads(secret_string)
        
        # 必要なフィールドが存在するかチェック
        required_fields = ['type', 'project_id', 'private_key', 'client_email']
        missing_fields = [field for field in required_fields if field not in credentials_dict]
        
        if missing_fields:
            print(f"❌ Google credentials from AWS Secrets Manager missing fields: {', '.join(missing_fields)}")
            return None
        
        print("✅ Google credentials successfully retrieved from AWS Secrets Manager")
        return credentials_dict
        
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse Google credentials JSON from AWS Secrets Manager: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error parsing Google credentials from AWS: {e}")
        return None


def test_aws_connection() -> bool:
    """
    AWS Secrets Managerへの接続をテスト
    
    Returns:
        bool: 接続成功時True、失敗時False
    """
    try:
        secret_string = get_secret()
        return secret_string is not None
    except Exception as e:
        print(f"❌ AWS Secrets Manager connection test failed: {e}")
        return False 
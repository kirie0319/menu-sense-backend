#!/usr/bin/env python3
"""
AWS Secrets Manager接続テストスクリプト
Google認証情報の取得をテストします
"""

import os
import sys
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

def test_aws_secrets_configuration():
    """AWS Secrets Managerの設定をテスト"""
    print("🔍 AWS Secrets Manager設定チェック...")
    
    # 設定の確認
    use_aws = os.getenv("USE_AWS_SECRETS_MANAGER", "false").lower() == "true"
    aws_region = os.getenv("AWS_REGION", "us-east-1")
    secret_name = os.getenv("AWS_SECRET_NAME", "prod/menu-sense/google-credentials")
    
    print(f"✅ USE_AWS_SECRETS_MANAGER: {use_aws}")
    print(f"✅ AWS_REGION: {aws_region}")
    print(f"✅ AWS_SECRET_NAME: {secret_name}")
    
    if not use_aws:
        print("⚠️ AWS Secrets Manager is disabled. Set USE_AWS_SECRETS_MANAGER=true to enable.")
        return False
    
    return True

def test_aws_credentials():
    """AWS認証情報をテスト"""
    print("\n🔍 AWS認証情報チェック...")
    
    # 環境変数の確認
    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_session_token = os.getenv("AWS_SESSION_TOKEN")
    
    print(f"✅ AWS_ACCESS_KEY_ID: {'設定済み' if aws_access_key else '未設定'}")
    print(f"✅ AWS_SECRET_ACCESS_KEY: {'設定済み' if aws_secret_key else '未設定'}")
    print(f"✅ AWS_SESSION_TOKEN: {'設定済み' if aws_session_token else '未設定（オプション）'}")
    
    try:
        import boto3
        
        # AWS認証情報の確認
        session_kwargs = {}
        if aws_access_key and aws_secret_key:
            session_kwargs.update({
                'aws_access_key_id': aws_access_key,
                'aws_secret_access_key': aws_secret_key,
            })
            if aws_session_token:
                session_kwargs['aws_session_token'] = aws_session_token
            print("🔐 Using explicit AWS credentials from environment variables")
        else:
            print("🔐 Using default AWS credentials")
        
        session = boto3.Session(**session_kwargs)
        sts = session.client('sts')
        
        # 現在の認証情報を確認
        identity = sts.get_caller_identity()
        print(f"✅ AWS Account ID: {identity.get('Account', 'Unknown')}")
        print(f"✅ AWS User/Role: {identity.get('Arn', 'Unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ AWS認証エラー: {e}")
        print("💡 Hint: AWS認証情報を設定してください:")
        print("   - AWS CLI: aws configure")
        print("   - 環境変数: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY")
        print("   - IAM Role (EC2/Lambda等)")
        return False

def test_secrets_manager_connection():
    """AWS Secrets Manager接続をテスト"""
    print("\n🔍 AWS Secrets Manager接続テスト...")
    
    try:
        # アプリケーションモジュールのインポート
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from app.services.auth.aws_secrets import test_aws_connection, get_google_credentials_from_aws
        
        # 接続テスト
        connection_result = test_aws_connection()
        
        if connection_result:
            print("✅ AWS Secrets Manager接続成功")
            
            # Google認証情報の取得テスト
            print("\n🔍 Google認証情報取得テスト...")
            credentials = get_google_credentials_from_aws()
            
            if credentials:
                print("✅ Google認証情報取得成功")
                print(f"   - Project ID: {credentials.get('project_id', 'Unknown')}")
                print(f"   - Client Email: {credentials.get('client_email', 'Unknown')}")
                return True
            else:
                print("❌ Google認証情報取得失敗")
                return False
        else:
            print("❌ AWS Secrets Manager接続失敗")
            return False
            
    except ImportError as e:
        print(f"❌ モジュールインポートエラー: {e}")
        return False
    except Exception as e:
        print(f"❌ 予期しないエラー: {e}")
        return False

def test_google_cloud_integration():
    """Google Cloud APIとの統合をテスト"""
    print("\n🔍 Google Cloud API統合テスト...")
    
    try:
        # 認証情報マネージャーのテスト
        from app.services.auth.credentials import get_credentials_manager
        
        cm = get_credentials_manager()
        
        if cm.has_google_credentials():
            print("✅ Google Cloud認証情報が正常に読み込まれました")
            
            # Vision APIクライアントのテスト
            from app.services.auth.clients import get_api_clients_manager
            clients = get_api_clients_manager()
            
            if clients.VISION_AVAILABLE:
                print("✅ Google Vision APIクライアント初期化成功")
            else:
                print("❌ Google Vision APIクライアント初期化失敗")
                
            if clients.TRANSLATE_AVAILABLE:
                print("✅ Google Translate APIクライアント初期化成功")
            else:
                print("❌ Google Translate APIクライアント初期化失敗")
                
            return True
        else:
            print("❌ Google Cloud認証情報の読み込みに失敗しました")
            return False
            
    except Exception as e:
        print(f"❌ Google Cloud API統合エラー: {e}")
        return False

def main():
    """メインテスト関数"""
    print("🚀 AWS Secrets Manager + Google Cloud API 統合テスト開始\n")
    
    # 1. AWS設定チェック
    if not test_aws_secrets_configuration():
        print("\n❌ AWS Secrets Manager設定に問題があります")
        return False
    
    # 2. AWS認証情報チェック
    if not test_aws_credentials():
        print("\n❌ AWS認証情報に問題があります")
        return False
    
    # 3. Secrets Manager接続テスト
    if not test_secrets_manager_connection():
        print("\n❌ AWS Secrets Manager接続に問題があります")
        return False
    
    # 4. Google Cloud API統合テスト
    if not test_google_cloud_integration():
        print("\n❌ Google Cloud API統合に問題があります")
        return False
    
    print("\n🎉 すべてのテストが成功しました！")
    print("✅ AWS Secrets Managerを使用したGoogle認証情報管理が正常に動作しています")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 
#!/usr/bin/env python3
"""
統一認証システムのテストスクリプト

すべての認証方法（AWS Secrets Manager、環境変数、ファイル）を
統一されたインターフェースでテストします。
"""

import os
import sys
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

def test_unified_auth_system():
    """統一認証システムの総合テスト"""
    print("🚀 統一認証システム テスト開始\n")
    
    try:
        # アプリケーションモジュールのインポート
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from app.services.auth.unified_auth import (
            get_unified_auth_manager, 
            get_auth_status, 
            get_auth_troubleshooting,
            is_google_auth_available
        )
        
        # 統一認証マネージャーを取得
        auth_manager = get_unified_auth_manager()
        auth_status = get_auth_status()
        
        print("📊 認証状態レポート:")
        print("=" * 50)
        print(f"✅ 認証可能: {auth_status['available']}")
        print(f"🔧 認証方法: {auth_status['method']}")
        print(f"📍 認証ソース: {auth_status['source']}")
        print(f"🔒 AWS Secrets Manager使用: {auth_status['use_aws_secrets_manager']}")
        
        if auth_status['available']:
            print("\n✅ 認証情報が正常に読み込まれました！")
            
            # Google Cloud APIクライアントのテスト
            try:
                from app.services.auth.clients import get_api_clients_manager
                clients = get_api_clients_manager()
                
                print("\n🔍 APIクライアント初期化状況:")
                print(f"  - Vision API: {'✅ 利用可能' if clients.VISION_AVAILABLE else '❌ 利用不可'}")
                print(f"  - Translate API: {'✅ 利用可能' if clients.TRANSLATE_AVAILABLE else '❌ 利用不可'}")
                print(f"  - OpenAI API: {'✅ 利用可能' if clients.OPENAI_AVAILABLE else '❌ 利用不可'}")
                print(f"  - Gemini API: {'✅ 利用可能' if clients.GEMINI_AVAILABLE else '❌ 利用不可'}")
                
            except Exception as e:
                print(f"\n⚠️ APIクライアント初期化エラー: {e}")
        
        else:
            print("\n❌ 認証情報が見つかりません")
            print("\n💡 トラブルシューティング:")
            troubleshooting = get_auth_troubleshooting()
            for i, suggestion in enumerate(troubleshooting, 1):
                if suggestion.strip():
                    print(f"   {i}. {suggestion}")
        
        return auth_status['available']
        
    except ImportError as e:
        print(f"❌ モジュールインポートエラー: {e}")
        return False
    except Exception as e:
        print(f"❌ 予期しないエラー: {e}")
        return False

def test_environment_variables():
    """環境変数の設定状況をテスト"""
    print("\n🔍 環境変数設定チェック:")
    print("=" * 30)
    
    # 主要API認証情報
    openai_key = os.getenv("OPENAI_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")
    
    print(f"✅ OPENAI_API_KEY: {'設定済み' if openai_key else '未設定'}")
    print(f"✅ GEMINI_API_KEY: {'設定済み' if gemini_key else '未設定'}")
    
    # AWS Secrets Manager設定
    use_aws = os.getenv("USE_AWS_SECRETS_MANAGER", "false").lower() == "true"
    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_region = os.getenv("AWS_REGION", "us-east-1")
    secret_name = os.getenv("AWS_SECRET_NAME", "prod/menu-sense/google-credentials")
    
    print(f"\n🔒 AWS Secrets Manager:")
    print(f"  - 使用設定: {'有効' if use_aws else '無効'}")
    if use_aws:
        print(f"  - AWS_ACCESS_KEY_ID: {'設定済み' if aws_access_key else '未設定'}")
        print(f"  - AWS_SECRET_ACCESS_KEY: {'設定済み' if aws_secret_key else '未設定'}")
        print(f"  - AWS_REGION: {aws_region}")
        print(f"  - AWS_SECRET_NAME: {secret_name}")
    
    # 従来の認証方法
    google_creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    google_app_creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    
    print(f"\n📁 従来の認証方法:")
    print(f"  - GOOGLE_CREDENTIALS_JSON: {'設定済み' if google_creds_json else '未設定'}")
    print(f"  - GOOGLE_APPLICATION_CREDENTIALS: {'設定済み' if google_app_creds else '未設定'}")

def test_backward_compatibility():
    """後方互換性をテスト"""
    print("\n🔄 後方互換性テスト:")
    print("=" * 25)
    
    try:
        # 従来のCredentialsManagerインターフェース
        from app.services.auth.credentials import get_credentials_manager
        cm = get_credentials_manager()
        
        print(f"✅ CredentialsManager: {cm.has_google_credentials()}")
        
        # 従来のAPIクライアント取得
        from app.services.auth import get_google_credentials, get_vision_client, get_translate_client
        
        google_creds = get_google_credentials()
        vision_client = get_vision_client()
        translate_client = get_translate_client()
        
        print(f"✅ get_google_credentials(): {'利用可能' if google_creds else '利用不可'}")
        print(f"✅ get_vision_client(): {'利用可能' if vision_client else '利用不可'}")
        print(f"✅ get_translate_client(): {'利用可能' if translate_client else '利用不可'}")
        
        return True
        
    except Exception as e:
        print(f"❌ 後方互換性エラー: {e}")
        return False

def main():
    """メインテスト関数"""
    print("🌟 Google Cloud 統一認証システム 総合テスト")
    print("=" * 60)
    
    # 1. 環境変数チェック
    test_environment_variables()
    
    # 2. 統一認証システムテスト
    auth_success = test_unified_auth_system()
    
    # 3. 後方互換性テスト
    compat_success = test_backward_compatibility()
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print("📋 テスト結果サマリー:")
    print(f"🔐 統一認証システム: {'✅ 成功' if auth_success else '❌ 失敗'}")
    print(f"🔄 後方互換性: {'✅ 成功' if compat_success else '❌ 失敗'}")
    
    if auth_success and compat_success:
        print("\n🎉 すべてのテストが成功しました！")
        print("✅ 統一認証システムが正常に動作しています")
        return True
    else:
        print("\n⚠️ 一部のテストが失敗しました")
        print("💡 上記のトラブルシューティング情報を確認してください")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 
#!/usr/bin/env python3
"""
Menu Processor Setup Checker
Google Vision API、OpenAI API、その他の設定を確認します
"""

import os
import sys
import json
from dotenv import load_dotenv

def check_environment():
    """環境変数をチェック"""
    print("🔍 環境変数チェック...")
    
    load_dotenv()
    
    checks = {
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "GOOGLE_CREDENTIALS_JSON": os.getenv("GOOGLE_CREDENTIALS_JSON"),
        "GOOGLE_APPLICATION_CREDENTIALS": os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    }
    
    for key, value in checks.items():
        if value:
            if key == "GOOGLE_CREDENTIALS_JSON":
                try:
                    json.loads(value)
                    print(f"✅ {key}: 有効なJSON形式")
                except json.JSONDecodeError:
                    print(f"❌ {key}: 無効なJSON形式")
            elif key == "GOOGLE_APPLICATION_CREDENTIALS":
                if os.path.exists(value):
                    print(f"✅ {key}: ファイルが存在")
                else:
                    print(f"❌ {key}: ファイルが見つかりません")
            else:
                print(f"✅ {key}: 設定済み（{len(value)}文字）")
        else:
            print(f"❌ {key}: 未設定")
    
    return checks

def check_google_cloud():
    """Google Cloud APIをチェック"""
    print("\n🔍 Google Cloud API チェック...")
    
    try:
        from google.cloud import vision
        print("✅ google-cloud-vision: インストール済み")
        
        # 認証チェック
        try:
            client = vision.ImageAnnotatorClient()
            print("✅ Google Vision API: 認証成功")
            return True
        except Exception as e:
            print(f"❌ Google Vision API: 認証失敗 - {e}")
            return False
            
    except ImportError:
        print("❌ google-cloud-vision: 未インストール")
        return False

def check_openai():
    """OpenAI APIをチェック"""
    print("\n🔍 OpenAI API チェック...")
    
    try:
        import openai
        from openai import AsyncOpenAI
        print("✅ openai: インストール済み")
        
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            # 簡単なテスト（実際にAPIコールはしない）
            try:
                client = AsyncOpenAI(api_key=api_key)
                print("✅ OpenAI API: クライアント初期化成功")
                return True
            except Exception as e:
                print(f"❌ OpenAI API: 初期化失敗 - {e}")
                return False
        else:
            print("❌ OpenAI API: APIキーが未設定")
            return False
            
    except ImportError:
        print("❌ openai: 未インストール")
        return False

def check_dependencies():
    """依存関係をチェック"""
    print("\n🔍 依存関係チェック...")
    
    required_packages = [
        'fastapi',
        'uvicorn',
        'python-dotenv',
        'aiofiles',
        'google-cloud-vision',
        'google-cloud-translate',
        'openai'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}: インストール済み")
        except ImportError:
            print(f"❌ {package}: 未インストール")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️ 不足しているパッケージ: {', '.join(missing_packages)}")
        print("次のコマンドでインストールしてください:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    return True

def test_apis():
    """APIの基本テスト"""
    print("\n🧪 API基本テスト...")
    
    # Google Vision APIテスト
    try:
        from google.cloud import vision
        client = vision.ImageAnnotatorClient()
        
        # 空の画像でテスト（エラーが返るが、接続は確認できる）
        try:
            response = client.text_detection(vision.Image(content=b''))
            print("✅ Google Vision API: 接続テスト成功")
        except Exception as e:
            if "Invalid image" in str(e) or "empty" in str(e):
                print("✅ Google Vision API: 接続OK（空画像エラーは正常）")
            else:
                print(f"❌ Google Vision API: 接続エラー - {e}")
                
    except Exception as e:
        print(f"❌ Google Vision API: テスト失敗 - {e}")

def provide_solutions():
    """解決策を提案"""
    print("\n💡 問題がある場合の解決策:")
    
    print("\n1. Google Vision APIの設定:")
    print("   - Google Cloud Projectを作成")
    print("   - Vision APIを有効化")
    print("   - サービスアカウントを作成して権限付与")
    print("   - 認証情報をGOOGLE_CREDENTIALS_JSON環境変数に設定")
    
    print("\n2. OpenAI APIの設定:")
    print("   - OpenAI APIキーを取得")
    print("   - OPENAI_API_KEY環境変数に設定")
    
    print("\n3. 依存関係のインストール:")
    print("   pip install -r requirements.txt")
    
    print("\n4. 環境変数の設定:")
    print("   - .envファイルを作成")
    print("   - env_example.txtを参考に必要な変数を設定")

def main():
    """メイン関数"""
    print("🚀 Menu Processor セットアップチェッカー")
    print("=" * 50)
    
    all_good = True
    
    # 各チェックを実行
    env_checks = check_environment()
    all_good &= bool(env_checks["OPENAI_API_KEY"])
    all_good &= bool(env_checks["GOOGLE_CREDENTIALS_JSON"] or env_checks["GOOGLE_APPLICATION_CREDENTIALS"])
    
    deps_ok = check_dependencies()
    all_good &= deps_ok
    
    if deps_ok:
        gcp_ok = check_google_cloud()
        openai_ok = check_openai()
        all_good &= gcp_ok and openai_ok
        
        if gcp_ok and openai_ok:
            test_apis()
    
    print("\n" + "=" * 50)
    
    if all_good:
        print("🎉 セットアップ完了！すべてのAPIが正常に設定されています。")
        print("次のコマンドでサーバーを起動できます:")
        print("python run_mvp.py")
    else:
        print("⚠️ 一部の設定に問題があります。")
        provide_solutions()
        sys.exit(1)

if __name__ == "__main__":
    main() 
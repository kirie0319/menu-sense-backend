#!/usr/bin/env python3
"""
Menu Processor MVP 起動スクリプト
本番環境用の4段階処理システム
"""

import os
import sys, json
import subprocess
from pathlib import Path
from dotenv import load_dotenv

def check_requirements():
    """必要なファイルと設定の確認"""
    print("🔍 システム要件をチェック中...")
    
    # .envファイルの確認
    if not Path(".env").exists():
        print("❌ .envファイルが見つかりません")
        print("   env_example.txtを参考に.envファイルを作成してください")
        return False
    
    # 環境変数の読み込み
    load_dotenv()
    
    # OpenAI API Keyの確認
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        print("❌ OPENAI_API_KEYが設定されていません")
        return False
    print("✅ OpenAI API Key: 設定済み")
    
    # Google Vision API認証の確認
    google_creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    # google_creds = json.loads(os.getenv("GOOGLE_CREDENTIALS_CREDENTIALS"))
    if not google_creds:
        print("❌ GOOGLE_APPLICATION_CREDENTIALSが設定されていません")
        return False
    
    if not Path(google_creds).exists():
        print(f"❌ Google認証ファイルが見つかりません: {google_creds}")
        return False
    print("✅ Google Vision API: 設定済み")
    # google_creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    # if not google_creds_json:
    #     print("❌ GOOGLE_CREDENTIALS_JSON が設定されていません")
    #     return False
    # else:
    #     try:
    #         json.loads(google_creds_json)
    #         print("✅ Google Vision API認証情報: 設定済み")
    #     except json.JSONDecodeError:
    #         print("❌ GOOGLE_CREDENTIALS_JSON の形式が不正です")
    #         return False
    
    # uploadsディレクトリの確認/作成
    uploads_dir = Path("uploads")
    if not uploads_dir.exists():
        uploads_dir.mkdir()
        print("✅ uploadsディレクトリを作成しました")
    else:
        print("✅ uploadsディレクトリ: 存在確認")
    
    return True

def check_dependencies():
    """依存関係の確認"""
    print("\n📦 依存関係をチェック中...")
    
    required_packages = [
        "fastapi",
        "uvicorn",
        "google-cloud-vision",
        "openai",
        "python-dotenv",
        "aiofiles"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"✅ {package}: インストール済み")
        except ImportError:
            print(f"❌ {package}: 未インストール")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n❌ 不足している依存関係: {', '.join(missing_packages)}")
        print("以下のコマンドで依存関係をインストールしてください:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    return True

def run_health_check():
    """ヘルスチェックの実行"""
    print("\n🏥 ヘルスチェックを実行中...")
    
    try:
        # mvp_menu_processor.pyを直接インポートしてテスト
        sys.path.insert(0, ".")
        from mvp_menu_processor import VISION_AVAILABLE, OPENAI_AVAILABLE
        
        if VISION_AVAILABLE:
            print("✅ Google Vision API: 利用可能")
        else:
            print("❌ Google Vision API: 利用不可")
            
        if OPENAI_AVAILABLE:
            print("✅ OpenAI API: 利用可能")
        else:
            print("❌ OpenAI API: 利用不可")
            
        return VISION_AVAILABLE and OPENAI_AVAILABLE
        
    except Exception as e:
        print(f"❌ ヘルスチェック失敗: {e}")
        return False

def start_server(port=8000, host="0.0.0.0"):
    """サーバーの起動"""
    print(f"\n🚀 MVP Menu Processor を起動中...")
    print(f"   Host: {host}")
    print(f"   Port: {port}")
    print(f"   URL: http://localhost:{port}")
    print("\n🔄 4段階処理システム:")
    print("   Stage 1: OCR (Google Vision API)")
    print("   Stage 2: Categorize (OpenAI Function Calling)")
    print("   Stage 3: Translate (OpenAI Function Calling)")
    print("   Stage 4: Describe (OpenAI Function Calling)")
    print("\nCtrl+C で停止します\n")
    
    try:
        cmd = [
            "uvicorn", 
            "mvp_menu_processor:app",
            "--host", host,
            "--port", str(port),
            "--reload"
        ]
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n\n👋 Menu Processor MVP を停止しました")
    except FileNotFoundError:
        print("❌ uvicornが見つかりません")
        print("以下のコマンドでインストールしてください:")
        print("pip install uvicorn")

def main():
    """メイン処理"""
    print("🍜 Menu Processor MVP - Production Ready")
    print("=" * 50)
    
    # システム要件チェック
    if not check_requirements():
        print("\n❌ セットアップが完了していません")
        sys.exit(1)
    
    # 依存関係チェック
    if not check_dependencies():
        print("\n❌ 依存関係が不足しています")
        sys.exit(1)
    
    # ヘルスチェック
    if not run_health_check():
        print("\n⚠️  警告: 一部のAPIが利用できません")
        print("システムは起動しますが、機能が制限される可能性があります")
        
        response = input("\n続行しますか? [y/N]: ")
        if response.lower() != 'y':
            print("起動をキャンセルしました")
            sys.exit(1)
    
    print("\n✅ 全てのチェックが完了しました")
    
    # ポート設定
    port = int(os.getenv("PORT", 8000))
    
    # サーバー起動
    start_server(port=port)

if __name__ == "__main__":
    main() 
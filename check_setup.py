#!/usr/bin/env python3
"""
Menu Processor Setup Checker
実際のアプリケーション環境をテストします
"""

import os
import sys
import json

def check_environment():
    """環境変数をチェック（統一認証システム使用）"""
    print("🔍 環境変数チェック（統一認証システム使用）...")
    
    try:
        # アプリケーションの設定を直接使用
        from app.core.config import settings
        from app.services.auth.unified_auth import get_auth_status, get_auth_troubleshooting
        
        print(f"✅ OPENAI_API_KEY: {'設定済み' if settings.OPENAI_API_KEY else '未設定'}")
        print(f"✅ GEMINI_API_KEY: {'設定済み' if settings.GEMINI_API_KEY else '未設定'}")
        
        # 統一認証システムで認証状態をチェック
        auth_status = get_auth_status()
        print(f"✅ Google Cloud認証: {'設定済み' if auth_status['available'] else '未設定'}")
        
        if auth_status['available']:
            print(f"   ✅ 認証方法: {auth_status['method']}")
            print(f"   ✅ 認証ソース: {auth_status['source']}")
                else:
            print("   ❌ 認証情報が見つかりません")
            troubleshooting = get_auth_troubleshooting()
            for suggestion in troubleshooting[:5]:  # 最初の5つのサジェスチョンのみ表示
                if suggestion.strip():
                    print(f"   💡 {suggestion}")
        
        return auth_status['available']
        
    except Exception as e:
        print(f"❌ アプリケーション設定の読み込みに失敗: {e}")
        return False

def check_actual_services():
    """実際のアプリケーションサービスをテスト"""
    print("\n🧪 実際のアプリケーションサービステスト...")
    
    services_status = {}
    
    # 認証情報管理
    try:
        from app.services.auth.credentials import get_credentials_manager
        cm = get_credentials_manager()
        
        if cm.has_google_credentials():
            print("✅ Google Cloud認証情報管理: 正常")
            services_status['auth'] = True
        else:
            print("⚠️ Google Cloud認証情報管理: 認証情報なし")
            services_status['auth'] = False
            
    except Exception as e:
        print(f"❌ Google Cloud認証情報管理: エラー - {e}")
        services_status['auth'] = False
    
    # Gemini OCR Service (Primary)
    try:
        from app.services.ocr.gemini import GeminiOCRService
        gemini_ocr = GeminiOCRService()
        
        if gemini_ocr.is_available():
            print("✅ Gemini OCR Service (Primary): 利用可能")
            services_status['gemini_ocr'] = True
        else:
            print("❌ Gemini OCR Service (Primary): 利用不可")
            services_status['gemini_ocr'] = False
            
    except Exception as e:
        print(f"❌ Gemini OCR Service: エラー - {e}")
        services_status['gemini_ocr'] = False
    
    # Google Vision OCR Service (Parallel)
    try:
        from app.services.ocr.google_vision import GoogleVisionOCRService
        vision_ocr = GoogleVisionOCRService()
        
        if vision_ocr.is_available():
            print("✅ Google Vision OCR Service (Parallel): 利用可能")
            services_status['google_vision'] = True
        else:
            print("❌ Google Vision OCR Service (Parallel): 利用不可")
            services_status['google_vision'] = False
            
    except Exception as e:
        print(f"❌ Google Vision OCR Service: エラー - {e}")
        services_status['google_vision'] = False
    
    # OpenAI Services
    try:
        from app.services.category.openai import OpenAICategoryService
        from app.services.translation.openai import OpenAITranslationService
        from app.services.description.openai import OpenAIDescriptionService
        
        openai_services = []
        
        category_service = OpenAICategoryService()
        if category_service.is_available():
            print("✅ OpenAI Category Service: 利用可能")
            openai_services.append('category')
        
        translation_service = OpenAITranslationService()
        if translation_service.is_available():
            print("✅ OpenAI Translation Service: 利用可能")
            openai_services.append('translation')
            
        description_service = OpenAIDescriptionService()
        if description_service.is_available():
            print("✅ OpenAI Description Service: 利用可能")
            openai_services.append('description')
        
        services_status['openai'] = len(openai_services) == 3
        if len(openai_services) < 3:
            print(f"⚠️ OpenAI Services: {len(openai_services)}/3 利用可能")
            
    except Exception as e:
        print(f"❌ OpenAI Services: エラー - {e}")
        services_status['openai'] = False
    
    # Google Translate Service
    try:
        from app.services.translation.google_translate import GoogleTranslateService
        translate_service = GoogleTranslateService()
        
        if translate_service.is_available():
            print("✅ Google Translate Service: 利用可能")
            services_status['google_translate'] = True
        else:
            print("⚠️ Google Translate Service: デフォルト認証で動作")
            services_status['google_translate'] = True  # デフォルトでも動作するのでOK
            
    except Exception as e:
        print(f"❌ Google Translate Service: エラー - {e}")
        services_status['google_translate'] = False
    
    # Imagen 3 Service
    try:
        from app.services.image.imagen3 import Imagen3Service
        imagen_service = Imagen3Service()
        
        if imagen_service.is_available():
            print("✅ Imagen 3 Image Service: 利用可能")
            services_status['imagen'] = True
        else:
            print("❌ Imagen 3 Image Service: 利用不可")
            services_status['imagen'] = False
            
    except Exception as e:
        print(f"❌ Imagen 3 Service: エラー - {e}")
        services_status['imagen'] = False
    
    return services_status

def check_critical_dependencies():
    """重要な依存関係のみをチェック"""
    print("\n🔍 重要な依存関係チェック...")
    
    critical_packages = [
        ('fastapi', 'FastAPI Web Framework'),
        ('uvicorn', 'ASGI Server'),
        ('google.cloud.vision', 'Google Vision API'),
        ('google.cloud.translate', 'Google Translate API'),
        ('google.generativeai', 'Gemini API'),
        ('openai', 'OpenAI API')
    ]
    
    all_good = True
    
    for import_name, description in critical_packages:
        try:
            if import_name == 'google.cloud.vision':
                from google.cloud import vision
            elif import_name == 'google.cloud.translate':
                from google.cloud import translate
            elif import_name == 'google.generativeai':
                import google.generativeai
            else:
                __import__(import_name)
            print(f"✅ {description}: 利用可能")
        except ImportError:
            print(f"❌ {description}: 未インストール")
            all_good = False
    
    return all_good

def provide_optimized_solutions():
    """最適化された解決策を提案"""
    print("\n💡 問題がある場合の解決策:")
    
    print("\n🔧 基本的なトラブルシューティング:")
    print("1. アプリケーションを再起動してください:")
    print("   python -m app.main")
    
    print("\n2. 環境変数の確認:")
    print("   - .envファイルが存在することを確認")
    print("   - GOOGLE_CREDENTIALS_JSONが一行で記述されていることを確認")
    print("   - JSON内に不正な制御文字がないことを確認")
    
    print("\n3. 依存関係の更新:")
    print("   pip install -r requirements.txt")
    
    print("\n4. Google Cloud認証の確認:")
    print("   - サービスアカウントキーが有効であることを確認")
    print("   - Vision API、Translate APIが有効化されていることを確認")
    
    print("\n⚠️ 注意: このチェッカーでエラーが表示されても、")
    print("   実際のアプリケーションが正常に動作している場合があります。")
    print("   最終的な動作確認は 'python -m app.main' で行ってください。")

def main():
    """メイン関数"""
    print("🚀 Menu Processor 最適化セットアップチェッカー")
    print("=" * 55)
    
    # Step 1: 環境変数チェック
    env_ok = check_environment()
    
    # Step 2: 重要な依存関係チェック
    deps_ok = check_critical_dependencies()
    
    # Step 3: 実際のサービステスト
    if env_ok and deps_ok:
        services_status = check_actual_services()
        
        # 結果の評価
        core_services = ['gemini_ocr', 'openai']  # 最低限必要なサービス
        core_ok = all(services_status.get(service, False) for service in core_services)
        
        optional_services = ['google_vision', 'google_translate', 'imagen']
        optional_count = sum(1 for service in optional_services if services_status.get(service, False))
        
        print("\n" + "=" * 55)
        
        if core_ok:
            print("🎉 メインサービスが正常に動作しています！")
            print("次のコマンドでサーバーを起動できます:")
            print("python -m app.main")
            
            print(f"\n📊 サービス状況:")
            print(f"- メインサービス: ✅ {len(core_services)}/{len(core_services)}")
            print(f"- オプションサービス: {'✅' if optional_count == len(optional_services) else '⚠️'} {optional_count}/{len(optional_services)}")
            
            if optional_count < len(optional_services):
                print("\n⚠️ 一部のオプションサービスが利用できませんが、")
                print("   アプリケーションの基本機能は正常に動作します。")
        else:
            print("⚠️ 一部のメインサービスに問題があります。")
            provide_optimized_solutions()
            sys.exit(1)
    else:
        print("❌ 基本設定に問題があります。")
        provide_optimized_solutions()
        sys.exit(1)

if __name__ == "__main__":
    main() 
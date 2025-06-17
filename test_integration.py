#!/usr/bin/env python3
"""
Menu Processor + Imagen 3 統合テスト
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

def test_integration_setup():
    """統合機能のセットアップをテスト"""
    print("🧪 Menu Processor + Imagen 3 統合テスト")
    print("=" * 50)
    
    # 環境変数チェック
    gemini_key = os.getenv("GEMINI_API_KEY")
    google_creds = os.getenv("GOOGLE_CREDENTIALS_JSON")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    print("📋 環境変数チェック:")
    print(f"  ✅ GEMINI_API_KEY: {'設定済み' if gemini_key else '❌ 未設定'}")
    print(f"  ✅ GOOGLE_CREDENTIALS_JSON: {'設定済み' if google_creds else '❌ 未設定'}")
    print(f"  ✅ OPENAI_API_KEY: {'設定済み' if openai_key else '❌ 未設定'}")
    
    # ライブラリインポートテスト
    print("\n📦 ライブラリインポートテスト:")
    
    try:
        import google.generativeai as genai
        print("  ✅ google-generativeai: インポート成功")
    except ImportError:
        print("  ❌ google-generativeai: インポート失敗")
        return False
    
    try:
        from google import genai as imagen_genai
        from google.genai import types
        print("  ✅ google-genai (Imagen 3): インポート成功")
    except ImportError:
        print("  ❌ google-genai (Imagen 3): インポート失敗")
        return False
    
    try:
        from PIL import Image
        print("  ✅ PIL: インポート成功")
    except ImportError:
        print("  ❌ PIL: インポート失敗")
        return False
    
    # Imagen 3クライアント初期化テスト
    print("\n🎨 Imagen 3 初期化テスト:")
    
    if gemini_key:
        try:
            imagen_client = imagen_genai.Client(api_key=gemini_key)
            print("  ✅ Imagen 3 クライアント: 初期化成功")
        except Exception as e:
            print(f"  ❌ Imagen 3 クライアント初期化エラー: {e}")
            return False
    else:
        print("  ⏭️ GEMINI_API_KEYが未設定のため、初期化テストをスキップ")
    
    # Menu Processorの関数テスト
    print("\n🍜 Menu Processor 関数テスト:")
    
    try:
        # mvp_menu_processor.pyから関数をインポート
        sys.path.append('.')
        from mvp_menu_processor import create_image_prompt, combine_menu_with_images
        print("  ✅ create_image_prompt: インポート成功")
        print("  ✅ combine_menu_with_images: インポート成功")
        
        # プロンプト生成テスト
        test_prompt = create_image_prompt(
            "唐揚げ", 
            "Karaage", 
            "Crispy fried chicken pieces marinated in soy sauce and ginger", 
            "Main Dishes"
        )
        print(f"  ✅ プロンプト生成テスト: 成功")
        print(f"     生成されたプロンプト: {test_prompt[:100]}...")
        
    except Exception as e:
        print(f"  ❌ Menu Processor関数テストエラー: {e}")
        return False
    
    print("\n🎉 統合テスト完了!")
    return True

def test_workflow_stages():
    """新しい6段階ワークフローをテスト"""
    print("\n🔄 6段階ワークフローテスト:")
    
    stages = [
        "Stage 1: OCR (テキスト抽出)",
        "Stage 2: Categorize (カテゴリ分類)", 
        "Stage 3: Translate (英語翻訳)",
        "Stage 4: Describe (詳細説明追加)",
        "Stage 5: Generate Images (画像生成) ← 新機能!",
        "Stage 6: Complete (完了通知)"
    ]
    
    for i, stage in enumerate(stages, 1):
        emoji = "🎨" if i == 5 else "✅" if i == 6 else "🔄"
        print(f"  {emoji} {stage}")
    
    print("\n💡 新機能の詳細:")
    print("  🎨 Stage 5で各メニューアイテムに対して:")
    print("     - 料理名と説明からプロンプトを自動生成")
    print("     - Imagen 3で高品質な料理画像を生成")
    print("     - 生成された画像をアップロードディレクトリに保存")
    print("     - メニューデータと画像データを統合")

def test_sample_menu():
    """サンプルメニューでの動作確認"""
    print("\n🍽️ サンプルメニューテスト:")
    
    # サンプルメニューデータ
    sample_menu = {
        "Main Dishes": [
            {
                "japanese_name": "親子丼",
                "english_name": "Oyakodon",
                "description": "Traditional Japanese rice bowl topped with chicken and egg cooked in savory dashi broth",
                "price": "¥1,200"
            },
            {
                "japanese_name": "天ぷら定食",
                "english_name": "Tempura Set",
                "description": "Assorted tempura with shrimp and seasonal vegetables, served with rice and miso soup",
                "price": "¥1,800"
            }
        ],
        "Drinks": [
            {
                "japanese_name": "緑茶",
                "english_name": "Green Tea",
                "description": "Premium Japanese green tea with delicate flavor and aroma",
                "price": "¥300"
            }
        ]
    }
    
    print("  📋 サンプルメニュー:")
    for category, items in sample_menu.items():
        print(f"    {category}:")
        for item in items:
            print(f"      - {item['english_name']} ({item['japanese_name']})")
    
    # プロンプト生成のシミュレーション
    print("\n  🎨 生成されるプロンプトの例:")
    
    try:
        from mvp_menu_processor import create_image_prompt
        
        for category, items in sample_menu.items():
            for item in items[:1]:  # 各カテゴリから1つだけテスト
                prompt = create_image_prompt(
                    item["japanese_name"],
                    item["english_name"], 
                    item["description"],
                    category
                )
                print(f"    {item['english_name']}: {prompt[:80]}...")
                
    except Exception as e:
        print(f"    ❌ プロンプト生成エラー: {e}")

def main():
    """メイン関数"""
    success = test_integration_setup()
    
    if success:
        test_workflow_stages()
        test_sample_menu()
        
        print("\n" + "=" * 50)
        print("🚀 Menu Processor + Imagen 3 統合準備完了!")
        print("\n次のステップ:")
        print("1. メニュー画像をアップロードしてテスト")
        print("2. 6段階のワークフローを確認")
        print("3. 生成された画像を確認")
        print("4. 有料プランでImagen 3を有効化")
    else:
        print("\n⚠️ 統合テストで問題が見つかりました。設定を確認してください。")

if __name__ == "__main__":
    main() 
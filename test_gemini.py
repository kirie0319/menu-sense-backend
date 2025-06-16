#!/usr/bin/env python3
"""
Gemini 2.0 Flash API テストスクリプト
Menu ProcessorでのGemini API統合テスト用
"""

import os
import sys
from dotenv import load_dotenv

def test_gemini_setup():
    """Gemini APIの設定をテスト"""
    print("🧪 Gemini 2.0 Flash API テスト")
    print("=" * 40)
    
    # 環境変数読み込み
    load_dotenv()
    
    # APIキーチェック
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY が設定されていません")
        print("   .envファイルにGEMINI_API_KEY=your_api_key_hereを追加してください")
        return False
    
    print(f"✅ GEMINI_API_KEY: 設定済み ({len(api_key)}文字)")
    
    # パッケージインポートテスト
    try:
        import google.generativeai as genai
        print("✅ google-generativeai: インポート成功")
    except ImportError:
        print("❌ google-generativeai: パッケージが見つかりません")
        print("   pip install google-generativeai でインストールしてください")
        return False
    
    # API設定テスト
    try:
        genai.configure(api_key=api_key)
        print("✅ Gemini API: 設定成功")
    except Exception as e:
        print(f"❌ Gemini API設定エラー: {e}")
        return False
    
    # モデル初期化テスト
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        print("✅ Gemini 2.0 Flash モデル: 初期化成功")
    except Exception as e:
        print(f"❌ モデル初期化エラー: {e}")
        return False
    
    # 簡単なテキスト生成テスト
    try:
        print("\n🧪 簡単なテキスト生成テスト...")
        response = model.generate_content("Hello, Gemini! Can you confirm you're working?")
        if response.text:
            print("✅ テキスト生成テスト: 成功")
            print(f"   レスポンス: {response.text[:100]}...")
        else:
            print("❌ テキスト生成テスト: 空のレスポンス")
            return False
    except Exception as e:
        print(f"❌ テキスト生成テストエラー: {e}")
        return False
    
    print("\n🎉 すべてのテストが成功しました！")
    print("Gemini 2.0 Flash APIは正常に動作しています。")
    return True

def test_ocr_function():
    """OCR関数の基本テスト（画像ファイルがあれば）"""
    print("\n🖼️ OCR機能テスト")
    print("-" * 30)
    
    # テスト用画像があるかチェック
    test_images = ["test_menu.jpg", "test_menu.png", "sample_menu.jpg"]
    test_image = None
    
    for img in test_images:
        if os.path.exists(img):
            test_image = img
            break
    
    if not test_image:
        print("⏭️ テスト用画像が見つかりません。OCR機能テストをスキップします。")
        print("   テスト用のメニュー画像をtest_menu.jpgとして保存すると、OCRテストを実行できます。")
        return True
    
    print(f"📷 テスト画像: {test_image}")
    
    try:
        # Gemini APIでOCRテスト
        import google.generativeai as genai
        
        api_key = os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # 画像読み込み
        with open(test_image, 'rb') as f:
            image_data = f.read()
        
        # OCR実行
        image_parts = [{
            "mime_type": "image/jpeg",
            "data": image_data
        }]
        
        prompt = "この画像に含まれるテキストを抽出してください。"
        response = model.generate_content([prompt] + image_parts)
        
        if response.text:
            print("✅ OCRテスト: 成功")
            print(f"   抽出されたテキスト: {response.text[:200]}...")
        else:
            print("❌ OCRテスト: テキストを抽出できませんでした")
            return False
        
    except Exception as e:
        print(f"❌ OCRテストエラー: {e}")
        return False
    
    print("✅ OCR機能テスト完了")
    return True

def main():
    """メイン関数"""
    success = test_gemini_setup()
    
    if success:
        test_ocr_function()
    
    print("\n" + "=" * 40)
    if success:
        print("🚀 Menu ProcessorでGemini 2.0 Flash OCRを使用する準備ができました！")
        print("python run_mvp.py でサーバーを起動してください。")
    else:
        print("⚠️ 設定を確認してください。")
        sys.exit(1)

if __name__ == "__main__":
    main() 
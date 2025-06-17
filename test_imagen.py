#!/usr/bin/env python3
"""
Imagen 3 (Gemini API) テストスクリプト
Menu ProcessorでのImagen 3統合テスト用
"""

import os
import sys
import base64
from datetime import datetime
from dotenv import load_dotenv

def test_imagen_setup():
    """Imagen 3 (Gemini API)の設定をテスト"""
    print("🖼️ Imagen 3 (Gemini API) テスト")
    print("=" * 40)
    
    # 環境変数読み込み
    load_dotenv()
    
    # Gemini APIキーチェック
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY が設定されていません")
        print("   .envファイルにGEMINI_API_KEY=your_api_key_hereを追加してください")
        return False
    
    print(f"✅ GEMINI_API_KEY: 設定済み ({len(api_key)}文字)")
    
    # パッケージインポートテスト
    try:
        from google import genai
        from google.genai import types
        from PIL import Image
        from io import BytesIO
        print("✅ google-genai: インポート成功")
        print("✅ PIL: インポート成功")
    except ImportError as e:
        print(f"❌ 必要なパッケージがインポートできません: {e}")
        print("   以下をインストールしてください:")
        print("   pip install google-genai pillow")
        return False
    
    # Gemini クライアント初期化テスト
    try:
        client = genai.Client(api_key=api_key)
        print("✅ Gemini クライアント: 初期化成功")
    except Exception as e:
        print(f"❌ Gemini クライアント初期化エラー: {e}")
        return False
    
    print("\n🎉 基本設定のテストが成功しました！")
    return True

def test_imagen_generation():
    """Imagen 3での画像生成テスト"""
    print("\n🎨 Imagen 3 画像生成テスト")
    print("-" * 40)
    
    try:
        from google import genai
        from google.genai import types
        from PIL import Image
        from io import BytesIO
        
        # クライアント初期化
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key)
        
        # テスト用プロンプト
        test_prompts = [
            "A delicious Japanese bento box with various colorful dishes, beautifully arranged",
            "A modern restaurant menu design with elegant typography and food photos",
            "A fresh sushi platter on a wooden board with wasabi and ginger"
        ]
        
        for i, prompt in enumerate(test_prompts):
            print(f"\n🎯 テスト {i+1}/3: {prompt[:50]}...")
            
            try:
                # 画像生成
                response = client.models.generate_images(
                    model='imagen-3.0-generate-002',
                    prompt=prompt,
                    config=types.GenerateImagesConfig(
                        number_of_images=1,
                        aspect_ratio="1:1"
                    )
                )
                
                if response.generated_images:
                    # 生成された画像を保存
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"imagen_test_{i+1}_{timestamp}.png"
                    
                    # uploadsディレクトリが存在しない場合は作成
                    os.makedirs("uploads", exist_ok=True)
                    
                    # 画像を保存
                    generated_image = response.generated_images[0]
                    image = Image.open(BytesIO(generated_image.image.image_bytes))
                    image.save(f"uploads/{filename}")
                    print(f"✅ 画像生成成功: uploads/{filename}")
                else:
                    print("❌ 画像が生成されませんでした")
                    return False
                
            except Exception as e:
                print(f"❌ 画像生成エラー: {e}")
                # より詳細なエラー情報
                if hasattr(e, 'response'):
                    print(f"   レスポンス: {e.response}")
                return False
        
        print("\n🎉 すべての画像生成テストが成功しました！")
        return True
        
    except Exception as e:
        print(f"❌ Imagen テストエラー: {e}")
        return False

def test_imagen_batch_generation():
    """複数画像の一括生成テスト"""
    print("\n🔄 複数画像一括生成テスト")
    print("-" * 40)
    
    try:
        from google import genai
        from google.genai import types
        from PIL import Image
        from io import BytesIO
        
        # クライアント初期化
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key)
        
        prompt = "Cute cartoon-style food mascot characters for a restaurant"
        
        print(f"🎯 プロンプト: {prompt}")
        print("🔄 4枚の画像を一括生成中...")
        
        # 4枚の画像を一括生成
        response = client.models.generate_images(
            model='imagen-3.0-generate-002',
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=4,
                aspect_ratio="1:1"
            )
        )
        
        if response.generated_images:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            os.makedirs("uploads", exist_ok=True)
            
            for i, generated_image in enumerate(response.generated_images):
                filename = f"imagen_batch_{i+1}_{timestamp}.png"
                image = Image.open(BytesIO(generated_image.image.image_bytes))
                image.save(f"uploads/{filename}")
                print(f"✅ 画像 {i+1}/4 保存成功: uploads/{filename}")
        else:
            print("❌ 画像が生成されませんでした")
            return False
        
        print("✅ 一括生成テスト完了")
        return True
        
    except Exception as e:
        print(f"❌ 一括生成テストエラー: {e}")
        return False

def test_aspect_ratios():
    """異なるアスペクト比のテスト"""
    print("\n📐 アスペクト比テスト")
    print("-" * 30)
    
    try:
        from google import genai
        from google.genai import types
        from PIL import Image
        from io import BytesIO
        
        # クライアント初期化
        api_key = os.getenv("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key)
        
        aspect_ratios = ["1:1", "3:4", "4:3", "9:16", "16:9"]
        prompt = "A beautiful Japanese garden with cherry blossoms"
        
        for ratio in aspect_ratios:
            print(f"\n🔲 アスペクト比 {ratio} をテスト中...")
            
            try:
                response = client.models.generate_images(
                    model='imagen-3.0-generate-002',
                    prompt=prompt,
                    config=types.GenerateImagesConfig(
                        number_of_images=1,
                        aspect_ratio=ratio
                    )
                )
                
                if response.generated_images:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"imagen_ratio_{ratio.replace(':', 'x')}_{timestamp}.png"
                    
                    os.makedirs("uploads", exist_ok=True)
                    
                    generated_image = response.generated_images[0]
                    image = Image.open(BytesIO(generated_image.image.image_bytes))
                    image.save(f"uploads/{filename}")
                    print(f"✅ {ratio} 生成成功: uploads/{filename}")
                else:
                    print(f"❌ {ratio} 画像が生成されませんでした")
                    
            except Exception as e:
                print(f"❌ {ratio} 生成エラー: {e}")
        
        print("\n✅ アスペクト比テスト完了")
        return True
        
    except Exception as e:
        print(f"❌ アスペクト比テストエラー: {e}")
        return False

def main():
    """メイン関数"""
    success = test_imagen_setup()
    
    if success:
        # 基本画像生成テスト
        generation_success = test_imagen_generation()
        
        # 追加テスト
        if generation_success:
            print("\n🚀 追加テストを実行中...")
            test_imagen_batch_generation()
            test_aspect_ratios()
    
    print("\n" + "=" * 40)
    if success:
        print("🚀 Imagen 3 (Gemini API)の準備ができました！")
        print("\n📝 生成された画像は uploads/ ディレクトリに保存されています。")
        print("🔧 Menu Processorでの画像生成機能統合が可能です。")
        print("\n💡 主な機能:")
        print("- テキストから高品質画像生成")
        print("- 複数アスペクト比対応 (1:1, 3:4, 4:3, 9:16, 16:9)")
        print("- 一括生成 (最大4枚)")
        print("- 安全フィルター内蔵")
    else:
        print("⚠️ 設定を確認してください。")
        print("\n必要な設定:")
        print("1. GEMINI_API_KEY の設定")
        print("2. google-genai ライブラリのインストール")
        print("3. Gemini API Paid Tierの契約")
        sys.exit(1)

if __name__ == "__main__":
    main() 
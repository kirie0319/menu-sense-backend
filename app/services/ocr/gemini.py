import base64
import mimetypes
from typing import Optional

try:
    import google.generativeai as genai
except ImportError:
    genai = None

from app.core.config import settings
from .base import BaseOCRService, OCRResult

class GeminiOCRService(BaseOCRService):
    """Gemini 2.0 Flashを使用したOCRサービス（高精度版）"""
    
    def __init__(self):
        super().__init__()
        self.model = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Gemini APIクライアントを初期化"""
        try:
            if not genai:
                print("❌ google-generativeai package not installed. Install with: pip install google-generativeai")
                return
                
            if settings.GEMINI_API_KEY:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self.model = genai.GenerativeModel(settings.GEMINI_MODEL)
                print("✅ Gemini 2.0 Flash API configured successfully")
            else:
                print("⚠️ GEMINI_API_KEY not found in environment variables")
                
        except Exception as e:
            print(f"❌ Gemini API initialization failed: {e}")
            self.model = None
    
    def is_available(self) -> bool:
        """Gemini APIが利用可能かどうかを確認"""
        return self.model is not None and genai is not None
    
    def _get_menu_ocr_prompt(self) -> str:
        """メニュー画像OCR用のプロンプト（飲食店特化）"""
        return """
この画像は日本の飲食店のメニューです。以下の要件に従ってテキストを抽出してください：

1. 料理名、価格、説明を正確に読み取る
2. メニューの視覚的構造（セクション、カテゴリ）を保持する
3. 「ドリンク」「メイン」「前菜」「デザート」などの基本カテゴリを推測して分類
4. 文字が不鮮明な場合は可能な限り推測
5. 価格表記（円、¥など）を正確に抽出
6. テキストの読み取り順序を視覚的な配置に合わせる

抽出形式:
- カテゴリごとに整理
- 各料理について： 料理名 価格（ある場合）
- セクション間に空行を入れる
- 推測したカテゴリ名は [カテゴリ名] の形式で記載

画像から読み取れる全てのテキストを丁寧に抽出してください。
        """
    
    async def extract_text(self, image_path: str, session_id: str = None) -> OCRResult:
        """Gemini 2.0 Flashを使って画像からテキストを抽出（高精度版）"""
        print("🔍 Starting OCR with Gemini 2.0 Flash...")
        
        # Gemini API利用可能性チェック
        if not self.is_available():
            suggestions = [
                "GEMINI_API_KEY環境変数が設定されているか確認してください",
                "google-generativeaiパッケージがインストールされているか確認してください",
                "Gemini APIが有効化されているか確認してください"
            ]
            
            if not genai:
                suggestions.insert(0, "pip install google-generativeai でパッケージをインストールしてください")
            
            return self._create_error_result(
                "Gemini APIが利用できません。GEMINI_API_KEYが設定されているか確認してください。",
                error_type="api_unavailable",
                suggestions=suggestions
            )
        
        try:
            # 画像ファイル検証
            self.validate_image_file(image_path)
            
            # 画像ファイル読み込み
            with open(image_path, 'rb') as image_file:
                image_data = image_file.read()
            
            # ファイルタイプの検出
            mime_type, _ = mimetypes.guess_type(image_path)
            if not mime_type or not mime_type.startswith('image/'):
                mime_type = 'image/jpeg'  # デフォルト
            
            # Gemini用の画像データ準備
            image_parts = [
                {
                    "mime_type": mime_type,
                    "data": image_data
                }
            ]
            
            # メニュー画像OCR用のプロンプト取得
            prompt = self._get_menu_ocr_prompt()
            
            # Gemini APIに画像とプロンプトを送信
            response = self.model.generate_content([prompt] + image_parts)
            
            # レスポンスからテキストを抽出
            if response.text:
                extracted_text = response.text.strip()
            else:
                extracted_text = ""
            
            print(f"✅ Gemini OCR Complete: Extracted {len(extracted_text)} characters")
            
            # 結果が空の場合の処理
            if not extracted_text.strip():
                return self._create_error_result(
                    "画像からテキストを検出できませんでした。より鮮明な画像をお試しください。",
                    error_type="no_text_detected",
                    suggestions=[
                        "より鮮明な画像を使用してください",
                        "文字が大きく写っている画像を選んでください",
                        "照明が良い環境で撮影した画像を使用してください",
                        "メニューテキストが中央に写っている画像を選んでください"
                    ]
                )
            
            # 成功結果
            return self._create_success_result(
                extracted_text,
                metadata={
                    "file_size": len(image_data),
                    "text_length": len(extracted_text),
                    "ocr_method": "gemini_2.0_flash",
                    "mime_type": mime_type,
                    "stage": 1
                }
            )
                
        except FileNotFoundError as e:
            return self._create_error_result(
                str(e),
                error_type="file_not_found"
            )
        
        except ValueError as e:
            return self._create_error_result(
                str(e),
                error_type="validation_error"
            )
            
        except Exception as e:
            print(f"❌ Gemini OCR Failed: {e}")
            
            # エラータイプの判定
            error_type = "unknown_error"
            suggestions = []
            
            error_str = str(e).lower()
            if "api" in error_str and "key" in error_str:
                error_type = "api_key_error"
                suggestions = [
                    "GEMINI_API_KEYが正しく設定されているか確認してください",
                    "Gemini APIキーが有効であることを確認してください"
                ]
            elif "quota" in error_str or "limit" in error_str:
                error_type = "quota_exceeded"
                suggestions = [
                    "Gemini APIクォータを確認してください",
                    "しばらく時間をおいてから再試行してください"
                ]
            elif "permission" in error_str or "forbidden" in error_str:
                error_type = "permission_error"
                suggestions = [
                    "Gemini API権限を確認してください",
                    "APIキーが正しく設定されているか確認してください"
                ]
            elif "network" in error_str or "connection" in error_str:
                error_type = "network_error"
                suggestions = [
                    "インターネット接続を確認してください",
                    "しばらく時間をおいてから再試行してください"
                ]
            else:
                suggestions = [
                    "画像ファイルが破損していないか確認してください",
                    "サポートされている画像形式（JPG、PNG、GIF、WEBP）を使用してください",
                    "しばらく時間をおいてから再試行してください"
                ]
            
            return self._create_error_result(
                f"Gemini OCR処理中にエラーが発生しました: {str(e)}",
                error_type=error_type,
                suggestions=suggestions
            )

"""
🔍 Google Provider Service

Google APIを使用した統合サービス
- Vision API: OCR テキスト抽出
- Translate API: 翻訳サービス
- Imagen3 API: 画像生成

既存のapp.services.ocr.google_vision + app.services.translation.google_translate + app.services.image.imagen3を統合
"""

import io
import json
import asyncio
from typing import Optional, Dict, List, Any
from datetime import datetime
from io import BytesIO
from pydantic import BaseModel, Field
from enum import Enum

# Google APIs
try:
    from google.cloud import vision
    from google.cloud import translate_v2 as translate
    from google import genai as imagen_genai
    from google.genai import types
    from PIL import Image
    # Gemini for OCR
    import google.generativeai as gemini_genai
    import mimetypes
except ImportError:
    vision = None
    translate = None
    imagen_genai = None
    types = None
    Image = None
    gemini_genai = None
    mimetypes = None

from app.core.config.ai import ai_settings
from app.core.config.processing import processing_settings
from app.core.config.base import base_settings

# OCRResult class definition (moved from external import)
class OCRProvider(str, Enum):
    """OCRプロバイダーの定義"""
    GEMINI = "gemini"
    GOOGLE_VISION = "google_vision"
    ENHANCED = "enhanced"

class OCRResult(BaseModel):
    """
    OCR結果を格納するクラス
    """
    
    # 既存フィールド（互換性維持）
    success: bool
    extracted_text: str = ""
    provider: str = ""
    error: Optional[str] = None
    metadata: Dict = {}
    
    # Enhanced機能追加フィールド（オプション）
    processing_time: Optional[float] = Field(default=None, description="処理時間（秒）")
    
    # 品質指標（Enhanced機能）
    quality_score: Optional[float] = Field(default=None, description="品質スコア (0-1)")
    confidence: Optional[float] = Field(default=None, description="信頼度 (0-1)")
    text_clarity_score: Optional[float] = Field(default=None, description="テキスト明瞭度")
    character_count: Optional[int] = Field(default=None, description="文字数")
    japanese_character_ratio: Optional[float] = Field(default=None, description="日本語文字比率")
    
    def to_dict(self) -> Dict:
        """辞書形式に変換（既存互換性維持）"""
        result = {
            "success": self.success,
            "extracted_text": self.extracted_text,
            "provider": self.provider
        }
        if self.error:
            result["error"] = self.error
        if self.metadata:
            result.update(self.metadata)
        return result

# TranslationResult class definition (moved from external import)
class TranslationProvider(str, Enum):
    """翻訳プロバイダーの定義"""
    GOOGLE_TRANSLATE = "google_translate"
    OPENAI = "openai"
    ENHANCED = "enhanced"

class TranslationResult(BaseModel):
    """
    翻訳結果を格納するクラス
    """
    
    # 既存フィールド（互換性維持）
    success: bool
    translated_menu: Dict[str, List[Dict]] = {}
    translation_method: str = ""
    error: Optional[str] = None
    metadata: Dict = {}
    
    # Enhanced機能追加フィールド（オプション）
    total_items: Optional[int] = Field(default=None, description="総アイテム数")
    translated_items: Optional[int] = Field(default=None, description="翻訳済みアイテム数")
    processing_time: Optional[float] = Field(default=None, description="処理時間（秒）")
    
    # 品質指標（Enhanced機能）
    quality_score: Optional[float] = Field(default=None, description="品質スコア (0-1)")
    confidence: Optional[float] = Field(default=None, description="信頼度 (0-1)")
    translation_coverage: Optional[float] = Field(default=None, description="翻訳カバレッジ")
    consistency_score: Optional[float] = Field(default=None, description="一貫性スコア")
    accuracy_estimate: Optional[float] = Field(default=None, description="精度推定")
    
    # 統計情報（Enhanced機能）
    failed_translations: List[str] = Field(default_factory=list, description="翻訳失敗アイテム")
    processing_metadata: Dict[str, Any] = Field(default_factory=dict, description="処理メタデータ")
    fallback_used: bool = Field(default=False, description="フォールバック使用フラグ")
    
    def to_dict(self) -> Dict:
        """辞書形式に変換（既存互換性維持）"""
        result = {
            "success": self.success,
            "translated_menu": self.translated_menu,
            "translation_method": self.translation_method
        }
        if self.error:
            result["error"] = self.error
        if self.metadata:
            result.update(self.metadata)
        return result

# ImageResult class definition (moved from external import)
class ImageProvider(str, Enum):
    """画像生成プロバイダーの定義"""
    IMAGEN3 = "imagen3"
    ENHANCED = "enhanced"

class ImageResult(BaseModel):
    """
    画像生成結果を格納するクラス
    """
    
    # 既存フィールド（互換性維持）
    success: bool
    images_generated: Dict[str, List[Dict]] = {}
    total_images: int = 0
    total_items: int = 0
    image_method: str = ""
    error: Optional[str] = None
    metadata: Dict = {}
    
    # Enhanced機能追加フィールド（オプション）
    processing_time: Optional[float] = Field(default=None, description="処理時間（秒）")
    generated_items: Optional[int] = Field(default=None, description="画像生成済みアイテム数")
    
    # 品質指標（Enhanced機能）
    quality_score: Optional[float] = Field(default=None, description="品質スコア (0-1)")
    confidence: Optional[float] = Field(default=None, description="信頼度 (0-1)")
    generation_success_rate: Optional[float] = Field(default=None, description="生成成功率")
    visual_quality: Optional[float] = Field(default=None, description="視覚品質")
    prompt_effectiveness: Optional[float] = Field(default=None, description="プロンプト効果")
    
    # 統計情報（Enhanced機能）
    failed_generations: List[str] = Field(default_factory=list, description="生成失敗アイテム")
    generation_stats: Dict[str, Any] = Field(default_factory=dict, description="生成統計")
    fallback_used: bool = Field(default=False, description="フォールバック使用フラグ")
    storage_stats: Dict[str, Any] = Field(default_factory=dict, description="ストレージ統計")
    
    def to_dict(self) -> Dict:
        """辞書形式に変換（既存互換性維持）"""
        result = {
            "success": self.success,
            "images_generated": self.images_generated,
            "total_images": self.total_images,
            "total_items": self.total_items,
            "image_method": self.image_method
        }
        if self.error:
            result["error"] = self.error
        if self.metadata:
            result.update(self.metadata)
        return result

# Storage service
from app.services.s3_storage import s3_storage


class GoogleProviderService:
    """Google統合プロバイダーサービス"""
    
    def __init__(self):
        self.service_name = "GoogleProviderService"
        self.vision_client = None
        self.translate_client = None
        self.imagen_client = None
        self.gemini_model = None
        self.credentials = None
        self._initialize_clients()
        # 画像生成並列処理用セマフォ
        self.semaphore = asyncio.Semaphore(processing_settings.image_concurrent_chunk_limit)
    
    def _initialize_clients(self):
        """Google APIクライアントを初期化"""
        # 統一認証情報を取得
        try:
            from app.services.auth import get_credentials_manager
            credentials_manager = get_credentials_manager()
            self.credentials = credentials_manager.get_google_credentials()
        except Exception as e:
            print(f"❌ Failed to get Google credentials: {e}")
            self.credentials = None
        
        # Vision APIクライアント
        self._initialize_vision_client()
        
        # Translate APIクライアント
        self._initialize_translate_client()
        
        # Imagen APIクライアント
        self._initialize_imagen_client()
        
        # Gemini APIクライアント（OCR用）
        self._initialize_gemini_client()
    
    def _initialize_vision_client(self):
        """Google Vision APIクライアントを初期化"""
        try:
            if not vision:
                print("❌ google-cloud-vision package not installed")
                return
            
            if self.credentials:
                self.vision_client = vision.ImageAnnotatorClient(credentials=self.credentials)
                print("✅ Google Vision API client initialized with unified credentials")
            else:
                try:
                    self.vision_client = vision.ImageAnnotatorClient()
                    print("✅ Google Vision API client initialized with default credentials")
                except Exception as e:
                    print(f"❌ Google Vision API initialization failed: {e}")
                    self.vision_client = None
        except Exception as e:
            print(f"❌ Google Vision API initialization failed: {e}")
            self.vision_client = None
    
    def _initialize_translate_client(self):
        """Google Translate APIクライアントを初期化"""
        try:
            if not translate:
                print("❌ google-cloud-translate package not installed")
                return
            
            if self.credentials:
                self.translate_client = translate.Client(credentials=self.credentials)
                print("🔧 Google Translate Service initialized with unified credentials")
            else:
                try:
                    self.translate_client = translate.Client()
                    print("🔧 Google Translate Service initialized with default auth")
                except Exception as e:
                    print(f"⚠️ Failed to initialize Google Translate with default auth: {e}")
                    self.translate_client = None
        except Exception as e:
            print(f"❌ Failed to initialize Google Translate Service: {e}")
            self.translate_client = None
    
    def _initialize_imagen_client(self):
        """Imagen 3 APIクライアントを初期化"""
        try:
            if not imagen_genai or not types or not Image:
                print("❌ google-genai or PIL package not installed")
                return
                
            if ai_settings.gemini_api_key and ai_settings.image_generation_enabled:
                self.imagen_client = imagen_genai.Client(api_key=ai_settings.gemini_api_key)
                print("🔧 Imagen 3 Service initialized successfully")
            else:
                print("⚠️ GEMINI_API_KEY not set or IMAGE_GENERATION_ENABLED is False")
        except Exception as e:
            print(f"❌ Failed to initialize Imagen 3 Service: {e}")
            self.imagen_client = None
    
    def _initialize_gemini_client(self):
        """Gemini OCR APIクライアントを初期化"""
        try:
            if not gemini_genai:
                print("❌ google-generativeai package not installed")
                return
                
            if ai_settings.gemini_api_key:
                gemini_genai.configure(api_key=ai_settings.gemini_api_key)
                self.gemini_model = gemini_genai.GenerativeModel(ai_settings.gemini_model)
                print("🔧 Gemini OCR Service initialized successfully")
            else:
                print("⚠️ GEMINI_API_KEY not set")
        except Exception as e:
            print(f"❌ Failed to initialize Gemini OCR Service: {e}")
            self.gemini_model = None
    
    def is_vision_available(self) -> bool:
        """Vision APIが利用可能かチェック"""
        return self.vision_client is not None
    
    def is_translate_available(self) -> bool:
        """Translate APIが利用可能かチェック"""
        return self.translate_client is not None
    
    def is_imagen_available(self) -> bool:
        """Imagen APIが利用可能かチェック"""
        return (self.imagen_client is not None and 
                bool(ai_settings.gemini_api_key) and 
                ai_settings.image_generation_enabled and
                imagen_genai is not None and
                types is not None and
                Image is not None)
    
    def is_gemini_available(self) -> bool:
        """Gemini OCRが利用可能かチェック"""
        return (self.gemini_model is not None and 
                bool(ai_settings.gemini_api_key) and
                gemini_genai is not None)
    
    # ==========================================
    # OCR Features (Vision + Gemini)
    # ==========================================
    
    def validate_image_file(self, image_path: str) -> None:
        """画像ファイルの検証"""
        import os
        
        # ファイル存在チェック
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"画像ファイルが見つかりません: {image_path}")
        
        # ファイルサイズチェック
        file_size = os.path.getsize(image_path)
        if file_size == 0:
            raise ValueError("画像ファイルが空です")
        
        if file_size > base_settings.max_file_size:
            max_size_mb = base_settings.max_file_size // (1024*1024)
            raise ValueError(f"画像ファイルが大きすぎます（{max_size_mb}MB以下にしてください）")
    
    async def extract_text(self, image_path: str, session_id: str = None) -> OCRResult:
        """Google Vision APIを使って画像からテキストを抽出"""
        print("🔍 Starting OCR with Google Vision API...")
        
        # Vision API利用可能性チェック
        if not self.is_vision_available():
            return OCRResult(
                success=False,
                error="Google Vision APIが利用できません。認証情報を確認してください。",
                metadata={
                    "error_type": "api_unavailable",
                    "suggestions": [
                        "Set GOOGLE_APPLICATION_CREDENTIALS environment variable",
                        "Install google-cloud-vision package",
                        "Check Google Cloud Vision API is enabled",
                        "Verify service account permissions"
                    ]
                }
            )
        
        try:
            # 画像ファイル検証
            self.validate_image_file(image_path)
            
            # 画像ファイル読み込み
            with io.open(image_path, 'rb') as image_file:
                content = image_file.read()
            
            # Vision API呼び出し
            image = vision.Image(content=content)
            response = self.vision_client.text_detection(image=image)
            
            # エラーレスポンスチェック
            if response.error.message:
                raise Exception(f'Vision API Error: {response.error.message}')
            
            # テキスト抽出
            texts = response.text_annotations
            extracted_text = texts[0].description if texts else ""
            
            print(f"✅ Google Vision OCR Complete: Extracted {len(extracted_text)} characters")
            
            # 結果が空の場合の処理
            if not extracted_text.strip():
                return OCRResult(
                    success=False,
                    error="画像からテキストを検出できませんでした。より鮮明な画像をお試しください。",
                    metadata={
                        "error_type": "no_text_detected",
                        "suggestions": [
                            "より鮮明な画像を使用してください",
                            "文字が大きく写っている画像を選んでください",
                            "照明が良い環境で撮影した画像を使用してください",
                            "メニューテキストが中央に写っている画像を選んでください"
                        ]
                    }
                )
            
            # 成功結果
            return OCRResult(
                success=True,
                extracted_text=extracted_text,
                metadata={
                    "total_detections": len(texts),
                    "file_size": len(content),
                    "text_length": len(extracted_text),
                    "stage": 1,
                    "provider": "Google Vision API"
                }
            )
                
        except FileNotFoundError as e:
            return OCRResult(
                success=False,
                error=str(e),
                metadata={"error_type": "file_not_found"}
            )
        
        except ValueError as e:
            return OCRResult(
                success=False,
                error=str(e),
                metadata={"error_type": "validation_error"}
            )
            
        except Exception as e:
            print(f"❌ Google Vision OCR Failed: {e}")
            
            # エラータイプの判定
            error_type = self._get_vision_error_type(e)
            suggestions = self._get_vision_error_suggestions(e)
            
            return OCRResult(
                success=False,
                error=f"OCR処理中にエラーが発生しました: {str(e)}",
                metadata={
                    "error_type": error_type,
                    "suggestions": suggestions,
                    "provider": "Google Vision API"
                }
            )
    
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
    
    async def extract_text_gemini(self, image_path: str, session_id: str = None) -> OCRResult:
        """Gemini 2.0 Flashを使って画像からテキストを抽出（高精度版）"""
        print("🔍 Starting OCR with Gemini 2.0 Flash...")
        
        # Gemini API利用可能性チェック
        if not self.is_gemini_available():
            suggestions = [
                "GEMINI_API_KEY環境変数が設定されているか確認してください",
                "google-generativeaiパッケージがインストールされているか確認してください",
                "Gemini APIが有効化されているか確認してください"
            ]
            
            if not gemini_genai:
                suggestions.insert(0, "pip install google-generativeai でパッケージをインストールしてください")
            
            return OCRResult(
                success=False,
                error="Gemini APIが利用できません。GEMINI_API_KEYが設定されているか確認してください。",
                metadata={
                    "error_type": "api_unavailable",
                    "suggestions": suggestions
                }
            )
        
        try:
            # 画像ファイル検証
            self.validate_image_file(image_path)
            
            # 画像ファイル読み込み
            with open(image_path, 'rb') as image_file:
                image_data = image_file.read()
            
            # ファイルタイプの検出
            mime_type, _ = mimetypes.guess_type(image_path) if mimetypes else (None, None)
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
            response = self.gemini_model.generate_content([prompt] + image_parts)
            
            # レスポンスからテキストを抽出
            if response.text:
                extracted_text = response.text.strip()
            else:
                extracted_text = ""
            
            print(f"✅ Gemini OCR Complete: Extracted {len(extracted_text)} characters")
            
            # 結果が空の場合の処理
            if not extracted_text.strip():
                return OCRResult(
                    success=False,
                    error="画像からテキストを検出できませんでした。より鮮明な画像をお試しください。",
                    metadata={
                        "error_type": "no_text_detected",
                        "suggestions": [
                            "より鮮明な画像を使用してください",
                            "文字が大きく写っている画像を選んでください",
                            "照明が良い環境で撮影した画像を使用してください",
                            "メニューテキストが中央に写っている画像を選んでください"
                        ]
                    }
                )
            
            # 成功結果
            return OCRResult(
                success=True,
                extracted_text=extracted_text,
                metadata={
                    "file_size": len(image_data),
                    "text_length": len(extracted_text),
                    "ocr_method": "gemini_2.0_flash",
                    "mime_type": mime_type,
                    "stage": 1,
                    "provider": "Gemini 2.0 Flash"
                }
            )
                
        except FileNotFoundError as e:
            return OCRResult(
                success=False,
                error=str(e),
                metadata={"error_type": "file_not_found"}
            )
        
        except ValueError as e:
            return OCRResult(
                success=False,
                error=str(e),
                metadata={"error_type": "validation_error"}
            )
            
        except Exception as e:
            print(f"❌ Gemini OCR Failed: {e}")
            
            # エラータイプの判定
            error_type = self._get_gemini_error_type(e)
            suggestions = self._get_gemini_error_suggestions(e)
            
            return OCRResult(
                success=False,
                error=f"Gemini OCR処理中にエラーが発生しました: {str(e)}",
                metadata={
                    "error_type": error_type,
                    "suggestions": suggestions,
                    "provider": "Gemini 2.0 Flash"
                }
            )
    
    # ==========================================
    # Translation Features
    # ==========================================
    
    def get_category_mapping(self) -> Dict[str, str]:
        """カテゴリ名の事前定義マッピング"""
        return {
            "前菜": "Appetizers",
            "メイン": "Main Dishes", 
            "主菜": "Main Dishes",
            "メインディッシュ": "Main Dishes",
            "ドリンク": "Beverages",
            "飲み物": "Beverages",
            "お酒": "Alcoholic Beverages",
            "アルコール": "Alcoholic Beverages",
            "デザート": "Desserts",
            "スイーツ": "Desserts",
            "サイド": "Side Dishes",
            "副菜": "Side Dishes",
            "スープ": "Soups",
            "汁物": "Soups",
            "サラダ": "Salads",
            "丼": "Rice Bowls",
            "丼物": "Rice Bowls",
            "ご飯物": "Rice Dishes",
            "麺類": "Noodles",
            "うどん": "Udon Noodles",
            "そば": "Soba Noodles",
            "ラーメン": "Ramen",
            "寿司": "Sushi",
            "刺身": "Sashimi",
            "天ぷら": "Tempura",
            "焼き物": "Grilled Dishes",
            "揚げ物": "Fried Dishes"
        }
    
    def clean_translated_text(self, text: str) -> str:
        """翻訳されたテキストをクリーンアップ"""
        if not text:
            return ""
        
        # HTMLエンティティをデコード
        import html
        text = html.unescape(text)
        
        # 不要な引用符を削除
        text = text.strip().strip('"').strip("'")
        
        return text
    
    def extract_menu_item_data(self, item) -> tuple:
        """メニューアイテムデータを抽出"""
        if isinstance(item, dict):
            name = item.get("name", "")
            price = item.get("price", "")
        elif isinstance(item, str):
            # 価格パターンを探す
            import re
            price_pattern = r'[￥¥\$]\s*[\d,]+|[\d,]+\s*[円dollars?]'
            price_match = re.search(price_pattern, item)
            
            if price_match:
                price = price_match.group().strip()
                name = item.replace(price, "").strip()
            else:
                name = item.strip()
                price = ""
        else:
            name = str(item)
            price = ""
        
        return name, price
    
    async def translate_category_name(self, japanese_category: str) -> str:
        """カテゴリ名を翻訳"""
        # まず事前定義マッピングをチェック
        category_mapping = self.get_category_mapping()
        if japanese_category in category_mapping:
            english_category = category_mapping[japanese_category]
            print(f"📋 Using predefined mapping: {japanese_category} → {english_category}")
            return english_category
        
        # Google Translate APIで翻訳
        try:
            result = self.translate_client.translate(
                japanese_category,
                source_language='ja',
                target_language='en'
            )
            english_category = result['translatedText']
            english_category = self.clean_translated_text(english_category)
            print(f"📋 Google Translate: {japanese_category} → {english_category}")
            return english_category
        except Exception as e:
            print(f"⚠️ Category translation failed for '{japanese_category}': {e}")
            return japanese_category  # フォールバック
    
    async def translate_menu_item(self, item_name: str) -> str:
        """メニューアイテムを翻訳"""
        try:
            result = self.translate_client.translate(
                item_name,
                source_language='ja',
                target_language='en'
            )
            english_name = result['translatedText']
            return self.clean_translated_text(english_name)
        except Exception as e:
            print(f"  ⚠️ Translation failed for '{item_name}': {e}")
            return item_name  # フォールバック
    
    def validate_categorized_data(self, categorized_data: Dict) -> bool:
        """カテゴリ分類データの妥当性をチェック"""
        if not categorized_data or not isinstance(categorized_data, dict):
            return False
        
        # 少なくとも1つのカテゴリにアイテムがあることを確認
        has_items = any(
            isinstance(items, list) and len(items) > 0 
            for items in categorized_data.values()
        )
        
        return has_items
    
    async def translate_menu(
        self, 
        categorized_data: dict, 
        session_id: Optional[str] = None
    ) -> TranslationResult:
        """
        Google Translate APIを使ってカテゴリ分類されたメニューを英語に翻訳
        
        Args:
            categorized_data: カテゴリ分類されたメニューデータ
            session_id: セッションID（進行状況通知用）
            
        Returns:
            TranslationResult: 翻訳結果
        """
        print("🌍 Starting menu translation with Google Translate API...")
        
        # サービス利用可能性チェック
        if not self.is_translate_available():
            return TranslationResult(
                success=False,
                translation_method="google_translate",
                error="Google Translate API is not available. Check authentication setup.",
                metadata={
                    "error_type": "service_unavailable",
                    "suggestions": [
                        "Set GOOGLE_APPLICATION_CREDENTIALS environment variable",
                        "Install google-cloud-translate package",
                        "Check Google Cloud Translate API is enabled",
                        "Verify service account permissions",
                        "Check internet connectivity"
                    ]
                }
            )
        
        # 入力データの妥当性チェック
        if not self.validate_categorized_data(categorized_data):
            return TranslationResult(
                success=False,
                translation_method="google_translate",
                error="Invalid categorized data",
                metadata={
                    "error_type": "invalid_input",
                    "suggestions": [
                        "Provide valid categorized menu data",
                        "Ensure at least one category has menu items",
                        "Check category structure format"
                    ]
                }
            )
        
        try:
            translated_categories = {}
            total_items = sum(len(items) for items in categorized_data.values())
            processed_items = 0
            
            print(f"🔢 Total items to translate: {total_items}")
            
            # カテゴリごとに翻訳処理
            for japanese_category, items in categorized_data.items():
                if not items:
                    continue
                
                print(f"🔄 Processing category: {japanese_category} ({len(items)} items)")
                
                # カテゴリ名を翻訳
                english_category = await self.translate_category_name(japanese_category)
                
                translated_items = []
                
                # 各料理を翻訳
                for item_index, item in enumerate(items):
                    item_name, item_price = self.extract_menu_item_data(item)
                    
                    if not item_name.strip():
                        continue
                    
                    # Google Translate APIで料理名を翻訳
                    english_name = await self.translate_menu_item(item_name)
                    
                    translated_items.append({
                        "japanese_name": item_name,
                        "english_name": english_name,
                        "price": item_price
                    })
                    
                    processed_items += 1
                    print(f"  ✅ {item_name} → {english_name}")
                    
                    # レート制限対策
                    await asyncio.sleep(0.1)
                
                if translated_items:
                    translated_categories[english_category] = translated_items
            
            print(f"✅ Google Translate Complete: Translated {len(translated_categories)} categories")
            
            return TranslationResult(
                success=True,
                translated_categories=translated_categories,
                translation_method="google_translate",
                metadata={
                    "total_items": total_items,
                    "total_categories": len(translated_categories),
                    "provider": "Google Translate API",
                    "features": [
                        "category_mapping",
                        "html_entity_cleanup",
                        "rate_limiting"
                    ]
                }
            )
            
        except Exception as e:
            print(f"❌ Google Translate Failed: {e}")
            
            # エラータイプの判定
            error_type = self._get_translate_error_type(e)
            suggestions = self._get_translate_error_suggestions(e)
            
            return TranslationResult(
                success=False,
                translation_method="google_translate",
                error=f"Google Translate error: {str(e)}",
                metadata={
                    "error_type": error_type,
                    "original_error": str(e),
                    "suggestions": suggestions,
                    "provider": "Google Translate API"
                }
            )
    
    # ==========================================
    # Image Generation Features
    # ==========================================
    
    def validate_menu_data(self, final_menu: Dict) -> bool:
        """メニューデータの妥当性をチェック"""
        if not final_menu or not isinstance(final_menu, dict):
            return False
        
        # 少なくとも1つのカテゴリにアイテムがあることを確認
        has_items = any(
            isinstance(items, list) and len(items) > 0 
            for items in final_menu.values()
        )
        
        return has_items
    
    def validate_menu_item(self, item: dict) -> bool:
        """メニューアイテムの妥当性をチェック"""
        if not isinstance(item, dict):
            return False
        
        required_fields = ["japanese_name", "english_name"]
        return all(field in item and item[field] for field in required_fields)
    
    def validate_prompt_content(self, prompt: str) -> bool:
        """プロンプト内容の妥当性をチェック"""
        if not prompt or len(prompt.strip()) < 10:
            return False
        return True
    
    def create_safe_filename(self, english_name: str, timestamp: str) -> str:
        """安全なファイル名を作成"""
        import re
        # 特殊文字を除去してファイル名作成
        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', english_name)
        safe_name = safe_name[:30]  # 長さ制限
        return f"imagen3_{safe_name}_{timestamp}.jpg"
    
    def create_enhanced_image_prompt(
        self, 
        japanese_name: str, 
        english_name: str, 
        description: str, 
        category: str,
        detailed_description: str = ""
    ) -> str:
        """画像生成用の強化プロンプトを作成"""
        # カテゴリ別のスタイル調整
        category_styles = {
            "Appetizers": "elegant appetizer presentation on fine dining plate, garnished with herbs",
            "Main Dishes": "beautiful main course plating with colorful garnishes and sauce art",
            "Desserts": "artistic dessert presentation with elegant styling and decoration",
            "Beverages": "professional beverage photography with appropriate glassware and lighting",
            "Soups": "warm soup presentation in traditional Japanese bowl with steam rising",
            "Salads": "fresh salad with vibrant colors and textures, beautifully arranged",
            "Noodles": "steaming noodles in authentic Japanese bowl with chopsticks",
            "Sushi": "premium sushi presentation on wooden board with wasabi and ginger",
            "Rice Dishes": "appetizing rice dish in traditional Japanese serving style"
        }
        
        style = category_styles.get(category, "professional Japanese food photography")
        
        # 詳細説明がある場合は優先使用
        description_text = detailed_description if detailed_description else description
        if not description_text:
            description_text = f"Traditional Japanese {category.lower()} dish"
        
        prompt = f"""Professional food photography of {english_name} ({japanese_name}), a Japanese {category.lower()}. 
{description_text[:150]}. 
{style}, restaurant quality, high resolution, appetizing, authentic Japanese cuisine presentation, 
soft natural lighting, shallow depth of field, food styling perfection."""
        
        return prompt
    
    async def generate_single_image(
        self, 
        japanese_name: str, 
        english_name: str, 
        description: str, 
        category: str,
        detailed_description: str = ""
    ) -> dict:
        """単一のメニューアイテムの画像を生成"""
        try:
            # 詳細説明を含むプロンプト作成
            prompt = self.create_enhanced_image_prompt(
                japanese_name, english_name, description, category, detailed_description
            )
            
            if not self.validate_prompt_content(prompt):
                raise ValueError("Invalid prompt content")
            
            # Imagen 3で画像生成
            response = self.imagen_client.models.generate_images(
                model=ai_settings.imagen_model,
                prompt=prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=ai_settings.imagen_number_of_images,
                    aspect_ratio=ai_settings.imagen_aspect_ratio
                )
            )
            
            if response.generated_images:
                # 画像を取得
                generated_image = response.generated_images[0]
                image = Image.open(BytesIO(generated_image.image.image_bytes))
                
                # ファイル名を生成
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = self.create_safe_filename(english_name, timestamp)
                
                # S3ストレージを試行、失敗時はローカル保存
                image_url = await self._save_image_with_fallback(
                    image, filename, japanese_name, english_name, description, 
                    detailed_description, category, prompt
                )
                
                # 結果を返す
                return {
                    "japanese_name": japanese_name,
                    "english_name": english_name,
                    "image_url": image_url,
                    "image_path": f"{base_settings.upload_dir}/{filename}" if not image_url or image_url.startswith('/') else None,
                    "prompt_used": prompt,
                    "generation_success": True,
                    "storage_type": "s3" if image_url and not image_url.startswith('/') else "local",
                    "detailed_description_used": bool(detailed_description)
                }
            else:
                return {
                    "japanese_name": japanese_name,
                    "english_name": english_name,
                    "image_url": None,
                    "error": "No image generated by Imagen 3",
                    "generation_success": False
                }
                
        except Exception as e:
            return {
                "japanese_name": japanese_name,
                "english_name": english_name,
                "image_url": None,
                "error": str(e),
                "generation_success": False
            }
    
    async def generate_images(
        self, 
        final_menu: dict, 
        session_id: Optional[str] = None
    ) -> ImageResult:
        """
        メニューアイテムの画像をImagen 3で生成
        
        Args:
            final_menu: 詳細説明付きメニューデータ
            session_id: セッションID（進行状況通知用）
            
        Returns:
            ImageResult: 画像生成結果
        """
        print("🎨 Starting image generation with Imagen 3...")
        
        # サービス利用可能性チェック
        if not self.is_imagen_available():
            return ImageResult(
                success=True,  # 画像生成はオプショナルなので成功とする
                image_method="imagen3",
                metadata={
                    "skipped_reason": "Imagen 3 not available",
                    "error_type": "service_unavailable",
                    "suggestions": [
                        "Set GEMINI_API_KEY environment variable",
                        "Install required packages: google-genai, pillow",
                        "Enable IMAGE_GENERATION_ENABLED in settings",
                        "Check Gemini API access permissions"
                    ]
                }
            )
        
        # 入力データの妥当性チェック
        if not self.validate_menu_data(final_menu):
            return ImageResult(
                success=False,
                image_method="imagen3",
                error="Invalid menu data",
                metadata={
                    "error_type": "invalid_input",
                    "suggestions": [
                        "Provide valid menu data with descriptions",
                        "Ensure at least one category has menu items",
                        "Check menu data structure format"
                    ]
                }
            )
        
        try:
            images_generated = {}
            total_items = sum(len(items) for items in final_menu.values())
            successful_images = 0
            
            print(f"🖼️ Total items to generate images for: {total_items}")
            print(f"🚀 Parallel image processing enabled with max {processing_settings.image_concurrent_chunk_limit} concurrent chunks")
            
            # カテゴリごとに順次処理（但しチャンク内は並列）
            for category, items in final_menu.items():
                if not items:
                    images_generated[category] = []
                    continue
                
                # カテゴリ内並列処理を実行
                category_results = await self.process_category_parallel(category, items, session_id)
                images_generated[category] = category_results
                
                # 成功した画像数をカウント
                successful_images += sum(1 for img in category_results if img.get("generation_success"))
            
            print(f"🎉 Imagen 3 Image Generation Complete: Generated {successful_images}/{total_items} images")
            
            return ImageResult(
                success=True,
                images_generated=images_generated,
                total_images=successful_images,
                total_items=total_items,
                image_method="imagen3",
                metadata={
                    "provider": "Imagen 3 (Google)",
                    "model": ai_settings.imagen_model,
                    "successful_images": successful_images,
                    "failed_images": total_items - successful_images,
                    "features": [
                        "professional_food_photography",
                        "category_specific_styling",
                        "japanese_cuisine_focus",
                        "high_quality_generation",
                        "parallel_chunked_processing"
                    ]
                }
            )
            
        except Exception as e:
            print(f"❌ Imagen 3 Image Generation Failed: {e}")
            
            return ImageResult(
                success=False,
                image_method="imagen3",
                error=f"Imagen 3 image generation error: {str(e)}",
                metadata={
                    "error_type": self._get_imagen_error_type(e),
                    "original_error": str(e),
                    "suggestions": self._get_imagen_error_suggestions(e),
                    "provider": "Imagen 3 (Google)"
                }
            )
    
    async def process_category_parallel(
        self,
        category: str,
        items: list,
        session_id: Optional[str] = None
    ) -> list:
        """カテゴリ内のアイテムを並列チャンク処理で画像生成"""
        if not items:
            return []
            
        print(f"🎨 Processing category images: {category} ({len(items)} items) - PARALLEL MODE")
        
        # チャンクに分割
        chunk_size = processing_settings.image_processing_chunk_size
        chunks = []
        
        for i in range(0, len(items), chunk_size):
            chunk = items[i:i + chunk_size]
            chunk_number = (i // chunk_size) + 1
            total_chunks = (len(items) + chunk_size - 1) // chunk_size
            chunks.append((chunk, chunk_number, total_chunks))
        
        print(f"  📦 Created {len(chunks)} image chunks for parallel processing")
        
        # 全チャンクを並列で処理
        tasks = []
        for chunk, chunk_number, total_chunks in chunks:
            task = self.process_image_chunk_with_semaphore(
                category, chunk, chunk_number, total_chunks, session_id
            )
            tasks.append(task)
        
        # 並列実行
        print(f"  🚀 Starting {len(tasks)} parallel image chunk tasks...")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 結果を処理
        category_results = []
        successful_chunks = 0
        
        # チャンク番号でソート（元の順序を維持）
        sorted_results = []
        for result in results:
            if isinstance(result, tuple):
                sorted_results.append(result)
            else:
                print(f"  ⚠️ Exception in parallel image processing: {result}")
        
        sorted_results.sort(key=lambda x: x[0])  # chunk_numberでソート
        
        for chunk_number, chunk_result, error in sorted_results:
            if error:
                print(f"  ⚠️ Image chunk {chunk_number} failed: {error}")
            elif chunk_result:
                category_results.extend(chunk_result)
                successful_chunks += 1
        
        print(f"  ✅ Parallel image processing complete: {successful_chunks} successful chunks")
        
        return category_results
    
    async def process_image_chunk_with_semaphore(
        self, 
        category: str, 
        chunk: list, 
        chunk_number: int, 
        total_chunks: int,
        session_id: Optional[str] = None
    ) -> tuple:
        """セマフォを使用して画像チャンクを並列処理"""
        async with self.semaphore:
            try:
                # チャンク処理を実行
                result = await self.process_image_chunk(category, chunk, chunk_number, total_chunks, session_id)
                return (chunk_number, result, None)  # (chunk_number, result, error)
                
            except Exception as e:
                print(f"  ❌ Error in parallel image chunk {chunk_number}/{total_chunks}: {e}")
                return (chunk_number, None, str(e))
    
    async def process_image_chunk(
        self, 
        category: str, 
        chunk: list, 
        chunk_number: int, 
        total_chunks: int,
        session_id: Optional[str] = None
    ) -> list:
        """画像生成チャンクを処理"""
        print(f"  🖼️ Processing image chunk {chunk_number}/{total_chunks} ({len(chunk)} items)")
        
        chunk_results = []
        
        try:
            for i, item in enumerate(chunk):
                if not self.validate_menu_item(item):
                    print(f"    ⚠️ Skipping invalid menu item: {item}")
                    continue
                
                japanese_name = item.get("japanese_name", "N/A")
                english_name = item.get("english_name", "N/A")
                description = item.get("description", "")
                # 詳細説明: OpenAIサービスがdescriptionフィールドに保存しているため、両方をチェック
                detailed_description = item.get("detailed_description", "") or item.get("description", "")
                
                print(f"    🎨 Generating image for: {english_name} (item {i+1}/{len(chunk)})")
                
                # 単一画像生成（詳細説明を含む）
                image_result = await self.generate_single_image(
                    japanese_name, english_name, description, category, detailed_description
                )
                
                chunk_results.append(image_result)
                
                if image_result.get("generation_success"):
                    print(f"      ✅ Image generated successfully: {image_result.get('image_url')}")
                else:
                    print(f"      ❌ Failed to generate image: {image_result.get('error', 'Unknown error')}")
                
                # レート制限対策（チャンク内では短めに）
                if i < len(chunk) - 1:  # 最後のアイテムでない場合のみ待機
                    await asyncio.sleep(ai_settings.image_rate_limit_sleep * 0.5)
            
            print(f"    ✅ Successfully processed image chunk {chunk_number}/{total_chunks}")
            return chunk_results
            
        except Exception as chunk_error:
            print(f"  ⚠️ Image chunk processing error: {chunk_error}")
            print(f"    🔄 Creating fallback results for chunk {chunk_number}")
            
            # エラー時はフォールバック結果を生成
            fallback_results = []
            for item in chunk:
                fallback_results.append({
                    "japanese_name": item.get("japanese_name", "N/A"),
                    "english_name": item.get("english_name", "N/A"),
                    "image_url": None,
                    "error": f"Chunk processing error: {str(chunk_error)}",
                    "generation_success": False
                })
            
            return fallback_results
    
    # ==========================================
    # Utility Methods
    # ==========================================
    
    async def _save_image_with_fallback(
        self,
        image: Image.Image,
        filename: str,
        japanese_name: str,
        english_name: str,
        description: str,
        detailed_description: str,
        category: str,
        prompt: str
    ) -> str:
        """画像を保存（S3優先、失敗時はローカル）"""
        try:
            # まずS3保存を試行
            if s3_storage.is_available():
                # 画像をバイトストリームに変換
                buffer = BytesIO()
                image.save(buffer, format='JPEG', quality=95)
                image_bytes = buffer.getvalue()
                
                # メタデータ作成
                metadata = {
                    'japanese_name': japanese_name,
                    'english_name': english_name,
                    'category': category,
                    'description': description[:200],  # 長さ制限
                    'prompt_used': prompt[:500],  # 長さ制限
                    'generation_service': 'imagen3'
                }
                
                if detailed_description:
                    metadata['detailed_description'] = detailed_description[:200]
                
                # S3にアップロード
                s3_url = await s3_storage.upload_generated_image(
                    image_bytes, filename, metadata
                )
                
                if s3_url:
                    print(f"    ☁️ Image saved to S3: {s3_url}")
                    return s3_url
                
        except Exception as s3_error:
            print(f"    ⚠️ S3 upload failed: {s3_error}")
        
        # S3が失敗した場合はローカル保存
        try:
            local_path = await self._save_locally_with_timestamp(image, filename)
            print(f"    💾 Image saved locally: {local_path}")
            return local_path
            
        except Exception as local_error:
            print(f"    ❌ Local save failed: {local_error}")
            return None
    
    async def _save_locally_with_timestamp(self, image: Image.Image, filename: str) -> str:
        """タイムスタンプ付きでローカル保存"""
        import os
        
        # アップロードディレクトリを確保
        os.makedirs(base_settings.upload_dir, exist_ok=True)
        
        local_path = os.path.join(base_settings.upload_dir, filename)
        
        # 画像を保存
        image.save(local_path, 'JPEG', quality=95)
        
        # 相対パスを返す（URLとして使用）
        return f"/{local_path}"
    
    def _get_vision_error_type(self, error: Exception) -> str:
        """Vision APIエラータイプを判定"""
        error_str = str(error).lower()
        
        if "permission" in error_str or "forbidden" in error_str:
            return "permission_error"
        elif "quota" in error_str or "limit" in error_str:
            return "quota_exceeded"
        elif "network" in error_str or "connection" in error_str:
            return "network_error"
        else:
            return "unknown_error"
    
    def _get_vision_error_suggestions(self, error: Exception) -> List[str]:
        """Vision APIエラーに対する改善提案を取得"""
        error_type = self._get_vision_error_type(error)
        
        suggestions_map = {
            "permission_error": [
                "Google Cloud認証が正しく設定されているか確認してください",
                "サービスアカウントにVision API権限があるか確認してください"
            ],
            "quota_exceeded": [
                "Vision APIクォータを確認してください",
                "しばらく時間をおいてから再試行してください"
            ],
            "network_error": [
                "インターネット接続を確認してください",
                "しばらく時間をおいてから再試行してください"
            ],
            "unknown_error": [
                "画像ファイルが破損していないか確認してください",
                "サポートされている画像形式（JPG、PNG、GIF）を使用してください",
                "しばらく時間をおいてから再試行してください"
            ]
        }
        
        return suggestions_map.get(error_type, suggestions_map["unknown_error"])
    
    def _get_translate_error_type(self, error: Exception) -> str:
        """Translate APIエラータイプを判定"""
        error_str = str(error).lower()
        
        if "quota" in error_str or "limit" in error_str:
            return "quota_exceeded"
        elif "credentials" in error_str or "auth" in error_str:
            return "authentication_error"
        elif "network" in error_str or "connection" in error_str:
            return "network_error"
        else:
            return "unknown_error"
    
    def _get_translate_error_suggestions(self, error: Exception) -> List[str]:
        """Translate APIエラーに対する改善提案を取得"""
        error_type = self._get_translate_error_type(error)
        
        suggestions_map = {
            "quota_exceeded": [
                "Check Google Cloud API quotas",
                "Wait before retrying",
                "Consider upgrading your Google Cloud plan"
            ],
            "authentication_error": [
                "Set GOOGLE_APPLICATION_CREDENTIALS environment variable",
                "Check service account permissions",
                "Ensure Translate API is enabled in Google Cloud Console"
            ],
            "network_error": [
                "Check internet connectivity",
                "Verify Google Cloud API endpoints are accessible",
                "Try again after a short wait"
            ],
            "unknown_error": [
                "Check Google Cloud Translate API status",
                "Verify API key permissions",
                "Try with a smaller batch of menu items"
            ]
        }
        
        return suggestions_map.get(error_type, suggestions_map["unknown_error"])
    
    def _get_imagen_error_type(self, error: Exception) -> str:
        """Imagen APIエラータイプを判定"""
        error_str = str(error).lower()
        
        if "api key" in error_str or "auth" in error_str:
            return "authentication_error"
        elif "quota" in error_str or "limit" in error_str:
            return "quota_exceeded"
        elif "network" in error_str or "connection" in error_str:
            return "network_error"
        else:
            return "unknown_error"
    
    def _get_imagen_error_suggestions(self, error: Exception) -> List[str]:
        """Imagen APIエラーに対する改善提案を取得"""
        error_type = self._get_imagen_error_type(error)
        
        suggestions_map = {
            "authentication_error": [
                "Set GEMINI_API_KEY environment variable",
                "Check Gemini API access permissions",
                "Verify API key is valid"
            ],
            "quota_exceeded": [
                "Check Gemini API quotas",
                "Wait before retrying",
                "Consider upgrading your Gemini plan"
            ],
            "network_error": [
                "Check internet connectivity",
                "Verify Gemini API endpoints are accessible",
                "Try again after a short wait"
            ],
            "unknown_error": [
                "Check Gemini API status",
                "Verify API key permissions",
                "Enable IMAGE_GENERATION_ENABLED in settings"
            ]
        }
        
        return suggestions_map.get(error_type, suggestions_map["unknown_error"])
    
    def _get_gemini_error_type(self, error: Exception) -> str:
        """Gemini OCR APIエラータイプを判定"""
        error_str = str(error).lower()
        
        if "api" in error_str and "key" in error_str:
            return "api_key_error"
        elif "quota" in error_str or "limit" in error_str:
            return "quota_exceeded"
        elif "permission" in error_str or "forbidden" in error_str:
            return "permission_error"
        elif "network" in error_str or "connection" in error_str:
            return "network_error"
        else:
            return "unknown_error"
    
    def _get_gemini_error_suggestions(self, error: Exception) -> List[str]:
        """Gemini OCR APIエラーに対する改善提案を取得"""
        error_type = self._get_gemini_error_type(error)
        
        suggestions_map = {
            "api_key_error": [
                "GEMINI_API_KEYが正しく設定されているか確認してください",
                "Gemini APIキーが有効であることを確認してください"
            ],
            "quota_exceeded": [
                "Gemini APIクォータを確認してください",
                "しばらく時間をおいてから再試行してください"
            ],
            "permission_error": [
                "Gemini API権限を確認してください",
                "APIキーが正しく設定されているか確認してください"
            ],
            "network_error": [
                "インターネット接続を確認してください",
                "しばらく時間をおいてから再試行してください"
            ],
            "unknown_error": [
                "画像ファイルが破損していないか確認してください",
                "サポートされている画像形式（JPG、PNG、GIF、WEBP）を使用してください",
                "しばらく時間をおいてから再試行してください"
            ]
        }
        
        return suggestions_map.get(error_type, suggestions_map["unknown_error"]) 
import asyncio
from typing import Optional

try:
    from google.cloud import translate_v2 as translate
except ImportError:
    translate = None

from app.core.config import settings
from .base import BaseTranslationService, TranslationResult, TranslationProvider

class GoogleTranslateService(BaseTranslationService):
    """Google Translate APIを使用した翻訳サービス"""
    
    def __init__(self):
        super().__init__()
        self.provider = TranslationProvider.GOOGLE_TRANSLATE
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Google Translate APIクライアントを初期化"""
        try:
            if not translate:
                print("❌ google-cloud-translate package not installed. Install with: pip install google-cloud-translate")
                return
            
            # Google Cloud認証情報を取得
            google_credentials = self._get_google_credentials()
            
            if google_credentials:
                self.client = translate.Client(credentials=google_credentials)
                print("🔧 Google Translate Service initialized with credentials")
            else:
                # デフォルト認証を試行
                try:
                    self.client = translate.Client()
                    print("🔧 Google Translate Service initialized with default auth")
                except Exception as e:
                    print(f"⚠️ Failed to initialize Google Translate with default auth: {e}")
                    self.client = None
                
        except Exception as e:
            print(f"❌ Failed to initialize Google Translate Service: {e}")
            self.client = None
    
    def _get_google_credentials(self):
        """Google Cloud認証情報を取得"""
        try:
            if settings.GOOGLE_CREDENTIALS_JSON:
                import json
                from google.oauth2 import service_account
                
                credentials_info = json.loads(settings.GOOGLE_CREDENTIALS_JSON)
                return service_account.Credentials.from_service_account_info(credentials_info)
            return None
        except Exception as e:
            print(f"⚠️ Failed to load Google credentials: {e}")
            return None
    
    def is_available(self) -> bool:
        """サービスが利用可能かチェック"""
        return self.client is not None
    
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
            result = self.client.translate(
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
            result = self.client.translate(
                item_name,
                source_language='ja',
                target_language='en'
            )
            english_name = result['translatedText']
            return self.clean_translated_text(english_name)
        except Exception as e:
            print(f"  ⚠️ Translation failed for '{item_name}': {e}")
            return item_name  # フォールバック
    
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
        if not self.is_available():
            return TranslationResult(
                success=False,
                translation_method="google_translate",
                error="Google Translate API is not available",
                metadata={
                    "error_type": "service_unavailable",
                    "suggestions": [
                        "Set GOOGLE_CREDENTIALS_JSON environment variable",
                        "Install google-cloud-translate package: pip install google-cloud-translate",
                        "Check Google Cloud API permissions",
                        "Verify internet connectivity"
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
                
                # 進行状況を送信（カテゴリー開始）
                if session_id:
                    # send_progressを動的にインポート（循環インポート回避）
                    from app.services.realtime import send_progress
                    await send_progress(
                        session_id, 3, "active", 
                        f"🌍 Translating {japanese_category}...",
                        {
                            "processing_category": japanese_category,
                            "total_categories": len(categorized_data),
                            "translatedCategories": translated_categories  # リアルタイム反映用
                        }
                    )
                
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
                    
                    # アイテム単位でのリアルタイム更新（3つごと、またはカテゴリー完了時）
                    if (len(translated_items) % 3 == 0) or (item_index == len(items) - 1):
                        if session_id:
                            # 現在のカテゴリーの部分的な翻訳結果を送信
                            current_translated = translated_categories.copy()
                            current_translated[english_category] = translated_items.copy()
                            
                            progress_percent = int((processed_items / total_items) * 100) if total_items > 0 else 100
                            
                            await send_progress(
                                session_id, 3, "active", 
                                f"🌍 {japanese_category}: {len(translated_items)}/{len(items)} items translated",
                                {
                                    "progress_percent": progress_percent,
                                    "processing_category": japanese_category,
                                    "translatedCategories": current_translated,  # リアルタイム更新
                                    "category_progress": f"{len(translated_items)}/{len(items)}"
                                }
                            )
                    
                    # レート制限対策
                    await asyncio.sleep(0.1)
                
                if translated_items:
                    translated_categories[english_category] = translated_items
                    
                    # カテゴリー完了通知（リアルタイム反映）
                    if session_id:
                        progress_percent = int((processed_items / total_items) * 100) if total_items > 0 else 100
                        await send_progress(
                            session_id, 3, "active", 
                            f"✅ Completed {japanese_category} ({len(translated_items)} items)",
                            {
                                "progress_percent": progress_percent,
                                "translatedCategories": translated_categories,  # 完全な翻訳結果
                                "category_completed": japanese_category,
                                "category_items": len(translated_items)
                            }
                        )
            
            print(f"✅ Google Translate Complete: Translated {len(translated_categories)} categories")
            
            # 最終的な翻訳完了通知（show_translated_menuフラグ付き）
            if session_id:
                await send_progress(
                    session_id, 3, "completed", 
                    "✅ Translation Complete! All menu items translated.",
                    {
                        "translatedCategories": translated_categories,
                        "total_translated_items": total_items,
                        "total_categories": len(translated_categories),
                        "translation_method": "google_translate",
                        "show_translated_menu": True,  # UIにメニュー表示を指示
                        "completion_status": "success"
                    }
                )
            
            return TranslationResult(
                success=True,
                translated_categories=translated_categories,
                translation_method="google_translate",
                metadata={
                    "total_items": total_items,
                    "total_categories": len(translated_categories),
                    "provider": "Google Translate API",
                    "features": [
                        "real_time_progress",
                        "category_mapping",
                        "html_entity_cleanup",
                        "rate_limiting"
                    ]
                }
            )
            
        except Exception as e:
            print(f"❌ Google Translate Failed: {e}")
            
            # エラータイプの判定
            error_type = "unknown_error"
            suggestions = []
            
            if "quota" in str(e).lower() or "limit" in str(e).lower():
                error_type = "quota_exceeded"
                suggestions = [
                    "Check Google Cloud API quotas",
                    "Wait before retrying",
                    "Consider upgrading your Google Cloud plan"
                ]
            elif "credentials" in str(e).lower() or "auth" in str(e).lower():
                error_type = "authentication_error"
                suggestions = [
                    "Check GOOGLE_CREDENTIALS_JSON environment variable",
                    "Verify Google Cloud credentials are valid",
                    "Ensure Translate API is enabled in Google Cloud Console"
                ]
            elif "network" in str(e).lower() or "connection" in str(e).lower():
                error_type = "network_error"
                suggestions = [
                    "Check internet connectivity",
                    "Verify Google Cloud API endpoints are accessible",
                    "Try again after a short wait"
                ]
            else:
                suggestions = [
                    "Check Google Cloud Translate API status",
                    "Verify API key permissions",
                    "Try with a smaller batch of menu items"
                ]
            
            return TranslationResult(
                success=False,
                translation_method="google_translate",
                error=f"Google Translate error: {str(e)}",
                metadata={
                    "error_type": error_type,
                    "original_error": str(e),
                    "suggestions": suggestions,
                    "provider": "Google Translate API",
                    "total_items": sum(len(items) for items in categorized_data.values()),
                    "processed_items": processed_items if 'processed_items' in locals() else 0
                }
            )

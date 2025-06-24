from typing import Optional, Dict

from .base import BaseTranslationService, TranslationResult, TranslationProvider
from .google_translate import GoogleTranslateService
from .openai import OpenAITranslationService

class TranslationServiceManager:
    """翻訳サービスの統合管理クラス"""
    
    def __init__(self):
        self.services = {}
        self._initialize_services()
    
    def _initialize_services(self):
        """利用可能な翻訳サービスを初期化"""
        # Google Translateサービス（メイン翻訳エンジン）
        try:
            google_service = GoogleTranslateService()
            self.services[TranslationProvider.GOOGLE_TRANSLATE] = google_service
            status = "✅ Available" if google_service.is_available() else "❌ Unavailable"
            print(f"🌍 Google Translate Service: {status}")
        except Exception as e:
            print(f"❌ Failed to initialize Google Translate Service: {e}")
        
        # OpenAIサービス（フォールバック翻訳エンジン）
        try:
            openai_service = OpenAITranslationService()
            self.services[TranslationProvider.OPENAI] = openai_service
            status = "✅ Available" if openai_service.is_available() else "❌ Unavailable"
            print(f"🔄 OpenAI Translation Service (Fallback): {status}")
        except Exception as e:
            print(f"❌ Failed to initialize OpenAI Translation Service: {e}")
    
    def get_service(self, provider: TranslationProvider) -> Optional[BaseTranslationService]:
        """指定されたプロバイダーのサービスを取得"""
        return self.services.get(provider)
    
    def get_primary_service(self) -> Optional[BaseTranslationService]:
        """Google Translate翻訳サービスを取得（メインエンジン）"""
        google_service = self.services.get(TranslationProvider.GOOGLE_TRANSLATE)
        if google_service and google_service.is_available():
            return google_service
        return None
    
    def get_fallback_service(self) -> Optional[BaseTranslationService]:
        """OpenAI翻訳サービスを取得（フォールバックエンジン）"""
        openai_service = self.services.get(TranslationProvider.OPENAI)
        if openai_service and openai_service.is_available():
            return openai_service
        return None
    
    def get_available_services(self) -> list:
        """利用可能なサービスのリストを取得"""
        return [
            service for service in self.services.values() 
            if service.is_available()
        ]
    
    def get_service_status(self) -> Dict[str, Dict]:
        """全サービスの状態を取得"""
        status = {}
        
        for provider, service in self.services.items():
            try:
                service_info = service.get_service_info()
                status[provider.value] = {
                    "available": service.is_available(),
                    "service_name": service.service_name,
                    "display_name": self._get_display_name(provider),
                    "provider": provider.value,
                    "capabilities": service_info.get("capabilities", []),
                    "supported_languages": service_info.get("supported_languages", {}),
                    "role": "primary" if provider == TranslationProvider.GOOGLE_TRANSLATE else "fallback"
                }
                
                if not service.is_available():
                    status[provider.value]["error"] = "Service not available"
                    
            except Exception as e:
                status[provider.value] = {
                    "available": False,
                    "service_name": service.service_name,
                    "provider": provider.value,
                    "error": str(e)
                }
        
        return status
    
    def _get_display_name(self, provider: TranslationProvider) -> str:
        """プロバイダーの表示名を取得"""
        if provider == TranslationProvider.GOOGLE_TRANSLATE:
            return "Google Translate API"
        elif provider == TranslationProvider.OPENAI:
            from app.core.config import settings
            return f"OpenAI {settings.OPENAI_MODEL}"
        return provider.value
    
    async def translate_with_fallback(
        self, 
        categorized_data: Dict, 
        session_id: Optional[str] = None
    ) -> TranslationResult:
        """
        Google Translateメイン、OpenAIフォールバックで翻訳実行
        
        Args:
            categorized_data: カテゴリ分類されたメニューデータ
            session_id: セッションID（進行状況通知用）
            
        Returns:
            TranslationResult: 翻訳結果
        """
        # Google Translateメイン処理
        google_service = self.get_primary_service()
        
        if google_service:
            print(f"🌍 Starting translation with Google Translate (Primary)")
            
            try:
                result = await google_service.translate_menu(categorized_data, session_id)
                
                if result.success:
                    print(f"✅ Google Translate successful - {result.metadata.get('total_items', 0)} items translated")
                    # 成功した場合はGoogle Translate専用情報を追加
                    result.metadata.update({
                        "successful_service": "GoogleTranslateService",
                        "translation_mode": "google_translate_primary",
                        "fallback_used": False
                    })
                    return result
                else:
                    print(f"❌ Google Translate failed: {result.error}")
                    print("🔄 Attempting OpenAI fallback...")
                    
            except Exception as e:
                print(f"❌ Exception in Google Translate: {str(e)}")
                print("🔄 Attempting OpenAI fallback...")
        else:
            print("⚠️ Google Translate not available, starting with OpenAI fallback...")
        
        # OpenAIフォールバック処理
        openai_service = self.get_fallback_service()
        
        if openai_service:
            try:
                result = await openai_service.translate_menu(categorized_data, session_id)
                
                if result.success:
                    print(f"✅ OpenAI fallback successful - {result.metadata.get('total_items', 0)} items translated")
                    # フォールバック成功情報を追加
                    result.metadata.update({
                        "successful_service": "OpenAITranslationService",
                        "translation_mode": "openai_fallback",
                        "fallback_used": True,
                        "primary_service_failed": True
                    })
                    return result
                else:
                    print(f"❌ OpenAI fallback also failed: {result.error}")
                    return result
                    
            except Exception as e:
                print(f"❌ Exception in OpenAI fallback: {str(e)}")
                return TranslationResult(
                    success=False,
                    translation_method="openai_fallback",
                    error=f"OpenAI fallback service error: {str(e)}",
                    metadata={
                        "error_type": "fallback_service_exception",
                        "service": "OpenAITranslationService",
                        "original_error": str(e),
                        "fallback_used": True,
                        "primary_service_failed": True,
                        "suggestions": [
                            "Check both Google Translate and OpenAI API configurations",
                            "Verify API keys and permissions",
                            "Check for temporary service issues",
                            "Ensure input data is valid"
                        ]
                    }
                )
        
        # 両方のサービスが利用できない場合
        from app.services.auth.unified_auth import get_auth_troubleshooting
        
        return TranslationResult(
            success=False,
            translation_method="none_available", 
            error="Both Google Translate and OpenAI translation services are unavailable",
            metadata={
                "error_type": "all_services_unavailable",
                "services_checked": ["google_translate", "openai_fallback"],
                "suggestions": get_auth_troubleshooting() + [
                    "",
                    "Additional steps:",
                    "Set OPENAI_API_KEY environment variable", 
                    "Install required packages: google-cloud-translate, openai",
                    "Check API access permissions and quotas",
                    "Verify internet connectivity"
                ]
            }
        )

# サービスマネージャーのインスタンス化
translation_manager = TranslationServiceManager()

# 便利な関数をエクスポート
async def translate_menu(
    categorized_data: Dict, 
    session_id: Optional[str] = None
) -> TranslationResult:
    """
    Google Translateメイン、OpenAIフォールバックで翻訳する便利関数
    
    Args:
        categorized_data: カテゴリ分類されたメニューデータ
        session_id: セッションID（進行状況通知用）
        
    Returns:
        TranslationResult: 翻訳結果
    """
    return await translation_manager.translate_with_fallback(categorized_data, session_id)

def get_translation_service_status() -> Dict[str, Dict]:
    """翻訳サービスの状態を取得する便利関数"""
    return translation_manager.get_service_status()

def get_supported_languages() -> Dict:
    """サポートされている言語情報を取得"""
    primary_service = translation_manager.get_primary_service()
    if primary_service:
        return primary_service.get_service_info().get("supported_languages", {})
    return {"source": ["Japanese"], "target": ["English"]}

def get_category_mapping() -> Dict[str, str]:
    """カテゴリ名のマッピングを取得"""
    return {
        "前菜・冷菜": "Appetizers & Cold Dishes",
        "サラダ": "Salads", 
        "スープ": "Soups",
        "メインディッシュ": "Main Dishes",
        "魚料理": "Fish & Seafood",
        "肉料理": "Meat Dishes",
        "パスタ・麺類": "Pasta & Noodles",
        "ライス・ご飯物": "Rice Dishes",
        "デザート": "Desserts",
        "ドリンク・飲み物": "Beverages",
        "その他": "Others"
    }

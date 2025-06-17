from typing import Optional, Dict
from enum import Enum

from .base import BaseCategoryService, CategoryResult
from .openai import OpenAICategoryService

class CategoryProvider(str, Enum):
    """カテゴリ分類プロバイダーの定義"""
    OPENAI = "openai"

class CategoryServiceManager:
    """カテゴリ分類サービスの統合管理クラス"""
    
    def __init__(self):
        self.services = {}
        self._initialize_services()
    
    def _initialize_services(self):
        """利用可能なカテゴリ分類サービスを初期化"""
        # OpenAIサービス（メインカテゴリ分類エンジン）
        try:
            openai_service = OpenAICategoryService()
            self.services[CategoryProvider.OPENAI] = openai_service
            status = "✅ Available" if openai_service.is_available() else "❌ Unavailable"
            print(f"🏷️ OpenAI Category Service: {status}")
        except Exception as e:
            print(f"❌ Failed to initialize OpenAI Category Service: {e}")
    
    def get_service(self, provider: CategoryProvider) -> Optional[BaseCategoryService]:
        """指定されたプロバイダーのサービスを取得"""
        return self.services.get(provider)
    
    def get_preferred_service(self) -> Optional[BaseCategoryService]:
        """OpenAIカテゴリ分類サービスを取得（メインエンジン）"""
        # OpenAI専用モード: OpenAIのみ使用
        openai_service = self.services.get(CategoryProvider.OPENAI)
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
                    "display_name": f"OpenAI {settings.OPENAI_MODEL}" if provider == CategoryProvider.OPENAI else service.service_name,
                    "capabilities": service_info.get("capabilities", []),
                    "default_categories": service_info.get("default_categories", [])
                }
                
                if not service.is_available():
                    status[provider.value]["error"] = "Service not available"
                    
            except Exception as e:
                status[provider.value] = {
                    "available": False,
                    "service_name": service.service_name,
                    "error": str(e)
                }
        
        return status
    
    async def categorize_with_openai(
        self, 
        extracted_text: str, 
        session_id: Optional[str] = None
    ) -> CategoryResult:
        """
        OpenAIでメニューテキストをカテゴリ分類（OpenAI専用モード）
        
        Args:
            extracted_text: OCRで抽出されたメニューテキスト
            session_id: セッションID（進行状況通知用）
            
        Returns:
            CategoryResult: 分類結果
        """
        # OpenAIカテゴリ分類サービスを取得
        openai_service = self.get_service(CategoryProvider.OPENAI)
        
        # OpenAIサービスが利用できない場合
        if not openai_service or not openai_service.is_available():
            return CategoryResult(
                success=False,
                error="OpenAI categorization service is not available",
                metadata={
                    "error_type": "openai_unavailable",
                    "service": "openai_exclusive_mode",
                    "suggestions": [
                        "Set OPENAI_API_KEY environment variable",
                        "Install openai package: pip install openai",
                        "Check OpenAI API access permissions",
                        "Verify internet connectivity"
                    ]
                }
            )
        
        try:
            print(f"🏷️ Starting categorization with OpenAI Function Calling")
            
            # OpenAI カテゴリ分類を実行
            result = await openai_service.categorize_menu(extracted_text, session_id)
            
            if result.success:
                print(f"✅ OpenAI categorization successful - {result.metadata.get('total_items', 0)} items categorized")
                # 成功した場合はOpenAI専用情報を追加
                result.metadata.update({
                    "successful_service": "OpenAICategoryService", 
                    "categorization_mode": "openai_exclusive",
                    "model": settings.OPENAI_MODEL,
                    "features": ["function_calling", "structured_output", "japanese_text", "menu_specialized"]
                })
                return result
            else:
                print(f"❌ OpenAI categorization failed: {result.error}")
                # エラー情報を強化
                result.metadata.update({
                    "categorization_mode": "openai_exclusive",
                    "model": settings.OPENAI_MODEL,
                    "fallback_available": False
                })
                return result
                
        except Exception as e:
            print(f"❌ Exception in OpenAI categorization: {str(e)}")
            return CategoryResult(
                success=False,
                error=f"OpenAI categorization service error: {str(e)}",
                metadata={
                    "error_type": "openai_service_exception",
                    "service": "OpenAICategoryService",
                    "categorization_mode": "openai_exclusive",
                    "original_error": str(e),
                    "suggestions": [
                        "Check OPENAI_API_KEY is valid",
                        "Verify OpenAI API access and quotas",
                        "Check for temporary service issues",
                        "Ensure input text is valid Japanese menu text"
                    ]
                }
            )

# サービスマネージャーのインスタンス化
from app.core.config import settings
category_manager = CategoryServiceManager()

# 便利な関数をエクスポート（OpenAI専用）
async def categorize_menu(
    extracted_text: str, 
    session_id: Optional[str] = None
) -> CategoryResult:
    """
    OpenAIでメニューテキストをカテゴリ分類する便利関数（OpenAI専用モード）
    
    Args:
        extracted_text: OCRで抽出されたメニューテキスト
        session_id: セッションID（進行状況通知用）
        
    Returns:
        CategoryResult: 分類結果
    """
    return await category_manager.categorize_with_openai(extracted_text, session_id)

def get_category_service_status() -> Dict[str, Dict]:
    """カテゴリ分類サービスの状態を取得する便利関数（OpenAI専用モード）"""
    return category_manager.get_service_status()

def get_default_categories() -> list:
    """デフォルトのカテゴリリストを取得"""
    openai_service = category_manager.get_service(CategoryProvider.OPENAI)
    if openai_service:
        return openai_service.get_default_categories()
    return ["前菜", "メイン", "ドリンク", "デザート"]

# エクスポート
__all__ = [
    "CategoryResult",
    "CategoryProvider", 
    "categorize_menu",
    "get_category_service_status",
    "get_default_categories"
]

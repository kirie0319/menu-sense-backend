from typing import Optional, Dict

from .base import BaseDescriptionService, DescriptionResult, DescriptionProvider
from .openai import OpenAIDescriptionService

class DescriptionServiceManager:
    """詳細説明サービスの統合管理クラス"""
    
    def __init__(self):
        self.services = {}
        self._initialize_services()
    
    def _initialize_services(self):
        """利用可能な詳細説明サービスを初期化"""
        # OpenAIサービス（メイン詳細説明エンジン）
        try:
            openai_service = OpenAIDescriptionService()
            self.services[DescriptionProvider.OPENAI] = openai_service
            status = "✅ Available" if openai_service.is_available() else "❌ Unavailable"
            print(f"📝 OpenAI Description Service: {status}")
        except Exception as e:
            print(f"❌ Failed to initialize OpenAI Description Service: {e}")
    
    def get_service(self, provider: DescriptionProvider) -> Optional[BaseDescriptionService]:
        """指定されたプロバイダーのサービスを取得"""
        return self.services.get(provider)
    
    def get_primary_service(self) -> Optional[BaseDescriptionService]:
        """OpenAI詳細説明サービスを取得（メインエンジン）"""
        openai_service = self.services.get(DescriptionProvider.OPENAI)
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
                    "supported_categories": service_info.get("supported_categories", []),
                    "description_features": service_info.get("description_features", []),
                    "role": "primary"
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
    
    def _get_display_name(self, provider: DescriptionProvider) -> str:
        """プロバイダーの表示名を取得"""
        if provider == DescriptionProvider.OPENAI:
            from app.core.config import settings
            return f"OpenAI {settings.OPENAI_MODEL}"
        return provider.value
    
    async def add_descriptions_with_openai(
        self, 
        translated_data: Dict, 
        session_id: Optional[str] = None
    ) -> DescriptionResult:
        """
        OpenAIで詳細説明を追加
        
        Args:
            translated_data: 翻訳されたメニューデータ
            session_id: セッションID（進行状況通知用）
            
        Returns:
            DescriptionResult: 詳細説明生成結果
        """
        # OpenAI詳細説明サービスを取得
        openai_service = self.get_primary_service()
        
        if openai_service:
            print(f"📝 Starting description generation with OpenAI (Primary)")
            
            try:
                result = await openai_service.add_descriptions(translated_data, session_id)
                
                if result.success:
                    print(f"✅ OpenAI description generation successful - {result.metadata.get('total_items', 0)} items processed")
                    # 成功した場合はOpenAI専用情報を追加
                    result.metadata.update({
                        "successful_service": "OpenAIDescriptionService",
                        "description_mode": "openai_primary",
                        "fallback_used": False
                    })
                    return result
                else:
                    print(f"❌ OpenAI description generation failed: {result.error}")
                    return result
                    
            except Exception as e:
                print(f"❌ Exception in OpenAI description generation: {str(e)}")
                return DescriptionResult(
                    success=False,
                    description_method="openai",
                    error=f"OpenAI description service error: {str(e)}",
                    metadata={
                        "error_type": "service_exception",
                        "service": "OpenAIDescriptionService",
                        "original_error": str(e),
                        "suggestions": [
                            "Check OpenAI API configuration",
                            "Verify API key and permissions",
                            "Check for temporary service issues",
                            "Ensure input data is valid"
                        ]
                    }
                )
        
        # OpenAIサービスが利用できない場合
        return DescriptionResult(
            success=False,
            description_method="none_available", 
            error="OpenAI description service is unavailable",
            metadata={
                "error_type": "service_unavailable",
                "services_checked": ["openai"],
                "suggestions": [
                    "Set OPENAI_API_KEY environment variable",
                    "Install required packages: openai",
                    "Check OpenAI API access permissions and quotas",
                    "Verify internet connectivity"
                ]
            }
        )
    
    def get_supported_categories(self) -> list:
        """サポートされているカテゴリ一覧を取得"""
        primary_service = self.get_primary_service()
        if primary_service:
            return primary_service.get_service_info().get("supported_categories", [])
        return ["Appetizers", "Main Dishes", "Drinks", "Desserts"]
    
    def get_description_features(self) -> list:
        """詳細説明の特徴一覧を取得"""
        primary_service = self.get_primary_service()
        if primary_service:
            return primary_service.get_service_info().get("description_features", [])
        return ["cooking_methods", "ingredients", "flavor_profiles"]
    
    def get_example_descriptions(self) -> Dict[str, str]:
        """説明例を取得"""
        primary_service = self.get_primary_service()
        if primary_service:
            return primary_service.get_example_descriptions()
        return {}

# サービスマネージャーのインスタンス化
description_manager = DescriptionServiceManager()

# 便利な関数をエクスポート
async def add_descriptions(
    translated_data: Dict, 
    session_id: Optional[str] = None
) -> DescriptionResult:
    """
    OpenAIで詳細説明を追加する便利関数
    
    Args:
        translated_data: 翻訳されたメニューデータ
        session_id: セッションID（進行状況通知用）
        
    Returns:
        DescriptionResult: 詳細説明生成結果
    """
    return await description_manager.add_descriptions_with_openai(translated_data, session_id)

def get_description_service_status() -> Dict[str, Dict]:
    """詳細説明サービスの状態を取得する便利関数"""
    return description_manager.get_service_status()

def get_supported_categories() -> list:
    """サポートされているカテゴリを取得"""
    return description_manager.get_supported_categories()

def get_description_features() -> list:
    """詳細説明の特徴を取得"""
    return description_manager.get_description_features()

def get_example_descriptions() -> Dict[str, str]:
    """説明例を取得"""
    return description_manager.get_example_descriptions()

# エクスポート
__all__ = [
    "DescriptionResult",
    "DescriptionProvider",
    "add_descriptions",
    "get_description_service_status", 
    "get_supported_categories",
    "get_description_features",
    "get_example_descriptions"
]

from typing import Optional, Dict

from .base import BaseImageService, ImageResult, ImageProvider
from .imagen3 import Imagen3Service

class ImageServiceManager:
    """画像生成サービスの統合管理クラス"""
    
    def __init__(self):
        self.services = {}
        self._initialize_services()
    
    def _initialize_services(self):
        """利用可能な画像生成サービスを初期化"""
        # Imagen 3サービス（メイン画像生成エンジン）
        try:
            imagen3_service = Imagen3Service()
            self.services[ImageProvider.IMAGEN3] = imagen3_service
            status = "✅ Available" if imagen3_service.is_available() else "❌ Unavailable"
            print(f"🎨 Imagen 3 Image Service: {status}")
        except Exception as e:
            print(f"❌ Failed to initialize Imagen 3 Image Service: {e}")
    
    def get_service(self, provider: ImageProvider) -> Optional[BaseImageService]:
        """指定されたプロバイダーのサービスを取得"""
        return self.services.get(provider)
    
    def get_primary_service(self) -> Optional[BaseImageService]:
        """Imagen 3画像生成サービスを取得（メインエンジン）"""
        imagen3_service = self.services.get(ImageProvider.IMAGEN3)
        if imagen3_service and imagen3_service.is_available():
            return imagen3_service
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
                    "image_features": service_info.get("image_features", []),
                    "role": "primary"
                }
                
                # Imagen 3固有の情報を追加
                if provider == ImageProvider.IMAGEN3:
                    status[provider.value].update({
                        "model": service_info.get("model", "unknown"),
                        "aspect_ratio": service_info.get("aspect_ratio", "1:1"),
                        "image_format": service_info.get("image_format", "PNG"),
                        "provider_name": service_info.get("provider_name", "Google Imagen 3")
                    })
                
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
    
    def _get_display_name(self, provider: ImageProvider) -> str:
        """プロバイダーの表示名を取得"""
        if provider == ImageProvider.IMAGEN3:
            from app.core.config import settings
            return f"Imagen 3 ({settings.IMAGEN_MODEL})"
        return provider.value
    
    async def generate_images_with_imagen3(
        self, 
        final_menu: Dict, 
        session_id: Optional[str] = None
    ) -> ImageResult:
        """
        Imagen 3で画像生成
        
        Args:
            final_menu: 詳細説明付きメニューデータ
            session_id: セッションID（進行状況通知用）
            
        Returns:
            ImageResult: 画像生成結果
        """
        # Imagen 3画像生成サービスを取得
        imagen3_service = self.get_primary_service()
        
        if imagen3_service:
            print(f"🎨 Starting image generation with Imagen 3 (Primary)")
            
            try:
                result = await imagen3_service.generate_images(final_menu, session_id)
                
                if result.success:
                    print(f"✅ Imagen 3 image generation successful - {result.total_images} images generated")
                    # 成功した場合はImagen 3専用情報を追加
                    result.metadata.update({
                        "successful_service": "Imagen3Service",
                        "image_mode": "imagen3_primary",
                        "generation_completed": True
                    })
                    return result
                else:
                    print(f"❌ Imagen 3 image generation failed: {result.error}")
                    return result
                    
            except Exception as e:
                print(f"❌ Exception in Imagen 3 image generation: {str(e)}")
                return ImageResult(
                    success=False,
                    image_method="imagen3",
                    error=f"Imagen 3 image service error: {str(e)}",
                    metadata={
                        "error_type": "service_exception",
                        "service": "Imagen3Service",
                        "original_error": str(e),
                        "suggestions": [
                            "Check Imagen 3 API configuration",
                            "Verify API key and permissions",
                            "Check for temporary service issues",
                            "Ensure menu data is valid"
                        ]
                    }
                )
        
        # Imagen 3サービスが利用できない場合（スキップモード）
        return ImageResult(
            success=True,  # 画像生成はオプショナルなので成功とする
            image_method="none_available", 
            metadata={
                "skipped_reason": "Imagen 3 image service is unavailable",
                "error_type": "service_unavailable",
                "services_checked": ["imagen3"],
                "suggestions": [
                    "Set GEMINI_API_KEY environment variable",
                    "Install required packages: google-genai, pillow",
                    "Enable IMAGE_GENERATION_ENABLED in settings",
                    "Check Imagen 3 API access permissions and quotas",
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
    
    def get_image_features(self) -> list:
        """画像生成の特徴一覧を取得"""
        primary_service = self.get_primary_service()
        if primary_service:
            return primary_service.get_service_info().get("image_features", [])
        return ["professional_lighting", "appetizing_appearance", "clean_background"]
    
    def get_category_styles(self) -> Dict[str, str]:
        """カテゴリ別スタイル定義を取得"""
        primary_service = self.get_primary_service()
        if primary_service:
            return primary_service.get_category_styles()
        return {}
    
    def get_supported_styles(self) -> Dict:
        """サポートされているスタイル一覧を取得"""
        primary_service = self.get_primary_service()
        if primary_service and hasattr(primary_service, 'get_supported_styles'):
            return primary_service.get_supported_styles()
        return {}
    
    def combine_menu_with_images(self, final_menu: Dict, images_generated: Dict) -> Dict:
        """最終メニューと生成された画像を統合"""
        primary_service = self.get_primary_service()
        if primary_service:
            return primary_service.combine_menu_with_images(final_menu, images_generated)
        
        # サービスが利用できない場合のフォールバック
        combined_menu = {}
        for category, items in final_menu.items():
            combined_items = []
            for item in items:
                combined_item = item.copy()
                combined_item["image_url"] = None
                combined_item["image_generated"] = False
                combined_item["image_prompt"] = None
                combined_item["image_error"] = "Image generation service not available"
                combined_items.append(combined_item)
            combined_menu[category] = combined_items
        return combined_menu
    
    def get_generation_statistics(self, final_menu: Dict, images_generated: Dict) -> Dict:
        """画像生成統計を取得"""
        primary_service = self.get_primary_service()
        if primary_service:
            return primary_service.extract_generation_statistics(final_menu, images_generated)
        return {
            "input_statistics": {"total_items": 0},
            "output_statistics": {"successful_images": 0},
            "success_rate": 0,
            "processing_completeness": 0
        }

# サービスマネージャーのインスタンス化
image_manager = ImageServiceManager()

# 便利な関数をエクスポート
async def generate_images(
    final_menu: Dict, 
    session_id: Optional[str] = None
) -> ImageResult:
    """
    ⚠️ **DEPRECATED**: この関数は非推奨です。代わりに非同期処理 `/api/v1/image/generate-async` を使用してください。
    
    Imagen 3で画像生成する便利関数（同期処理 - 将来削除予定）
    
    Args:
        final_menu: 詳細説明付きメニューデータ
        session_id: セッションID（進行状況通知用）
        
    Returns:
        ImageResult: 画像生成結果
        
    Note:
        この関数は互換性のためにのみ残されています。
        新しい実装では AsyncImageManager (/generate-async) を使用することを強く推奨します。
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # 非推奨警告を出力
    logger.warning(
        "⚠️ DEPRECATED: generate_images() is deprecated and will be removed in future versions. "
        "Please use AsyncImageManager (/api/v1/image/generate-async) for new implementations."
    )
    logger.warning(
        f"📊 Called with {sum(len(items) for items in final_menu.values())} items. "
        "Consider using async processing for better performance and scalability."
    )
    
    return await image_manager.generate_images_with_imagen3(final_menu, session_id)

def get_image_service_status() -> Dict[str, Dict]:
    """画像生成サービスの状態を取得する便利関数"""
    return image_manager.get_service_status()

def get_supported_categories() -> list:
    """サポートされているカテゴリを取得"""
    return image_manager.get_supported_categories()

def get_image_features() -> list:
    """画像生成の特徴を取得"""
    return image_manager.get_image_features()

def get_category_styles() -> Dict[str, str]:
    """カテゴリ別スタイルを取得"""
    return image_manager.get_category_styles()

def get_supported_styles() -> Dict:
    """サポートされているスタイル一覧を取得"""
    return image_manager.get_supported_styles()

def combine_menu_with_images(final_menu: Dict, images_generated: Dict) -> Dict:
    """最終メニューと生成された画像を統合"""
    return image_manager.combine_menu_with_images(final_menu, images_generated)

# エクスポート
__all__ = [
    "ImageResult",
    "ImageProvider",
    "generate_images",
    "get_image_service_status", 
    "get_supported_categories",
    "get_image_features",
    "get_category_styles",
    "get_supported_styles",
    "combine_menu_with_images"
]

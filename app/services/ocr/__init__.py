from typing import List, Optional, Union
from enum import Enum

from .base import BaseOCRService, OCRResult
from .google_vision import GoogleVisionOCRService
from .gemini import GeminiOCRService

class OCRProvider(str, Enum):
    """OCRプロバイダーの定義"""
    GEMINI = "gemini"
    GOOGLE_VISION = "google_vision"

class OCRServiceManager:
    """OCRサービスの統合管理クラス"""
    
    def __init__(self):
        self.services = {}
        self._initialize_services()
    
    def _initialize_services(self):
        """利用可能なOCRサービスを初期化（Gemini特化）"""
        # Geminiサービス（メインOCR）
        try:
            gemini_service = GeminiOCRService()
            self.services[OCRProvider.GEMINI] = gemini_service
            status = "✅ Available" if gemini_service.is_available() else "❌ Unavailable"
            print(f"🎯 Gemini OCR Service (Primary): {status}")
        except Exception as e:
            print(f"❌ Failed to initialize Gemini OCR Service: {e}")
        
        # Google Visionサービス（並列処理用に有効化）
        try:
            vision_service = GoogleVisionOCRService()
            self.services[OCRProvider.GOOGLE_VISION] = vision_service
            status = "✅ Available" if vision_service.is_available() else "❌ Unavailable"
            print(f"👁️ Google Vision OCR Service (Parallel): {status}")
        except Exception as e:
            print(f"❌ Failed to initialize Google Vision OCR Service: {e}")
    
    def get_service(self, provider: OCRProvider) -> Optional[BaseOCRService]:
        """指定されたプロバイダーのサービスを取得"""
        return self.services.get(provider)
    
    def get_available_services(self) -> List[BaseOCRService]:
        """利用可能なサービスのリストを取得"""
        return [service for service in self.services.values() if service.is_available()]
    
    def get_preferred_service(self) -> Optional[BaseOCRService]:
        """Gemini OCRサービスを取得（Gemini専用モード）"""
        # Gemini専用モード: Geminiのみ使用
        gemini_service = self.services.get(OCRProvider.GEMINI)
        if gemini_service and gemini_service.is_available():
            return gemini_service
        
        return None
    
    async def extract_text_with_gemini(
        self, 
        image_path: str, 
        session_id: str = None
    ) -> OCRResult:
        """
        Gemini OCRでテキストを抽出（Gemini専用モード）
        
        Args:
            image_path: 画像ファイルのパス
            session_id: セッションID（進行状況通知用）
            
        Returns:
            OCRResult: 抽出結果
        """
        # Gemini OCRサービスを取得
        gemini_service = self.get_service(OCRProvider.GEMINI)
        
        # Geminiサービスが利用できない場合
        if not gemini_service or not gemini_service.is_available():
            return OCRResult(
                success=False,
                error="Gemini OCRサービスが利用できません。GEMINI_API_KEYの設定を確認してください。",
                metadata={
                    "error_type": "gemini_unavailable",
                    "service": "gemini_exclusive_mode",
                    "suggestions": [
                        "GEMINI_API_KEY環境変数を設定してください",
                        "google-generativeaiパッケージがインストールされているか確認してください",
                        "Gemini APIキーが有効であることを確認してください",
                        "インターネット接続を確認してください"
                    ]
                }
            )
        
        try:
            print(f"🎯 Starting OCR with Gemini 2.0 Flash (Exclusive Mode)")
            
            # Gemini OCRを実行
            result = await gemini_service.extract_text(image_path, session_id)
            
            if result.success:
                print(f"✅ Gemini OCR successful - extracted {len(result.extracted_text)} characters")
                # 成功した場合はGemini専用情報を追加
                result.metadata.update({
                    "successful_service": "GeminiOCRService", 
                    "ocr_mode": "gemini_exclusive",
                    "model": "gemini-2.0-flash-exp",
                    "features": ["menu_optimized", "japanese_text", "high_precision"]
                })
                return result
            else:
                print(f"❌ Gemini OCR failed: {result.error}")
                # エラー情報を強化
                result.metadata.update({
                    "ocr_mode": "gemini_exclusive",
                    "model": "gemini-2.0-flash-exp",
                    "fallback_available": False
                })
                return result
                
        except Exception as e:
            print(f"❌ Exception in Gemini OCR: {str(e)}")
            return OCRResult(
                success=False,
                error=f"Gemini OCRサービスでエラーが発生しました: {str(e)}",
                metadata={
                    "error_type": "gemini_service_exception",
                    "service": "GeminiOCRService",
                    "ocr_mode": "gemini_exclusive",
                    "original_error": str(e),
                    "suggestions": [
                        "GEMINI_API_KEYが正しく設定されているか確認してください",
                        "Gemini APIの利用状況・クォータを確認してください",
                        "一時的なネットワーク問題の可能性があります - 少し時間をおいて再試行してください",
                        "画像ファイルが破損していないか確認してください"
                    ]
                }
            )
    
    def get_service_status(self) -> dict:
        """各サービスの状態を取得"""
        status = {}
        for provider, service in self.services.items():
            status[provider.value] = {
                "available": service.is_available(),
                "service_name": service.service_name
            }
        return status

# グローバルインスタンス
ocr_manager = OCRServiceManager()

# 便利な関数をエクスポート（Gemini専用）
async def extract_text(
    image_path: str, 
    session_id: str = None
) -> OCRResult:
    """
    Gemini OCRで画像からテキストを抽出する便利関数（Gemini専用モード）
    
    Args:
        image_path: 画像ファイルのパス
        session_id: セッションID（進行状況通知用）
        
    Returns:
        OCRResult: 抽出結果
    """
    return await ocr_manager.extract_text_with_gemini(image_path, session_id)

def get_ocr_service_status() -> dict:
    """Gemini OCRサービスの状態を取得する便利関数（Gemini専用モード）"""
    return ocr_manager.get_service_status()

# エクスポート
__all__ = [
    'OCRProvider',
    'OCRServiceManager', 
    'ocr_manager',
    'extract_text',
    'get_ocr_service_status',
    'OCRResult',
    'BaseOCRService'
]

from abc import ABC, abstractmethod
from typing import Dict, Optional, Union
import os
from app.core.config import settings

class OCRResult:
    """OCR処理結果を格納するクラス"""
    
    def __init__(
        self, 
        success: bool, 
        extracted_text: str = "", 
        error: str = None, 
        metadata: Dict = None
    ):
        self.success = success
        self.extracted_text = extracted_text
        self.error = error
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict:
        """辞書形式に変換"""
        result = {
            "success": self.success,
            "extracted_text": self.extracted_text
        }
        if self.error:
            result["error"] = self.error
        if self.metadata:
            result.update(self.metadata)
        return result

class BaseOCRService(ABC):
    """OCRサービスの基底クラス"""
    
    def __init__(self):
        self.service_name = self.__class__.__name__
    
    def validate_image_file(self, image_path: str) -> None:
        """画像ファイルの検証"""
        # ファイル存在チェック
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"画像ファイルが見つかりません: {image_path}")
        
        # ファイルサイズチェック
        file_size = os.path.getsize(image_path)
        if file_size == 0:
            raise ValueError("画像ファイルが空です")
        
        if file_size > settings.MAX_FILE_SIZE:
            max_size_mb = settings.MAX_FILE_SIZE // (1024*1024)
            raise ValueError(f"画像ファイルが大きすぎます（{max_size_mb}MB以下にしてください）")
    
    def _create_error_result(self, error_message: str, error_type: str = "unknown_error", suggestions: list = None) -> OCRResult:
        """エラー結果を作成"""
        return OCRResult(
            success=False,
            error=error_message,
            metadata={
                "error_type": error_type,
                "suggestions": suggestions or [],
                "service": self.service_name
            }
        )
    
    def _create_success_result(self, extracted_text: str, metadata: Dict = None) -> OCRResult:
        """成功結果を作成"""
        return OCRResult(
            success=True,
            extracted_text=extracted_text,
            metadata={
                **(metadata or {}),
                "service": self.service_name
            }
        )
    
    @abstractmethod
    async def extract_text(self, image_path: str, session_id: str = None) -> OCRResult:
        """
        画像からテキストを抽出する抽象メソッド
        
        Args:
            image_path: 画像ファイルのパス
            session_id: セッションID（進行状況通知用）
            
        Returns:
            OCRResult: 抽出結果
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """サービスが利用可能かどうかを確認"""
        pass

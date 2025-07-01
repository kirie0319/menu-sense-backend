"""
Menu Sensor Backend - 共通例外クラス
統一されたエラーハンドリングとエラータイプの定義
"""
from enum import Enum
from typing import Optional, List, Dict, Any


class ErrorType(str, Enum):
    """エラータイプの列挙型"""
    VALIDATION_ERROR = "validation_error"
    FILE_ERROR = "file_error"
    API_ERROR = "api_error"
    SERVICE_UNAVAILABLE = "service_unavailable"
    PROCESSING_ERROR = "processing_error"
    NETWORK_ERROR = "network_error"
    AUTHENTICATION_ERROR = "authentication_error"
    QUOTA_EXCEEDED = "quota_exceeded"
    TIMEOUT_ERROR = "timeout_error"
    UNKNOWN_ERROR = "unknown_error"


class MenuSensorServiceError(Exception):
    """Menu Sensor サービスの基底例外クラス"""
    
    def __init__(
        self,
        message: str,
        error_type: ErrorType = ErrorType.UNKNOWN_ERROR,
        suggestions: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.suggestions = suggestions or []
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "error_message": self.message,
            "error_type": self.error_type.value,
            "suggestions": self.suggestions,
            "metadata": self.metadata
        }


class ValidationError(MenuSensorServiceError):
    """入力検証エラー"""
    
    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        suggestions: Optional[List[str]] = None
    ):
        if field_name:
            message = f"{field_name}: {message}"
        
        super().__init__(
            message=message,
            error_type=ErrorType.VALIDATION_ERROR,
            suggestions=suggestions or [
                "入力データの形式を確認してください",
                "必須フィールドが含まれているか確認してください"
            ]
        )
        self.field_name = field_name


class FileError(MenuSensorServiceError):
    """ファイル関連エラー"""
    
    def __init__(
        self,
        message: str,
        file_path: Optional[str] = None,
        suggestions: Optional[List[str]] = None
    ):
        super().__init__(
            message=message,
            error_type=ErrorType.FILE_ERROR,
            suggestions=suggestions or [
                "ファイルパスが正しいか確認してください",
                "ファイルが存在し、読み取り可能か確認してください",
                "ファイルサイズ制限内か確認してください"
            ]
        )
        self.file_path = file_path


class APIError(MenuSensorServiceError):
    """API関連エラー"""
    
    def __init__(
        self,
        message: str,
        api_service: Optional[str] = None,
        status_code: Optional[int] = None,
        suggestions: Optional[List[str]] = None
    ):
        super().__init__(
            message=message,
            error_type=ErrorType.API_ERROR,
            suggestions=suggestions or [
                "APIキーが正しく設定されているか確認してください",
                "API利用制限に達していないか確認してください",
                "しばらく時間をおいて再試行してください"
            ]
        )
        self.api_service = api_service
        self.status_code = status_code


class ServiceUnavailableError(MenuSensorServiceError):
    """サービス利用不可エラー"""
    
    def __init__(
        self,
        message: str,
        service_name: Optional[str] = None,
        suggestions: Optional[List[str]] = None
    ):
        super().__init__(
            message=message,
            error_type=ErrorType.SERVICE_UNAVAILABLE,
            suggestions=suggestions or [
                "しばらく時間をおいて再試行してください",
                "代替サービスが利用可能か確認してください",
                "ネットワーク接続を確認してください"
            ]
        )
        self.service_name = service_name


class ProcessingError(MenuSensorServiceError):
    """処理実行エラー"""
    
    def __init__(
        self,
        message: str,
        processing_stage: Optional[str] = None,
        suggestions: Optional[List[str]] = None
    ):
        super().__init__(
            message=message,
            error_type=ErrorType.PROCESSING_ERROR,
            suggestions=suggestions or [
                "入力データを確認してください",
                "処理パラメータを見直してください",
                "システム管理者に連絡してください"
            ]
        )
        self.processing_stage = processing_stage


def create_error_suggestions(error_type: ErrorType, context: str = "") -> List[str]:
    """エラータイプに応じた提案を生成"""
    base_suggestions = {
        ErrorType.VALIDATION_ERROR: [
            "入力データの形式を確認してください",
            "必須フィールドが含まれているか確認してください"
        ],
        ErrorType.FILE_ERROR: [
            "ファイルパスが正しいか確認してください", 
            "ファイルが存在し、読み取り可能か確認してください"
        ],
        ErrorType.API_ERROR: [
            "APIキーの設定を確認してください",
            "ネットワーク接続を確認してください"
        ],
        ErrorType.SERVICE_UNAVAILABLE: [
            "しばらく時間をおいて再試行してください",
            "代替サービスの利用を検討してください"
        ],
        ErrorType.PROCESSING_ERROR: [
            "入力データを確認してください",
            "処理パラメータを見直してください"
        ]
    }
    
    suggestions = base_suggestions.get(error_type, ["システム管理者に連絡してください"])
    
    if context:
        suggestions.append(f"詳細: {context}")
    
    return suggestions 
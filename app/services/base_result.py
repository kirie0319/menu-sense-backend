"""
基底結果クラス

すべてのサービス結果クラスの基底となるクラスを定義します。
共通のフィールドとメソッドを提供し、コードの重複を削減します。
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class BaseServiceResult:
    """
    すべてのサービス結果の基底クラス
    
    Attributes:
        success: 処理が成功したかどうか
        error: エラーメッセージ（エラーの場合）
        metadata: 追加のメタデータ
    """
    success: bool
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """初期化後の処理"""
        if self.metadata is None:
            self.metadata = {}
    
    def add_metadata(self, key: str, value: Any) -> None:
        """メタデータを追加"""
        self.metadata[key] = value
    
    def get_error_type(self) -> Optional[str]:
        """エラータイプを取得"""
        return self.metadata.get("error_type")
    
    def get_suggestions(self) -> list:
        """エラー解決のサジェスチョンを取得"""
        return self.metadata.get("suggestions", [])
    
    def get_processing_time(self) -> Optional[float]:
        """処理時間を取得"""
        return self.metadata.get("processing_time")
    
    def is_fallback_used(self) -> bool:
        """フォールバックが使用されたかどうか"""
        return self.metadata.get("fallback_used", False)
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        result = {
            "success": self.success,
        }
        if self.error:
            result["error"] = self.error
        if self.metadata:
            result["metadata"] = self.metadata
        return result 
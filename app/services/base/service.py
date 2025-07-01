from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Type
from datetime import datetime
from .result import BaseResult
from .exceptions import (
    ErrorType, 
    MenuSensorServiceError,
    ValidationError,
    ServiceUnavailableError,
    ProcessingError,
    create_error_suggestions
)

class BaseService(ABC):
    """
    全サービスの基底クラス（強化版）
    
    このクラスは新しいリファクタリング用で、既存のサービスには影響しません。
    段階的に移行していくために使用されます。
    
    新機能:
    - 統一された例外ハンドリング
    - パフォーマンス測定
    - 詳細なサービス情報
    - エラー回復機能
    """
    
    def __init__(self):
        self.service_name = self.__class__.__name__
        self.provider = None
        self._performance_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_processing_time": 0.0
        }
    
    @abstractmethod
    def is_available(self) -> bool:
        """サービスが利用可能かチェック"""
        pass
    
    def get_service_info(self) -> Dict[str, Any]:
        """詳細なサービス情報を取得"""
        return {
            "service_name": self.service_name,
            "provider": getattr(self.provider, 'value', 'unknown') if self.provider else "unknown",
            "available": self.is_available(),
            "capabilities": self.get_capabilities(),
            "version": "2.0.0",  # 強化版のバージョン
            "performance_stats": self._performance_stats.copy(),
            "error_handling": {
                "supports_detailed_errors": True,
                "supports_error_recovery": True,
                "supports_suggestions": True
            }
        }
    
    def get_capabilities(self) -> list:
        """サービスの機能一覧（サブクラスでオーバーライド）"""
        return []
    
    def _update_performance_stats(self, processing_time: float, success: bool) -> None:
        """パフォーマンス統計を更新"""
        self._performance_stats["total_requests"] += 1
        
        if success:
            self._performance_stats["successful_requests"] += 1
        else:
            self._performance_stats["failed_requests"] += 1
        
        # 平均処理時間を更新
        total_requests = self._performance_stats["total_requests"]
        current_avg = self._performance_stats["average_processing_time"]
        self._performance_stats["average_processing_time"] = (
            (current_avg * (total_requests - 1) + processing_time) / total_requests
        )
    
    def _create_error_result(
        self, 
        error_message: str, 
        result_class: Type[BaseResult], 
        error_type: ErrorType = ErrorType.UNKNOWN_ERROR,
        suggestions: Optional[list] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> BaseResult:
        """統一されたエラー結果を作成（強化版）"""
        
        # エラー提案を生成
        if suggestions is None:
            suggestions = create_error_suggestions(error_type, str(context) if context else "")
        
        # 基本的なメタデータ
        metadata = {
            "service": self.service_name,
            "error_details": {
                "timestamp": self._get_timestamp(),
                "error_category": error_type.value,
                "service_available": self.is_available()
            }
        }
        
        # コンテキスト情報を追加
        if context:
            metadata["error_details"].update(context)
        
        # 結果オブジェクトを作成
        result = result_class(
            success=False,
            error=error_message,
            metadata=metadata,
            suggestions=suggestions,
            error_type=error_type.value,
            error_context=context or {},
            **kwargs
        )
        
        return result
    
    def _create_success_result(
        self,
        result_class: Type[BaseResult],
        start_time: Optional[datetime] = None,
        quality_metrics: Optional[Dict[str, float]] = None,
        **kwargs
    ) -> BaseResult:
        """統一された成功結果を作成（強化版）"""
        
        # 基本的なメタデータ
        metadata = kwargs.pop('metadata', {})
        metadata.update({
            "service": self.service_name,
            "processed_at": self._get_timestamp(),
            "service_version": "2.0.0"
        })
        
        # 結果オブジェクトを作成
        result = result_class(
            success=True,
            metadata=metadata,
            **kwargs
        )
        
        # 処理時間を設定
        if start_time:
            result.set_processing_time(start_time)
        
        # 品質指標を設定
        if quality_metrics:
            result.set_quality_metrics(
                quality_score=quality_metrics.get("quality_score"),
                confidence=quality_metrics.get("confidence")
            )
        
        return result
    
    def _execute_with_error_handling(
        self,
        operation_func,
        result_class: Type[BaseResult],
        operation_name: str = "operation",
        **kwargs
    ):
        """エラーハンドリング付きで操作を実行"""
        start_time = datetime.now()
        
        try:
            # 操作を実行
            result = operation_func(**kwargs)
            
            # パフォーマンス統計を更新
            processing_time = (datetime.now() - start_time).total_seconds()
            self._update_performance_stats(processing_time, True)
            
            return result
            
        except ValidationError as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            self._update_performance_stats(processing_time, False)
            
            return self._create_error_result(
                str(e),
                result_class,
                ErrorType.VALIDATION_ERROR,
                e.suggestions,
                {"operation": operation_name, "field_name": getattr(e, 'field_name', None)}
            )
        
        except ServiceUnavailableError as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            self._update_performance_stats(processing_time, False)
            
            return self._create_error_result(
                str(e),
                result_class,
                ErrorType.SERVICE_UNAVAILABLE,
                e.suggestions,
                {"operation": operation_name, "service_name": getattr(e, 'service_name', None)}
            )
        
        except MenuSensorServiceError as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            self._update_performance_stats(processing_time, False)
            
            return self._create_error_result(
                str(e),
                result_class,
                e.error_type,
                e.suggestions,
                {"operation": operation_name, **e.metadata}
            )
        
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            self._update_performance_stats(processing_time, False)
            
            return self._create_error_result(
                f"Unexpected error in {operation_name}: {str(e)}",
                result_class,
                ErrorType.UNKNOWN_ERROR,
                ["システム管理者に連絡してください", "ログを確認してください"],
                {
                    "operation": operation_name,
                    "exception_type": type(e).__name__,
                    "exception_details": str(e)
                }
            )
    
    def _get_timestamp(self) -> str:
        """現在のタイムスタンプを取得"""
        return datetime.now().isoformat()
    
    def validate_input(self, input_data: Any) -> bool:
        """基本的な入力検証（サブクラスでオーバーライド）"""
        return input_data is not None
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """パフォーマンス概要を取得"""
        stats = self._performance_stats.copy()
        
        # 成功率を計算
        if stats["total_requests"] > 0:
            stats["success_rate"] = stats["successful_requests"] / stats["total_requests"]
            stats["failure_rate"] = stats["failed_requests"] / stats["total_requests"]
        else:
            stats["success_rate"] = 0.0
            stats["failure_rate"] = 0.0
        
        return {
            "service_name": self.service_name,
            "performance_statistics": stats,
            "health_status": "healthy" if stats["success_rate"] >= 0.9 else "degraded" if stats["success_rate"] >= 0.7 else "unhealthy"
        }
    
    def reset_performance_stats(self) -> None:
        """パフォーマンス統計をリセット"""
        self._performance_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_processing_time": 0.0
        } 
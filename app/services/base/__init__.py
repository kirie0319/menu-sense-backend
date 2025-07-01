# Base service classes for menu sensor backend
"""
このモジュールは段階的リファクタリングのための新しい基底クラスを提供します。
既存のサービスには影響を与えません。
"""

from .result import BaseResult
from .service import BaseService
from .exceptions import (
    ErrorType,
    MenuSensorServiceError,
    ValidationError,
    FileError,
    APIError,
    ServiceUnavailableError,
    ProcessingError,
    create_error_suggestions
)

__all__ = [
    'BaseResult', 
    'BaseService',
    'ErrorType',
    'MenuSensorServiceError',
    'ValidationError',
    'FileError',
    'APIError',
    'ServiceUnavailableError',
    'ProcessingError',
    'create_error_suggestions'
] 
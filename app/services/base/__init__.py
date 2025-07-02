# Base service classes and utilities for enhanced service implementations
from .result import BaseResult
from .service import BaseService
from .exceptions import (
    ErrorType,
    MenuSensorServiceError,
    ValidationError,
    ServiceUnavailableError,
    ProcessingError,
    FileError,
    APIError,
    create_error_suggestions
)

__all__ = [
    # Base classes
    'BaseResult',
    'BaseService',
    
    # Exception types
    'ErrorType',
    'MenuSensorServiceError',
    'ValidationError', 
    'ServiceUnavailableError',
    'ProcessingError',
    'FileError',
    'APIError',
    
    # Utility functions
    'create_error_suggestions'
] 
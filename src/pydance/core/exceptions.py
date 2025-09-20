"""
Unified Exceptions Module for PyDance Framework.

This module provides a comprehensive, hierarchical exception system for the framework,
with proper error codes, HTTP status mappings, and production-ready error handling.
"""

from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
import logging
import json

logger = logging.getLogger(__name__)


@dataclass
class ErrorDetail:
    """Detailed error information"""
    field: Optional[str] = None
    message: str = ""
    code: str = ""
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {"message": self.message, "code": self.code}
        if self.field:
            result["field"] = self.field
        if self.details:
            result["details"] = self.details
        return result


class BaseFrameworkException(Exception):
    """
    Base exception class for PyDance framework.

    All framework exceptions should inherit from this class to ensure
    consistent error handling and API responses.
    """

    def __init__(self,
                 message: str,
                 status_code: int = 500,
                 error_code: str = "internal_error",
                 details: Optional[List[ErrorDetail]] = None,
                 headers: Optional[Dict[str, str]] = None,
                 payload: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or []
        self.headers = headers or {}
        self.payload = payload or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses"""
        result = {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "status_code": self.status_code
            }
        }

        if self.details:
            result["error"]["details"] = [detail.to_dict() for detail in self.details]

        if self.payload:
            result.update(self.payload)

        return result

    def to_json(self) -> str:
        """Convert exception to JSON string"""
        return json.dumps(self.to_dict(), default=str)

    def __str__(self) -> str:
        return f"{self.error_code}: {self.message}"


# HTTP Status Code Exceptions
class HTTPException(BaseFrameworkException):
    """Base HTTP exception"""
    pass


class BadRequest(HTTPException):
    """400 Bad Request"""
    def __init__(self, message: str = "Bad request", **kwargs):
        super().__init__(message, status_code=400, error_code="bad_request", **kwargs)


class Unauthorized(HTTPException):
    """401 Unauthorized"""
    def __init__(self, message: str = "Unauthorized", **kwargs):
        super().__init__(message, status_code=401, error_code="unauthorized", **kwargs)


class Forbidden(HTTPException):
    """403 Forbidden"""
    def __init__(self, message: str = "Forbidden", **kwargs):
        super().__init__(message, status_code=403, error_code="forbidden", **kwargs)


class NotFound(HTTPException):
    """404 Not Found"""
    def __init__(self, message: str = "Not found", **kwargs):
        super().__init__(message, status_code=404, error_code="not_found", **kwargs)


class MethodNotAllowed(HTTPException):
    """405 Method Not Allowed"""
    def __init__(self, message: str = "Method not allowed", **kwargs):
        super().__init__(message, status_code=405, error_code="method_not_allowed", **kwargs)


class NotAcceptable(HTTPException):
    """406 Not Acceptable"""
    def __init__(self, message: str = "Not acceptable", **kwargs):
        super().__init__(message, status_code=406, error_code="not_acceptable", **kwargs)


class UnsupportedMediaType(HTTPException):
    """415 Unsupported Media Type"""
    def __init__(self, message: str = "Unsupported media type", **kwargs):
        super().__init__(message, status_code=415, error_code="unsupported_media_type", **kwargs)


class Conflict(HTTPException):
    """409 Conflict"""
    def __init__(self, message: str = "Conflict", **kwargs):
        super().__init__(message, status_code=409, error_code="conflict", **kwargs)


class Gone(HTTPException):
    """410 Gone"""
    def __init__(self, message: str = "Gone", **kwargs):
        super().__init__(message, status_code=410, error_code="gone", **kwargs)


class UnprocessableEntity(HTTPException):
    """422 Unprocessable Entity"""
    def __init__(self, message: str = "Unprocessable entity", **kwargs):
        super().__init__(message, status_code=422, error_code="unprocessable_entity", **kwargs)


class TooManyRequests(HTTPException):
    """429 Too Many Requests"""
    def __init__(self, message: str = "Too many requests", retry_after: Optional[int] = None, **kwargs):
        super().__init__(message, status_code=429, error_code="too_many_requests", **kwargs)
        if retry_after:
            self.headers["Retry-After"] = str(retry_after)


class InternalServerError(HTTPException):
    """500 Internal Server Error"""
    def __init__(self, message: str = "Internal server error", **kwargs):
        super().__init__(message, status_code=500, error_code="internal_server_error", **kwargs)


class NotImplemented(HTTPException):
    """501 Not Implemented"""
    def __init__(self, message: str = "Not implemented", **kwargs):
        super().__init__(message, status_code=501, error_code="not_implemented", **kwargs)


class BadGateway(HTTPException):
    """502 Bad Gateway"""
    def __init__(self, message: str = "Bad gateway", **kwargs):
        super().__init__(message, status_code=502, error_code="bad_gateway", **kwargs)


class ServiceUnavailable(HTTPException):
    """503 Service Unavailable"""
    def __init__(self, message: str = "Service unavailable", **kwargs):
        super().__init__(message, status_code=503, error_code="service_unavailable", **kwargs)


class GatewayTimeout(HTTPException):
    """504 Gateway Timeout"""
    def __init__(self, message: str = "Gateway timeout", **kwargs):
        super().__init__(message, status_code=504, error_code="gateway_timeout", **kwargs)


# Validation Exceptions
class ValidationError(BadRequest):
    """Validation error with field-level details"""

    def __init__(self, message: str = "Validation failed", field_errors: Optional[Dict[str, List[str]]] = None, **kwargs):
        super().__init__(message, error_code="validation_error", **kwargs)

        if field_errors:
            self.details = [
                ErrorDetail(field=field, message=", ".join(messages), code="field_error")
                for field, messages in field_errors.items()
            ]


class FieldValidationError(ValidationError):
    """Field-specific validation error"""

    def __init__(self, field: str, message: str, **kwargs):
        super().__init__(**kwargs)
        self.details = [ErrorDetail(field=field, message=message, code="field_error")]


# Authentication & Authorization Exceptions
class AuthenticationError(Unauthorized):
    """Base authentication error"""
    pass


class TokenExpired(AuthenticationError):
    """Authentication token has expired"""

    def __init__(self, message: str = "Token has expired", **kwargs):
        super().__init__(message, error_code="token_expired", **kwargs)


class TokenInvalid(AuthenticationError):
    """Authentication token is invalid"""

    def __init__(self, message: str = "Token is invalid", **kwargs):
        super().__init__(message, error_code="token_invalid", **kwargs)


class TokenMissing(AuthenticationError):
    """Authentication token is missing"""

    def __init__(self, message: str = "Token is missing", **kwargs):
        super().__init__(message, error_code="token_missing", **kwargs)


class PermissionDenied(Forbidden):
    """Permission denied error"""

    def __init__(self, message: str = "Permission denied", required_permission: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="permission_denied", **kwargs)
        if required_permission:
            self.payload["required_permission"] = required_permission


# User-related Exceptions
class UserError(BadRequest):
    """Base user error"""
    pass


class UserNotFound(NotFound):
    """User not found"""

    def __init__(self, user_id: Optional[Union[str, int]] = None, **kwargs):
        message = f"User not found"
        if user_id:
            message += f": {user_id}"
        super().__init__(message, error_code="user_not_found", **kwargs)


class UserAlreadyExists(Conflict):
    """User already exists"""

    def __init__(self, identifier: str, **kwargs):
        super().__init__(f"User already exists: {identifier}", error_code="user_already_exists", **kwargs)


class InvalidCredentials(AuthenticationError):
    """Invalid login credentials"""

    def __init__(self, message: str = "Invalid credentials", **kwargs):
        super().__init__(message, error_code="invalid_credentials", **kwargs)


class PasswordTooWeak(UserError):
    """Password does not meet strength requirements"""

    def __init__(self, message: str = "Password too weak", requirements: Optional[List[str]] = None, **kwargs):
        super().__init__(message, error_code="password_too_weak", **kwargs)
        if requirements:
            self.payload["requirements"] = requirements


class InvalidEmailFormat(ValidationError):
    """Invalid email format"""

    def __init__(self, email: str, **kwargs):
        super().__init__(error_code="invalid_email_format", **kwargs)
        self.details = [ErrorDetail(field="email", message=f"Invalid email format: {email}", code="invalid_format")]


class InvalidUsernameFormat(ValidationError):
    """Invalid username format"""

    def __init__(self, username: str, **kwargs):
        super().__init__(error_code="invalid_username_format", **kwargs)
        self.details = [ErrorDetail(field="username", message=f"Invalid username format: {username}", code="invalid_format")]


class AccountLocked(Forbidden):
    """Account is locked due to too many failed attempts"""

    def __init__(self, message: str = "Account is locked", unlock_time: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="account_locked", **kwargs)
        if unlock_time:
            self.payload["unlock_time"] = unlock_time


class AccountNotVerified(Forbidden):
    """Account not verified"""

    def __init__(self, message: str = "Account not verified", **kwargs):
        super().__init__(message, error_code="account_not_verified", **kwargs)


class AccountSuspended(Forbidden):
    """Account is suspended"""

    def __init__(self, message: str = "Account is suspended", reason: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="account_suspended", **kwargs)
        if reason:
            self.payload["reason"] = reason


class AccountInactive(Forbidden):
    """Account is inactive"""

    def __init__(self, message: str = "Account is inactive", **kwargs):
        super().__init__(message, error_code="account_inactive", **kwargs)


# Database Exceptions
class DatabaseError(InternalServerError):
    """Database operation error"""
    pass


class ConnectionError(DatabaseError):
    """Database connection error"""

    def __init__(self, message: str = "Database connection failed", **kwargs):
        super().__init__(message, error_code="database_connection_error", **kwargs)


class IntegrityError(DatabaseError):
    """Database integrity constraint violation"""

    def __init__(self, message: str = "Database integrity error", constraint: Optional[str] = None, **kwargs):
        super().__init__(message, error_code="database_integrity_error", **kwargs)
        if constraint:
            self.payload["constraint"] = constraint


class TransactionError(DatabaseError):
    """Database transaction error"""

    def __init__(self, message: str = "Transaction failed", **kwargs):
        super().__init__(message, error_code="transaction_error", **kwargs)


# File Upload Exceptions
class FileUploadError(BadRequest):
    """File upload error"""
    pass


class FileTooLarge(FileUploadError):
    """Uploaded file is too large"""

    def __init__(self, filename: str, max_size: int, actual_size: int, **kwargs):
        message = f"File too large: {filename} ({actual_size} bytes, max: {max_size} bytes)"
        super().__init__(message, error_code="file_too_large", **kwargs)
        self.payload.update({
            "filename": filename,
            "max_size": max_size,
            "actual_size": actual_size
        })


class InvalidFileType(FileUploadError):
    """Invalid file type"""

    def __init__(self, filename: str, allowed_types: List[str], actual_type: str, **kwargs):
        message = f"Invalid file type: {filename} (allowed: {', '.join(allowed_types)}, got: {actual_type})"
        super().__init__(message, error_code="invalid_file_type", **kwargs)
        self.payload.update({
            "filename": filename,
            "allowed_types": allowed_types,
            "actual_type": actual_type
        })


class FileNotFound(NotFound):
    """File not found"""

    def __init__(self, filename: str, **kwargs):
        super().__init__(f"File not found: {filename}", error_code="file_not_found", **kwargs)


# Rate Limiting Exceptions
class RateLimitExceeded(TooManyRequests):
    """Rate limit exceeded"""

    def __init__(self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None,
                 limit: Optional[int] = None, remaining: Optional[int] = None, **kwargs):
        super().__init__(message, retry_after=retry_after, error_code="rate_limit_exceeded", **kwargs)
        if limit is not None:
            self.payload["limit"] = limit
        if remaining is not None:
            self.payload["remaining"] = remaining


# Configuration Exceptions
class ConfigurationError(InternalServerError):
    """Configuration error"""
    pass


class MissingConfiguration(ConfigurationError):
    """Required configuration is missing"""

    def __init__(self, key: str, **kwargs):
        super().__init__(f"Missing configuration: {key}", error_code="missing_configuration", **kwargs)
        self.payload["missing_key"] = key


class InvalidConfiguration(ConfigurationError):
    """Invalid configuration value"""

    def __init__(self, key: str, value: Any, expected: str, **kwargs):
        message = f"Invalid configuration for {key}: got {value}, expected {expected}"
        super().__init__(message, error_code="invalid_configuration", **kwargs)
        self.payload.update({
            "key": key,
            "value": value,
            "expected": expected
        })


# Dependency Injection Exceptions
class DependencyInjectionException(InternalServerError):
    """Exception raised when dependency injection fails"""

    def __init__(self, service_name: str, message: str = "Dependency injection failed", **kwargs):
        super().__init__(f"{message}: {service_name}", error_code="dependency_injection_error", **kwargs)
        self.payload["service_name"] = service_name


# Routing Exceptions
class RouteNotFound(NotFound):
    """Exception raised when a route is not found"""

    def __init__(self, path: str, method: str, **kwargs):
        super().__init__(f"Route not found: {method} {path}", error_code="route_not_found", **kwargs)
        self.payload.update({
            "path": path,
            "method": method
        })


class RouteConflict(Conflict):
    """Exception raised when route registration conflicts"""

    def __init__(self, path: str, method: str, **kwargs):
        super().__init__(f"Route conflict: {method} {path}", error_code="route_conflict", **kwargs)
        self.payload.update({
            "path": path,
            "method": method
        })


# WebSocket Exceptions
class WebSocketException(HTTPException):
    """WebSocket-related exception"""

    def __init__(self, message: str, code: int = 1000, **kwargs):
        super().__init__(message, status_code=101, error_code="websocket_error", **kwargs)
        self.websocket_code = code


class WebSocketDisconnect(WebSocketException):
    """WebSocket disconnect exception"""

    def __init__(self, code: int = 1000, reason: Optional[str] = None, **kwargs):
        message = f"WebSocket disconnected"
        if reason:
            message += f": {reason}"
        super().__init__(message, code=code, **kwargs)


# API-specific Exceptions (for backward compatibility)
class APIException(HTTPException):
    """API-specific exception"""
    pass


class APIError(APIException):
    """API error (legacy compatibility)"""
    pass


class ValidationError(APIException):
    """Validation error (legacy compatibility)"""
    pass


class PermissionDenied(APIException):
    """Permission denied (legacy compatibility)"""
    pass


# Utility functions
def get_exception_by_status_code(status_code: int) -> type:
    """Get exception class by HTTP status code"""
    status_exceptions = {
        400: BadRequest,
        401: Unauthorized,
        403: Forbidden,
        404: NotFound,
        405: MethodNotAllowed,
        406: NotAcceptable,
        409: Conflict,
        410: Gone,
        422: UnprocessableEntity,
        429: TooManyRequests,
        500: InternalServerError,
        501: NotImplemented,
        502: BadGateway,
        503: ServiceUnavailable,
        504: GatewayTimeout,
    }
    return status_exceptions.get(status_code, HTTPException)


def create_exception_from_dict(data: Dict[str, Any]) -> BaseFrameworkException:
    """Create exception instance from dictionary"""
    error_data = data.get("error", {})
    status_code = error_data.get("status_code", 500)
    error_code = error_data.get("code", "unknown_error")
    message = error_data.get("message", "Unknown error")

    exception_class = get_exception_by_status_code(status_code)
    return exception_class(message=message, status_code=status_code, error_code=error_code)


# Global exception handler registry
_exception_handlers: Dict[type, callable] = {}


def register_exception_handler(exception_class: type, handler: callable):
    """Register a custom exception handler"""
    _exception_handlers[exception_class] = handler


def get_exception_handler(exception: Exception) -> Optional[callable]:
    """Get handler for exception type"""
    for exc_class, handler in _exception_handlers.items():
        if isinstance(exception, exc_class):
            return handler
    return None


# Default exports
__all__ = [
    # Base classes
    'BaseFrameworkException',
    'ErrorDetail',

    # HTTP status exceptions
    'HTTPException',
    'BadRequest',
    'Unauthorized',
    'Forbidden',
    'NotFound',
    'MethodNotAllowed',
    'NotAcceptable',
    'UnsupportedMediaType',
    'Conflict',
    'Gone',
    'UnprocessableEntity',
    'TooManyRequests',
    'InternalServerError',
    'NotImplemented',
    'BadGateway',
    'ServiceUnavailable',
    'GatewayTimeout',

    # Validation exceptions
    'ValidationError',
    'FieldValidationError',

    # Authentication & authorization
    'AuthenticationError',
    'TokenExpired',
    'TokenInvalid',
    'TokenMissing',
    'PermissionDenied',

    # User exceptions
    'UserError',
    'UserNotFound',
    'UserAlreadyExists',
    'InvalidCredentials',
    'PasswordTooWeak',
    'InvalidEmailFormat',
    'InvalidUsernameFormat',
    'AccountLocked',
    'AccountNotVerified',
    'AccountSuspended',
    'AccountInactive',

    # Database exceptions
    'DatabaseError',
    'ConnectionError',
    'IntegrityError',
    'TransactionError',

    # File exceptions
    'FileUploadError',
    'FileTooLarge',
    'InvalidFileType',
    'FileNotFound',

    # Rate limiting
    'RateLimitExceeded',

    # Configuration
    'ConfigurationError',
    'MissingConfiguration',
    'InvalidConfiguration',

    # DI and routing
    'DependencyInjectionException',
    'RouteNotFound',
    'RouteConflict',

    # WebSocket
    'WebSocketException',
    'WebSocketDisconnect',

    # API (legacy)
    'APIException',
    'APIError',

    # Utilities
    'get_exception_by_status_code',
    'create_exception_from_dict',
    'register_exception_handler',
    'get_exception_handler',
]

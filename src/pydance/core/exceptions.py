# server_framework/core/exceptions.py
from typing import Any, Optional
from .i18n import _


class HTTPException(Exception):
    """Base HTTP exception"""
    
    def __init__(self, status_code: int, detail: str = None):
        self.status_code = status_code
        self.detail = detail or ""
        super().__init__(f"{status_code}: {detail}")

class BadRequest(HTTPException):
    """400 Bad Request"""
    def __init__(self, detail: str = None):
        if detail is None:
            detail = _('bad_request')
        super().__init__(400, detail)

class Unauthorized(HTTPException):
    """401 Unauthorized"""
    def __init__(self, detail: str = "Unauthorized"):
        super().__init__(401, detail)

class Forbidden(HTTPException):
    """403 Forbidden"""
    def __init__(self, detail: str = "Forbidden"):
        super().__init__(403, detail)

class NotFound(HTTPException):
    """404 Not Found"""
    def __init__(self, detail: str = "Not Found"):
        super().__init__(404, detail)

class InternalServerError(HTTPException):
    """500 Internal Server Error"""
    def __init__(self, detail: str = "Internal Server Error"):
        super().__init__(500, detail)

class WebSocketException(HTTPException):
    def __init__(self, detail: Any = None, code: int = 1000):
        super().__init__(400, detail)
        self.ws_code = code

class WebSocketDisconnect(Exception):
    def __init__(self, code: int = 1000, reason: Optional[str] = None):
        self.code = code
        self.reason = reason
        super().__init__(f"WebSocket disconnected with code {code}: {reason or 'No reason'}")


# User-related exceptions
class UserError(HTTPException):
    """Base user error"""
    pass

class UserNotFound(UserError):
    """User not found"""
    def __init__(self, message: str = "User not found"):
        super().__init__(404, message)

class UserAlreadyExists(UserError):
    """User already exists"""
    def __init__(self, message: str = "User already exists"):
        super().__init__(409, message)

class InvalidCredentials(UserError):
    """Invalid login credentials"""
    def __init__(self, message: str = "Invalid credentials"):
        super().__init__(401, message)

class PasswordTooWeak(UserError):
    """Password does not meet strength requirements"""
    def __init__(self, message: str = "Password does not meet strength requirements"):
        super().__init__(400, message)

class EmailAlreadyExists(UserAlreadyExists):
    """Email address already registered"""
    def __init__(self, message: str = "Email address already registered"):
        super().__init__(message)

class UsernameAlreadyExists(UserAlreadyExists):
    """Username already taken"""
    def __init__(self, message: str = "Username already taken"):
        super().__init__(message)

class InvalidEmailFormat(UserError):
    """Invalid email format"""
    def __init__(self, message: str = "Invalid email format"):
        super().__init__(400, message)

class InvalidUsernameFormat(UserError):
    """Invalid username format"""
    def __init__(self, message: str = "Invalid username format"):
        super().__init__(400, message)

class AccountLocked(UserError):
    """Account is locked due to too many failed attempts"""
    def __init__(self, message: str = "Account is locked"):
        super().__init__(423, message)

class AccountNotVerified(UserError):
    """Account not verified"""
    def __init__(self, message: str = "Account not verified"):
        super().__init__(403, message)

class AccountSuspended(UserError):
    """Account is suspended"""
    def __init__(self, message: str = "Account is suspended"):
        super().__init__(403, message)

class AccountInactive(UserError):
    """Account is inactive"""
    def __init__(self, message: str = "Account is inactive"):
        super().__init__(403, message)


# Validation exceptions
class ValidationError(BadRequest):
    """Validation error"""
    def __init__(self, field: str, message: str):
        self.field = field
        super().__init__(f"{field}: {message}")


# Database exceptions
class DatabaseError(InternalServerError):
    """Database operation error"""
    pass

class RecordNotFound(NotFound):
    """Database record not found"""
    def __init__(self, model: str, id: Any = None):
        message = f"{model} not found"
        if id:
            message += f" with id {id}"
        super().__init__(message)


# Authentication exceptions
class AuthenticationError(HTTPException):
    """Base authentication error"""
    pass

class TokenExpired(AuthenticationError):
    """Authentication token has expired"""
    def __init__(self, message: str = "Token has expired"):
        super().__init__(401, message)

class TokenInvalid(AuthenticationError):
    """Authentication token is invalid"""
    def __init__(self, message: str = "Invalid token"):
        super().__init__(401, message)

class PermissionDenied(Forbidden):
    """Permission denied"""
    def __init__(self, message: str = "Permission denied"):
        super().__init__(message)


# File upload exceptions
class FileUploadError(BadRequest):
    """File upload error"""
    pass

class FileTooLarge(FileUploadError):
    """Uploaded file is too large"""
    def __init__(self, max_size: int, actual_size: int):
        message = f"File too large. Maximum size: {max_size} bytes, actual size: {actual_size} bytes"
        super().__init__(message)

class InvalidFileType(FileUploadError):
    """Invalid file type"""
    def __init__(self, allowed_types: list, actual_type: str):
        message = f"Invalid file type '{actual_type}'. Allowed types: {', '.join(allowed_types)}"
        super().__init__(message)


# Rate limiting exceptions
class TooManyRequests(HTTPException):
    """Rate limit exceeded"""
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(429, message)


# Configuration exceptions
class ConfigurationError(InternalServerError):
    """Configuration error"""
    pass

class MissingConfiguration(ConfigurationError):
    """Required configuration is missing"""
    def __init__(self, key: str):
        message = f"Required configuration '{key}' is missing"
        super().__init__(message)

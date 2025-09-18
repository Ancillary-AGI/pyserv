"""
Core PyDance framework components.

This module provides the fundamental building blocks for PyDance applications,
including server components, HTTP handling, routing, middleware, and utilities.
"""

# Server components
from .server import Application, Server, AppConfig

# HTTP components
from .http import Request, Response

# WebSocket components
from .websocket import WebSocket

# Core utilities and types
from .middleware import Middleware, MiddlewareType, MiddlewareCallable
from .routing import Router, Route
from .exceptions import (
    HTTPException, BadRequest, NotFound, Forbidden,
    ValidationError, APIException
)
from .rate_limiting import RateLimiter, default_rate_limiter
from .pagination import PaginationParams, PageNumberPaginator, paginate
from .templating import TemplateEngineManager
from .security import Security, CryptoUtils

# Static file serving
from .static import (
    StaticFileMiddleware, StaticFileHandler, setup_static_files,
    create_static_route, get_static_url, ensure_static_dirs
)

__all__ = [
    # Server
    'Application', 'Server', 'AppConfig',
    # HTTP
    'Request', 'Response',
    # WebSocket
    'WebSocket',
    # Routing & Middleware
    'Router', 'Route', 'Middleware', 'MiddlewareType', 'MiddlewareCallable',
    # Exceptions
    'HTTPException', 'BadRequest', 'NotFound', 'Forbidden',
    'ValidationError', 'APIException',
    # Utilities
    'RateLimiter', 'default_rate_limiter',
    'PaginationParams', 'PageNumberPaginator', 'paginate',
    'TemplateEngineManager', 'Security', 'CryptoUtils',
    # Static files
    'StaticFileMiddleware', 'StaticFileHandler', 'setup_static_files',
    'create_static_route', 'get_static_url', 'ensure_static_dirs'
]

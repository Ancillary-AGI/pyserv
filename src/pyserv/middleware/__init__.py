"""
Middleware components for PyServ Framework.

This package contains various middleware components including:
- ThrottleMiddleware: Rate limiting middleware
- HTTPMiddleware: Base HTTP middleware
- WebSocketMiddleware: WebSocket middleware
"""

from pyserv.middleware.throttle import (
    ThrottleMiddleware,
    ThrottleConfig,
    throttle_per_ip,
    throttle_per_user,
    DEFAULT_THROTTLE_CONFIGS
)
from pyserv.middleware.resolver import (
    MiddlewareResolver,
    middleware_resolver
)
from pyserv.middleware.base import HTTPMiddleware, WebSocketMiddleware, MiddlewareCallable, MiddlewareType

__all__ = [
    # Throttle middleware
    'ThrottleMiddleware',
    'ThrottleConfig',
    'throttle_per_ip',
    'throttle_per_user',
    'DEFAULT_THROTTLE_CONFIGS',

    # Middleware resolver
    'MiddlewareResolver',
    'middleware_resolver',

    # Base middleware
    'HTTPMiddleware',
    'WebSocketMiddleware',
    'MiddlewareCallable',
    'MiddlewareType'
]

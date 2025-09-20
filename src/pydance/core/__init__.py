"""
PyDance Core - Minimal, solid framework core.

This module provides the fundamental building blocks:
- ASGI application (App)
- Fast routing (Router)
- Pluggable middleware (MiddlewareStack)
- Lightweight DI (Container)
- Type-safe with Pydantic
"""

# Core components
from pydance.core.server.application import Application as App, Application as Pydance
from pydance.core.http.request import Request
from pydance.core.http.response import Response
from pydance.core.routing import Router, Route, RouteGroup
from pydance.core.middleware import MiddlewareStack, cors_middleware, logging_middleware, json_middleware
from pydance.core.di import Container, DatabaseService, CacheService, LoggerService, setup_default_services
from pydance.core.config import Config
from pydance.core.types import ASGIApp, Scope, Receive, Send, Message

__all__ = [
    # Core App
    'App', 'Pydance', 'Request', 'Response',
    # Routing
    'Router', 'Route', 'RouteGroup',
    # Middleware
    'MiddlewareStack', 'cors_middleware', 'logging_middleware', 'json_middleware',
    # DI
    'Container', 'DatabaseService', 'CacheService', 'LoggerService', 'setup_default_services',
    # Config & Types
    'Config', 'ASGIApp', 'Scope', 'Receive', 'Send', 'Message'
]

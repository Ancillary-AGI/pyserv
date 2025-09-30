"""
Pyserv - Enterprise-grade Python web framework

A high-performance, secure web framework with optional C/C++ extensions
for building scalable web applications and microservices.

Features:
- ASGI-compliant application server
- High-performance routing and middleware
- Enterprise security features
- Database ORM with multiple backends
- Template engine with Jinja2 support
- WebSocket and SSE support
- Internationalization (i18n)
- Microservices and IoT support
- AI/ML integration (NeuralForge)
- Comprehensive monitoring and observability

Example:
    >>> from pyserv import Application, Response
    >>> 
    >>> app = Application()
    >>> 
    >>> @app.route('/')
    >>> async def hello(request):
    ...     return Response.text('Hello, World!')
    >>> 
    >>> if __name__ == '__main__':
    ...     app.run()
"""

__version__ = "0.1.0"
__author__ = "Pyserv Team"
__email__ = "team@pyserv.dev"

# Core framework components
from pyserv.server.application import Application
from pyserv.server.config import AppConfig
from pyserv.http import Request, Response
from pyserv.routing import Router, Route
from pyserv.exceptions import HTTPException, BadRequest, NotFound, Forbidden

# Essential middleware
from pyserv.middleware import HTTPMiddleware, WebSocketMiddleware

# Template engine
from pyserv.templating import TemplateEngine

# Database and models
from pyserv.models import BaseModel
from pyserv.database import DatabaseConnection

# Security (core only)
from pyserv.security import SecurityManager, get_security_manager

# Authentication
from pyserv.auth import AuthManager, login_required

# Events and plugins
from pyserv.events import EventBus, Event
from pyserv.plugins import PluginManager

# WebSocket support
from pyserv.websocket import WebSocket

# Utilities
from pyserv.utils.di import Container

__all__ = [
    # Core framework
    "Application", "AppConfig", "Request", "Response",
    "Router", "Route", "HTTPException", "BadRequest", "NotFound", "Forbidden",
    
    # Middleware
    "HTTPMiddleware", "WebSocketMiddleware",
    
    # Templates and models
    "TemplateEngine", "BaseModel", "DatabaseConnection",
    
    # Security and auth
    "SecurityManager", "get_security_manager", "AuthManager", "login_required",
    
    # Events and plugins
    "EventBus", "Event", "PluginManager",
    
    # WebSocket
    "WebSocket",
    
    # Utilities
    "Container",
    
    # Version info
    "__version__", "__author__", "__email__",
]

# Convenience alias
Pyserv = Application
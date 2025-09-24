"""
Route group functionality for Pyserv  routing system.
"""

from typing import Callable, List, Optional, Dict, Any, Union, Set
from pyserv.routing.route import Route


class RouteGroup:
    """
    Route group for organizing routes with common prefix and middleware.

    Features:
    - Common prefix for all routes
    - Shared middleware for all routes in group
    - Nested groups support
    """

    def __init__(self, router: 'Router', prefix: str, middleware: Optional[List[Callable]] = None):
        self.router = router
        self.prefix = prefix.rstrip('/')
        self.middleware = middleware or []

    def add_route(
        self,
        path: str,
        handler: Callable,
        methods: Optional[Union[List[str], Set[str]]] = None,
        name: Optional[str] = None,
        middleware: Optional[List[Callable]] = None,
        **kwargs
    ) -> Route:
        """Add route to group with prefix and combined middleware."""
        full_path = f"{self.prefix}{path}"
        combined_middleware = self.middleware + (middleware or [])
        return self.router.add_route(
            full_path, handler, methods, name,
            combined_middleware, **kwargs
        )

    def add_websocket_route(
        self,
        path: str,
        handler: Callable,
        name: Optional[str] = None,
        middleware: Optional[List[Callable]] = None,
        **kwargs
    ) -> Route:
        """Add WebSocket route to group."""
        full_path = f"{self.prefix}{path}"
        combined_middleware = self.middleware + (middleware or [])
        return self.router.add_websocket_route(
            full_path, handler, name, combined_middleware, **kwargs
        )

    def add(self, path: str, handler: Callable, methods: Optional[List[str]] = None) -> None:
        """Legacy method for backward compatibility."""
        self.add_route(path, handler, methods)

    def group(self, sub_prefix: str, middleware: Optional[List[Callable]] = None) -> 'RouteGroup':
        """Create nested route group."""
        full_prefix = f"{self.prefix}{sub_prefix}"
        combined_middleware = self.middleware + (middleware or [])
        return RouteGroup(self.router, full_prefix, combined_middleware)

    def route(self, path: str, methods: Optional[List[str]] = None, name: Optional[str] = None, middleware: Optional[List] = None):
        """Decorator for adding routes to the group"""
        def decorator(func: Callable) -> Callable:
            self.add_route(path, func, methods, name, middleware)
            return func
        return decorator


# Convenience functions for common HTTP methods
def get(path: str, **kwargs):
    """Decorator for GET routes."""
    def decorator(handler):
        handler._route_methods = ["GET"]
        handler._route_path = path
        handler._route_kwargs = kwargs
        return handler
    return decorator

def post(path: str, **kwargs):
    """Decorator for POST routes."""
    def decorator(handler):
        handler._route_methods = ["POST"]
        handler._route_path = path
        handler._route_kwargs = kwargs
        return handler
    return decorator

def put(path: str, **kwargs):
    """Decorator for PUT routes."""
    def decorator(handler):
        handler._route_methods = ["PUT"]
        handler._route_path = path
        handler._route_kwargs = kwargs
        return handler
    return decorator

def delete(path: str, **kwargs):
    """Decorator for DELETE routes."""
    def decorator(handler):
        handler._route_methods = ["DELETE"]
        handler._route_path = path
        handler._route_kwargs = kwargs
        return handler
    return decorator

def patch(path: str, **kwargs):
    """Decorator for PATCH routes."""
    def decorator(handler):
        handler._route_methods = ["PATCH"]
        handler._route_path = path
        handler._route_kwargs = kwargs
        return handler
    return decorator

def websocket(path: str, **kwargs):
    """Decorator for WebSocket routes."""
    def decorator(handler):
        handler._websocket_path = path
        handler._websocket_kwargs = kwargs
        return handler
    return decorator

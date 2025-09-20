"""
Route group functionality for PyDance routing system.
"""

from typing import Callable, List, Optional, Dict, Any


class RouteGroup:
    """Route group for organizing routes with common attributes"""

    def __init__(self, router: 'Router', prefix: str = "", middleware: Optional[List] = None, name_prefix: str = ""):
        self.router = router
        self.prefix = prefix.rstrip('/')
        self.middleware = middleware or []
        self.name_prefix = name_prefix

    def add_route(self, path: str, handler: Callable, methods: Optional[List[str]] = None, name: Optional[str] = None, middleware: Optional[List] = None):
        """Add a route to the group"""
        full_path = f"{self.prefix}{path}" if self.prefix else path
        full_name = f"{self.name_prefix}{name}" if name and self.name_prefix else name
        combined_middleware = self.middleware + (middleware or [])

        return self.router.add_route(full_path, handler, methods, full_name, combined_middleware)

    def route(self, path: str, methods: Optional[List[str]] = None, name: Optional[str] = None, middleware: Optional[List] = None):
        """Decorator for adding routes to the group"""
        def decorator(func: Callable) -> Callable:
            self.add_route(path, func, methods, name, middleware)
            return func
        return decorator

    def group(self, prefix: str = "", middleware: Optional[List] = None, name_prefix: str = "") -> 'RouteGroup':
        """Create a nested route group"""
        full_prefix = f"{self.prefix}/{prefix.lstrip('/')}" if prefix else self.prefix
        combined_middleware = self.middleware + (middleware or [])
        full_name_prefix = f"{self.name_prefix}{name_prefix}" if name_prefix else self.name_prefix

        return RouteGroup(self.router, full_prefix, combined_middleware, full_name_prefix)

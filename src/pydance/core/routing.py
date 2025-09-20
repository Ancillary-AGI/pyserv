"""
PyDance Core Routing - High-performance ASGI router with advanced features.

This module provides a comprehensive routing system for PyDance applications,
featuring fast pattern matching, parameter extraction, middleware support,
and flexible route organization.

Features:
- High-performance regex-based pattern matching
- Path parameter extraction with type conversion
- HTTP method filtering
- Route groups and prefixes
- Middleware support per route
- WebSocket route handling
- Caching for improved performance
- Type-safe route definitions
"""

import re
import asyncio
from typing import Dict, List, Optional, Tuple, Callable, Any, Pattern, Union, Set
from dataclasses import dataclass, field
from functools import lru_cache
from urllib.parse import unquote
from enum import Enum


class RouteType(Enum):
    """Types of routes"""
    NORMAL = "normal"
    REDIRECT = "redirect"
    VIEW = "view"
    FALLBACK = "fallback"
    INTENDED = "intended"


@dataclass
class RouteMatch:
    """Route match result with enhanced metadata."""
    handler: Callable
    params: Dict[str, Any] = field(default_factory=dict)
    route: Optional['Route'] = None
    middleware: List[Callable] = field(default_factory=list)


@dataclass
class RouteConfig:
    """Configuration for route behavior."""
    methods: Set[str] = field(default_factory=lambda: {"GET"})
    name: Optional[str] = None
    middleware: List[Callable] = field(default_factory=list)
    cache_timeout: Optional[int] = None
    priority: int = 0


class Route:
    """
    Enhanced route with advanced pattern matching and middleware support.

    Features:
    - Regex pattern compilation with parameter extraction
    - Type conversion for path parameters
    - Middleware pipeline per route
    - Caching support
    - Priority-based matching
    """

    def __init__(
        self,
        path: str,
        handler: Callable,
        methods: Optional[Union[List[str], Set[str]]] = None,
        name: Optional[str] = None,
        middleware: Optional[List[Callable]] = None,
        **kwargs
    ):
        self.path = path
        self.handler = handler
        self.name = name or f"{handler.__module__}.{handler.__name__}"
        self.methods = set(methods or ["GET"])
        self.middleware = middleware or []
        self.config = RouteConfig(
            methods=self.methods,
            name=name,
            middleware=self.middleware,
            **kwargs
        )

        # Pattern compilation
        self.pattern: Optional[Pattern] = None
        self.param_names: List[str] = []
        self.param_types: Dict[str, type] = {}
        self._compile_pattern()

    def _compile_pattern(self) -> None:
        """Compile regex pattern with enhanced parameter handling."""
        # Convert path parameters like {id:int} or {id} to regex groups
        pattern = self.path

        # Handle typed parameters like {id:int}, {name:str}, etc.
        typed_param_pattern = r'\{([^:}]+):([^}]+)\}'
        def typed_param_replacer(match):
            param_name = match.group(1)
            param_type = match.group(2)
            self.param_names.append(param_name)
            self.param_types[param_name] = self._get_type_from_string(param_type)
            return f'(?P<{param_name}>[^/]+)'

        pattern = re.sub(typed_param_pattern, typed_param_replacer, pattern)

        # Handle regular parameters like {id}
        simple_param_pattern = r'\{([^}]+)\}'
        def simple_param_replacer(match):
            param_name = match.group(1)
            if param_name not in self.param_names:
                self.param_names.append(param_name)
                self.param_types[param_name] = str  # Default to string
            return f'(?P<{param_name}>[^/]+)'

        pattern = re.sub(simple_param_pattern, simple_param_replacer, pattern)

        # Escape other special regex characters
        pattern = re.sub(r'([.+^$()])', r'\\\1', pattern)
        # Convert wildcards
        pattern = pattern.replace('*', '.*')
        # Add start and end anchors
        pattern = f'^{pattern}$'

        self.pattern = re.compile(pattern)

    def _get_type_from_string(self, type_str: str) -> type:
        """Convert string type representation to actual type."""
        type_map = {
            'int': int,
            'str': str,
            'float': float,
            'bool': bool,
            'uuid': str,  # UUID as string for simplicity
        }
        return type_map.get(type_str.lower(), str)

    def match(self, path: str, method: str) -> Optional[Dict[str, Any]]:
        """
        Match path against route pattern with type conversion.

        Returns:
            Dictionary of converted parameters or None if no match
        """
        if method not in self.methods:
            return None

        match = self.pattern.match(unquote(path))
        if not match:
            return None

        params = {}
        for param_name, param_value in match.groupdict().items():
            param_type = self.param_types.get(param_name, str)
            try:
                if param_type == bool:
                    params[param_name] = param_value.lower() in ('true', '1', 'yes', 'on')
                elif param_type == int:
                    params[param_name] = int(param_value)
                elif param_type == float:
                    params[param_name] = float(param_value)
                else:
                    params[param_name] = param_value
            except (ValueError, TypeError):
                return None  # Type conversion failed

        return params

    async def execute_middleware(self, request: Any, call_next: Callable) -> Any:
        """Execute route-specific middleware pipeline."""
        if not self.middleware:
            return await call_next(request)

        async def dispatch(index: int, req: Any) -> Any:
            if index >= len(self.middleware):
                return await call_next(req)

            middleware = self.middleware[index]

            async def next_middleware(next_req: Any) -> Any:
                return await dispatch(index + 1, next_req)

            if asyncio.iscoroutinefunction(middleware):
                return await middleware(req, next_middleware)
            else:
                return middleware(req, next_middleware)

        return await dispatch(0, request)


class Router:
    """
    High-performance ASGI router with advanced features.

    Features:
    - Fast pattern matching with caching
    - Type-safe parameter extraction
    - Middleware support per route
    - Route groups and prefixes
    - WebSocket route handling
    - Performance monitoring
    """

    def __init__(self):
        self.routes: List[Route] = []
        self.websocket_routes: List[Route] = []
        self._cache: Dict[str, Optional[RouteMatch]] = {}
        self._route_names: Dict[str, Route] = {}
        self._middleware_stack: List[Callable] = []

    def add_route(
        self,
        path: str,
        handler: Callable,
        methods: Optional[Union[List[str], Set[str]]] = None,
        name: Optional[str] = None,
        middleware: Optional[List[Callable]] = None,
        **kwargs
    ) -> Route:
        """Add HTTP route to router."""
        route = Route(path, handler, methods, name, middleware, **kwargs)
        self.routes.append(route)

        if name:
            self._route_names[name] = route

        # Clear cache when routes change
        self._cache.clear()
        return route

    def add_websocket_route(
        self,
        path: str,
        handler: Callable,
        name: Optional[str] = None,
        middleware: Optional[List[Callable]] = None,
        **kwargs
    ) -> Route:
        """Add WebSocket route to router."""
        route = Route(path, handler, ["GET"], name, middleware, **kwargs)
        self.websocket_routes.append(route)

        if name:
            self._route_names[name] = route

        self._cache.clear()
        return route

    def add(self, path: str, handler: Callable, methods: Optional[List[str]] = None) -> None:
        """Add route to router."""
        route = Route(path, handler, methods)
        self.routes.append(route)
        self._cache.clear()  # Clear cache when routes change

    def match(self, method: str, path: str) -> Tuple[Optional[Callable], Optional[Dict[str, Any]]]:
        """
        Match HTTP request to route with caching.

        Returns:
            Tuple of (handler, path_params) or (None, None) if no match
        """
        cache_key = f"{method}:{path}"

        # Check cache first
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if cached:
                return cached.handler, cached.params
            return None, None

        # Find matching route (sorted by priority)
        for route in sorted(self.routes, key=lambda r: r.config.priority, reverse=True):
            params = route.match(path, method)
            if params is not None:
                # Cache positive result
                self._cache[cache_key] = RouteMatch(route.handler, params, route, route.middleware)
                return route.handler, params

        # Cache negative result
        self._cache[cache_key] = None
        return None, None

    def match_websocket(self, path: str) -> Tuple[Optional[Callable], Optional[Dict[str, Any]]]:
        """Match WebSocket connection."""
        cache_key = f"WS:{path}"

        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if cached:
                return cached.handler, cached.params
            return None, None

        for route in self.websocket_routes:
            params = route.match(path, "GET")
            if params is not None:
                self._cache[cache_key] = RouteMatch(route.handler, params, route, route.middleware)
                return route.handler, params

        self._cache[cache_key] = None
        return None, None

    def get_route_by_name(self, name: str) -> Optional[Route]:
        """Get route by name."""
        return self._route_names.get(name)

    def reverse(self, name: str, **kwargs) -> Optional[str]:
        """Reverse route by name with parameters."""
        route = self.get_route_by_name(name)
        if not route:
            return None

        path = route.path
        for param_name, param_value in kwargs.items():
            placeholder = f"{{{param_name}}}"
            if placeholder in path:
                path = path.replace(placeholder, str(param_value))

        return path

    def group(self, prefix: str) -> 'RouteGroup':
        """Create route group with prefix."""
        return RouteGroup(self, prefix)

    def mount(self, path: str, other_router: 'Router') -> None:
        """Mount another router at the given path."""
        for route in other_router.routes:
            full_path = path.rstrip('/') + route.path
            self.add_route(full_path, route.handler, route.methods, route.name, route.middleware)

    def clear_cache(self) -> None:
        """Clear route matching cache."""
        self._cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get router statistics."""
        return {
            "total_routes": len(self.routes),
            "websocket_routes": len(self.websocket_routes),
            "cache_size": len(self._cache),
            "named_routes": len(self._route_names)
        }

    def add_permanent_redirect(self, from_path: str, to_path: str, name: Optional[str] = None):
        """Add a permanent redirect (301)."""
        def redirect_handler(request, **kwargs):
            from ..http.response import Response
            redirect_url = to_path
            # Replace parameters in redirect URL
            for key, value in kwargs.items():
                redirect_url = redirect_url.replace(f'{{{key}}}', str(value))
            return Response.redirect(redirect_url, 301)

        self.add_route(from_path, redirect_handler, name=name)

    def add_temporary_redirect(self, from_path: str, to_path: str, name: Optional[str] = None):
        """Add a temporary redirect (302)."""
        def redirect_handler(request, **kwargs):
            from ..http.response import Response
            redirect_url = to_path
            # Replace parameters in redirect URL
            for key, value in kwargs.items():
                redirect_url = redirect_url.replace(f'{{{key}}}', str(value))
            return Response.redirect(redirect_url, 302)

        self.add_route(from_path, redirect_handler, name=name)

    def find_route(self, path: str, method: str) -> Tuple[Optional[Route], Optional[Dict[str, str]]]:
        """Find a route that matches the given path and method (alias for match)."""
        handler, params = self.match(method, path)
        if handler:
            # Find the actual route object
            for route in self.routes:
                if route.handler == handler:
                    return route, params
        return None, None

    def url_for(self, name: str, **kwargs) -> Optional[str]:
        """Generate URL for a named route."""
        route = self.get_route_by_name(name)
        if not route:
            return None

        url = route.path
        for key, value in kwargs.items():
            url = url.replace(f'{{{key}}}', str(value))
        return url

    def add_view_route(self, path: str, view_class: Any, methods: Optional[List[str]] = None,
                      name: Optional[str] = None, middleware: Optional[List] = None,
                      view_kwargs: Optional[Dict[str, Any]] = None):
        """Add a view-based route"""
        def view_handler(request, **kwargs):
            view_instance = view_class(**view_kwargs or {})
            return view_instance.dispatch(request, **kwargs)

        self.add_route(path, view_handler, methods, name, middleware)

    def add_fallback_route(self, path: str, handler: Callable, methods: Optional[List[str]] = None,
                          name: Optional[str] = None, middleware: Optional[List] = None):
        """Add a fallback route that catches unmatched requests"""
        self.add_route(path, handler, methods, name, middleware)


class RouteGroup:
    """
    Route group for organizing routes with common prefix and middleware.

    Features:
    - Common prefix for all routes
    - Shared middleware for all routes in group
    - Nested groups support
    """

    def __init__(self, router: Router, prefix: str, middleware: Optional[List[Callable]] = None):
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

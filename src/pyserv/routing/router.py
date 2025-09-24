"""
Pyserv Router - High-performance ASGI router with advanced features.

Features:
- Fast pattern matching with caching
- Type-safe parameter extraction
- Middleware support per route
- Route groups and prefixes
- WebSocket route handling
- Performance monitoring
- Named routes and URL reversal
- Redirect support (301/302)
- View-based routes
- Fallback routes
"""

from typing import Callable, List, Optional, Dict, Any, Union, Set, Tuple
from dataclasses import dataclass, field
import re
import time
import logging
import os
from urllib.parse import urlparse, urljoin, urlencode

logger = logging.getLogger(__name__)

from .route import Route, WebSocketRoute
from .group import RouteGroup
from pyserv.middleware.base import MiddlewareType


@dataclass
class RouteMatch:
    """Route match result"""
    handler: Callable
    params: Dict[str, Any]
    route: 'Route'
    middleware: List[MiddlewareType]


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
    - Named routes and URL reversal
    - Redirect support (301/302)
    - View-based routes
    - Fallback routes
    """

    def __init__(self):
        self.routes: List[Route] = []
        self.websocket_routes: List[Route] = []
        self.mounted_routers: Dict[str, 'Router'] = {}
        self.named_routes: Dict[str, Route] = {}
        self._route_cache: Dict[str, Tuple[Optional[Route], Optional[Dict[str, str]]]] = {}
        self._cache_enabled = True
        self.fallback_route: Optional[Route] = None
        self.intended_url: Optional[str] = None
        self._redirects: Dict[str, str] = {}
        self._reverse_redirects: Dict[str, str] = {}

    def add_route(
        self,
        path: str,
        handler: Callable,
        methods: Optional[Union[List[str], Set[str]]] = None,
        name: Optional[str] = None,
        middleware: Optional[List[MiddlewareType]] = None,
        **kwargs
    ) -> Route:
        """Add HTTP route to router."""
        route = Route(path, handler, methods, name, middleware, **kwargs)
        self.routes.append(route)

        if name:
            self.named_routes[name] = route

        # Clear cache when routes change
        self._route_cache.clear()
        return route

    def add_websocket_route(
        self,
        path: str,
        handler: Callable,
        name: Optional[str] = None,
        middleware: Optional[List[MiddlewareType]] = None,
        **kwargs
    ) -> Route:
        """Add WebSocket route to router."""
        route = Route(path, handler, ["GET"], name, middleware, **kwargs)
        self.websocket_routes.append(route)

        if name:
            self.named_routes[name] = route

        self._route_cache.clear()
        return route

    def add(self, path: str, handler: Callable, methods: Optional[List[str]] = None) -> None:
        """Add route to router."""
        route = Route(path, handler, methods)
        self.routes.append(route)
        self._route_cache.clear()  # Clear cache when routes change

    def match(self, method: str, path: str) -> Optional[RouteMatch]:
        """
        Match HTTP request to route with caching.

        Returns:
            RouteMatch object or None if no match
        """
        cache_key = f"{method}:{path}"

        # Check cache first
        if cache_key in self._route_cache:
            cached = self._route_cache[cache_key]
            if cached:
                return cached
            return None

        # Check mounted routers first
        for mount_path, router in self.mounted_routers.items():
            if path.startswith(mount_path):
                remaining_path = path[len(mount_path):]
                match_result = router.match(method, remaining_path)
                if match_result:
                    if self._cache_enabled:
                        self._route_cache[cache_key] = match_result
                    return match_result

        # Find matching route (sorted by priority)
        for route in sorted(self.routes, key=lambda r: r.config.get('priority', 0), reverse=True):
            params = route.match(path, method)
            if params is not None:
                # Create RouteMatch object
                route_match = RouteMatch(
                    handler=route.handler,
                    params=params,
                    route=route,
                    middleware=route.middleware
                )
                # Cache positive result
                self._route_cache[cache_key] = route_match
                return route_match

        # Cache negative result
        self._route_cache[cache_key] = None
        return None

    def match_websocket(self, path: str) -> Optional[RouteMatch]:
        """Match WebSocket connection."""
        cache_key = f"WS:{path}"

        if cache_key in self._route_cache:
            cached = self._route_cache[cache_key]
            if cached:
                return cached
            return None

        for route in self.websocket_routes:
            params = route.match(path, "GET")
            if params is not None:
                # Create RouteMatch object for WebSocket
                route_match = RouteMatch(
                    handler=route.handler,
                    params=params,
                    route=route,
                    middleware=route.middleware
                )
                self._route_cache[cache_key] = route_match
                return route_match

        self._route_cache[cache_key] = None
        return None

    def get_route_by_name(self, name: str) -> Optional[Route]:
        """Get route by name."""
        return self.named_routes.get(name)

    def reverse(self, name: str, **kwargs) -> Optional[str]:
        """Reverse route by name with parameters."""
        route = self.get_route_by_name(name)
        if not route:
            return None

        path = route.path
        for param_name, param_value in kwargs.items():
            placeholder = f"<{param_name}>"
            if placeholder in path:
                path = path.replace(placeholder, str(param_value))

        return path

    def group(self, prefix: str = "", middleware: Optional[List] = None, name_prefix: str = "") -> 'RouteGroup':
        """Create route group with prefix."""
        return RouteGroup(self, prefix, middleware or [], name_prefix)

    def mount(self, path: str, other_router: 'Router') -> None:
        """Mount another router at the given path."""
        self.mounted_routers[path] = other_router

    def clear_cache(self) -> None:
        """Clear route matching cache."""
        self._route_cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get router statistics."""
        return {
            "total_routes": len(self.routes),
            "websocket_routes": len(self.websocket_routes),
            "mounted_routers": len(self.mounted_routers),
            "cache_size": len(self._route_cache),
            "named_routes": len(self.named_routes)
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

    def find_route(self, path: str, method: str) -> tuple[Optional[Route], Optional[Dict[str, str]]]:
        """Find a route that matches the given path and method (alias for match)."""
        match_result = self.match(method, path)
        if match_result:
            return match_result.route, match_result.params
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

    def set_intended_url(self, url: str) -> None:
        """Set the intended URL for post-login redirects"""
        self.intended_url = url

    def get_intended_url(self, default: str = "/") -> str:
        """Get the intended URL, clearing it after retrieval"""
        url = self.intended_url or default
        self.intended_url = None
        return url

    def remember_intended_url(self, request) -> None:
        """Remember the current URL as intended for post-login redirect"""
        if hasattr(request, 'url'):
            self.intended_url = str(request.url)


# Global router instance
_default_router = Router()

def get_router() -> Router:
    """Get the default router instance"""
    return _default_router

__all__ = ['Router', 'Route', 'RouteGroup', 'RouteMatch', 'get_router']

"""
Main Router class for PyDance routing system.
"""

from typing import Callable, Dict, List, Optional, Tuple, Any
from urllib.parse import urlparse, urljoin, urlencode

from .route import Route, WebSocketRoute
from .types import RouteType
from .group import RouteGroup


class Router:
    """Advanced Router for handling URL routing with redirects, views, and fallbacks"""

    def __init__(self):
        self.routes: List[Route] = []
        self.websocket_routes: List[WebSocketRoute] = []
        self.mounted_routers: Dict[str, 'Router'] = {}
        self.named_routes: Dict[str, Route] = {}
        self._route_cache: Dict[str, Tuple[Optional[Route], Optional[Dict[str, str]]]] = {}
        self._cache_enabled = True
        self.fallback_route: Optional[Route] = None
        self.intended_url: Optional[str] = None
        self._redirects: Dict[str, str] = {}
        self._reverse_redirects: Dict[str, str] = {}

    def add_route(self, path: str, handler: Callable, methods: Optional[List[str]] = None,
                  name: Optional[str] = None, middleware: Optional[List] = None,
                  route_type: RouteType = RouteType.NORMAL, redirect_to: Optional[str] = None,
                  redirect_code: int = 302, view_class: Optional[Any] = None,
                  view_kwargs: Optional[Dict[str, Any]] = None,
                  constraints: Optional[Dict[str, str]] = None,
                  defaults: Optional[Dict[str, Any]] = None,
                  host: Optional[str] = None, schemes: Optional[List[str]] = None):
        """Add a route to the router with advanced features"""
        route = Route(path, handler, methods, name, middleware, route_type,
                     redirect_to, redirect_code, view_class, view_kwargs,
                     constraints, defaults, host, schemes)
        self.routes.append(route)
        if name:
            self.named_routes[name] = route

        # Handle special route types
        if route_type == RouteType.FALLBACK:
            self.fallback_route = route

        # Clear cache when adding new routes
        self._route_cache.clear()

    def add_redirect(self, from_path: str, to_path: str, code: int = 302,
                    name: Optional[str] = None, methods: Optional[List[str]] = None):
        """Add a redirect route"""
        def redirect_handler(request, **kwargs):
            from ..http.response import Response
            redirect_url = to_path
            # Replace parameters in redirect URL
            for key, value in kwargs.items():
                redirect_url = redirect_url.replace(f'{{{key}}}', str(value))
            return Response.redirect(redirect_url, code)

        self.add_route(from_path, redirect_handler, methods or ["GET"], name,
                      route_type=RouteType.REDIRECT, redirect_to=to_path, redirect_code=code)

        # Store redirect mapping for reverse lookups
        self._redirects[from_path] = to_path
        self._reverse_redirects[to_path] = from_path

    def add_view_route(self, path: str, view_class: Any, methods: Optional[List[str]] = None,
                      name: Optional[str] = None, middleware: Optional[List] = None,
                      view_kwargs: Optional[Dict[str, Any]] = None):
        """Add a view-based route"""
        def view_handler(request, **kwargs):
            view_instance = view_class(**view_kwargs or {})
            return view_instance.dispatch(request, **kwargs)

        self.add_route(path, view_handler, methods, name, middleware,
                      route_type=RouteType.VIEW, view_class=view_class, view_kwargs=view_kwargs)

    def add_fallback_route(self, path: str, handler: Callable, methods: Optional[List[str]] = None,
                          name: Optional[str] = None, middleware: Optional[List] = None):
        """Add a fallback route that catches unmatched requests"""
        self.add_route(path, handler, methods, name, middleware, route_type=RouteType.FALLBACK)

    def set_intended_url(self, url: str):
        """Set the intended URL for post-login redirects"""
        self.intended_url = url

    def get_intended_url(self, default: str = "/") -> str:
        """Get the intended URL, clearing it after retrieval"""
        url = self.intended_url or default
        self.intended_url = None
        return url

    def remember_intended_url(self, request):
        """Remember the current URL as intended for post-login redirect"""
        if hasattr(request, 'url'):
            self.intended_url = str(request.url)

    def add_permanent_redirect(self, from_path: str, to_path: str, name: Optional[str] = None):
        """Add a permanent redirect (301)"""
        self.add_redirect(from_path, to_path, 301, name)

    def add_temporary_redirect(self, from_path: str, to_path: str, name: Optional[str] = None):
        """Add a temporary redirect (302)"""
        self.add_redirect(from_path, to_path, 302, name)

    def add_websocket_route(self, path: str, handler: Callable):
        """Add a WebSocket route to the router"""
        route = WebSocketRoute(path, handler)
        self.websocket_routes.append(route)

    def mount(self, path: str, router: 'Router'):
        """Mount another router at the specified path"""
        self.mounted_routers[path] = router

    def add_named_route(self, name: str, path: str, handler: Callable, methods: Optional[List[str]] = None, middleware: Optional[List] = None):
        """Add a named route"""
        return self.add_route(path, handler, methods, name, middleware)

    def get_route_by_name(self, name: str) -> Optional[Route]:
        """Get a route by its name"""
        return self.named_routes.get(name)

    def url_for(self, name: str, **kwargs) -> Optional[str]:
        """Generate URL for a named route"""
        route = self.get_route_by_name(name)
        if not route:
            return None

        url = route.path
        for key, value in kwargs.items():
            url = url.replace(f'{{{key}}}', str(value))
        return url

    def group(self, prefix: str = "", middleware: Optional[List] = None, name_prefix: str = "") -> RouteGroup:
        """Create a route group with common attributes"""
        return RouteGroup(self, prefix, middleware or [], name_prefix)

    def enable_cache(self):
        """Enable route caching"""
        self._cache_enabled = True

    def disable_cache(self):
        """Disable route caching"""
        self._cache_enabled = False
        self._route_cache.clear()

    def clear_cache(self):
        """Clear the route cache"""
        self._route_cache.clear()

    def find_route(self, path: str, method: str) -> Tuple[Optional[Route], Optional[Dict[str, str]]]:
        """Find a route that matches the given path and method"""
        cache_key = f"{method}:{path}"

        # Check cache first
        if self._cache_enabled and cache_key in self._route_cache:
            return self._route_cache[cache_key]

        # Check mounted routers first
        for mount_path, router in self.mounted_routers.items():
            if path.startswith(mount_path):
                remaining_path = path[len(mount_path):]
                route, params = router.find_route(remaining_path, method)
                if route:
                    if self._cache_enabled:
                        self._route_cache[cache_key] = (route, params)
                    return route, params

        # Check local routes
        for route in self.routes:
            if method in route.methods:
                params = route.match(path)
                if params is not None:
                    if self._cache_enabled:
                        self._route_cache[cache_key] = (route, params)
                    return route, params

        # Cache negative result
        if self._cache_enabled:
            self._route_cache[cache_key] = (None, None)

        return None, None

    def find_websocket_route(self, path: str) -> Tuple[Optional[WebSocketRoute], Optional[Dict[str, str]]]:
        """Find a WebSocket route that matches the given path"""
        # Check mounted routers first
        for mount_path, router in self.mounted_routers.items():
            if path.startswith(mount_path):
                remaining_path = path[len(mount_path):]
                route, params = router.find_websocket_route(remaining_path)
                if route:
                    return route, params

        # Check local WebSocket routes
        for route in self.websocket_routes:
            params = route.match(path)
            if params is not None:
                return route, params
        return None, None

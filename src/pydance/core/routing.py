# server_framework/core/routing.py
import re
from typing import Callable, Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

@dataclass
class Route:
    path: str
    handler: Callable
    methods: List[str]
    pattern: re.Pattern
    name: Optional[str] = None
    middleware: Optional[List] = None

    def __init__(self, path: str, handler: Callable, methods: Optional[List[str]] = None, name: Optional[str] = None, middleware: Optional[List] = None):
        self.path = path
        self.handler = handler
        self.methods = methods or ["GET"]
        self.name = name
        self.middleware = middleware or []
        self.pattern = self._compile_pattern(path)
        
    def _compile_pattern(self, path: str) -> re.Pattern:
        # Convert route path to regex pattern
        pattern = re.sub(r'\{(\w+)\}', r'(?P<\1>[^/]+)', path)
        return re.compile(f'^{pattern}$')
        
    def match(self, path: str) -> Optional[Dict[str, str]]:
        """Check if this route matches the given path"""
        match = self.pattern.match(path)
        if match:
            return match.groupdict()
        return None

@dataclass
class WebSocketRoute:
    path: str
    handler: Callable
    pattern: re.Pattern
    
    def __init__(self, path: str, handler: Callable):
        self.path = path
        self.handler = handler
        self.pattern = self._compile_pattern(path)
        
    def _compile_pattern(self, path: str) -> re.Pattern:
        # Convert route path to regex pattern
        pattern = re.sub(r'\{(\w+)\}', r'(?P<\1>[^/]+)', path)
        return re.compile(f'^{pattern}$')
        
    def match(self, path: str) -> Optional[Dict[str, str]]:
        """Check if this route matches the given path"""
        match = self.pattern.match(path)
        if match:
            return match.groupdict()
        return None

class Router:
    """Router for handling URL routing"""

    def __init__(self):
        self.routes: List[Route] = []
        self.websocket_routes: List[WebSocketRoute] = []
        self.mounted_routers: Dict[str, 'Router'] = {}
        self.named_routes: Dict[str, Route] = {}
        self._route_cache: Dict[str, Tuple[Optional[Route], Optional[Dict[str, str]]]] = {}
        self._cache_enabled = True
        
    def add_route(self, path: str, handler: Callable, methods: Optional[List[str]] = None, name: Optional[str] = None, middleware: Optional[List] = None):
        """Add a route to the router"""
        route = Route(path, handler, methods, name, middleware)
        self.routes.append(route)
        if name:
            self.named_routes[name] = route
        # Clear cache when adding new routes
        self._route_cache.clear()

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

    def group(self, prefix: str = "", middleware: Optional[List] = None, name_prefix: str = "") -> 'RouteGroup':
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


class RouteGroup:
    """Route group for organizing routes with common attributes"""

    def __init__(self, router: Router, prefix: str = "", middleware: Optional[List] = None, name_prefix: str = ""):
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

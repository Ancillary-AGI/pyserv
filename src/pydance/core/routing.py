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
    
    def __init__(self, path: str, handler: Callable, methods: Optional[List[str]] = None):
        self.path = path
        self.handler = handler
        self.methods = methods or ["GET"]
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
        
    def add_route(self, path: str, handler: Callable, methods: Optional[List[str]] = None):
        """Add a route to the router"""
        route = Route(path, handler, methods)
        self.routes.append(route)
        
    def add_websocket_route(self, path: str, handler: Callable):
        """Add a WebSocket route to the router"""
        route = WebSocketRoute(path, handler)
        self.websocket_routes.append(route)
    
    def mount(self, path: str, router: 'Router'):
        """Mount another router at the specified path"""
        self.mounted_routers[path] = router
        
    def find_route(self, path: str, method: str) -> Tuple[Optional[Route], Optional[Dict[str, str]]]:
        """Find a route that matches the given path and method"""
        # Check mounted routers first
        for mount_path, router in self.mounted_routers.items():
            if path.startswith(mount_path):
                remaining_path = path[len(mount_path):]
                route, params = router.find_route(remaining_path, method)
                if route:
                    return route, params
        
        # Check local routes
        for route in self.routes:
            if method in route.methods:
                params = route.match(path)
                if params is not None:
                    return route, params
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
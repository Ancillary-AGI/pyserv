"""
Route classes for PyDance routing system.
"""

import re
from typing import Callable, Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass


@dataclass
class Route:
    path: str
    handler: Callable
    methods: List[str]
    pattern: re.Pattern
    name: Optional[str] = None
    middleware: Optional[List] = None
    route_type: 'RouteType' = None  # Forward reference
    redirect_to: Optional[str] = None
    redirect_code: int = 302
    view_class: Optional[Any] = None
    view_kwargs: Optional[Dict[str, Any]] = None
    constraints: Optional[Dict[str, str]] = None
    defaults: Optional[Dict[str, Any]] = None
    host: Optional[str] = None
    schemes: Optional[List[str]] = None

    def __init__(self, path: str, handler: Callable, methods: Optional[List[str]] = None,
                 name: Optional[str] = None, middleware: Optional[List] = None,
                 route_type: 'RouteType' = None, redirect_to: Optional[str] = None,
                 redirect_code: int = 302, view_class: Optional[Any] = None,
                 view_kwargs: Optional[Dict[str, Any]] = None,
                 constraints: Optional[Dict[str, str]] = None,
                 defaults: Optional[Dict[str, Any]] = None,
                 host: Optional[str] = None, schemes: Optional[List[str]] = None):
        from .types import RouteType  # Import here to avoid circular import
        self.path = path
        self.handler = handler
        self.methods = methods or ["GET"]
        self.name = name
        self.middleware = middleware or []
        self.route_type = route_type or RouteType.NORMAL
        self.redirect_to = redirect_to
        self.redirect_code = redirect_code
        self.view_class = view_class
        self.view_kwargs = view_kwargs or {}
        self.constraints = constraints or {}
        self.defaults = defaults or {}
        self.host = host
        self.schemes = schemes or []
        self.pattern = self._compile_pattern(path)

    def _compile_pattern(self, path: str) -> re.Pattern:
        """Convert route path to regex pattern with constraints"""
        # Handle constraints
        pattern = path
        for param, constraint in self.constraints.items():
            pattern = pattern.replace(f'{{{param}}}', f'(?P<{param}>{constraint})')

        # Convert remaining parameters to generic pattern
        pattern = re.sub(r'\{(\w+)\}', r'(?P<\1>[^/]+)', pattern)
        return re.compile(f'^{pattern}$')

    def match(self, path: str, method: str = "GET", host: str = None,
              scheme: str = None) -> Optional[Dict[str, str]]:
        """Check if this route matches the given path with all constraints"""
        # Check method
        if method not in self.methods:
            return None

        # Check host constraint
        if self.host and host != self.host:
            return None

        # Check scheme constraint
        if self.schemes and scheme not in self.schemes:
            return None

        # Check path pattern
        match = self.pattern.match(path)
        if not match:
            return None

        params = match.groupdict()

        # Apply defaults for missing parameters
        for key, default_value in self.defaults.items():
            if key not in params:
                params[key] = default_value

        return params

    def get_redirect_url(self, params: Dict[str, str] = None) -> Optional[str]:
        """Get the redirect URL for redirect routes"""
        if not self.redirect_to:
            return None

        if not params:
            return self.redirect_to

        # Replace parameters in redirect URL
        redirect_url = self.redirect_to
        for key, value in params.items():
            redirect_url = redirect_url.replace(f'{{{key}}}', str(value))

        return redirect_url


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

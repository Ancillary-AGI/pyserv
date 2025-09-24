"""
Middleware Resolver for PyServ Framework.

This module provides Laravel-style middleware resolution, allowing middleware
to be specified as strings and resolved to actual middleware instances.
"""

from typing import Dict, Any, List, Union, Callable, Optional
from .throttle import ThrottleMiddleware


class MiddlewareResolver:
    """
    Resolves middleware from strings to instances.

    String-based middleware resolution:
    - 'throttle:100,10' -> ThrottleMiddleware with capacity=100, refill_rate=10
    - 'auth' -> Authentication middleware (when implemented)
    - 'cors' -> CORS middleware (when implemented)
    """

    def __init__(self):
        self._middleware_map: Dict[str, Callable] = {
            'throttle': self._resolve_throttle,
        }
        self._instances: Dict[str, Any] = {}

    def register(self, name: str, resolver: Callable):
        """Register a custom middleware resolver"""
        self._middleware_map[name] = resolver

    def resolve(self, middleware_spec: Union[str, Callable, type]) -> Optional[Callable]:
        """
        Resolve middleware specification to middleware instance.

        Args:
            middleware_spec: String like 'throttle:100,10' or middleware class/instance

        Returns:
            Middleware instance or None if resolution fails
        """
        if callable(middleware_spec):
            return middleware_spec

        if isinstance(middleware_spec, str):
            return self._resolve_string(middleware_spec)

        return None

    def _resolve_string(self, middleware_string: str) -> Optional[Callable]:
        """Resolve string-based middleware specification"""
        # Check cache first
        if middleware_string in self._instances:
            return self._instances[middleware_string]

        # Parse middleware string
        if ':' in middleware_string:
            name, params = middleware_string.split(':', 1)
            name = name.strip()
        else:
            name = middleware_string.strip()
            params = ''

        # Find resolver
        resolver = self._middleware_map.get(name)
        if not resolver:
            return None

        # Resolve and cache
        try:
            instance = resolver(params)
            self._instances[middleware_string] = instance
            return instance
        except Exception:
            return None

    def _resolve_throttle(self, params: str) -> ThrottleMiddleware:
        """Resolve throttle middleware from parameters"""
        return ThrottleMiddleware.from_string(f"throttle:{params}")

    def resolve_list(self, middleware_specs: List[Union[str, Callable, type]]) -> List[Callable]:
        """Resolve a list of middleware specifications"""
        resolved = []
        for spec in middleware_specs:
            middleware = self.resolve(spec)
            if middleware:
                resolved.append(middleware)
        return resolved

    def clear_cache(self):
        """Clear the middleware instance cache"""
        self._instances.clear()


# Global middleware resolver instance
middleware_resolver = MiddlewareResolver()

# Register common middleware resolvers
def register_builtin_middleware():
    """Register built-in middleware resolvers"""
    # Throttle middleware is already registered
    pass

# Initialize built-in middleware
register_builtin_middleware()


__all__ = [
    'MiddlewareResolver',
    'middleware_resolver'
]

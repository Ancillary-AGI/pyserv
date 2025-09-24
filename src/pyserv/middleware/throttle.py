"""
Throttle Middleware for PyServ Framework.

This middleware provides customizable rate limiting using the PyServ rate limiter.
It supports different rate limiting strategies, custom key functions, and
configurable responses for rate-limited requests.

Usage patterns:
    # Global middleware (applies to all routes)
    app.add_middleware(ThrottleMiddleware.per_ip())

    # Route-specific middleware
    @app.route('/api/data', middleware=['throttle:100,1'])
    def api_data(request):
        return {"data": "success"}

    # Controller middleware (applies to all methods in controller)
    class APIController(Controller):
        middleware = ['throttle:1000,10']

        def get_data(self, request):
            return {"data": "success"}

        def post_data(self, request):
            return {"created": True}
"""

import time
from typing import Callable, Dict, Any, Optional, Union, List
from dataclasses import dataclass

from pyserv.utils.rate_limiting import (
    RateLimiter, RateLimitConfig, RateLimitResult,
    RateLimitAlgorithm, RateLimitExceeded
)
from pyserv.http.response import Response
from pyserv.middleware.base import HTTPMiddleware
from pyserv.types.routing import HandlerType


@dataclass
class ThrottleConfig:
    """Configuration for throttle middleware"""

    # Rate limiting settings
    capacity: int = 100
    refill_rate: float = 10.0
    algorithm: RateLimitAlgorithm = RateLimitAlgorithm.TOKEN_BUCKET
    window_size: int = 60

    # Key generation
    key_func: Optional[Callable] = None
    key_prefix: str = "throttle"

    # Response customization
    status_code: int = 429
    error_message: str = "Rate limit exceeded"
    retry_after_header: bool = True
    rate_limit_headers: bool = True

    # Exemptions
    exempt_paths: List[str] = None
    exempt_methods: List[str] = None
    exempt_users: List[str] = None

    # Callbacks
    on_throttled: Optional[Callable] = None
    on_allowed: Optional[Callable] = None

    def __post_init__(self):
        if self.exempt_paths is None:
            self.exempt_paths = []
        if self.exempt_methods is None:
            self.exempt_methods = []
        if self.exempt_users is None:
            self.exempt_users = []


class ThrottleMiddleware(HTTPMiddleware):
    """
    Customizable throttle middleware using PyServ rate limiter.

    Features:
    - Multiple rate limiting algorithms
    - Custom key functions (IP, user, endpoint, etc.)
    - Configurable responses
    - Path/method/user exemptions
    - Event callbacks
    - Rate limit headers
    - Laravel-style middleware strings: 'throttle:100,10'
    """

    def __init__(self, config: ThrottleConfig = None):
        self.config = config or ThrottleConfig()
        self._rate_limiter = self._create_rate_limiter()

    @classmethod
    def from_string(cls, middleware_string: str) -> 'ThrottleMiddleware':
        """
        Create middleware from Laravel-style string.

        Examples:
            'throttle:100,10'     # 100 requests, 10 per second
            'throttle:1000,100'   # 1000 requests, 100 per second
            'throttle:50,5'       # 50 requests, 5 per second
        """
        if not middleware_string.startswith('throttle:'):
            raise ValueError(f"Invalid throttle middleware string: {middleware_string}")

        params = middleware_string[9:]  # Remove 'throttle:'
        try:
            capacity_str, refill_rate_str = params.split(',')
            capacity = int(capacity_str.strip())
            refill_rate = float(refill_rate_str.strip())
        except (ValueError, IndexError):
            raise ValueError(f"Invalid throttle parameters: {params}. Expected 'capacity,refill_rate'")

        config = ThrottleConfig(capacity=capacity, refill_rate=refill_rate)
        return cls(config)

    def _create_rate_limiter(self) -> RateLimiter:
        """Create the rate limiter instance"""
        rate_config = RateLimitConfig(
            algorithm=self.config.algorithm,
            capacity=self.config.capacity,
            refill_rate=self.config.refill_rate,
            window_size=self.config.window_size
        )

        # Create key function
        key_func = self.config.key_func or self._default_key_func

        return RateLimiter(
            config=rate_config,
            key_func=lambda req: f"{self.config.key_prefix}:{key_func(req)}"
        )

    def _default_key_func(self, request) -> str:
        """Default key function using client IP"""
        if hasattr(request, 'remote_addr'):
            return request.remote_addr or 'unknown'
        elif hasattr(request, 'client_ip'):
            return request.client_ip or 'unknown'
        elif hasattr(request, 'client'):
            return request.client.host or 'unknown'
        else:
            return 'default'

    def _is_exempt(self, request) -> bool:
        """Check if request is exempt from rate limiting"""
        # Check path exemptions
        if hasattr(request, 'path'):
            path = request.path
            for exempt_path in self.config.exempt_paths:
                if path.startswith(exempt_path):
                    return True

        # Check method exemptions
        if hasattr(request, 'method'):
            method = request.method.upper()
            if method in [m.upper() for m in self.config.exempt_methods]:
                return True

        # Check user exemptions
        if hasattr(request, 'user') and request.user:
            user_id = getattr(request.user, 'id', str(request.user))
            if user_id in self.config.exempt_users:
                return True

        return False

    def _create_error_response(self, result: RateLimitResult) -> Response:
        """Create error response for rate limited requests"""
        response_data = {
            'error': 'rate_limit_exceeded',
            'message': self.config.error_message,
            'retry_after': result.retry_after
        }

        response = Response.json(response_data, status=self.config.status_code)

        # Add rate limit headers
        if self.config.rate_limit_headers:
            response.headers['X-RateLimit-Limit'] = str(result.limit)
            response.headers['X-RateLimit-Remaining'] = str(result.remaining)
            response.headers['X-RateLimit-Reset'] = str(int(result.reset_time))

        # Add retry after header
        if self.config.retry_after_header and result.retry_after:
            response.headers['Retry-After'] = str(int(result.retry_after))

        return response

    async def __call__(self, request, handler: HandlerType):
        """Middleware entry point"""
        # Check exemptions
        if self._is_exempt(request):
            return await handler(request)

        # Check rate limit
        result = await self._rate_limiter.check_limit(request)

        # Call allowed callback
        if result.allowed and self.config.on_allowed:
            try:
                await self.config.on_allowed(request, result)
            except Exception:
                pass  # Don't let callback errors break the request

        # Handle rate limited request
        if not result.allowed:
            # Call throttled callback
            if self.config.on_throttled:
                try:
                    await self.config.on_throttled(request, result)
                except Exception:
                    pass  # Don't let callback errors break the response

            return self._create_error_response(result)

        # Process the request
        response = await handler(request)

        # Add rate limit headers to successful responses
        if self.config.rate_limit_headers and hasattr(response, 'headers'):
            response.headers['X-RateLimit-Limit'] = str(result.limit)
            response.headers['X-RateLimit-Remaining'] = str(result.remaining)
            response.headers['X-RateLimit-Reset'] = str(int(result.reset_time))

        return response

    # Convenience methods for different configurations
    @classmethod
    def per_ip(cls, capacity: int = 100, refill_rate: float = 10.0) -> 'ThrottleMiddleware':
        """Create IP-based rate limiter"""
        config = ThrottleConfig(
            capacity=capacity,
            refill_rate=refill_rate,
            key_prefix="ip"
        )
        return cls(config)

    @classmethod
    def per_user(cls, capacity: int = 1000, refill_rate: float = 100.0) -> 'ThrottleMiddleware':
        """Create user-based rate limiter"""
        config = ThrottleConfig(
            capacity=capacity,
            refill_rate=refill_rate,
            key_func=lambda req: getattr(req.user, 'id', 'anonymous') if req.user else 'anonymous',
            key_prefix="user"
        )
        return cls(config)

    @classmethod
    def per_endpoint(cls, capacity: int = 50, refill_rate: float = 5.0) -> 'ThrottleMiddleware':
        """Create endpoint-based rate limiter"""
        config = ThrottleConfig(
            capacity=capacity,
            refill_rate=refill_rate,
            key_func=lambda req: f"{req.method}:{req.path}",
            key_prefix="endpoint"
        )
        return cls(config)

    # Management methods
    async def reset_limit(self, request) -> bool:
        """Reset rate limit for a specific request"""
        return await self._rate_limiter.reset_limit(request)

    def get_stats(self, request) -> Dict[str, Any]:
        """Get rate limiting statistics for a request"""
        return self._rate_limiter.get_stats(request)


# Convenience functions for common configurations
def throttle_per_ip(capacity: int = 100, refill_rate: float = 10.0):
    """Decorator to apply IP-based throttling to a route"""
    middleware = ThrottleMiddleware.per_ip(capacity, refill_rate)
    def decorator(handler):
        async def wrapper(request):
            return await middleware(request, handler)
        return wrapper
    return decorator


def throttle_per_user(capacity: int = 1000, refill_rate: float = 100.0):
    """Decorator to apply user-based throttling to a route"""
    middleware = ThrottleMiddleware.per_user(capacity, refill_rate)
    def decorator(handler):
        async def wrapper(request):
            return await middleware(request, handler)
        return wrapper
    return decorator


# Example usage configurations
DEFAULT_THROTTLE_CONFIGS = {
    'strict': ThrottleConfig(capacity=10, refill_rate=1),
    'normal': ThrottleConfig(capacity=100, refill_rate=10),
    'lenient': ThrottleConfig(capacity=1000, refill_rate=100),
    'api': ThrottleConfig(
        capacity=500,
        refill_rate=50,
        exempt_paths=['/health', '/metrics'],
        exempt_methods=['OPTIONS']
    )
}


__all__ = [
    'ThrottleMiddleware',
    'ThrottleConfig',
    'throttle_per_ip',
    'throttle_per_user',
    'DEFAULT_THROTTLE_CONFIGS'
]

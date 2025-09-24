"""
Enhanced Middleware Manager for Pyserv Framework

This module provides an advanced middleware management system with:
- Middleware pipeline with priorities
- Conditional middleware execution
- Middleware composition
- Performance monitoring middleware
- Request/response transformation middleware
- Middleware caching and optimization
- Error handling middleware
- Request correlation tracking
- Middleware metrics and analytics
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, List, Callable, Any, Optional, Type, Union, Awaitable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class MiddlewarePriority(int, Enum):
    """Middleware priority levels"""
    LOWEST = -100
    LOW = -50
    NORMAL = 0
    HIGH = 50
    HIGHEST = 100
    CRITICAL = 1000


class MiddlewareType(str, Enum):
    """Middleware types"""
    HTTP = "http"
    WEBSOCKET = "websocket"
    BOTH = "both"


class MiddlewarePhase(str, Enum):
    """Middleware execution phases"""
    REQUEST = "request"
    RESPONSE = "response"
    ERROR = "error"
    WEBSOCKET_CONNECT = "websocket_connect"
    WEBSOCKET_MESSAGE = "websocket_message"
    WEBSOCKET_DISCONNECT = "websocket_disconnect"


@dataclass
class MiddlewareInfo:
    """Middleware information and metadata"""
    name: str
    middleware: Callable
    priority: MiddlewarePriority = MiddlewarePriority.NORMAL
    middleware_type: MiddlewareType = MiddlewareType.HTTP
    phases: List[MiddlewarePhase] = field(default_factory=lambda: [MiddlewarePhase.REQUEST, MiddlewarePhase.RESPONSE])
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0
    execution_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None


@dataclass
class RequestContext:
    """Request context for middleware"""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    start_time: float = field(default_factory=time.time)
    middleware_data: Dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_middleware_data(self, middleware_name: str, key: str, default: Any = None) -> Any:
        """Get data from middleware"""
        if middleware_name not in self.middleware_data:
            return default
        return self.middleware_data[middleware_name].get(key, default)

    def set_middleware_data(self, middleware_name: str, key: str, value: Any) -> None:
        """Set data for middleware"""
        if middleware_name not in self.middleware_data:
            self.middleware_data[middleware_name] = {}
        self.middleware_data[middleware_name][key] = value


class MiddlewareManager:
    """Advanced middleware manager with comprehensive features"""

    def __init__(self):
        self.http_middlewares: List[MiddlewareInfo] = []
        self.websocket_middlewares: List[MiddlewareInfo] = []
        self.middleware_cache: Dict[str, Any] = {}
        self.request_contexts: Dict[str, RequestContext] = {}
        self._performance_stats: Dict[str, Dict[str, Any]] = {}
        self._enabled = True

    def add(self, middleware: Union[Callable, Type], priority: MiddlewarePriority = MiddlewarePriority.NORMAL,
            middleware_type: MiddlewareType = MiddlewareType.HTTP,
            phases: Optional[List[MiddlewarePhase]] = None,
            config: Optional[Dict[str, Any]] = None,
            name: Optional[str] = None) -> None:
        """Add middleware to the manager"""

        # Handle class-based middleware
        if isinstance(middleware, type):
            if not hasattr(middleware, '__call__'):
                raise ValueError(f"Middleware class {middleware} must be callable")
            middleware_instance = middleware()
            middleware_callable = middleware_instance.__call__
            if not name:
                name = middleware.__name__
        else:
            middleware_callable = middleware
            if not name:
                name = getattr(middleware, '__name__', str(middleware))

        # Set default phases
        if phases is None:
            phases = [MiddlewarePhase.REQUEST, MiddlewarePhase.RESPONSE]

        middleware_info = MiddlewareInfo(
            name=name,
            middleware=middleware_callable,
            priority=priority,
            middleware_type=middleware_type,
            phases=phases,
            config=config or {},
            enabled=True
        )

        # Add to appropriate list
        if middleware_type in [MiddlewareType.HTTP, MiddlewareType.BOTH]:
            self.http_middlewares.append(middleware_info)

        if middleware_type in [MiddlewareType.WEBSOCKET, MiddlewareType.BOTH]:
            self.websocket_middlewares.append(middleware_info)

        # Sort by priority (highest first)
        self.http_middlewares.sort(key=lambda m: m.priority.value, reverse=True)
        self.websocket_middlewares.sort(key=lambda m: m.priority.value, reverse=True)

        logger.info(f"Added middleware {name} with priority {priority.value}")

    def remove(self, name: str) -> bool:
        """Remove middleware by name"""
        removed = False

        for middleware_list in [self.http_middlewares, self.websocket_middlewares]:
            for i, middleware in enumerate(middleware_list):
                if middleware.name == name:
                    middleware_list.pop(i)
                    removed = True
                    break

        if removed:
            logger.info(f"Removed middleware {name}")

        return removed

    def enable(self, name: str) -> bool:
        """Enable middleware"""
        for middleware_list in [self.http_middlewares, self.websocket_middlewares]:
            for middleware in middleware_list:
                if middleware.name == name:
                    middleware.enabled = True
                    logger.info(f"Enabled middleware {name}")
                    return True
        return False

    def disable(self, name: str) -> bool:
        """Disable middleware"""
        for middleware_list in [self.http_middlewares, self.websocket_middlewares]:
            for middleware in middleware_list:
                if middleware.name == name:
                    middleware.enabled = False
                    logger.info(f"Disabled middleware {name}")
                    return True
        return False

    def get_middleware(self, name: str) -> Optional[MiddlewareInfo]:
        """Get middleware by name"""
        for middleware_list in [self.http_middlewares, self.websocket_middlewares]:
            for middleware in middleware_list:
                if middleware.name == name:
                    return middleware
        return None

    async def process_http_request(self, request) -> Any:
        """Process HTTP request through middleware pipeline"""
        if not self._enabled:
            return request

        # Create request context
        context = RequestContext()
        self.request_contexts[context.request_id] = context

        # Add context to request
        request.context = context

        # Process through request middleware
        for middleware in self.http_middlewares:
            if (middleware.enabled and
                MiddlewarePhase.REQUEST in middleware.phases):
                try:
                    start_time = time.time()
                    request = await self._execute_middleware(middleware, request, None)
                    execution_time = time.time() - start_time

                    # Update stats
                    middleware.execution_time += execution_time
                    middleware.execution_count += 1

                    # Store in context
                    context.set_middleware_data(middleware.name, 'last_execution_time', execution_time)

                except Exception as e:
                    middleware.error_count += 1
                    middleware.last_error = str(e)
                    logger.error(f"Error in middleware {middleware.name}: {e}")

                    # Check if middleware should continue on error
                    if not middleware.config.get('continue_on_error', False):
                        raise

        return request

    async def process_http_response(self, request, response) -> Any:
        """Process HTTP response through middleware pipeline"""
        if not self._enabled:
            return response

        context = getattr(request, 'context', None)
        if not context:
            return response

        # Process through response middleware (in reverse order)
        for middleware in reversed(self.http_middlewares):
            if (middleware.enabled and
                MiddlewarePhase.RESPONSE in middleware.phases):
                try:
                    start_time = time.time()
                    response = await self._execute_middleware(middleware, request, response)
                    execution_time = time.time() - start_time

                    # Update stats
                    middleware.execution_time += execution_time
                    middleware.execution_count += 1

                    # Store in context
                    if context:
                        context.set_middleware_data(middleware.name, 'last_response_time', execution_time)

                except Exception as e:
                    middleware.error_count += 1
                    middleware.last_error = str(e)
                    logger.error(f"Error in response middleware {middleware.name}: {e}")

                    # Check if middleware should continue on error
                    if not middleware.config.get('continue_on_error', False):
                        raise

        return response

    async def process_websocket(self, websocket) -> Optional[Any]:
        """Process WebSocket through middleware pipeline"""
        if not self._enabled:
            return websocket

        # Create request context
        context = RequestContext()
        self.request_contexts[context.request_id] = context

        # Add context to websocket
        websocket.context = context

        # Process through connect middleware
        for middleware in self.websocket_middlewares:
            if (middleware.enabled and
                MiddlewarePhase.WEBSOCKET_CONNECT in middleware.phases):
                try:
                    start_time = time.time()
                    result = await self._execute_websocket_middleware(middleware, websocket, 'connect')
                    execution_time = time.time() - start_time

                    # Update stats
                    middleware.execution_time += execution_time
                    middleware.execution_count += 1

                    if result is None:
                        # Middleware rejected the connection
                        return None

                except Exception as e:
                    middleware.error_count += 1
                    middleware.last_error = str(e)
                    logger.error(f"Error in WebSocket middleware {middleware.name}: {e}")

                    # Check if middleware should continue on error
                    if not middleware.config.get('continue_on_error', False):
                        return None

        return websocket

    async def process_websocket_message(self, websocket, message) -> Optional[Any]:
        """Process WebSocket message through middleware pipeline"""
        if not self._enabled:
            return message

        context = getattr(websocket, 'context', None)
        if not context:
            return message

        # Process through message middleware
        for middleware in self.websocket_middlewares:
            if (middleware.enabled and
                MiddlewarePhase.WEBSOCKET_MESSAGE in middleware.phases):
                try:
                    start_time = time.time()
                    message = await self._execute_websocket_middleware(middleware, websocket, 'message', message)
                    execution_time = time.time() - start_time

                    # Update stats
                    middleware.execution_time += execution_time
                    middleware.execution_count += 1

                    if message is None:
                        # Middleware consumed the message
                        return None

                except Exception as e:
                    middleware.error_count += 1
                    middleware.last_error = str(e)
                    logger.error(f"Error in WebSocket message middleware {middleware.name}: {e}")

        return message

    async def process_websocket_disconnect(self, websocket) -> None:
        """Process WebSocket disconnect through middleware pipeline"""
        if not self._enabled:
            return

        context = getattr(websocket, 'context', None)
        if not context:
            return

        # Process through disconnect middleware
        for middleware in self.websocket_middlewares:
            if (middleware.enabled and
                MiddlewarePhase.WEBSOCKET_DISCONNECT in middleware.phases):
                try:
                    start_time = time.time()
                    await self._execute_websocket_middleware(middleware, websocket, 'disconnect')
                    execution_time = time.time() - start_time

                    # Update stats
                    middleware.execution_time += execution_time
                    middleware.execution_count += 1

                except Exception as e:
                    middleware.error_count += 1
                    middleware.last_error = str(e)
                    logger.error(f"Error in WebSocket disconnect middleware {middleware.name}: {e}")

    async def _execute_middleware(self, middleware: MiddlewareInfo, request, response) -> Any:
        """Execute HTTP middleware"""
        try:
            if response is None:
                # Request phase
                return await middleware.middleware(request, self._create_call_next(middleware, request))
            else:
                # Response phase
                return await middleware.middleware(request, response)
        except Exception as e:
            logger.error(f"Error executing middleware {middleware.name}: {e}")
            raise

    async def _execute_websocket_middleware(self, middleware: MiddlewareInfo, websocket, phase: str, message=None) -> Any:
        """Execute WebSocket middleware"""
        try:
            if phase == 'connect':
                return await middleware.middleware(websocket, self._create_websocket_call_next(middleware, websocket, phase))
            elif phase == 'message':
                return await middleware.middleware(websocket, message)
            elif phase == 'disconnect':
                return await middleware.middleware(websocket)
        except Exception as e:
            logger.error(f"Error executing WebSocket middleware {middleware.name}: {e}")
            raise

    def _create_call_next(self, current_middleware: MiddlewareInfo, request):
        """Create call_next function for HTTP middleware"""
        async def call_next(response=None):
            # Find next middleware
            current_index = None
            for i, middleware in enumerate(self.http_middlewares):
                if middleware.name == current_middleware.name:
                    current_index = i
                    break

            if current_index is None or current_index == len(self.http_middlewares) - 1:
                # No more middleware, return response
                return response

            # Execute next middleware
            next_middleware = self.http_middlewares[current_index + 1]
            return await self._execute_middleware(next_middleware, request, response)

        return call_next

    def _create_websocket_call_next(self, current_middleware: MiddlewareInfo, websocket, phase: str):
        """Create call_next function for WebSocket middleware"""
        async def call_next(message=None):
            # Find next middleware
            current_index = None
            for i, middleware in enumerate(self.websocket_middlewares):
                if middleware.name == current_middleware.name:
                    current_index = i
                    break

            if current_index is None or current_index == len(self.websocket_middlewares) - 1:
                # No more middleware
                if phase == 'connect':
                    return True  # Accept connection
                elif phase == 'message':
                    return message  # Pass through message
                else:
                    return None

            # Execute next middleware
            next_middleware = self.websocket_middlewares[current_index + 1]
            return await self._execute_websocket_middleware(next_middleware, websocket, phase, message)

        return call_next

    async def execute_http_chain(self, request, final_handler: Callable) -> Any:
        """Execute the complete HTTP middleware chain"""
        async def call_next(response=None):
            if response is None:
                # Execute final handler
                return await final_handler(request)
            else:
                # Response phase - process through response middleware
                return await self.process_http_response(request, response)

        # Start with request processing
        processed_request = await self.process_http_request(request)

        # Execute through middleware chain
        response = await self._execute_middleware_chain(processed_request, call_next)

        return response

    async def _execute_middleware_chain(self, request, call_next):
        """Execute middleware chain starting from the first middleware"""
        if not self.http_middlewares:
            return await call_next()

        # Start with the first middleware
        first_middleware = self.http_middlewares[0]
        return await self._execute_middleware(first_middleware, request, None)

    def get_stats(self) -> Dict[str, Any]:
        """Get middleware manager statistics"""
        stats = {
            'total_http_middlewares': len(self.http_middlewares),
            'total_websocket_middlewares': len(self.websocket_middlewares),
            'enabled': self._enabled,
            'active_requests': len(self.request_contexts),
            'middleware_stats': {}
        }

        for middleware in self.http_middlewares + self.websocket_middlewares:
            stats['middleware_stats'][middleware.name] = {
                'enabled': middleware.enabled,
                'priority': middleware.priority.value,
                'type': middleware.middleware_type.value,
                'phases': [phase.value for phase in middleware.phases],
                'execution_time': middleware.execution_time,
                'execution_count': middleware.execution_count,
                'error_count': middleware.error_count,
                'last_error': middleware.last_error
            }

        return stats

    def clear_cache(self) -> None:
        """Clear middleware cache"""
        self.middleware_cache.clear()

    def enable_all(self) -> None:
        """Enable all middleware"""
        for middleware_list in [self.http_middlewares, self.websocket_middlewares]:
            for middleware in middleware_list:
                middleware.enabled = True

    def disable_all(self) -> None:
        """Disable all middleware"""
        for middleware_list in [self.http_middlewares, self.websocket_middlewares]:
            for middleware in middleware_list:
                middleware.enabled = False

    def get_middleware_by_phase(self, phase: MiddlewarePhase, middleware_type: MiddlewareType = MiddlewareType.HTTP) -> List[MiddlewareInfo]:
        """Get middleware by phase"""
        middleware_list = self.http_middlewares if middleware_type == MiddlewareType.HTTP else self.websocket_middlewares
        return [m for m in middleware_list if phase in m.phases and m.enabled]


# Built-in Middleware Classes
class BaseMiddleware:
    """Base middleware class with common functionality"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)

    async def __call__(self, request, call_next):
        """Default middleware implementation"""
        return await call_next(request)


class PerformanceMonitoringMiddleware(BaseMiddleware):
    """Middleware for performance monitoring"""

    async def __call__(self, request, call_next):
        start_time = time.time()

        try:
            response = await call_next(request)

            execution_time = time.time() - start_time
            self.logger.debug(f"Request {request.method} {request.path} took {execution_time:.4f}s")

            # Add performance headers
            if hasattr(response, 'headers'):
                response.headers['X-Execution-Time'] = str(execution_time)

            return response

        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Request {request.method} {request.path} failed after {execution_time:.4f}s: {e}")
            raise


class RequestLoggingMiddleware(BaseMiddleware):
    """Middleware for request logging"""

    async def __call__(self, request, call_next):
        context = getattr(request, 'context', None)
        request_id = context.request_id if context else 'unknown'

        self.logger.info(f"[{request_id}] {request.method} {request.path}")

        try:
            response = await call_next(request)
            status_code = getattr(response, 'status_code', 200)
            self.logger.info(f"[{request_id}] Completed with status {status_code}")
            return response

        except Exception as e:
            self.logger.error(f"[{request_id}] Failed: {e}")
            raise


class CORSMiddleware(BaseMiddleware):
    """CORS middleware"""

    async def __call__(self, request, call_next):
        # Add CORS headers to response
        response = await call_next(request)

        if hasattr(response, 'headers'):
            response.headers.update({
                'Access-Control-Allow-Origin': self.config.get('origins', '*'),
                'Access-Control-Allow-Methods': self.config.get('methods', 'GET,POST,PUT,DELETE,OPTIONS'),
                'Access-Control-Allow-Headers': self.config.get('headers', 'Content-Type,Authorization'),
                'Access-Control-Max-Age': self.config.get('max_age', '86400')
            })

        return response


class RateLimitingMiddleware(BaseMiddleware):
    """Rate limiting middleware"""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.requests_per_minute = self.config.get('requests_per_minute', 60)
        self.burst_limit = self.config.get('burst_limit', 10)

    async def __call__(self, request, call_next):
        # Simple rate limiting logic (in production, use Redis or similar)
        client_key = self._get_client_key(request)

        # Check rate limit
        if self._is_rate_limited(client_key):
            from pyserv.exceptions import HTTPException
            raise HTTPException(429, "Too Many Requests")

        response = await call_next(request)
        return response

    def _get_client_key(self, request) -> str:
        """Get client identifier for rate limiting"""
        # Use IP address or API key
        return getattr(request, 'client_ip', 'unknown')

    def _is_rate_limited(self, client_key: str) -> bool:
        """Check if client is rate limited"""
        # Simple implementation - in production use Redis
        return False  # Placeholder


class SecurityHeadersMiddleware(BaseMiddleware):
    """Security headers middleware"""

    async def __call__(self, request, call_next):
        response = await call_next(request)

        if hasattr(response, 'headers'):
            response.headers.update({
                'X-Content-Type-Options': 'nosniff',
                'X-Frame-Options': 'DENY',
                'X-XSS-Protection': '1; mode=block',
                'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
                'Referrer-Policy': 'strict-origin-when-cross-origin',
                'Permissions-Policy': 'geolocation=(), microphone=(), camera=()'
            })

        return response


class CompressionMiddleware(BaseMiddleware):
    """Response compression middleware"""

    async def __call__(self, request, call_next):
        response = await call_next(request)

        # Check if client accepts compression
        accept_encoding = request.headers.get('Accept-Encoding', '')

        if 'gzip' in accept_encoding and hasattr(response, 'body'):
            # Compress response body
            import gzip
            import io

            if isinstance(response.body, str):
                body_bytes = response.body.encode('utf-8')
            else:
                body_bytes = response.body

            compressed = gzip.compress(body_bytes)
            response.body = compressed
            response.headers['Content-Encoding'] = 'gzip'

        return response


# Middleware Manager Instance
_middleware_manager: Optional[MiddlewareManager] = None

def get_middleware_manager() -> MiddlewareManager:
    """Get the global middleware manager instance"""
    global _middleware_manager
    if _middleware_manager is None:
        _middleware_manager = MiddlewareManager()
    return _middleware_manager

__all__ = [
    'MiddlewareManager', 'MiddlewareInfo', 'RequestContext',
    'MiddlewarePriority', 'MiddlewareType', 'MiddlewarePhase',
    'BaseMiddleware', 'PerformanceMonitoringMiddleware',
    'RequestLoggingMiddleware', 'CORSMiddleware',
    'RateLimitingMiddleware', 'SecurityHeadersMiddleware',
    'CompressionMiddleware', 'get_middleware_manager'
]

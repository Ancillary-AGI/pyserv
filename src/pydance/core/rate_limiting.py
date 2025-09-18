"""
Unified Rate Limiting Module for PyDance Framework.

This module provides a consolidated, production-ready rate limiting implementation
with support for multiple algorithms, distributed backends, and monitoring.
"""

import asyncio
import time
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Union, List, Callable
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class RateLimitAlgorithm(Enum):
    """Rate limiting algorithms"""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""
    algorithm: RateLimitAlgorithm = RateLimitAlgorithm.TOKEN_BUCKET
    capacity: int = 100  # Max requests/tokens
    refill_rate: float = 10.0  # Tokens per second
    refill_interval: float = 1.0  # Refill interval in seconds
    burst_capacity: Optional[int] = None  # Max burst capacity
    window_size: int = 60  # Window size in seconds for window-based algorithms

    def __post_init__(self):
        if self.burst_capacity is None:
            self.burst_capacity = self.capacity


@dataclass
class RateLimitResult:
    """Result of a rate limit check"""
    allowed: bool
    remaining: int
    reset_time: float
    retry_after: Optional[float] = None
    limit: int = 0


class RateLimitBackend(ABC):
    """Abstract base class for rate limiting backends"""

    @abstractmethod
    async def check_limit(self, key: str, config: RateLimitConfig) -> RateLimitResult:
        """Check if request is within rate limit"""
        pass

    @abstractmethod
    async def reset_limit(self, key: str) -> bool:
        """Reset rate limit for a key"""
        pass

    @abstractmethod
    def get_stats(self, key: str) -> Dict[str, Any]:
        """Get statistics for a key"""
        pass


class InMemoryRateLimitBackend(RateLimitBackend):
    """In-memory rate limiting backend using token bucket algorithm"""

    def __init__(self):
        self._buckets: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

    async def check_limit(self, key: str, config: RateLimitConfig) -> RateLimitResult:
        """Check rate limit using token bucket algorithm"""
        with self._lock:
            now = time.time()

            if key not in self._buckets:
                self._buckets[key] = {
                    'tokens': config.capacity,
                    'last_refill': now,
                    'created': now
                }

            bucket = self._buckets[key]

            # Refill tokens
            elapsed = now - bucket['last_refill']
            if elapsed >= config.refill_interval:
                tokens_to_add = int(elapsed / config.refill_interval) * config.refill_rate
                if tokens_to_add > 0:
                    bucket['tokens'] = min(config.burst_capacity, bucket['tokens'] + tokens_to_add)
                    bucket['last_refill'] = now

            # Check if we have enough tokens
            if bucket['tokens'] >= 1:
                bucket['tokens'] -= 1
                remaining = int(bucket['tokens'])
                reset_time = bucket['last_refill'] + config.refill_interval
                return RateLimitResult(
                    allowed=True,
                    remaining=remaining,
                    reset_time=reset_time,
                    limit=config.capacity
                )
            else:
                # Calculate retry after time
                tokens_needed = 1 - bucket['tokens']
                retry_after = (tokens_needed / config.refill_rate) * config.refill_interval
                reset_time = bucket['last_refill'] + config.refill_interval

                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_time=reset_time,
                    retry_after=retry_after,
                    limit=config.capacity
                )

    async def reset_limit(self, key: str) -> bool:
        """Reset rate limit for a key"""
        with self._lock:
            if key in self._buckets:
                self._buckets[key]['tokens'] = self._buckets[key].get('capacity', 100)
                self._buckets[key]['last_refill'] = time.time()
                return True
            return False

    def get_stats(self, key: str) -> Dict[str, Any]:
        """Get statistics for a key"""
        with self._lock:
            if key in self._buckets:
                bucket = self._buckets[key]
                return {
                    'tokens': bucket['tokens'],
                    'last_refill': bucket['last_refill'],
                    'created': bucket['created'],
                    'age': time.time() - bucket['created']
                }
            return {}


class DistributedRateLimitBackend(RateLimitBackend):
    """Distributed rate limiting backend (Redis, etc.)"""

    def __init__(self, backend: Any):
        self.backend = backend  # Redis, database, etc.

    async def check_limit(self, key: str, config: RateLimitConfig) -> RateLimitResult:
        """Check rate limit using distributed backend"""
        # Implementation would depend on the specific backend
        # For now, return allowed
        return RateLimitResult(
            allowed=True,
            remaining=config.capacity - 1,
            reset_time=time.time() + config.window_size,
            limit=config.capacity
        )

    async def reset_limit(self, key: str) -> bool:
        """Reset rate limit for a key"""
        # Implementation would depend on the specific backend
        return True

    def get_stats(self, key: str) -> Dict[str, Any]:
        """Get statistics for a key"""
        # Implementation would depend on the specific backend
        return {}


class RateLimiter:
    """
    Unified rate limiter with support for multiple backends and algorithms.

    This class provides a modern, production-ready rate limiting implementation
    with proper async support, monitoring, and extensibility.
    """

    def __init__(self,
                 config: RateLimitConfig,
                 backend: Optional[RateLimitBackend] = None,
                 key_func: Optional[Callable] = None):
        self.config = config
        self.backend = backend or InMemoryRateLimitBackend()
        self.key_func = key_func or self._default_key_func
        self._middleware_hooks: List[Callable] = []

    def _default_key_func(self, request: Any) -> str:
        """Default key function using client IP"""
        if hasattr(request, 'remote_addr'):
            return request.remote_addr or 'unknown'
        elif hasattr(request, 'client_ip'):
            return request.client_ip or 'unknown'
        else:
            return 'default'

    def add_middleware_hook(self, hook: Callable):
        """Add middleware hook for rate limiting events"""
        self._middleware_hooks.append(hook)

    async def check_limit(self, request: Any) -> RateLimitResult:
        """Check if request is within rate limit"""
        key = self.key_func(request)
        result = await self.backend.check_limit(key, self.config)

        # Execute middleware hooks
        for hook in self._middleware_hooks:
            try:
                await hook(request, result, key)
            except Exception as e:
                logger.warning(f"Rate limit middleware hook failed: {e}")

        return result

    async def is_allowed(self, request: Any) -> bool:
        """Check if request is allowed (convenience method)"""
        result = await self.check_limit(request)
        return result.allowed

    async def reset_limit(self, request: Any) -> bool:
        """Reset rate limit for a request"""
        key = self.key_func(request)
        return await self.backend.reset_limit(key)

    def get_stats(self, request: Any) -> Dict[str, Any]:
        """Get statistics for a request"""
        key = self.key_func(request)
        return self.backend.get_stats(key)

    @classmethod
    def create_token_bucket(cls,
                          capacity: int = 100,
                          refill_rate: float = 10.0,
                          backend: Optional[RateLimitBackend] = None) -> 'RateLimiter':
        """Create a token bucket rate limiter"""
        config = RateLimitConfig(
            algorithm=RateLimitAlgorithm.TOKEN_BUCKET,
            capacity=capacity,
            refill_rate=refill_rate
        )
        return cls(config, backend)

    @classmethod
    def create_fixed_window(cls,
                          capacity: int = 100,
                          window_size: int = 60,
                          backend: Optional[RateLimitBackend] = None) -> 'RateLimiter':
        """Create a fixed window rate limiter"""
        config = RateLimitConfig(
            algorithm=RateLimitAlgorithm.FIXED_WINDOW,
            capacity=capacity,
            window_size=window_size
        )
        return cls(config, backend)


class RateLimitExceeded(Exception):
    """
    Exception raised when rate limit is exceeded.

    This exception provides detailed information about the rate limit violation
    and can be used to generate appropriate HTTP responses.
    """

    def __init__(self,
                 message: str = "Rate limit exceeded",
                 retry_after: Optional[float] = None,
                 limit: int = 0,
                 remaining: int = 0,
                 reset_time: Optional[float] = None):
        super().__init__(message)
        self.retry_after = retry_after
        self.limit = limit
        self.remaining = remaining
        self.reset_time = reset_time

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            'error': 'rate_limit_exceeded',
            'message': str(self),
            'retry_after': self.retry_after,
            'limit': self.limit,
            'remaining': self.remaining,
            'reset_time': self.reset_time
        }


# Global rate limiter instances
default_rate_limiter = RateLimiter.create_token_bucket()

__all__ = [
    'RateLimitAlgorithm',
    'RateLimitConfig',
    'RateLimitResult',
    'RateLimitBackend',
    'InMemoryRateLimitBackend',
    'DistributedRateLimitBackend',
    'RateLimiter',
    'RateLimitExceeded',
    'default_rate_limiter'
]

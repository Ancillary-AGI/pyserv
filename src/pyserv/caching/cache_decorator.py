"""
Cache decorators for easy function result caching.
"""

import asyncio
import functools
import hashlib
import inspect
from typing import Any, Callable, Optional, Dict, Tuple

def cache_result(ttl_seconds: int = 3600, key_prefix: str = "", namespace: str = "default"):
    """Decorator to cache function results."""
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = generate_cache_key(func, args, kwargs, key_prefix)

            # Try to get from cache
            cached_result = await cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Execute function
            result = await func(*args, **kwargs)

            # Cache result
            await cache_manager.set(cache_key, result, ttl_seconds)

            return result
        return wrapper
    return decorator

def invalidate_cache(pattern: str, namespace: str = "default"):
    """Decorator to invalidate cache entries matching pattern."""
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)

            # Invalidate matching cache entries
            await cache_manager.invalidate_pattern(pattern)

            return result
        return wrapper
    return decorator

def cache_key(prefix: str = "", include_args: bool = True, include_kwargs: bool = False):
    """Generate cache key for function."""
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            key = generate_cache_key(func, args, kwargs, prefix, include_args, include_kwargs)
            return key
        return wrapper
    return decorator

def generate_cache_key(func: Callable, args: Tuple, kwargs: Dict,
                      prefix: str = "", include_args: bool = True,
                      include_kwargs: bool = False) -> str:
    """Generate cache key from function and arguments."""

    # Function name and module
    key_parts = [f"{func.__module__}.{func.__name__}"]

    if prefix:
        key_parts.append(prefix)

    if include_args:
        # Convert args to string representation
        args_str = str(args) if args else ""
        key_parts.append(args_str)

    if include_kwargs:
        # Sort kwargs for consistent ordering
        sorted_kwargs = sorted(kwargs.items())
        kwargs_str = str(sorted_kwargs) if sorted_kwargs else ""
        key_parts.append(kwargs_str)

    # Create hash
    key_string = ":".join(key_parts)
    return hashlib.md5(key_string.encode()).hexdigest()

# Global cache manager instance
cache_manager = None

def set_cache_manager(manager: CacheManager):
    """Set global cache manager."""
    global cache_manager
    cache_manager = manager

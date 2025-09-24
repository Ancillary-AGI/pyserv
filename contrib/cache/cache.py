"""
Caching system for Pyserv  framework.
"""

import asyncio
import hashlib
import json
import pickle
from typing import Any, Optional, Dict, List, Union, Callable
from functools import wraps
from datetime import datetime, timedelta

from .backends import CacheBackend


class Cache:
    """Main cache class"""

    def __init__(self,
                 backend: CacheBackend,
                 default_timeout: int = 300,  # 5 minutes
                 key_prefix: str = "",
                 key_function: Optional[Callable] = None,
                 serializer: str = 'json'):
        self.backend = backend
        self.default_timeout = default_timeout
        self.key_prefix = key_prefix
        self.key_function = key_function or self._default_key_function
        self.serializer = serializer

    def _default_key_function(self, *args, **kwargs) -> str:
        """Default key generation function"""
        # Create a hash of the arguments
        key_data = {
            'args': args,
            'kwargs': kwargs
        }
        key_string = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_string.encode()).hexdigest()

    def _make_key(self, key: str) -> str:
        """Make a cache key with prefix"""
        if self.key_prefix:
            return f"{self.key_prefix}:{key}"
        return key

    def _serialize(self, value: Any) -> str:
        """Serialize value for storage"""
        if self.serializer == 'json':
            return json.dumps(value, default=str)
        elif self.serializer == 'pickle':
            return pickle.dumps(value).decode('latin1')
        else:
            return str(value)

    def _deserialize(self, value: str) -> Any:
        """Deserialize value from storage"""
        if self.serializer == 'json':
            return json.loads(value)
        elif self.serializer == 'pickle':
            return pickle.loads(value.encode('latin1'))
        else:
            return value

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        cache_key = self._make_key(key)
        value = await self.backend.get(cache_key)
        if value is not None:
            return self._deserialize(value)
        return None

    async def set(self, key: str, value: Any, timeout: Optional[int] = None) -> bool:
        """Set value in cache"""
        cache_key = self._make_key(key)
        serialized_value = self._serialize(value)
        timeout = timeout or self.default_timeout
        return await self.backend.set(cache_key, serialized_value, timeout)

    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        cache_key = self._make_key(key)
        return await self.backend.delete(cache_key)

    async def has_key(self, key: str) -> bool:
        """Check if key exists in cache"""
        cache_key = self._make_key(key)
        return await self.backend.has_key(cache_key)

    async def clear(self) -> bool:
        """Clear all cache"""
        return await self.backend.clear()

    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from cache"""
        cache_keys = [self._make_key(key) for key in keys]
        values = await self.backend.get_many(cache_keys)

        result = {}
        for key, cache_key in zip(keys, cache_keys):
            if cache_key in values and values[cache_key] is not None:
                result[key] = self._deserialize(values[cache_key])

        return result

    async def set_many(self, data: Dict[str, Any], timeout: Optional[int] = None) -> bool:
        """Set multiple values in cache"""
        cache_data = {}
        for key, value in data.items():
            cache_key = self._make_key(key)
            cache_data[cache_key] = self._serialize(value)

        timeout = timeout or self.default_timeout
        return await self.backend.set_many(cache_data, timeout)

    async def delete_many(self, keys: List[str]) -> bool:
        """Delete multiple values from cache"""
        cache_keys = [self._make_key(key) for key in keys]
        return await self.backend.delete_many(cache_keys)

    async def incr(self, key: str, delta: int = 1) -> Optional[int]:
        """Increment numeric value in cache"""
        cache_key = self._make_key(key)
        return await self.backend.incr(cache_key, delta)

    async def decr(self, key: str, delta: int = 1) -> Optional[int]:
        """Decrement numeric value in cache"""
        cache_key = self._make_key(key)
        return await self.backend.decr(cache_key, delta)

    async def get_or_set(self, key: str, default: Any, timeout: Optional[int] = None) -> Any:
        """Get value or set default if not exists"""
        value = await self.get(key)
        if value is None:
            await self.set(key, default, timeout)
            return default
        return value

    async def close(self):
        """Close cache backend"""
        await self.backend.close()

    # Decorator methods

    def cached(self,
               timeout: Optional[int] = None,
               key_prefix: str = "",
               unless: Optional[Callable] = None):
        """
        Decorator to cache function results

        @cache.cached(timeout=300)
        async def expensive_function(param1, param2):
            return expensive_computation(param1, param2)
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Check if we should skip caching
                if unless and unless(*args, **kwargs):
                    return await func(*args, **kwargs)

                # Generate cache key
                key = self.key_function(func.__name__, *args, **kwargs)
                if key_prefix:
                    key = f"{key_prefix}:{key}"

                # Try to get from cache
                cached_value = await self.get(key)
                if cached_value is not None:
                    return cached_value

                # Execute function and cache result
                result = await func(*args, **kwargs)
                cache_timeout = timeout or self.default_timeout
                await self.set(key, result, cache_timeout)

                return result

            return wrapper
        return decorator

    def memoize(self, timeout: Optional[int] = None):
        """
        Decorator for function memoization

        @cache.memoize(timeout=600)
        async def compute_expensive_value(user_id):
            return await database_query(user_id)
        """
        return self.cached(timeout=timeout, key_prefix="memoize")


# Global cache instance
cache = None


def setup_cache(backend: CacheBackend,
                default_timeout: int = 300,
                key_prefix: str = "",
                serializer: str = 'json') -> Cache:
    """Setup global cache instance"""
    global cache
    cache = Cache(
        backend=backend,
        default_timeout=default_timeout,
        key_prefix=key_prefix,
        serializer=serializer
    )
    return cache


def get_cache() -> Optional[Cache]:
    """Get global cache instance"""
    return cache





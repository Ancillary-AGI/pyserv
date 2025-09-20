"""
Caching backends for PyDance framework.
Provides multiple cache options including memory, Redis, file, and database.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, Union
import pickle
import asyncio
from datetime import datetime, timedelta
import aioredis
from pydance.core.storage import LocalStorage

class CacheBackend(ABC):
    """Abstract base class for cache backends"""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, expire: int = None) -> bool:
        """Set value in cache with optional expiration"""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        pass

    @abstractmethod
    async def clear(self) -> bool:
        """Clear all cache entries"""
        pass

class MemoryCache(CacheBackend):
    """In-memory cache backend"""

    def __init__(self):
        self._cache = {}
        self._expirations = {}

    async def get(self, key: str) -> Optional[Any]:
        if key in self._expirations and datetime.now() > self._expirations[key]:
            await self.delete(key)
            return None
        return self._cache.get(key)

    async def set(self, key: str, value: Any, expire: int = None) -> bool:
        self._cache[key] = value
        if expire:
            self._expirations[key] = datetime.now() + timedelta(seconds=expire)
        return True

    async def delete(self, key: str) -> bool:
        self._cache.pop(key, None)
        self._expirations.pop(key, None)
        return True

    async def exists(self, key: str) -> bool:
        return key in self._cache

    async def clear(self) -> bool:
        self._cache.clear()
        self._expirations.clear()
        return True

class RedisCache(CacheBackend):
    """Redis cache backend"""

    def __init__(self, url: str = "redis://localhost:6379", **kwargs):
        self.redis_url = url
        self.redis = None
        self._kwargs = kwargs

    async def _get_redis(self):
        if self.redis is None:
            self.redis = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                **self._kwargs
            )
        return self.redis

    async def get(self, key: str) -> Optional[Any]:
        redis = await self._get_redis()
        value = await redis.get(key)
        return pickle.loads(value) if value else None

    async def set(self, key: str, value: Any, expire: int = None) -> bool:
        redis = await self._get_redis()
        serialized = pickle.dumps(value)
        if expire:
            await redis.setex(key, expire, serialized)
        else:
            await redis.set(key, serialized)
        return True

    async def delete(self, key: str) -> bool:
        redis = await self._get_redis()
        return await redis.delete(key) > 0

    async def exists(self, key: str) -> bool:
        redis = await self._get_redis()
        return await redis.exists(key) > 0

    async def clear(self) -> bool:
        redis = await self._get_redis()
        return await redis.flushdb()

class FileCache(CacheBackend):
    """File-based cache backend"""

    def __init__(self, base_path: str = "cache"):
        self.storage = LocalStorage(base_path)

    async def get(self, key: str) -> Optional[Any]:
        if await self.storage.exists(key):
            async with await self.storage.get(key) as f:
                return pickle.loads(await f.read())
        return None

    async def set(self, key: str, value: Any, expire: int = None) -> bool:
        serialized = pickle.dumps(value)
        # For simplicity, we ignore expire in file cache
        await self.storage.put(key, serialized)
        return True

    async def delete(self, key: str) -> bool:
        return await self.storage.delete(key)

    async def exists(self, key: str) -> bool:
        return await self.storage.exists(key)

    async def clear(self) -> bool:
        # This would need to be implemented properly
        return True

class DatabaseCache(CacheBackend):
    """Database-backed cache backend"""

    def __init__(self, db_connection):
        self.db = db_connection

    async def get(self, key: str) -> Optional[Any]:
        result = await self.db.fetchval(
            "SELECT value FROM cache WHERE key = $1 AND expires_at > NOW()",
            key
        )
        return pickle.loads(result) if result else None

    async def set(self, key: str, value: Any, expire: int = None) -> bool:
        serialized = pickle.dumps(value)
        expires_at = datetime.now() + timedelta(seconds=expire) if expire else None

        await self.db.execute("""
            INSERT INTO cache (key, value, expires_at)
            VALUES ($1, $2, $3)
            ON CONFLICT (key) DO UPDATE SET value = $2, expires_at = $3
        """, key, serialized, expires_at)
        return True

    async def delete(self, key: str) -> bool:
        await self.db.execute("DELETE FROM cache WHERE key = $1", key)
        return True

    async def exists(self, key: str) -> bool:
        return await self.db.fetchval(
            "SELECT EXISTS(SELECT 1 FROM cache WHERE key = $1 AND expires_at > NOW())",
            key
        )

    async def clear(self) -> bool:
        await self.db.execute("DELETE FROM cache")
        return True

class CacheManager:
    """Manager for cache backends"""

    def __init__(self, config):
        self.config = config
        self._backends = {}
        self._default_backend = None

    def get_backend(self, name: str = None) -> CacheBackend:
        """Get cache backend by name"""
        if name is None:
            if self._default_backend is None:
                self._default_backend = self._create_backend(self.config.backend)
            return self._default_backend

        if name not in self._backends:
            self._backends[name] = self._create_backend(name)

        return self._backends[name]

    def _create_backend(self, backend: str) -> CacheBackend:
        """Create cache backend based on type"""
        if backend == "memory":
            return MemoryCache()
        elif backend == "redis":
            redis_url = f"redis://{self.config.host}:{self.config.port}/{self.config.database}"
            return RedisCache(redis_url)
        elif backend == "file":
            return FileCache()
        elif backend == "database":
            # This would need a database connection
            raise NotImplementedError("Database cache backend requires database connection")
        else:
            raise ValueError(f"Unsupported cache backend: {backend}")

    async def get(self, key: str, backend: str = None) -> Optional[Any]:
        """Get value from cache"""
        cache = self.get_backend(backend)
        return await cache.get(self._make_key(key))

    async def set(self, key: str, value: Any, expire: int = None, backend: str = None) -> bool:
        """Set value in cache"""
        cache = self.get_backend(backend)
        return await cache.set(self._make_key(key), value, expire)

    async def delete(self, key: str, backend: str = None) -> bool:
        """Delete value from cache"""
        cache = self.get_backend(backend)
        return await cache.delete(self._make_key(key))

    async def exists(self, key: str, backend: str = None) -> bool:
        """Check if key exists in cache"""
        cache = self.get_backend(backend)
        return await cache.exists(self._make_key(key))

    async def clear(self, backend: str = None) -> bool:
        """Clear cache"""
        cache = self.get_backend(backend)
        return await cache.clear()

    def _make_key(self, key: str) -> str:
        """Make cache key with prefix"""
        return f"{self.config.key_prefix}{key}"

# Global cache manager instance
cache_manager = None

def get_cache_manager(config=None) -> CacheManager:
    """Get global cache manager instance"""
    global cache_manager
    if cache_manager is None:
        from pydance.core.config import AppConfig
        config = config or AppConfig()
        cache_manager = CacheManager(config.cache)
    return cache_manager

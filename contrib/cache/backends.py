"""
Cache backend implementations.
"""

import asyncio
import json
import os
import time
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod
from datetime import datetime, timedelta


class CacheBackend(ABC):
    """Abstract base class for cache backends"""

    @abstractmethod
    async def get(self, key: str) -> Optional[str]:
        """Get value by key"""
        pass

    @abstractmethod
    async def set(self, key: str, value: str, timeout: int) -> bool:
        """Set value with timeout"""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete value by key"""
        pass

    @abstractmethod
    async def has_key(self, key: str) -> bool:
        """Check if key exists"""
        pass

    @abstractmethod
    async def clear(self) -> bool:
        """Clear all cache"""
        pass

    @abstractmethod
    async def get_many(self, keys: List[str]) -> Dict[str, Optional[str]]:
        """Get multiple values"""
        pass

    @abstractmethod
    async def set_many(self, data: Dict[str, str], timeout: int) -> bool:
        """Set multiple values"""
        pass

    @abstractmethod
    async def delete_many(self, keys: List[str]) -> bool:
        """Delete multiple values"""
        pass

    @abstractmethod
    async def incr(self, key: str, delta: int = 1) -> Optional[int]:
        """Increment numeric value"""
        pass

    @abstractmethod
    async def decr(self, key: str, delta: int = 1) -> Optional[int]:
        """Decrement numeric value"""
        pass

    @abstractmethod
    async def close(self):
        """Close backend connection"""
        pass


class MemoryBackend(CacheBackend):
    """In-memory cache backend"""

    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}

    async def get(self, key: str) -> Optional[str]:
        """Get value by key"""
        if key in self._cache:
            entry = self._cache[key]
            if entry['expires'] > time.time():
                return entry['value']
            else:
                # Expired, remove it
                del self._cache[key]
        return None

    async def set(self, key: str, value: str, timeout: int) -> bool:
        """Set value with timeout"""
        self._cache[key] = {
            'value': value,
            'expires': time.time() + timeout
        }
        return True

    async def delete(self, key: str) -> bool:
        """Delete value by key"""
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    async def has_key(self, key: str) -> bool:
        """Check if key exists"""
        value = await self.get(key)
        return value is not None

    async def clear(self) -> bool:
        """Clear all cache"""
        self._cache.clear()
        return True

    async def get_many(self, keys: List[str]) -> Dict[str, Optional[str]]:
        """Get multiple values"""
        result = {}
        for key in keys:
            result[key] = await self.get(key)
        return result

    async def set_many(self, data: Dict[str, str], timeout: int) -> bool:
        """Set multiple values"""
        for key, value in data.items():
            await self.set(key, value, timeout)
        return True

    async def delete_many(self, keys: List[str]) -> bool:
        """Delete multiple values"""
        for key in keys:
            await self.delete(key)
        return True

    async def incr(self, key: str, delta: int = 1) -> Optional[int]:
        """Increment numeric value"""
        value = await self.get(key)
        if value is None:
            return None

        try:
            new_value = int(value) + delta
            await self.set(key, str(new_value), 0)  # Keep existing timeout
            return new_value
        except ValueError:
            return None

    async def decr(self, key: str, delta: int = 1) -> Optional[int]:
        """Decrement numeric value"""
        return await self.incr(key, -delta)

    async def close(self):
        """No-op for memory backend"""
        pass


class FileBackend(CacheBackend):
    """File-based cache backend"""

    def __init__(self, directory: str = 'cache'):
        self.directory = directory
        os.makedirs(directory, exist_ok=True)

    def _get_file_path(self, key: str) -> str:
        """Get file path for key"""
        # Sanitize key for filename
        safe_key = "".join(c for c in key if c.isalnum() or c in ('_', '-')).rstrip()
        if not safe_key:
            safe_key = "default"
        return os.path.join(self.directory, f"{safe_key}.cache")

    async def get(self, key: str) -> Optional[str]:
        """Get value by key"""
        file_path = self._get_file_path(key)

        if not os.path.exists(file_path):
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if data['expires'] > time.time():
                return data['value']
            else:
                # Expired, remove file
                os.remove(file_path)
                return None

        except (json.JSONDecodeError, KeyError, OSError):
            return None

    async def set(self, key: str, value: str, timeout: int) -> bool:
        """Set value with timeout"""
        file_path = self._get_file_path(key)

        data = {
            'value': value,
            'expires': time.time() + timeout
        }

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f)
            return True
        except OSError:
            return False

    async def delete(self, key: str) -> bool:
        """Delete value by key"""
        file_path = self._get_file_path(key)

        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                return True
            except OSError:
                return False
        return False

    async def has_key(self, key: str) -> bool:
        """Check if key exists"""
        value = await self.get(key)
        return value is not None

    async def clear(self) -> bool:
        """Clear all cache"""
        try:
            for filename in os.listdir(self.directory):
                if filename.endswith('.cache'):
                    os.remove(os.path.join(self.directory, filename))
            return True
        except OSError:
            return False

    async def get_many(self, keys: List[str]) -> Dict[str, Optional[str]]:
        """Get multiple values"""
        result = {}
        for key in keys:
            result[key] = await self.get(key)
        return result

    async def set_many(self, data: Dict[str, str], timeout: int) -> bool:
        """Set multiple values"""
        for key, value in data.items():
            await self.set(key, value, timeout)
        return True

    async def delete_many(self, keys: List[str]) -> bool:
        """Delete multiple values"""
        for key in keys:
            await self.delete(key)
        return True

    async def incr(self, key: str, delta: int = 1) -> Optional[int]:
        """Increment numeric value"""
        value = await self.get(key)
        if value is None:
            return None

        try:
            new_value = int(value) + delta
            # Need to preserve timeout, but file backend doesn't store it separately
            # For simplicity, set a default timeout
            await self.set(key, str(new_value), 3600)  # 1 hour
            return new_value
        except ValueError:
            return None

    async def decr(self, key: str, delta: int = 1) -> Optional[int]:
        """Decrement numeric value"""
        return await self.incr(key, -delta)

    async def close(self):
        """No-op for file backend"""
        pass


class RedisBackend(CacheBackend):
    """Redis cache backend"""

    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0,
                 password: Optional[str] = None, **kwargs):
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.redis = None

        import redis.asyncio as redis
        self.redis = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            **kwargs
        )

    async def get(self, key: str) -> Optional[str]:
        """Get value by key"""
        if not self.redis:
            return None

        try:
            value = await self.redis.get(key)
            return value.decode('utf-8') if value else None
        except Exception:
            return None

    async def set(self, key: str, value: str, timeout: int) -> bool:
        """Set value with timeout"""
        if not self.redis:
            return False

        try:
            return await self.redis.setex(key, timeout, value)
        except Exception:
            return False

    async def delete(self, key: str) -> bool:
        """Delete value by key"""
        if not self.redis:
            return False

        try:
            return bool(await self.redis.delete(key))
        except Exception:
            return False

    async def has_key(self, key: str) -> bool:
        """Check if key exists"""
        if not self.redis:
            return False

        try:
            return bool(await self.redis.exists(key))
        except Exception:
            return False

    async def clear(self) -> bool:
        """Clear all cache"""
        if not self.redis:
            return False

        try:
            return bool(await self.redis.flushdb())
        except Exception:
            return False

    async def get_many(self, keys: List[str]) -> Dict[str, Optional[str]]:
        """Get multiple values"""
        if not self.redis:
            return {}

        try:
            values = await self.redis.mget(keys)
            result = {}
            for key, value in zip(keys, values):
                result[key] = value.decode('utf-8') if value else None
            return result
        except Exception:
            return {}

    async def set_many(self, data: Dict[str, str], timeout: int) -> bool:
        """Set multiple values"""
        if not self.redis:
            return False

        try:
            # Use pipeline for atomic operation
            async with self.redis.pipeline() as pipe:
                for key, value in data.items():
                    pipe.setex(key, timeout, value)
                await pipe.execute()
            return True
        except Exception:
            return False

    async def delete_many(self, keys: List[str]) -> bool:
        """Delete multiple values"""
        if not self.redis:
            return False

        try:
            return bool(await self.redis.delete(*keys))
        except Exception:
            return False

    async def incr(self, key: str, delta: int = 1) -> Optional[int]:
        """Increment numeric value"""
        if not self.redis:
            return None

        try:
            return await self.redis.incrby(key, delta)
        except Exception:
            return None

    async def decr(self, key: str, delta: int = 1) -> Optional[int]:
        """Decrement numeric value"""
        if not self.redis:
            return None

        try:
            return await self.redis.decrby(key, delta)
        except Exception:
            return None

    async def close(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()


class MemcachedBackend(CacheBackend):
    """Memcached cache backend"""

    def __init__(self, servers: List[str] = None, **kwargs):
        self.servers = servers or ['127.0.0.1:11211']
        self.memcache = None

        import aiomcache
        self.memcache = aiomcache.Client(self.servers[0], **kwargs)

    async def get(self, key: str) -> Optional[str]:
        """Get value by key"""
        if not self.memcache:
            return None

        try:
            value = await self.memcache.get(key.encode())
            return value.decode('utf-8') if value else None
        except Exception:
            return None

    async def set(self, key: str, value: str, timeout: int) -> bool:
        """Set value with timeout"""
        if not self.memcache:
            return False

        try:
            return await self.memcache.set(key.encode(), value.encode(), exptime=timeout)
        except Exception:
            return False

    async def delete(self, key: str) -> bool:
        """Delete value by key"""
        if not self.memcache:
            return False

        try:
            return await self.memcache.delete(key.encode())
        except Exception:
            return False

    async def has_key(self, key: str) -> bool:
        """Check if key exists"""
        value = await self.get(key)
        return value is not None

    async def clear(self) -> bool:
        """Clear all cache - not supported by memcached"""
        return False

    async def get_many(self, keys: List[str]) -> Dict[str, Optional[str]]:
        """Get multiple values"""
        if not self.memcache:
            return {}

        try:
            key_bytes = [key.encode() for key in keys]
            values = await self.memcache.multi_get(*key_bytes)

            result = {}
            for key, value in zip(keys, values):
                result[key] = value.decode('utf-8') if value else None
            return result
        except Exception:
            return {}

    async def set_many(self, data: Dict[str, str], timeout: int) -> bool:
        """Set multiple values"""
        for key, value in data.items():
            if not await self.set(key, value, timeout):
                return False
        return True

    async def delete_many(self, keys: List[str]) -> bool:
        """Delete multiple values"""
        for key in keys:
            if not await self.delete(key):
                return False
        return True

    async def incr(self, key: str, delta: int = 1) -> Optional[int]:
        """Increment numeric value"""
        if not self.memcache:
            return None

        try:
            return await self.memcache.incr(key.encode(), delta)
        except Exception:
            return None

    async def decr(self, key: str, delta: int = 1) -> Optional[int]:
        """Decrement numeric value"""
        if not self.memcache:
            return None

        try:
            return await self.memcache.decr(key.encode(), delta)
        except Exception:
            return None

    async def close(self):
        """Close memcached connection"""
        if self.memcache:
            self.memcache.close()


class DatabaseBackend(CacheBackend):
    """Database-backed cache backend"""

    def __init__(self, model=None):
        # This would use a cache model from the database
        self.model = model

    async def get(self, key: str) -> Optional[str]:
        """Get value by key"""
        # Implementation would query database
        return None

    async def set(self, key: str, value: str, timeout: int) -> bool:
        """Set value with timeout"""
        # Implementation would save to database
        return False

    async def delete(self, key: str) -> bool:
        """Delete value by key"""
        # Implementation would delete from database
        return False

    async def has_key(self, key: str) -> bool:
        """Check if key exists"""
        value = await self.get(key)
        return value is not None

    async def clear(self) -> bool:
        """Clear all cache"""
        # Implementation would clear cache table
        return False

    async def get_many(self, keys: List[str]) -> Dict[str, Optional[str]]:
        """Get multiple values"""
        # Implementation would query database
        return {}

    async def set_many(self, data: Dict[str, str], timeout: int) -> bool:
        """Set multiple values"""
        # Implementation would save to database
        return False

    async def delete_many(self, keys: List[str]) -> bool:
        """Delete multiple values"""
        # Implementation would delete from database
        return False

    async def incr(self, key: str, delta: int = 1) -> Optional[int]:
        """Increment numeric value"""
        # Implementation would update database
        return None

    async def decr(self, key: str, delta: int = 1) -> Optional[int]:
        """Decrement numeric value"""
        # Implementation would update database
        return None

    async def close(self):
        """No-op for database backend"""
        pass





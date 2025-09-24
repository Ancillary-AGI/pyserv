"""
Redis cache implementation for distributed caching.
"""

import asyncio
import json
import logging
from typing import Optional, Any, Dict
from datetime import timedelta

class RedisCache:
    """
    Redis-based distributed cache implementation.
    """

    def __init__(self, config: CacheConfig):
        self.config = config
        self.redis_client = None
        self.logger = logging.getLogger("redis_cache")

    async def initialize(self):
        """Initialize Redis connection."""
        try:
            import redis.asyncio as redis
            self.redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            # Test connection
            await self.redis_client.ping()
            self.logger.info("Redis cache initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Redis cache: {e}")
            raise

    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis cache."""
        try:
            if not self.redis_client:
                return None

            value = await self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            self.logger.error(f"Error getting from Redis cache: {e}")
            return None

    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """Set value in Redis cache."""
        try:
            if not self.redis_client:
                return False

            serialized_value = json.dumps(value)
            if ttl_seconds:
                await self.redis_client.setex(key, ttl_seconds, serialized_value)
            else:
                await self.redis_client.set(key, serialized_value)
            return True
        except Exception as e:
            self.logger.error(f"Error setting in Redis cache: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from Redis cache."""
        try:
            if not self.redis_client:
                return False

            result = await self.redis_client.delete(key)
            return result > 0
        except Exception as e:
            self.logger.error(f"Error deleting from Redis cache: {e}")
            return False

    async def clear(self):
        """Clear all cache entries."""
        try:
            if not self.redis_client:
                return

            await self.redis_client.flushdb()
        except Exception as e:
            self.logger.error(f"Error clearing Redis cache: {e}")

    async def invalidate_pattern(self, pattern: str):
        """Invalidate cache entries matching pattern."""
        try:
            if not self.redis_client:
                return

            # Get all keys matching pattern
            keys = await self.redis_client.keys(pattern)
            if keys:
                await self.redis_client.delete(*keys)
        except Exception as e:
            self.logger.error(f"Error invalidating Redis cache pattern: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get Redis cache statistics."""
        if not self.redis_client:
            return {"status": "disconnected"}

        try:
            info = self.redis_client.info()
            return {
                "status": "connected",
                "used_memory": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0)
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

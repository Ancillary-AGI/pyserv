"""
Advanced cache manager with multiple cache levels and strategies.
"""

import asyncio
import hashlib
import json
import logging
import time
from typing import Dict, List, Optional, Any, Callable, Tuple, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

class CacheLevel(Enum):
    L1 = "L1"  # In-memory, fastest
    L2 = "L2"  # Redis, distributed
    L3 = "L3"  # CDN, global

class CacheStrategy(Enum):
    LRU = "LRU"  # Least Recently Used
    LFU = "LFU"  # Least Frequently Used
    TTL = "TTL"  # Time To Live
    WRITE_THROUGH = "WRITE_THROUGH"
    WRITE_BACK = "WRITE_BACK"

@dataclass
class CacheConfig:
    max_memory_size: int = 100 * 1024 * 1024  # 100MB
    ttl_seconds: int = 3600  # 1 hour
    strategy: CacheStrategy = CacheStrategy.LRU
    enable_compression: bool = True
    compression_threshold: int = 1024  # 1KB
    enable_metrics: bool = True
    enable_warmup: bool = False
    warmup_file: Optional[str] = None

@dataclass
class CacheEntry:
    key: str
    value: Any
    created_at: datetime
    accessed_at: datetime
    expires_at: Optional[datetime]
    access_count: int = 0
    size_bytes: int = 0
    compressed: bool = False

class CacheManager:
    """
    Advanced cache manager with multiple levels and strategies.
    """

    def __init__(self, config: CacheConfig):
        self.config = config
        self.caches: Dict[CacheLevel, Any] = {}
        self.metrics = CacheMetricsCollector()
        self.logger = logging.getLogger("cache_manager")
        self._lock = asyncio.Lock()

    async def initialize(self):
        """Initialize all cache levels."""
        # Initialize L1 (Memory) cache
        self.caches[CacheLevel.L1] = MemoryCache(self.config)

        # Initialize L2 (Redis) cache if available
        try:
            self.caches[CacheLevel.L2] = RedisCache(self.config)
            self.logger.info("Redis cache initialized")
        except Exception as e:
            self.logger.warning(f"Redis cache not available: {e}")

        # Initialize L3 (CDN) cache if configured
        try:
            self.caches[CacheLevel.L3] = CDNCache(self.config)
            self.logger.info("CDN cache initialized")
        except Exception as e:
            self.logger.warning(f"CDN cache not available: {e}")

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache using hierarchy."""
        cache_key = self._generate_key(key)

        # Try L1 cache first
        if CacheLevel.L1 in self.caches:
            value = await self.caches[CacheLevel.L1].get(cache_key)
            if value is not None:
                self.metrics.record_hit(CacheLevel.L1)
                return value

        # Try L2 cache
        if CacheLevel.L2 in self.caches:
            value = await self.caches[CacheLevel.L2].get(cache_key)
            if value is not None:
                self.metrics.record_hit(CacheLevel.L2)
                # Populate L1 cache
                await self.caches[CacheLevel.L1].set(cache_key, value)
                return value

        # Try L3 cache
        if CacheLevel.L3 in self.caches:
            value = await self.caches[CacheLevel.L3].get(cache_key)
            if value is not None:
                self.metrics.record_hit(CacheLevel.L3)
                # Populate L1 and L2 caches
                await self.caches[CacheLevel.L1].set(cache_key, value)
                if CacheLevel.L2 in self.caches:
                    await self.caches[CacheLevel.L2].set(cache_key, value)
                return value

        self.metrics.record_miss()
        return None

    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """Set value in all cache levels."""
        cache_key = self._generate_key(key)
        ttl = ttl_seconds or self.config.ttl_seconds

        success = True

        # Set in L1 cache
        if CacheLevel.L1 in self.caches:
            if not await self.caches[CacheLevel.L1].set(cache_key, value, ttl):
                success = False

        # Set in L2 cache (write-through)
        if CacheLevel.L2 in self.caches:
            if not await self.caches[CacheLevel.L2].set(cache_key, value, ttl):
                success = False

        # Set in L3 cache (write-back for CDN)
        if CacheLevel.L3 in self.caches:
            if not await self.caches[CacheLevel.L3].set(cache_key, value, ttl):
                success = False

        return success

    async def delete(self, key: str) -> bool:
        """Delete value from all cache levels."""
        cache_key = self._generate_key(key)

        success = True

        # Delete from all levels
        for level in self.caches.values():
            if not await level.delete(cache_key):
                success = False

        return success

    async def clear(self):
        """Clear all cache levels."""
        for level in self.caches.values():
            await level.clear()

    def _generate_key(self, key: str) -> str:
        """Generate cache key with namespace."""
        return f"pyserv:{hashlib.md5(key.encode()).hexdigest()}"

    def get_metrics(self) -> Dict[str, Any]:
        """Get cache metrics."""
        return {
            "total_hits": self.metrics.total_hits,
            "total_misses": self.metrics.total_misses,
            "hit_rate": self.metrics.hit_rate,
            "level_metrics": self.metrics.get_level_metrics(),
            "memory_usage": self.metrics.get_memory_usage()
        }

    async def warmup(self, data: Dict[str, Any]):
        """Warmup cache with provided data."""
        for key, value in data.items():
            await self.set(key, value)

    async def invalidate_pattern(self, pattern: str):
        """Invalidate cache entries matching pattern."""
        for level in self.caches.values():
            await level.invalidate_pattern(pattern)

# Global cache manager
cache_manager = CacheManager(CacheConfig())

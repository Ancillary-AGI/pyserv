"""
Multi-level distributed caching system for Pyserv  framework.

This module provides aggressive caching strategies with:
- Multi-level caching (L1: Memory, L2: Redis, L3: Database)
- Cache warming and prefetching
- Distributed cache invalidation
- Cache analytics and monitoring
- Intelligent cache eviction policies
- Cache-aside, write-through, and write-behind patterns
"""

import asyncio
import logging
import time
import hashlib
import json
from typing import Dict, List, Optional, Any, Callable, AsyncGenerator, Set
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum
import aioredis
from concurrent.futures import ThreadPoolExecutor
import threading

from pyserv.caching import CacheManager, MemoryCache, RedisCache, DatabaseCache
from pyserv.database.database_pool import get_pooled_connection
from pyserv.monitoring.metrics import get_metrics_collector


class CacheLevel(Enum):
    """Cache levels in hierarchy"""
    L1_MEMORY = 1
    L2_REDIS = 2
    L3_DATABASE = 3


class CacheStrategy(Enum):
    """Caching strategies"""
    CACHE_ASIDE = "cache_aside"
    WRITE_THROUGH = "write_through"
    WRITE_BEHIND = "write_behind"
    READ_THROUGH = "read_through"


@dataclass
class CacheConfig:
    """Configuration for distributed cache"""
    enable_l1: bool = True
    enable_l2: bool = True
    enable_l3: bool = True
    l1_ttl: int = 300  # 5 minutes
    l2_ttl: int = 3600  # 1 hour
    l3_ttl: int = 86400  # 24 hours
    max_memory_items: int = 10000
    redis_url: str = "redis://localhost:6379"
    cache_warming_enabled: bool = True
    prefetch_enabled: bool = True
    invalidation_propagation: bool = True
    compression_threshold: int = 1024  # Compress values > 1KB


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: str
    value: Any
    level: CacheLevel
    created_at: float = field(default_factory=time.time)
    accessed_at: float = field(default_factory=time.time)
    access_count: int = 0
    ttl: int = 0
    tags: Set[str] = field(default_factory=set)
    compressed: bool = False

    def is_expired(self) -> bool:
        """Check if entry is expired"""
        if self.ttl <= 0:
            return False
        return (time.time() - self.created_at) > self.ttl

    def touch(self):
        """Update access time and count"""
        self.accessed_at = time.time()
        self.access_count += 1


class CacheAnalytics:
    """Cache performance analytics"""

    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.sets = 0
        self.deletes = 0
        self.errors = 0
        self._lock = asyncio.Lock()

    async def record_hit(self, level: CacheLevel):
        async with self._lock:
            self.hits += 1

    async def record_miss(self, level: CacheLevel):
        async with self._lock:
            self.misses += 1

    async def record_eviction(self, level: CacheLevel):
        async with self._lock:
            self.evictions += 1

    async def record_set(self, level: CacheLevel):
        async with self._lock:
            self.sets += 1

    async def record_delete(self, level: CacheLevel):
        async with self._lock:
            self.deletes += 1

    async def record_error(self, level: CacheLevel):
        async with self._lock:
            self.errors += 1

    def get_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def get_stats(self) -> Dict[str, Any]:
        """Get analytics statistics"""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "sets": self.sets,
            "deletes": self.deletes,
            "errors": self.errors,
            "hit_rate": self.get_hit_rate()
        }


class DistributedCache:
    """Multi-level distributed cache implementation"""

    def __init__(self, config: CacheConfig = None):
        self.config = config or CacheConfig()
        self.logger = logging.getLogger("distributed_cache")
        self.metrics = get_metrics_collector()
        self.analytics = CacheAnalytics()

        # Cache levels
        self._l1_cache: Optional[MemoryCache] = None
        self._l2_cache: Optional[RedisCache] = None
        self._l3_cache: Optional[DatabaseCache] = None

        # Cache invalidation channels
        self._invalidation_channels: Dict[str, Set[str]] = {}
        self._pubsub_task: Optional[asyncio.Task] = None

        # Background tasks
        self._warming_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None

        # Thread pool for compression
        self._executor = ThreadPoolExecutor(max_workers=4)

        # Initialize caches
        self._init_caches()

        # Register metrics
        self._register_metrics()

    def _init_caches(self):
        """Initialize cache levels"""
        if self.config.enable_l1:
            self._l1_cache = MemoryCache()

        if self.config.enable_l2:
            self._l2_cache = RedisCache(self.config.redis_url)

        if self.config.enable_l3:
            # Initialize database cache with pooled connection
            db_config = type('Config', (), {
                'database_url': 'sqlite:///cache.db'  # Default cache database
            })()
            db_conn = get_pooled_connection(db_config)
            self._l3_cache = DatabaseCache(db_conn)

    def _register_metrics(self):
        """Register cache metrics"""
        self.metrics.create_gauge(
            "cache_l1_items",
            "Number of items in L1 cache"
        )
        self.metrics.create_gauge(
            "cache_l2_items",
            "Number of items in L2 cache"
        )
        self.metrics.create_counter(
            "cache_hits_total",
            "Total cache hits"
        )
        self.metrics.create_counter(
            "cache_misses_total",
            "Total cache misses"
        )
        self.metrics.create_histogram(
            "cache_operation_duration_seconds",
            "Cache operation duration",
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
        )

    async def start(self):
        """Start the distributed cache"""
        # Start background tasks
        if self.config.cache_warming_enabled:
            self._warming_task = asyncio.create_task(self._cache_warming_loop())

        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        if self.config.invalidation_propagation and self._l2_cache:
            self._pubsub_task = asyncio.create_task(self._invalidation_listener())

        self.logger.info("Distributed cache started")

    async def stop(self):
        """Stop the distributed cache"""
        # Cancel background tasks
        tasks = []
        if self._warming_task:
            self._warming_task.cancel()
            tasks.append(self._warming_task)
        if self._cleanup_task:
            self._cleanup_task.cancel()
            tasks.append(self._cleanup_task)
        if self._pubsub_task:
            self._pubsub_task.cancel()
            tasks.append(self._pubsub_task)

        await asyncio.gather(*tasks, return_exceptions=True)
        self.logger.info("Distributed cache stopped")

    async def get(self, key: str, strategy: CacheStrategy = CacheStrategy.CACHE_ASIDE) -> Optional[Any]:
        """Get value from cache using specified strategy"""
        start_time = time.time()

        try:
            # Try L1 cache first
            if self._l1_cache and self.config.enable_l1:
                value = await self._l1_cache.get(key)
                if value is not None:
                    await self.analytics.record_hit(CacheLevel.L1_MEMORY)
                    duration = time.time() - start_time
                    self.metrics.get_metric("cache_operation_duration_seconds").observe(duration)
                    return self._decompress_if_needed(value)

            # Try L2 cache
            if self._l2_cache and self.config.enable_l2:
                value = await self._l2_cache.get(key)
                if value is not None:
                    await self.analytics.record_hit(CacheLevel.L2_REDIS)
                    # Promote to L1
                    if self._l1_cache:
                        await self._l1_cache.set(key, value, self.config.l1_ttl)
                    duration = time.time() - start_time
                    self.metrics.get_metric("cache_operation_duration_seconds").observe(duration)
                    return self._decompress_if_needed(value)

            # Try L3 cache
            if self._l3_cache and self.config.enable_l3:
                value = await self._l3_cache.get(key)
                if value is not None:
                    await self.analytics.record_hit(CacheLevel.L3_DATABASE)
                    # Promote to higher levels
                    await self._promote_to_higher_levels(key, value)
                    duration = time.time() - start_time
                    self.metrics.get_metric("cache_operation_duration_seconds").observe(duration)
                    return self._decompress_if_needed(value)

            # Cache miss
            await self.analytics.record_miss(CacheLevel.L1_MEMORY)
            self.metrics.get_metric("cache_misses_total").increment()
            duration = time.time() - start_time
            self.metrics.get_metric("cache_operation_duration_seconds").observe(duration)
            return None

        except Exception as e:
            self.logger.error(f"Cache get error for key {key}: {e}")
            await self.analytics.record_error(CacheLevel.L1_MEMORY)
            return None

    async def set(self, key: str, value: Any, ttl: int = None,
                  strategy: CacheStrategy = CacheStrategy.CACHE_ASIDE,
                  tags: Set[str] = None) -> bool:
        """Set value in cache using specified strategy"""
        start_time = time.time()

        try:
            # Compress if needed
            compressed_value = await self._compress_if_needed(value)

            # Determine TTL for each level
            l1_ttl = ttl or self.config.l1_ttl
            l2_ttl = ttl or self.config.l2_ttl
            l3_ttl = ttl or self.config.l3_ttl

            success = True

            # Set in L1
            if self._l1_cache and self.config.enable_l1:
                success &= await self._l1_cache.set(key, compressed_value, l1_ttl)
                await self.analytics.record_set(CacheLevel.L1_MEMORY)

            # Set in L2
            if self._l2_cache and self.config.enable_l2:
                success &= await self._l2_cache.set(key, compressed_value, l2_ttl)
                await self.analytics.record_set(CacheLevel.L2_REDIS)

            # Set in L3
            if self._l3_cache and self.config.enable_l3:
                success &= await self._l3_cache.set(key, compressed_value, l3_ttl)
                await self.analytics.record_set(CacheLevel.L3_DATABASE)

            # Store tags for invalidation
            if tags:
                await self._store_tags(key, tags)

            duration = time.time() - start_time
            self.metrics.get_metric("cache_operation_duration_seconds").observe(duration)
            return success

        except Exception as e:
            self.logger.error(f"Cache set error for key {key}: {e}")
            await self.analytics.record_error(CacheLevel.L1_MEMORY)
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from all cache levels"""
        try:
            success = True

            # Delete from L1
            if self._l1_cache:
                success &= await self._l1_cache.delete(key)
                await self.analytics.record_delete(CacheLevel.L1_MEMORY)

            # Delete from L2
            if self._l2_cache:
                success &= await self._l2_cache.delete(key)
                await self.analytics.record_delete(CacheLevel.L2_REDIS)

            # Delete from L3
            if self._l3_cache:
                success &= await self._l3_cache.delete(key)
                await self.analytics.record_delete(CacheLevel.L3_DATABASE)

            # Propagate invalidation
            if self.config.invalidation_propagation:
                await self._propagate_invalidation(key)

            return success

        except Exception as e:
            self.logger.error(f"Cache delete error for key {key}: {e}")
            await self.analytics.record_error(CacheLevel.L1_MEMORY)
            return False

    async def invalidate_by_tag(self, tag: str) -> int:
        """Invalidate all cache entries with a specific tag"""
        try:
            keys_to_delete = await self._get_keys_by_tag(tag)
            deleted_count = 0

            for key in keys_to_delete:
                if await self.delete(key):
                    deleted_count += 1

            self.logger.info(f"Invalidated {deleted_count} cache entries for tag {tag}")
            return deleted_count

        except Exception as e:
            self.logger.error(f"Tag invalidation error for tag {tag}: {e}")
            return 0

    async def clear(self) -> bool:
        """Clear all cache levels"""
        try:
            success = True

            if self._l1_cache:
                success &= await self._l1_cache.clear()
            if self._l2_cache:
                success &= await self._l2_cache.clear()
            if self._l3_cache:
                success &= await self._l3_cache.clear()

            return success

        except Exception as e:
            self.logger.error(f"Cache clear error: {e}")
            return False

    async def prefetch(self, keys: List[str]) -> None:
        """Prefetch multiple keys into cache"""
        if not self.config.prefetch_enabled:
            return

        tasks = []
        for key in keys:
            tasks.append(self.get(key))

        await asyncio.gather(*tasks, return_exceptions=True)

    async def warmup(self, key_patterns: List[str]) -> None:
        """Warm up cache with keys matching patterns"""
        # This would typically load frequently accessed data
        # Implementation depends on specific use case
        pass

    def get_analytics(self) -> Dict[str, Any]:
        """Get cache analytics"""
        return self.analytics.get_stats()

    async def _promote_to_higher_levels(self, key: str, value: Any):
        """Promote value to higher cache levels"""
        try:
            # Promote to L2
            if self._l2_cache and self.config.enable_l2:
                await self._l2_cache.set(key, value, self.config.l2_ttl)

            # Promote to L1
            if self._l1_cache and self.config.enable_l1:
                await self._l1_cache.set(key, value, self.config.l1_ttl)

        except Exception as e:
            self.logger.error(f"Promotion error for key {key}: {e}")

    async def _compress_if_needed(self, value: Any) -> Any:
        """Compress value if it exceeds threshold"""
        if not isinstance(value, (str, bytes, dict, list)):
            return value

        serialized = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
        if len(serialized) > self.config.compression_threshold:
            # Compress using gzip in thread pool
            loop = asyncio.get_event_loop()
            compressed = await loop.run_in_executor(
                self._executor, self._gzip_compress, serialized
            )
            return compressed

        return value

    def _gzip_compress(self, data: str) -> bytes:
        """Compress data using gzip"""
        import gzip
        return gzip.compress(data.encode('utf-8'))

    def _decompress_if_needed(self, value: Any) -> Any:
        """Decompress value if it's compressed"""
        if isinstance(value, bytes):
            try:
                # Try to decompress
                import gzip
                decompressed = gzip.decompress(value).decode('utf-8')
                return json.loads(decompressed)
            except:
                return value
        return value

    async def _store_tags(self, key: str, tags: Set[str]):
        """Store tags for cache invalidation"""
        for tag in tags:
            if tag not in self._invalidation_channels:
                self._invalidation_channels[tag] = set()
            self._invalidation_channels[tag].add(key)

    async def _get_keys_by_tag(self, tag: str) -> List[str]:
        """Get all keys associated with a tag"""
        if tag in self._invalidation_channels:
            return list(self._invalidation_channels[tag])
        return []

    async def _propagate_invalidation(self, key: str):
        """Propagate cache invalidation to other instances"""
        if self._l2_cache and self.config.invalidation_propagation:
            try:
                # Publish invalidation message to Redis pubsub
                await self._l2_cache._get_redis().publish(
                    "cache_invalidation",
                    json.dumps({"action": "invalidate", "key": key})
                )
            except Exception as e:
                self.logger.error(f"Invalidation propagation error: {e}")

    async def _invalidation_listener(self):
        """Listen for cache invalidation messages"""
        try:
            redis = await self._l2_cache._get_redis()
            pubsub = redis.pubsub()
            await pubsub.subscribe("cache_invalidation")

            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = json.loads(message["data"])
                    if data["action"] == "invalidate":
                        # Invalidate local cache
                        await self.delete(data["key"])
        except Exception as e:
            self.logger.error(f"Invalidation listener error: {e}")

    async def _cache_warming_loop(self):
        """Periodic cache warming"""
        while True:
            try:
                await asyncio.sleep(300)  # Warm up every 5 minutes
                await self.warmup([])  # Implement specific warming logic
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Cache warming error: {e}")

    async def _cleanup_loop(self):
        """Periodic cleanup of expired entries"""
        while True:
            try:
                await asyncio.sleep(60)  # Cleanup every minute
                await self._cleanup_expired_entries()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Cleanup error: {e}")

    async def _cleanup_expired_entries(self):
        """Clean up expired cache entries"""
        # This is mainly for L1 cache as L2/L3 handle expiration automatically
        if self._l1_cache:
            # Memory cache cleanup is handled by the cache itself
            pass


# Global distributed cache instance
_distributed_cache: Optional[DistributedCache] = None

def get_distributed_cache(config: CacheConfig = None) -> DistributedCache:
    """Get global distributed cache instance"""
    global _distributed_cache
    if _distributed_cache is None:
        _distributed_cache = DistributedCache(config)
    return _distributed_cache

async def init_distributed_cache(config: CacheConfig = None):
    """Initialize the distributed cache"""
    cache = get_distributed_cache(config)
    await cache.start()
    return cache

async def shutdown_distributed_cache():
    """Shutdown the distributed cache"""
    global _distributed_cache
    if _distributed_cache:
        await _distributed_cache.stop()
        _distributed_cache = None





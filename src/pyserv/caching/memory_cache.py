"""
In-memory cache implementation with LRU eviction.
"""

import asyncio
import heapq
import json
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

from pyserv.caching.cache_manager import CacheConfig

@dataclass
class CacheItem:
    key: str
    value: Any
    created_at: datetime
    accessed_at: datetime
    expires_at: Optional[datetime]
    access_count: int = 0
    size_bytes: int = 0

class MemoryCache:
    """
    High-performance in-memory cache with LRU eviction.
    """

    def __init__(self, config: CacheConfig):
        self.config = config
        self.cache: Dict[str, CacheItem] = {}
        self.access_order: List[Tuple[float, str]] = []  # (access_time, key) for LRU
        self.current_size = 0
        self.logger = logging.getLogger("memory_cache")
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        async with self._lock:
            if key not in self.cache:
                return None

            item = self.cache[key]

            # Check expiration
            if item.expires_at and datetime.now() > item.expires_at:
                await self._evict(key)
                return None

            # Update access information
            item.accessed_at = datetime.now()
            item.access_count += 1

            # Update LRU order
            self._update_access_order(key)

            return item.value

    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """Set value in cache."""
        async with self._lock:
            # Calculate size
            value_size = self._calculate_size(value)
            ttl = timedelta(seconds=ttl_seconds) if ttl_seconds else None

            # Check if we need to evict
            if self.current_size + value_size > self.config.max_memory_size:
                await self._evict_lru()

            # Create cache item
            expires_at = datetime.now() + ttl if ttl else None
            item = CacheItem(
                key=key,
                value=value,
                created_at=datetime.now(),
                accessed_at=datetime.now(),
                expires_at=expires_at,
                size_bytes=value_size
            )

            # Remove old item if exists
            if key in self.cache:
                self.current_size -= self.cache[key].size_bytes
                self._remove_from_access_order(key)

            # Add new item
            self.cache[key] = item
            self.current_size += value_size
            self._update_access_order(key)

            return True

    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        async with self._lock:
            if key in self.cache:
                self.current_size -= self.cache[key].size_bytes
                await self._evict(key)
                return True
            return False

    async def clear(self):
        """Clear all cache entries."""
        async with self._lock:
            self.cache.clear()
            self.access_order.clear()
            self.current_size = 0

    async def _evict(self, key: str):
        """Evict a single cache entry."""
        if key in self.cache:
            self.current_size -= self.cache[key].size_bytes
            del self.cache[key]
            self._remove_from_access_order(key)

    async def _evict_lru(self):
        """Evict least recently used items."""
        while self.current_size > self.config.max_memory_size and self.cache:
            if not self.access_order:
                break

            # Get LRU key
            _, lru_key = heapq.heappop(self.access_order)

            if lru_key in self.cache:
                await self._evict(lru_key)

    def _update_access_order(self, key: str):
        """Update access order for LRU."""
        # Remove old entry
        self._remove_from_access_order(key)

        # Add new entry (negative time for max-heap behavior)
        access_time = -time.time()
        heapq.heappush(self.access_order, (access_time, key))

    def _remove_from_access_order(self, key: str):
        """Remove key from access order."""
        self.access_order = [(t, k) for t, k in self.access_order if k != key]
        heapq.heapify(self.access_order)

    def _calculate_size(self, value: Any) -> int:
        """Calculate approximate size of cached value."""
        try:
            if isinstance(value, str):
                return len(value.encode('utf-8'))
            elif isinstance(value, (dict, list)):
                return len(json.dumps(value).encode('utf-8'))
            else:
                return 64  # Default size for other objects
        except:
            return 64

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "entries": len(self.cache),
            "current_size": self.current_size,
            "max_size": self.config.max_memory_size,
            "utilization": self.current_size / self.config.max_memory_size,
            "access_order_size": len(self.access_order)
        }

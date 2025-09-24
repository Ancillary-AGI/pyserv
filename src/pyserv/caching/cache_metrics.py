"""
Cache metrics collection and monitoring.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, DefaultDict
from collections import defaultdict
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

class CacheMetricsCollector:
    """
    Collects and analyzes cache performance metrics.
    """

    def __init__(self):
        self.total_hits = 0
        self.total_misses = 0
        self.level_hits: Dict[str, int] = defaultdict(int)
        self.level_misses: Dict[str, int] = defaultdict(int)
        self.response_times: List[float] = []
        self.memory_usage: Dict[str, int] = {}
        self._lock = asyncio.Lock()

    async def record_hit(self, level: str):
        """Record a cache hit."""
        async with self._lock:
            self.total_hits += 1
            self.level_hits[level] += 1

    async def record_miss(self):
        """Record a cache miss."""
        async with self._lock:
            self.total_misses += 1

    async def record_response_time(self, response_time: float):
        """Record cache response time."""
        async with self._lock:
            self.response_times.append(response_time)
            # Keep only last 1000 response times
            if len(self.response_times) > 1000:
                self.response_times = self.response_times[-1000:]

    async def record_memory_usage(self, level: str, usage_bytes: int):
        """Record memory usage for cache level."""
        async with self._lock:
            self.memory_usage[level] = usage_bytes

    @property
    def hit_rate(self) -> float:
        """Calculate overall hit rate."""
        total = self.total_hits + self.total_misses
        return self.total_hits / total if total > 0 else 0.0

    def get_level_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for each cache level."""
        return {
            level: {
                "hits": self.level_hits[level],
                "misses": self.level_misses[level],
                "hit_rate": (
                    self.level_hits[level] / (self.level_hits[level] + self.level_misses[level])
                    if (self.level_hits[level] + self.level_misses[level]) > 0 else 0.0
                )
            }
            for level in set(list(self.level_hits.keys()) + list(self.level_misses.keys()))
        }

    def get_memory_usage(self) -> Dict[str, int]:
        """Get memory usage for all cache levels."""
        return self.memory_usage.copy()

    def get_average_response_time(self) -> float:
        """Get average cache response time."""
        if not self.response_times:
            return 0.0
        return sum(self.response_times) / len(self.response_times)

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary."""
        return {
            "total_requests": self.total_hits + self.total_misses,
            "total_hits": self.total_hits,
            "total_misses": self.total_misses,
            "hit_rate": self.hit_rate,
            "average_response_time": self.get_average_response_time(),
            "level_metrics": self.get_level_metrics(),
            "memory_usage": self.get_memory_usage(),
            "timestamp": datetime.now().isoformat()
        }

    def reset_metrics(self):
        """Reset all metrics."""
        self.total_hits = 0
        self.total_misses = 0
        self.level_hits.clear()
        self.level_misses.clear()
        self.response_times.clear()
        self.memory_usage.clear()

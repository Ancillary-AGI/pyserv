"""
Performance Anti-Patterns and Best Practices for PyDance Framework

This module identifies and provides solutions for common performance anti-patterns
that can occur when implementing high-performance optimizations.
"""

import asyncio
import logging
import time
import weakref
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass
from contextlib import asynccontextmanager
import threading
import functools


@dataclass
class AntiPattern:
    """Represents a performance anti-pattern"""
    name: str
    description: str
    symptoms: List[str]
    solutions: List[str]
    severity: str  # 'low', 'medium', 'high', 'critical'


class PerformanceAntiPatterns:
    """Detector and fixer for performance anti-patterns"""

    def __init__(self):
        self.logger = logging.getLogger("PerformanceAntiPatterns")
        self.detected_patterns: List[AntiPattern] = []
        self._pattern_detectors = {
            "cache_stampede": self._detect_cache_stampede,
            "connection_leak": self._detect_connection_leak,
            "blocking_async": self._detect_blocking_async,
            "memory_bloat": self._detect_memory_bloat,
            "thundering_herd": self._detect_thundering_herd,
            "excessive_monitoring": self._detect_excessive_monitoring,
            "improper_caching": self._detect_improper_caching,
            "resource_contention": self._detect_resource_contention,
        }

    def detect_anti_patterns(self) -> List[AntiPattern]:
        """Detect common anti-patterns in the current system"""
        patterns = []

        for detector_name, detector_func in self._pattern_detectors.items():
            try:
                pattern = detector_func()
                if pattern:
                    patterns.append(pattern)
                    self.logger.warning(f"Anti-pattern detected: {pattern.name}")
            except Exception as e:
                self.logger.error(f"Error detecting {detector_name}: {e}")

        return patterns

    def _detect_cache_stampede(self) -> Optional[AntiPattern]:
        """Detect cache stampede (thundering herd) problems"""
        # Check for multiple simultaneous cache misses for same key
        # This would require monitoring cache access patterns

        return AntiPattern(
            name="Cache Stampede",
            description="Multiple requests simultaneously trying to populate the same cache entry",
            symptoms=[
                "High CPU usage during cache misses",
                "Database load spikes",
                "Increased response time variance",
                "Multiple identical queries executing simultaneously"
            ],
            solutions=[
                "Implement cache warming for known keys",
                "Use single-flight pattern for cache misses",
                "Add jitter to cache expiration times",
                "Implement probabilistic early expiration"
            ],
            severity="high"
        )

    def _detect_connection_leak(self) -> Optional[AntiPattern]:
        """Detect database connection leaks"""
        # Monitor connection pool usage patterns

        return AntiPattern(
            name="Connection Leak",
            description="Database connections not properly returned to pool",
            symptoms=[
                "Growing number of active connections",
                "Connection pool exhaustion",
                "Database connection timeouts",
                "Memory usage growth over time"
            ],
            solutions=[
                "Always use context managers for connections",
                "Implement connection leak detection",
                "Set maximum connection lifetime",
                "Monitor connection pool metrics"
            ],
            severity="critical"
        )

    def _detect_blocking_async(self) -> Optional[AntiPattern]:
        """Detect blocking operations in async code"""
        # This would require runtime inspection of async code

        return AntiPattern(
            name="Blocking Async Operations",
            description="Synchronous operations blocking the event loop",
            symptoms=[
                "High event loop latency",
                "Poor concurrent request handling",
                "CPU usage not scaling with load",
                "Timeouts on async operations"
            ],
            solutions=[
                "Use async/await consistently",
                "Move blocking operations to thread pools",
                "Implement proper async database drivers",
                "Use asyncio.to_thread() for sync operations"
            ],
            severity="high"
        )

    def _detect_memory_bloat(self) -> Optional[AntiPattern]:
        """Detect memory bloat from caching or other issues"""
        # Monitor memory usage patterns

        return AntiPattern(
            name="Memory Bloat",
            description="Excessive memory usage from caching or data structures",
            symptoms=[
                "High memory usage",
                "Frequent garbage collection",
                "Out of memory errors",
                "Slow response times due to GC pauses"
            ],
            solutions=[
                "Implement cache size limits",
                "Use weak references for large objects",
                "Implement LRU eviction policies",
                "Monitor and limit cache memory usage"
            ],
            severity="high"
        )

    def _detect_thundering_herd(self) -> Optional[AntiPattern]:
        """Detect thundering herd problems"""
        return AntiPattern(
            name="Thundering Herd",
            description="Multiple processes trying to perform the same operation simultaneously",
            symptoms=[
                "Database load spikes on startup",
                "Cache invalidation causing mass cache misses",
                "High CPU usage during peak loads",
                "Service unavailability during scale events"
            ],
            solutions=[
                "Implement startup staggering",
                "Use distributed locks for critical operations",
                "Implement circuit breakers",
                "Use exponential backoff for retries"
            ],
            severity="medium"
        )

    def _detect_excessive_monitoring(self) -> Optional[AntiPattern]:
        """Detect excessive monitoring overhead"""
        return AntiPattern(
            name="Excessive Monitoring",
            description="Monitoring overhead impacting performance",
            symptoms=[
                "High CPU usage from monitoring",
                "Increased memory usage from metrics storage",
                "Network overhead from metric transmission",
                "Performance degradation under load"
            ],
            solutions=[
                "Sample metrics instead of collecting all data",
                "Use efficient metric storage formats",
                "Implement adaptive monitoring levels",
                "Offload monitoring to separate processes"
            ],
            severity="medium"
        )

    def _detect_improper_caching(self) -> Optional[AntiPattern]:
        """Detect improper caching strategies"""
        return AntiPattern(
            name="Improper Caching",
            description="Inefficient or incorrect caching implementation",
            symptoms=[
                "Low cache hit rates",
                "Cache invalidation storms",
                "Memory waste from unused cache entries",
                "Stale data serving"
            ],
            solutions=[
                "Analyze access patterns for optimal TTL",
                "Implement proper cache key strategies",
                "Use cache tagging for selective invalidation",
                "Implement cache warming strategies"
            ],
            severity="medium"
        )

    def _detect_resource_contention(self) -> Optional[AntiPattern]:
        """Detect resource contention issues"""
        return AntiPattern(
            name="Resource Contention",
            description="Multiple components competing for shared resources",
            symptoms=[
                "Lock contention",
                "Thread pool exhaustion",
                "Database connection pool contention",
                "High context switching"
            ],
            solutions=[
                "Use lock-free data structures where possible",
                "Implement proper connection pooling",
                "Use async primitives instead of threads",
                "Implement request queuing and rate limiting"
            ],
            severity="high"
        )


# Best Practices Implementation

class SafeConnectionPool:
    """Connection pool that avoids common anti-patterns"""

    def __init__(self, max_size: int = 10):
        self.max_size = max_size
        self._pool = asyncio.Queue(maxsize=max_size)
        self._created = 0
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None

    @asynccontextmanager
    async def get_connection(self):
        """Safe context manager for connection usage"""
        conn = await self._acquire_connection()

        try:
            yield conn
        except Exception as e:
            # Log the error but don't re-raise to ensure cleanup
            logging.error(f"Connection usage error: {e}")
            # Mark connection as potentially unhealthy
            if hasattr(conn, '_mark_unhealthy'):
                conn._mark_unhealthy()
        finally:
            await self._release_connection(conn)

    async def _acquire_connection(self):
        """Acquire connection with timeout and proper error handling"""
        try:
            # Try to get existing connection first
            conn = await asyncio.wait_for(
                self._pool.get(),
                timeout=5.0
            )
            return conn
        except asyncio.TimeoutError:
            # Create new connection if pool is empty and under limit
            async with self._lock:
                if self._created < self.max_size:
                    conn = await self._create_connection()
                    self._created += 1
                    return conn
                else:
                    # Wait for a connection to become available
                    return await self._pool.get()

    async def _release_connection(self, conn):
        """Release connection back to pool"""
        try:
            # Check if connection is still healthy
            if await self._is_connection_healthy(conn):
                await self._pool.put(conn)
            else:
                # Connection is unhealthy, don't return to pool
                await self._close_connection(conn)
                async with self._lock:
                    self._created -= 1
        except Exception as e:
            logging.error(f"Error releasing connection: {e}")
            async with self._lock:
                self._created -= 1

    async def _create_connection(self):
        """Create a new connection"""
        # Implementation depends on connection type
        raise NotImplementedError

    async def _is_connection_healthy(self, conn) -> bool:
        """Check if connection is healthy"""
        # Implementation depends on connection type
        return True

    async def _close_connection(self, conn):
        """Close a connection"""
        # Implementation depends on connection type
        pass


class OptimizedCache:
    """Cache implementation that avoids common anti-patterns"""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache: Dict[str, Any] = {}
        self._access_times: Dict[str, float] = {}
        self._lock = asyncio.Lock()
        self._single_flight: Dict[str, asyncio.Future] = {}

    async def get(self, key: str) -> Optional[Any]:
        """Get value with proper locking and single-flight pattern"""
        async with self._lock:
            if key in self._cache:
                self._access_times[key] = time.time()
                return self._cache[key]

            # Check if another request is already fetching this key
            if key in self._single_flight:
                # Wait for the other request to complete
                return await self._single_flight[key]

            # Create a future for single-flight pattern
            future = asyncio.Future()
            self._single_flight[key] = future

        try:
            # Fetch the value (this should be implemented by subclass)
            value = await self._fetch_value(key)

            async with self._lock:
                if value is not None:
                    await self._set_internal(key, value)
                return value

        finally:
            async with self._lock:
                # Clean up single-flight future
                if key in self._single_flight:
                    del self._single_flight[key]

    async def set(self, key: str, value: Any, ttl: Optional[float] = None):
        """Set value with proper locking and eviction"""
        async with self._lock:
            await self._set_internal(key, value, ttl)

            # Evict least recently used items if over limit
            if len(self._cache) > self.max_size:
                await self._evict_lru()

    async def _set_internal(self, key: str, value: Any, ttl: Optional[float] = None):
        """Internal set method"""
        self._cache[key] = value
        self._access_times[key] = time.time()

        if ttl:
            # Schedule cleanup (simplified - should use proper timer)
            asyncio.create_task(self._schedule_cleanup(key, ttl))

    async def _evict_lru(self):
        """Evict least recently used items"""
        if not self._access_times:
            return

        # Find least recently used key
        lru_key = min(self._access_times.items(), key=lambda x: x[1])[0]

        del self._cache[lru_key]
        del self._access_times[lru_key]

    async def _schedule_cleanup(self, key: str, ttl: float):
        """Schedule cleanup of expired key"""
        await asyncio.sleep(ttl)
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                if key in self._access_times:
                    del self._access_times[key]

    async def _fetch_value(self, key: str) -> Optional[Any]:
        """Fetch value from underlying storage"""
        # Should be implemented by subclass
        raise NotImplementedError


class AsyncSafeMetrics:
    """Metrics collection that avoids blocking operations"""

    def __init__(self):
        self._metrics: Dict[str, Any] = {}
        self._lock = asyncio.Lock()
        self._batch_queue: asyncio.Queue = asyncio.Queue()
        self._batch_size = 100
        self._flush_interval = 5.0  # seconds
        self._flush_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the metrics collector"""
        self._flush_task = asyncio.create_task(self._batch_flush_loop())

    async def stop(self):
        """Stop the metrics collector"""
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        # Final flush
        await self._flush_batch()

    async def record_metric(self, name: str, value: Any, labels: Optional[Dict[str, str]] = None):
        """Record a metric asynchronously"""
        # Add to batch queue instead of immediate processing
        await self._batch_queue.put({
            'name': name,
            'value': value,
            'labels': labels or {},
            'timestamp': time.time()
        })

        # Process batch if queue is full
        if self._batch_queue.qsize() >= self._batch_size:
            await self._flush_batch()

    async def _batch_flush_loop(self):
        """Periodic batch flush"""
        while True:
            try:
                await asyncio.sleep(self._flush_interval)
                await self._flush_batch()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"Metrics batch flush error: {e}")

    async def _flush_batch(self):
        """Flush batched metrics"""
        batch = []

        # Collect all items from queue
        while not self._batch_queue.empty():
            try:
                item = self._batch_queue.get_nowait()
                batch.append(item)
            except asyncio.QueueEmpty:
                break

        if not batch:
            return

        # Process batch (send to monitoring system, database, etc.)
        try:
            await self._process_batch(batch)
        except Exception as e:
            logging.error(f"Batch processing error: {e}")

    async def _process_batch(self, batch: List[Dict[str, Any]]):
        """Process a batch of metrics"""
        # Implementation depends on monitoring backend
        # This could send to Prometheus, DataDog, etc.
        pass


# Utility functions for avoiding anti-patterns

def avoid_cache_stampede(func: Callable) -> Callable:
    """Decorator to avoid cache stampede using single-flight pattern"""
    single_flight: Dict[str, asyncio.Future] = {}

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Create a cache key from function arguments
        key = str(hash((func.__name__, args, tuple(sorted(kwargs.items())))))

        # Check if another call is already in flight
        if key in single_flight:
            return await single_flight[key]

        # Create future for this call
        future = asyncio.Future()
        single_flight[key] = future

        try:
            result = await func(*args, **kwargs)
            future.set_result(result)
            return result
        except Exception as e:
            future.set_exception(e)
            raise
        finally:
            # Clean up
            del single_flight[key]

    return wrapper


def avoid_blocking_async(func: Callable) -> Callable:
    """Decorator to automatically move blocking operations to thread pool"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_running_loop()

        # Check if function might block (heuristic)
        if hasattr(func, '_might_block') or 'sync' in func.__name__.lower():
            return await loop.run_in_executor(None, func, *args, **kwargs)
        else:
            return await func(*args, **kwargs)

    return wrapper


def with_timeout(timeout_seconds: float):
    """Decorator to add timeout to async functions"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                logging.error(f"Function {func.__name__} timed out after {timeout_seconds}s")
                raise

        return wrapper
    return decorator


# Performance monitoring for anti-patterns

class AntiPatternMonitor:
    """Monitor for detecting anti-patterns in real-time"""

    def __init__(self):
        self.patterns_detected: Dict[str, int] = {}
        self._lock = asyncio.Lock()

    async def report_pattern(self, pattern_name: str, severity: str = "medium"):
        """Report detection of an anti-pattern"""
        async with self._lock:
            self.patterns_detected[pattern_name] = self.patterns_detected.get(pattern_name, 0) + 1

            # Log based on severity
            if severity == "critical":
                logging.critical(f"Critical anti-pattern detected: {pattern_name}")
            elif severity == "high":
                logging.error(f"High-priority anti-pattern detected: {pattern_name}")
            elif severity == "medium":
                logging.warning(f"Anti-pattern detected: {pattern_name}")
            else:
                logging.info(f"Anti-pattern detected: {pattern_name}")

    async def get_report(self) -> Dict[str, Any]:
        """Get anti-pattern detection report"""
        async with self._lock:
            return {
                "patterns_detected": self.patterns_detected.copy(),
                "total_incidents": sum(self.patterns_detected.values()),
                "most_common": max(self.patterns_detected.items(), key=lambda x: x[1]) if self.patterns_detected else None
            }


# Global anti-pattern monitor
_anti_pattern_monitor = AntiPatternMonitor()

def get_anti_pattern_monitor() -> AntiPatternMonitor:
    """Get global anti-pattern monitor"""
    return _anti_pattern_monitor

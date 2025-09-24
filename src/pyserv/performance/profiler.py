"""
Performance profiling and benchmarking tools for PyServ.
"""

import asyncio
import cProfile
import functools
import io
import pstats
import time
import tracemalloc
from contextlib import contextmanager
from typing import Any, Callable, Dict, List, Optional, Tuple

class Profiler:
    """
    Performance profiler for PyServ applications.
    """

    def __init__(self):
        self.profiler = cProfile.Profile()
        self.is_profiling = False

    def start_profiling(self):
        """Start performance profiling."""
        if not self.is_profiling:
            self.profiler.enable()
            self.is_profiling = True

    def stop_profiling(self) -> str:
        """Stop profiling and return formatted stats."""
        if self.is_profiling:
            self.profiler.disable()
            self.is_profiling = False

            # Get stats
            s = io.StringIO()
            ps = pstats.Stats(self.profiler, stream=s).sort_stats('cumulative')
            ps.print_stats()
            return s.getvalue()
        return "Profiler not running"

    @contextmanager
    def profile_context(self):
        """Context manager for profiling code blocks."""
        self.start_profiling()
        try:
            yield
        finally:
            yield self.stop_profiling()

def profile_function(func: Callable):
    """Decorator to profile a function."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        profiler = Profiler()
        profiler.start_profiling()

        try:
            result = func(*args, **kwargs)
            return result
        finally:
            stats = profiler.stop_profiling()
            print(f"Profile for {func.__name__}:")
            print(stats)
    return wrapper

def benchmark(func: Callable, iterations: int = 100):
    """Benchmark a function over multiple iterations."""
    times = []

    for _ in range(iterations):
        start_time = time.time()
        result = func()
        end_time = time.time()
        times.append(end_time - start_time)

    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)

    return {
        "function": func.__name__,
        "iterations": iterations,
        "avg_time": avg_time,
        "min_time": min_time,
        "max_time": max_time,
        "total_time": sum(times)
    }

class MemoryProfiler:
    """
    Memory usage profiler using tracemalloc.
    """

    def __init__(self):
        self.is_tracing = False

    def start_tracing(self):
        """Start memory tracing."""
        if not self.is_tracing:
            tracemalloc.start()
            self.is_tracing = True

    def stop_tracing(self) -> Dict[str, Any]:
        """Stop tracing and return memory stats."""
        if self.is_tracing:
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            self.is_tracing = False

            return {
                "current_memory_mb": current / 1024 / 1024,
                "peak_memory_mb": peak / 1024 / 1024,
                "current_memory_bytes": current,
                "peak_memory_bytes": peak
            }
        return {"message": "Memory tracing not active"}

    @contextmanager
    def trace_context(self):
        """Context manager for memory tracing."""
        self.start_tracing()
        try:
            yield
        finally:
            stats = self.stop_tracing()
            print(f"Memory usage: {stats}")

# Global profiler instances
profiler = Profiler()
memory_profiler = MemoryProfiler()

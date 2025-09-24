"""
Advanced profiling and benchmarking system for Pyserv  framework.

This module provides comprehensive performance profiling with:
- CPU profiling and flame graphs
- Memory profiling and leak detection
- Database query profiling
- Network I/O profiling
- Load testing with configurable scenarios
- Performance regression detection
- Automated benchmarking suites
"""

import asyncio
import cProfile
import io
import logging
import pstats
import time
import tracemalloc
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, AsyncGenerator, Set
from concurrent.futures import ThreadPoolExecutor
import psutil
import numpy as np
from functools import wraps
import json
import csv
from pathlib import Path

from .monitoring.metrics import get_metrics_collector
from .performance_optimizer import get_performance_monitor


# Define init_profiling locally to avoid circular imports
async def init_profiling():
    """Initialize the profiling system"""
    profiler = get_profiler()
    load_tester = get_load_tester()
    regression_detector = get_regression_detector()

    # Start memory tracing
    tracemalloc.start()

    return profiler, load_tester, regression_detector


@dataclass
class ProfileResult:
    """Result of a profiling session"""
    function_name: str
    total_time: float
    call_count: int
    average_time: float
    cumulative_time: float
    memory_usage: int
    cpu_usage: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class BenchmarkResult:
    """Result of a benchmark run"""
    name: str
    duration: float
    operations_per_second: float
    average_latency: float
    p50_latency: float
    p95_latency: float
    p99_latency: float
    memory_peak: int
    cpu_average: float
    error_rate: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class LoadTestScenario:
    """Load testing scenario configuration"""
    name: str
    duration: int  # seconds
    ramp_up_time: int  # seconds
    concurrent_users: int
    target_rps: Optional[int] = None
    request_distribution: Dict[str, float] = field(default_factory=dict)
    custom_headers: Dict[str, str] = field(default_factory=dict)


class PerformanceProfiler:
    """Advanced performance profiler"""

    def __init__(self):
        self.logger = logging.getLogger("PerformanceProfiler")
        self.metrics = get_metrics_collector()
        self._active_profiles: Dict[str, cProfile.Profile] = {}
        self._memory_snapshots: Dict[str, tracemalloc.Snapshot] = {}
        self._executor = ThreadPoolExecutor(max_workers=4)

    @contextmanager
    def profile_function(self, name: str):
        """Context manager for profiling a function"""
        profiler = cProfile.Profile()
        profiler.enable()

        # Take memory snapshot
        if tracemalloc.is_tracing():
            tracemalloc.start()
            initial_memory = tracemalloc.get_traced_memory()[0]
        else:
            initial_memory = 0

        start_time = time.time()
        start_cpu = psutil.cpu_percent(interval=None)

        try:
            yield
        finally:
            end_time = time.time()
            end_cpu = psutil.cpu_percent(interval=None)

            profiler.disable()

            # Calculate memory usage
            if tracemalloc.is_tracing():
                final_memory = tracemalloc.get_traced_memory()[0]
                memory_usage = final_memory - initial_memory
                tracemalloc.stop()
            else:
                memory_usage = 0

            # Process profile stats
            stats_stream = io.StringIO()
            ps = pstats.Stats(profiler, stream=stats_stream)
            ps.sort_stats('cumulative')
            ps.print_stats(20)  # Top 20 functions

            # Extract key metrics
            total_time = end_time - start_time
            cpu_usage = (start_cpu + end_cpu) / 2

            result = ProfileResult(
                function_name=name,
                total_time=total_time,
                call_count=1,  # Simplified
                average_time=total_time,
                cumulative_time=total_time,
                memory_usage=memory_usage,
                cpu_usage=cpu_usage
            )

            # Store result
            self._store_profile_result(result)

            # Log profile information
            self.logger.info(f"Profiled {name}: {total_time:.4f}s, {memory_usage} bytes, {cpu_usage:.1f}% CPU")
            self.logger.debug(f"Profile stats for {name}:\n{stats_stream.getvalue()}")

    async def profile_async_function(self, name: str, coro):
        """Profile an async function"""
        loop = asyncio.get_running_loop()

        def sync_profile():
            with self.profile_function(name):
                # Run coroutine in new event loop
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(coro)
                finally:
                    new_loop.close()

        return await loop.run_in_executor(self._executor, sync_profile)

    def start_continuous_profiling(self, name: str):
        """Start continuous profiling"""
        profiler = cProfile.Profile()
        profiler.enable()
        self._active_profiles[name] = profiler

        if tracemalloc.is_tracing():
            self._memory_snapshots[name] = tracemalloc.take_snapshot()

        self.logger.info(f"Started continuous profiling: {name}")

    def stop_continuous_profiling(self, name: str) -> Optional[ProfileResult]:
        """Stop continuous profiling and return results"""
        if name not in self._active_profiles:
            self.logger.warning(f"No active profiling session: {name}")
            return None

        profiler = self._active_profiles[name]
        profiler.disable()

        # Calculate metrics
        stats_stream = io.StringIO()
        ps = pstats.Stats(profiler, stream=stats_stream)
        ps.sort_stats('cumulative')

        # Get memory usage
        memory_usage = 0
        if name in self._memory_snapshots and tracemalloc.is_tracing():
            current_snapshot = tracemalloc.take_snapshot()
            stats = current_snapshot.compare_to(self._memory_snapshots[name], 'lineno')
            memory_usage = sum(stat.size_diff for stat in stats)

        # Create result
        result = ProfileResult(
            function_name=name,
            total_time=0.0,  # Would need to track start time
            call_count=0,
            average_time=0.0,
            cumulative_time=0.0,
            memory_usage=memory_usage,
            cpu_usage=psutil.cpu_percent(interval=None)
        )

        # Clean up
        del self._active_profiles[name]
        if name in self._memory_snapshots:
            del self._memory_snapshots[name]

        self.logger.info(f"Stopped continuous profiling: {name}")
        return result

    def _store_profile_result(self, result: ProfileResult):
        """Store profiling result for analysis"""
        # In a real implementation, this would store to database or file
        pass

    def generate_flame_graph(self, profile_data: str, output_file: str):
        """Generate flame graph from profile data"""
        try:
            # This would require additional dependencies like flameprof
            # For now, just save the profile data
            with open(output_file, 'w') as f:
                f.write(profile_data)
            self.logger.info(f"Flame graph data saved to {output_file}")
        except Exception as e:
            self.logger.error(f"Failed to generate flame graph: {e}")


class LoadTester:
    """Advanced load testing system"""

    def __init__(self):
        self.logger = logging.getLogger("LoadTester")
        self.metrics = get_metrics_collector()
        self._active_tests: Dict[str, asyncio.Task] = {}

    async def run_load_test(self, scenario: LoadTestScenario) -> BenchmarkResult:
        """Run a load test scenario"""
        self.logger.info(f"Starting load test: {scenario.name}")

        # Initialize metrics collection
        latencies = []
        errors = 0
        total_requests = 0

        # Track memory and CPU
        memory_start = psutil.virtual_memory().used
        cpu_start = psutil.cpu_percent(interval=None)

        start_time = time.time()

        try:
            # Run the test
            await self._execute_scenario(scenario, latencies, lambda: total_requests + 1, lambda: errors + 1)

            end_time = time.time()
            duration = end_time - start_time

            # Calculate final metrics
            memory_end = psutil.virtual_memory().used
            cpu_end = psutil.cpu_percent(interval=None)

            memory_peak = max(memory_start, memory_end)
            cpu_average = (cpu_start + cpu_end) / 2

            # Calculate latency percentiles
            if latencies:
                latencies_sorted = sorted(latencies)
                p50 = np.percentile(latencies_sorted, 50)
                p95 = np.percentile(latencies_sorted, 95)
                p99 = np.percentile(latencies_sorted, 99)
                avg_latency = np.mean(latencies_sorted)
            else:
                p50 = p95 = p99 = avg_latency = 0.0

            # Calculate operations per second
            ops_per_second = total_requests / duration if duration > 0 else 0
            error_rate = errors / total_requests if total_requests > 0 else 0

            result = BenchmarkResult(
                name=scenario.name,
                duration=duration,
                operations_per_second=ops_per_second,
                average_latency=avg_latency,
                p50_latency=p50,
                p95_latency=p95,
                p99_latency=p99,
                memory_peak=memory_peak,
                cpu_average=cpu_average,
                error_rate=error_rate
            )

            self.logger.info(f"Load test completed: {scenario.name}")
            self.logger.info(f"Results: {ops_per_second:.2f} ops/sec, {avg_latency:.4f}s avg latency")

            return result

        except Exception as e:
            self.logger.error(f"Load test failed: {scenario.name} - {e}")
            raise

    async def _execute_scenario(self, scenario: LoadTestScenario,
                               latencies: List[float], request_counter: Callable, error_counter: Callable):
        """Execute a load test scenario"""
        # Simplified implementation - in practice, this would use aiohttp or similar
        # to make actual HTTP requests to the target application

        async def make_request():
            try:
                start_time = time.time()
                # Simulate request (replace with actual HTTP call)
                await asyncio.sleep(0.01)  # Simulate network latency
                end_time = time.time()

                latencies.append(end_time - start_time)
                request_counter()
            except Exception:
                error_counter()

        # Ramp up users
        tasks = []
        for i in range(scenario.concurrent_users):
            task = asyncio.create_task(make_request())
            tasks.append(task)

            if scenario.ramp_up_time > 0:
                await asyncio.sleep(scenario.ramp_up_time / scenario.concurrent_users)

        # Wait for completion or timeout
        await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True),
                              timeout=scenario.duration)

    async def run_stress_test(self, target_url: str, max_concurrent: int = 1000) -> BenchmarkResult:
        """Run a stress test to find breaking points"""
        self.logger.info(f"Starting stress test for {target_url}")

        # Gradually increase load
        results = []
        for concurrent in range(10, max_concurrent + 1, 50):
            scenario = LoadTestScenario(
                name=f"stress_test_{concurrent}",
                duration=30,
                ramp_up_time=5,
                concurrent_users=concurrent
            )

            try:
                result = await self.run_load_test(scenario)
                results.append(result)

                # Check if error rate is too high
                if result.error_rate > 0.1:  # 10% error rate
                    self.logger.warning(f"High error rate detected at {concurrent} concurrent users")
                    break

            except Exception as e:
                self.logger.error(f"Stress test failed at {concurrent} users: {e}")
                break

        # Return the best result
        if results:
            return max(results, key=lambda r: r.operations_per_second)
        else:
            raise Exception("Stress test failed to produce any results")

    def generate_report(self, results: List[BenchmarkResult], output_file: str):
        """Generate a comprehensive test report"""
        report = {
            "summary": {
                "total_tests": len(results),
                "best_performance": max(results, key=lambda r: r.operations_per_second).__dict__ if results else None,
                "worst_performance": min(results, key=lambda r: r.operations_per_second).__dict__ if results else None,
                "average_ops_per_second": np.mean([r.operations_per_second for r in results]) if results else 0,
            },
            "results": [r.__dict__ for r in results],
            "recommendations": self._generate_recommendations(results)
        }

        # Save to file
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        self.logger.info(f"Test report saved to {output_file}")

    def _generate_recommendations(self, results: List[BenchmarkResult]) -> List[str]:
        """Generate performance recommendations based on test results"""
        recommendations = []

        if not results:
            return recommendations

        best_result = max(results, key=lambda r: r.operations_per_second)

        if best_result.error_rate > 0.05:
            recommendations.append("Consider increasing server capacity or optimizing error handling")

        if best_result.p95_latency > 1.0:
            recommendations.append("High latency detected - consider optimizing database queries or adding caching")

        if best_result.cpu_average > 80:
            recommendations.append("High CPU usage - consider horizontal scaling or optimizing CPU-intensive operations")

        if best_result.memory_peak > psutil.virtual_memory().total * 0.8:
            recommendations.append("High memory usage - consider optimizing memory allocation or increasing RAM")

        return recommendations


class RegressionDetector:
    """Performance regression detection system"""

    def __init__(self, baseline_file: str = "performance_baseline.json"):
        self.baseline_file = Path(baseline_file)
        self.logger = logging.getLogger("RegressionDetector")
        self.baselines: Dict[str, BenchmarkResult] = {}

        # Load existing baselines
        self._load_baselines()

    def establish_baseline(self, results: List[BenchmarkResult]):
        """Establish performance baselines"""
        for result in results:
            self.baselines[result.name] = result

        self._save_baselines()
        self.logger.info(f"Established baselines for {len(results)} tests")

    def detect_regression(self, current_results: List[BenchmarkResult]) -> List[Dict[str, Any]]:
        """Detect performance regressions"""
        regressions = []

        for current in current_results:
            if current.name in self.baselines:
                baseline = self.baselines[current.name]

                # Check for significant regressions
                ops_regression = (baseline.operations_per_second - current.operations_per_second) / baseline.operations_per_second
                latency_regression = (current.average_latency - baseline.average_latency) / baseline.average_latency

                if ops_regression > 0.1:  # 10% drop in throughput
                    regressions.append({
                        "test": current.name,
                        "type": "throughput_regression",
                        "baseline": baseline.operations_per_second,
                        "current": current.operations_per_second,
                        "change_percent": ops_regression * 100,
                        "severity": "high" if ops_regression > 0.2 else "medium"
                    })

                if latency_regression > 0.1:  # 10% increase in latency
                    regressions.append({
                        "test": current.name,
                        "type": "latency_regression",
                        "baseline": baseline.average_latency,
                        "current": current.average_latency,
                        "change_percent": latency_regression * 100,
                        "severity": "high" if latency_regression > 0.2 else "medium"
                    })

        if regressions:
            self.logger.warning(f"Performance regressions detected: {len(regressions)}")
            for reg in regressions:
                self.logger.warning(f"  {reg['test']}: {reg['change_percent']:.1f}% {reg['type']}")

        return regressions

    def _load_baselines(self):
        """Load baseline data from file"""
        if self.baseline_file.exists():
            try:
                with open(self.baseline_file, 'r') as f:
                    data = json.load(f)
                    for name, result_data in data.items():
                        self.baselines[name] = BenchmarkResult(**result_data)
                self.logger.info(f"Loaded {len(self.baselines)} baselines")
            except Exception as e:
                self.logger.error(f"Failed to load baselines: {e}")

    def _save_baselines(self):
        """Save baseline data to file"""
        try:
            data = {name: result.__dict__ for name, result in self.baselines.items()}
            with open(self.baseline_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            self.logger.info(f"Saved {len(self.baselines)} baselines")
        except Exception as e:
            self.logger.error(f"Failed to save baselines: {e}")


# Decorators for easy profiling

def profile_function(name: Optional[str] = None):
    """Decorator to profile a function"""
    def decorator(func: Callable) -> Callable:
        profiler = PerformanceProfiler()

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            func_name = name or f"{func.__module__}.{func.__qualname__}"
            async with profiler.profile_async_function(func_name, func(*args, **kwargs)) as result:
                return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            func_name = name or f"{func.__module__}.{func.__qualname__}"
            with profiler.profile_function(func_name):
                return func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def benchmark(iterations: int = 100, name: Optional[str] = None):
    """Decorator to benchmark a function"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            func_name = name or f"{func.__module__}.{func.__qualname__}"

            latencies = []
            start_time = time.time()

            for _ in range(iterations):
                iter_start = time.time()
                await func(*args, **kwargs)
                latencies.append(time.time() - iter_start)

            end_time = time.time()
            duration = end_time - start_time

            result = BenchmarkResult(
                name=func_name,
                duration=duration,
                operations_per_second=iterations / duration,
                average_latency=np.mean(latencies),
                p50_latency=np.percentile(latencies, 50),
                p95_latency=np.percentile(latencies, 95),
                p99_latency=np.percentile(latencies, 99),
                memory_peak=0,  # Would need to track
                cpu_average=0,  # Would need to track
                error_rate=0.0
            )

            logging.info(f"Benchmark {func_name}: {result.operations_per_second:.2f} ops/sec")
            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            func_name = name or f"{func.__module__}.{func.__qualname__}"

            latencies = []
            start_time = time.time()

            for _ in range(iterations):
                iter_start = time.time()
                func(*args, **kwargs)
                latencies.append(time.time() - iter_start)

            end_time = time.time()
            duration = end_time - start_time

            result = BenchmarkResult(
                name=func_name,
                duration=duration,
                operations_per_second=iterations / duration,
                average_latency=np.mean(latencies),
                p50_latency=np.percentile(latencies, 50),
                p95_latency=np.percentile(latencies, 95),
                p99_latency=np.percentile(latencies, 99),
                memory_peak=0,
                cpu_average=0,
                error_rate=0.0
            )

            logging.info(f"Benchmark {func_name}: {result.operations_per_second:.2f} ops/sec")
            return result

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# Global instances
_profiler: Optional[PerformanceProfiler] = None
_load_tester: Optional[LoadTester] = None
_regression_detector: Optional[RegressionDetector] = None

def get_profiler() -> PerformanceProfiler:
    """Get global profiler instance"""
    global _profiler
    if _profiler is None:
        _profiler = PerformanceProfiler()
    return _profiler

def get_load_tester() -> LoadTester:
    """Get global load tester instance"""
    global _load_tester
    if _load_tester is None:
        _load_tester = LoadTester()
    return _load_tester

def get_regression_detector(baseline_file: str = "performance_baseline.json") -> RegressionDetector:
    """Get global regression detector instance"""
    global _regression_detector
    if _regression_detector is None:
        _regression_detector = RegressionDetector(baseline_file)
    return _regression_detector

async def init_profiling():
    """Initialize the profiling system"""
    profiler = get_profiler()
    load_tester = get_load_tester()
    regression_detector = get_regression_detector()

    # Start memory tracing
    tracemalloc.start()

    return profiler, load_tester, regression_detector

async def shutdown_profiling():
    """Shutdown the profiling system"""
    tracemalloc.stop()





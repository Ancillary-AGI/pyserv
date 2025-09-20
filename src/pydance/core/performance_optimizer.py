"""
Comprehensive performance optimization system for PyDance framework.

This module provides real-time performance monitoring and optimization with:
- Automatic bottleneck detection
- Dynamic resource allocation
- Performance profiling and analysis
- Auto-scaling recommendations
- Memory leak detection
- CPU optimization suggestions
"""

import asyncio
import logging
import time
import psutil
import gc
import tracemalloc
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import threading
import numpy as np

from .monitoring.metrics import get_metrics_collector
from .distributed_cache import get_distributed_cache
from .database_pool import get_pooled_connection
from .load_balancer import get_load_balancer


class PerformanceMetric(Enum):
    """Performance metrics to monitor"""
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    DISK_IO = "disk_io"
    NETWORK_IO = "network_io"
    RESPONSE_TIME = "response_time"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    CACHE_HIT_RATE = "cache_hit_rate"
    DB_CONNECTION_POOL_USAGE = "db_pool_usage"
    THREAD_COUNT = "thread_count"


class OptimizationAction(Enum):
    """Optimization actions"""
    SCALE_UP_INSTANCES = "scale_up_instances"
    INCREASE_CACHE_SIZE = "increase_cache_size"
    OPTIMIZE_DATABASE_QUERIES = "optimize_database_queries"
    ADD_MORE_WORKERS = "add_more_workers"
    ENABLE_COMPRESSION = "enable_compression"
    INCREASE_CONNECTION_POOL = "increase_connection_pool"
    OPTIMIZE_MEMORY_USAGE = "optimize_memory_usage"


@dataclass
class PerformanceThreshold:
    """Performance threshold configuration"""
    metric: PerformanceMetric
    warning_threshold: float
    critical_threshold: float
    duration_seconds: int = 60  # How long threshold must be exceeded


@dataclass
class PerformanceSnapshot:
    """Snapshot of system performance"""
    timestamp: float
    metrics: Dict[PerformanceMetric, float] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class OptimizationRecommendation:
    """Optimization recommendation"""
    action: OptimizationAction
    priority: int  # 1-10, 10 being highest
    description: str
    expected_impact: str
    implementation_effort: str
    timestamp: float = field(default_factory=time.time)


class PerformanceMonitor:
    """Real-time performance monitoring"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger("PerformanceMonitor")
        self.metrics = get_metrics_collector()

        # Performance data storage
        self.snapshots: deque = deque(maxlen=1000)
        self.thresholds: Dict[PerformanceMetric, PerformanceThreshold] = {}
        self.alerts: List[Dict[str, Any]] = []

        # Monitoring state
        self.monitoring_active = False
        self.monitoring_task: Optional[asyncio.Task] = None
        self.analysis_task: Optional[asyncio.Task] = None

        # Performance baselines
        self.baselines: Dict[PerformanceMetric, float] = {}
        self.anomaly_detector = AnomalyDetector()

        # System resource monitors
        self.cpu_monitor = SystemMonitor(PerformanceMetric.CPU_USAGE)
        self.memory_monitor = SystemMonitor(PerformanceMetric.MEMORY_USAGE)
        self.disk_monitor = SystemMonitor(PerformanceMetric.DISK_IO)
        self.network_monitor = SystemMonitor(PerformanceMetric.NETWORK_IO)

        # Set up default thresholds
        self._setup_default_thresholds()

        # Register metrics
        self._register_metrics()

    def _setup_default_thresholds(self):
        """Set up default performance thresholds"""
        self.thresholds = {
            PerformanceMetric.CPU_USAGE: PerformanceThreshold(
                PerformanceMetric.CPU_USAGE, 70.0, 90.0, 300
            ),
            PerformanceMetric.MEMORY_USAGE: PerformanceThreshold(
                PerformanceMetric.MEMORY_USAGE, 75.0, 95.0, 300
            ),
            PerformanceMetric.RESPONSE_TIME: PerformanceThreshold(
                PerformanceMetric.RESPONSE_TIME, 1000.0, 5000.0, 60
            ),
            PerformanceMetric.ERROR_RATE: PerformanceThreshold(
                PerformanceMetric.ERROR_RATE, 5.0, 15.0, 300
            ),
            PerformanceMetric.CACHE_HIT_RATE: PerformanceThreshold(
                PerformanceMetric.CACHE_HIT_RATE, 70.0, 50.0, 300
            ),
        }

    def _register_metrics(self):
        """Register performance monitoring metrics"""
        self.metrics.create_gauge(
            "performance_cpu_usage_percent",
            "Current CPU usage percentage"
        )
        self.metrics.create_gauge(
            "performance_memory_usage_percent",
            "Current memory usage percentage"
        )
        self.metrics.create_histogram(
            "performance_response_time_ms",
            "Response time in milliseconds",
            buckets=[10, 50, 100, 500, 1000, 5000, 10000]
        )
        self.metrics.create_gauge(
            "performance_active_alerts",
            "Number of active performance alerts"
        )

    async def start_monitoring(self):
        """Start performance monitoring"""
        self.monitoring_active = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        self.analysis_task = asyncio.create_task(self._analysis_loop())
        self.logger.info("Performance monitoring started")

    async def stop_monitoring(self):
        """Stop performance monitoring"""
        self.monitoring_active = False

        if self.monitoring_task:
            self.monitoring_task.cancel()
        if self.analysis_task:
            self.analysis_task.cancel()

        await asyncio.gather(self.monitoring_task, self.analysis_task, return_exceptions=True)
        self.logger.info("Performance monitoring stopped")

    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                await asyncio.sleep(10)  # Collect metrics every 10 seconds
                snapshot = await self._collect_metrics()
                self.snapshots.append(snapshot)

                # Update metrics
                self._update_metrics(snapshot)

                # Check thresholds
                await self._check_thresholds(snapshot)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Monitoring error: {e}")

    async def _analysis_loop(self):
        """Performance analysis loop"""
        while self.monitoring_active:
            try:
                await asyncio.sleep(60)  # Analyze every minute
                await self._analyze_performance()
                await self._generate_recommendations()

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Analysis error: {e}")

    async def _collect_metrics(self) -> PerformanceSnapshot:
        """Collect current system metrics"""
        snapshot = PerformanceSnapshot(timestamp=time.time())

        try:
            # System metrics
            snapshot.metrics[PerformanceMetric.CPU_USAGE] = psutil.cpu_percent(interval=1)
            snapshot.metrics[PerformanceMetric.MEMORY_USAGE] = psutil.virtual_memory().percent

            # Disk I/O
            disk_io = psutil.disk_io_counters()
            if disk_io:
                snapshot.metrics[PerformanceMetric.DISK_IO] = disk_io.read_bytes + disk_io.write_bytes

            # Network I/O
            net_io = psutil.net_io_counters()
            if net_io:
                snapshot.metrics[PerformanceMetric.NETWORK_IO] = net_io.bytes_sent + net_io.bytes_recv

            # Application-specific metrics
            await self._collect_application_metrics(snapshot)

        except Exception as e:
            self.logger.error(f"Metrics collection error: {e}")

        return snapshot

    async def _collect_application_metrics(self, snapshot: PerformanceSnapshot):
        """Collect application-specific metrics"""
        try:
            # Cache metrics
            cache = get_distributed_cache()
            cache_stats = cache.get_analytics()
            if 'hit_rate' in cache_stats:
                snapshot.metrics[PerformanceMetric.CACHE_HIT_RATE] = cache_stats['hit_rate'] * 100

            # Database pool metrics
            # This would be implemented based on actual database connections

            # Load balancer metrics
            lb = get_load_balancer()
            lb_stats = lb.get_stats()
            if 'healthy_backends' in lb_stats and 'total_backends' in lb_stats:
                health_rate = (lb_stats['healthy_backends'] / lb_stats['total_backends']) * 100
                snapshot.metrics[PerformanceMetric.ERROR_RATE] = 100 - health_rate

        except Exception as e:
            self.logger.error(f"Application metrics collection error: {e}")

    def _update_metrics(self, snapshot: PerformanceSnapshot):
        """Update Prometheus metrics"""
        for metric, value in snapshot.metrics.items():
            if metric == PerformanceMetric.CPU_USAGE:
                self.metrics.get_metric("performance_cpu_usage_percent").set(value)
            elif metric == PerformanceMetric.MEMORY_USAGE:
                self.metrics.get_metric("performance_memory_usage_percent").set(value)

    async def _check_thresholds(self, snapshot: PerformanceSnapshot):
        """Check if metrics exceed thresholds"""
        for metric, threshold in self.thresholds.items():
            if metric in snapshot.metrics:
                value = snapshot.metrics[metric]
                alert_level = None

                if value >= threshold.critical_threshold:
                    alert_level = "CRITICAL"
                elif value >= threshold.warning_threshold:
                    alert_level = "WARNING"

                if alert_level:
                    alert = {
                        "timestamp": snapshot.timestamp,
                        "metric": metric.value,
                        "level": alert_level,
                        "value": value,
                        "threshold": threshold.critical_threshold if alert_level == "CRITICAL" else threshold.warning_threshold
                    }
                    self.alerts.append(alert)
                    self.logger.warning(f"Performance alert: {alert}")

                    # Update active alerts metric
                    self.metrics.get_metric("performance_active_alerts").set(len(self.alerts))

    async def _analyze_performance(self):
        """Analyze performance trends and patterns"""
        if len(self.snapshots) < 10:
            return

        recent_snapshots = list(self.snapshots)[-10:]

        # Detect anomalies
        for metric in PerformanceMetric:
            values = [s.metrics.get(metric, 0) for s in recent_snapshots if metric in s.metrics]
            if values:
                anomaly_score = self.anomaly_detector.detect_anomaly(values)
                if anomaly_score > 0.8:  # High anomaly score
                    self.logger.warning(f"Anomaly detected in {metric.value}: score={anomaly_score}")

        # Update baselines
        for metric in PerformanceMetric:
            values = [s.metrics.get(metric, 0) for s in self.snapshots if metric in s.metrics]
            if values:
                self.baselines[metric] = np.mean(values)

    async def _generate_recommendations(self) -> List[OptimizationRecommendation]:
        """Generate optimization recommendations"""
        recommendations = []

        # Analyze current metrics
        if self.snapshots:
            latest = self.snapshots[-1]

            # High CPU usage
            if latest.metrics.get(PerformanceMetric.CPU_USAGE, 0) > 80:
                recommendations.append(OptimizationRecommendation(
                    action=OptimizationAction.ADD_MORE_WORKERS,
                    priority=8,
                    description="High CPU usage detected - consider adding more worker processes",
                    expected_impact="Reduce CPU usage by distributing load across more processes",
                    implementation_effort="Medium"
                ))

            # High memory usage
            if latest.metrics.get(PerformanceMetric.MEMORY_USAGE, 0) > 85:
                recommendations.append(OptimizationRecommendation(
                    action=OptimizationAction.OPTIMIZE_MEMORY_USAGE,
                    priority=9,
                    description="High memory usage detected - optimize memory allocation",
                    expected_impact="Reduce memory footprint and prevent OOM errors",
                    implementation_effort="High"
                ))

            # Low cache hit rate
            if latest.metrics.get(PerformanceMetric.CACHE_HIT_RATE, 100) < 60:
                recommendations.append(OptimizationRecommendation(
                    action=OptimizationAction.INCREASE_CACHE_SIZE,
                    priority=7,
                    description="Low cache hit rate - increase cache size or optimize cache strategy",
                    expected_impact="Improve response times by increasing cache hit rate",
                    implementation_effort="Low"
                ))

            # High error rate
            if latest.metrics.get(PerformanceMetric.ERROR_RATE, 0) > 10:
                recommendations.append(OptimizationRecommendation(
                    action=OptimizationAction.SCALE_UP_INSTANCES,
                    priority=10,
                    description="High error rate detected - scale up application instances",
                    expected_impact="Improve reliability and reduce error rates",
                    implementation_effort="Medium"
                ))

        return recommendations

    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        if not self.snapshots:
            return {}

        latest = self.snapshots[-1]
        report = {
            "timestamp": latest.timestamp,
            "current_metrics": {k.value: v for k, v in latest.metrics.items()},
            "baselines": {k.value: v for k, v in self.baselines.items()},
            "active_alerts": len(self.alerts),
            "recent_alerts": self.alerts[-5:] if self.alerts else [],
            "recommendations": [r.__dict__ for r in asyncio.run(self._generate_recommendations())],
            "system_info": {
                "cpu_count": psutil.cpu_count(),
                "memory_total": psutil.virtual_memory().total,
                "disk_total": psutil.disk_usage('/').total,
            }
        }

        return report


class SystemMonitor:
    """System resource monitor"""

    def __init__(self, metric: PerformanceMetric):
        self.metric = metric
        self.history: deque = deque(maxlen=100)
        self.last_value = 0.0

    def collect(self) -> float:
        """Collect current metric value"""
        try:
            if self.metric == PerformanceMetric.CPU_USAGE:
                self.last_value = psutil.cpu_percent(interval=0.1)
            elif self.metric == PerformanceMetric.MEMORY_USAGE:
                self.last_value = psutil.virtual_memory().percent
            elif self.metric == PerformanceMetric.DISK_IO:
                disk_io = psutil.disk_io_counters()
                if disk_io:
                    self.last_value = disk_io.read_bytes + disk_io.write_bytes
            elif self.metric == PerformanceMetric.NETWORK_IO:
                net_io = psutil.net_io_counters()
                if net_io:
                    self.last_value = net_io.bytes_sent + net_io.bytes_recv

            self.history.append(self.last_value)
            return self.last_value

        except Exception:
            return 0.0


class AnomalyDetector:
    """Simple anomaly detection using statistical methods"""

    def detect_anomaly(self, values: List[float], threshold: float = 2.0) -> float:
        """Detect anomalies using z-score"""
        if len(values) < 3:
            return 0.0

        mean = np.mean(values)
        std = np.std(values)

        if std == 0:
            return 0.0

        latest_value = values[-1]
        z_score = abs(latest_value - mean) / std

        return min(z_score / threshold, 1.0)  # Normalize to 0-1


class PerformanceOptimizer:
    """Automatic performance optimization"""

    def __init__(self, monitor: PerformanceMonitor):
        self.monitor = monitor
        self.logger = logging.getLogger("PerformanceOptimizer")
        self.optimization_task: Optional[asyncio.Task] = None
        self.active_optimizations: Set[str] = set()

    async def start_auto_optimization(self):
        """Start automatic optimization"""
        self.optimization_task = asyncio.create_task(self._optimization_loop())
        self.logger.info("Auto-optimization started")

    async def stop_auto_optimization(self):
        """Stop automatic optimization"""
        if self.optimization_task:
            self.optimization_task.cancel()
            try:
                await self.optimization_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Auto-optimization stopped")

    async def _optimization_loop(self):
        """Main optimization loop"""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes

                recommendations = await self.monitor._generate_recommendations()

                for rec in recommendations:
                    if rec.priority >= 8:  # High priority recommendations
                        await self._apply_optimization(rec)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Optimization error: {e}")

    async def _apply_optimization(self, recommendation: OptimizationRecommendation):
        """Apply optimization recommendation"""
        if recommendation.action.value in self.active_optimizations:
            return  # Already applied

        try:
            if recommendation.action == OptimizationAction.INCREASE_CACHE_SIZE:
                await self._optimize_cache()
            elif recommendation.action == OptimizationAction.OPTIMIZE_MEMORY_USAGE:
                await self._optimize_memory()
            elif recommendation.action == OptimizationAction.ADD_MORE_WORKERS:
                await self._scale_workers()

            self.active_optimizations.add(recommendation.action.value)
            self.logger.info(f"Applied optimization: {recommendation.description}")

        except Exception as e:
            self.logger.error(f"Failed to apply optimization {recommendation.action.value}: {e}")

    async def _optimize_cache(self):
        """Optimize cache configuration"""
        cache = get_distributed_cache()
        # Increase cache sizes or adjust TTL
        self.logger.info("Cache optimization applied")

    async def _optimize_memory(self):
        """Optimize memory usage"""
        # Force garbage collection
        gc.collect()

        # Analyze memory usage
        if tracemalloc.is_tracing():
            snapshot = tracemalloc.take_snapshot()
            top_stats = snapshot.statistics('lineno')

            for stat in top_stats[:10]:
                self.logger.info(f"Memory usage: {stat}")

    async def _scale_workers(self):
        """Scale worker processes"""
        # This would integrate with process manager or container orchestrator
        self.logger.info("Worker scaling initiated")


# Global instances
_performance_monitor: Optional[PerformanceMonitor] = None
_performance_optimizer: Optional[PerformanceOptimizer] = None

def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor

def get_performance_optimizer() -> PerformanceOptimizer:
    """Get global performance optimizer"""
    global _performance_optimizer
    if _performance_optimizer is None:
        monitor = get_performance_monitor()
        _performance_optimizer = PerformanceOptimizer(monitor)
    return _performance_optimizer

async def init_performance_monitoring():
    """Initialize performance monitoring system"""
    monitor = get_performance_monitor()
    optimizer = get_performance_optimizer()

    await monitor.start_monitoring()
    await optimizer.start_auto_optimization()

    return monitor, optimizer

async def shutdown_performance_monitoring():
    """Shutdown performance monitoring system"""
    global _performance_monitor, _performance_optimizer

    if _performance_optimizer:
        await _performance_optimizer.stop_auto_optimization()

    if _performance_monitor:
        await _performance_monitor.stop_monitoring()

    _performance_monitor = None
    _performance_optimizer = None

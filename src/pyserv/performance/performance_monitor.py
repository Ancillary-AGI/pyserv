"""
Performance monitoring system for PyServ applications.
Tracks response times, throughput, error rates, and resource usage.
"""

import asyncio
import psutil
import logging
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict

@dataclass
class PerformanceMetrics:
    """Performance metrics data structure."""
    timestamp: datetime
    response_time: float
    throughput: float
    error_rate: float
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_io: Dict[str, float]
    active_connections: int
    cache_hit_rate: float
    database_connections: int

class PerformanceMonitor:
    """
    Comprehensive performance monitoring system.
    """

    def __init__(self):
        self.metrics: List[PerformanceMetrics] = []
        self.is_monitoring = False
        self.logger = logging.getLogger("performance_monitor")
        self._lock = asyncio.Lock()

    async def start_monitoring(self, interval: float = 1.0):
        """Start performance monitoring."""
        if self.is_monitoring:
            self.logger.warning("Performance monitoring is already running")
            return

        self.is_monitoring = True
        self.logger.info("Starting performance monitoring")

        # Start monitoring task
        asyncio.create_task(self._monitor_loop(interval))

    async def stop_monitoring(self):
        """Stop performance monitoring."""
        self.is_monitoring = False
        self.logger.info("Stopped performance monitoring")

    async def _monitor_loop(self, interval: float):
        """Main monitoring loop."""
        while self.is_monitoring:
            try:
                metrics = await self._collect_metrics()
                async with self._lock:
                    self.metrics.append(metrics)

                    # Keep only last 10000 metrics
                    if len(self.metrics) > 10000:
                        self.metrics = self.metrics[-10000:]

                await asyncio.sleep(interval)

            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(interval)

    async def _collect_metrics(self) -> PerformanceMetrics:
        """Collect current performance metrics."""
        try:
            # System metrics
            cpu_usage = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            disk = psutil.disk_usage('/')
            disk_usage = disk.percent

            # Network I/O
            network_io = {"bytes_sent": 0, "bytes_recv": 0}
            try:
                network = psutil.net_io_counters()
                if network:
                    network_io = {
                        "bytes_sent": network.bytes_sent,
                        "bytes_recv": network.bytes_recv
                    }
            except:
                pass

            # Active connections (simplified)
            active_connections = len(psutil.pids())

            # Calculate throughput and error rate from recent metrics
            throughput = 0.0
            error_rate = 0.0
            cache_hit_rate = 0.0
            database_connections = 0

            if len(self.metrics) > 0:
                recent_metrics = self.metrics[-10:]  # Last 10 metrics
                throughput = len(recent_metrics) / max(1, (datetime.now() - recent_metrics[0].timestamp).total_seconds())
                error_rate = sum(1 for m in recent_metrics if m.error_rate > 0.1) / len(recent_metrics)
                cache_hit_rate = sum(m.cache_hit_rate for m in recent_metrics) / len(recent_metrics)

            return PerformanceMetrics(
                timestamp=datetime.now(),
                response_time=0.1,  # Would be calculated from actual requests
                throughput=throughput,
                error_rate=error_rate,
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                disk_usage=disk_usage,
                network_io=network_io,
                active_connections=active_connections,
                cache_hit_rate=cache_hit_rate,
                database_connections=database_connections
            )

        except Exception as e:
            self.logger.error(f"Error collecting metrics: {e}")
            return PerformanceMetrics(
                timestamp=datetime.now(),
                response_time=0,
                throughput=0,
                error_rate=0,
                cpu_usage=0,
                memory_usage=0,
                disk_usage=0,
                network_io={},
                active_connections=0,
                cache_hit_rate=0,
                database_connections=0
            )

    def get_current_metrics(self) -> Optional[PerformanceMetrics]:
        """Get the most recent metrics."""
        if not self.metrics:
            return None
        return self.metrics[-1]

    def get_metrics_summary(self, last_minutes: int = 60) -> Dict[str, Any]:
        """Get metrics summary for the specified time period."""
        if not self.metrics:
            return {"message": "No metrics available"}

        cutoff_time = datetime.now() - timedelta(minutes=last_minutes)
        recent_metrics = [m for m in self.metrics if m.timestamp > cutoff_time]

        if not recent_metrics:
            return {"message": "No recent metrics available"}

        # Calculate averages
        avg_response_time = sum(m.response_time for m in recent_metrics) / len(recent_metrics)
        avg_throughput = sum(m.throughput for m in recent_metrics) / len(recent_metrics)
        avg_error_rate = sum(m.error_rate for m in recent_metrics) / len(recent_metrics)
        avg_cpu_usage = sum(m.cpu_usage for m in recent_metrics) / len(recent_metrics)
        avg_memory_usage = sum(m.memory_usage for m in recent_metrics) / len(recent_metrics)
        avg_cache_hit_rate = sum(m.cache_hit_rate for m in recent_metrics) / len(recent_metrics)

        # Get peak values
        peak_cpu = max(m.cpu_usage for m in recent_metrics)
        peak_memory = max(m.memory_usage for m in recent_metrics)
        peak_throughput = max(m.throughput for m in recent_metrics)

        return {
            "time_period_minutes": last_minutes,
            "total_samples": len(recent_metrics),
            "averages": {
                "response_time": avg_response_time,
                "throughput": avg_throughput,
                "error_rate": avg_error_rate,
                "cpu_usage": avg_cpu_usage,
                "memory_usage": avg_memory_usage,
                "cache_hit_rate": avg_cache_hit_rate
            },
            "peaks": {
                "cpu_usage": peak_cpu,
                "memory_usage": peak_memory,
                "throughput": peak_throughput
            },
            "current": {
                "response_time": recent_metrics[-1].response_time,
                "throughput": recent_metrics[-1].throughput,
                "error_rate": recent_metrics[-1].error_rate,
                "cpu_usage": recent_metrics[-1].cpu_usage,
                "memory_usage": recent_metrics[-1].memory_usage,
                "cache_hit_rate": recent_metrics[-1].cache_hit_rate
            },
            "timestamp": datetime.now().isoformat()
        }

    def get_performance_alerts(self) -> List[Dict[str, Any]]:
        """Get performance alerts based on current metrics."""
        alerts = []

        if not self.metrics:
            return alerts

        current = self.metrics[-1]

        # CPU usage alert
        if current.cpu_usage > 90:
            alerts.append({
                "type": "high_cpu_usage",
                "severity": "critical",
                "message": f"CPU usage is {current.cpu_usage:.1f}%",
                "value": current.cpu_usage,
                "threshold": 90
            })
        elif current.cpu_usage > 70:
            alerts.append({
                "type": "high_cpu_usage",
                "severity": "warning",
                "message": f"CPU usage is {current.cpu_usage:.1f}%",
                "value": current.cpu_usage,
                "threshold": 70
            })

        # Memory usage alert
        if current.memory_usage > 90:
            alerts.append({
                "type": "high_memory_usage",
                "severity": "critical",
                "message": f"Memory usage is {current.memory_usage:.1f}%",
                "value": current.memory_usage,
                "threshold": 90
            })
        elif current.memory_usage > 80:
            alerts.append({
                "type": "high_memory_usage",
                "severity": "warning",
                "message": f"Memory usage is {current.memory_usage:.1f}%",
                "value": current.memory_usage,
                "threshold": 80
            })

        # Error rate alert
        if current.error_rate > 0.1:
            alerts.append({
                "type": "high_error_rate",
                "severity": "critical",
                "message": f"Error rate is {current.error_rate:.2f}",
                "value": current.error_rate,
                "threshold": 0.1
            })
        elif current.error_rate > 0.05:
            alerts.append({
                "type": "high_error_rate",
                "severity": "warning",
                "message": f"Error rate is {current.error_rate:.2f}",
                "value": current.error_rate,
                "threshold": 0.05
            })

        # Response time alert
        if current.response_time > 5.0:
            alerts.append({
                "type": "high_response_time",
                "severity": "critical",
                "message": f"Response time is {current.response_time:.2f}s",
                "value": current.response_time,
                "threshold": 5.0
            })
        elif current.response_time > 2.0:
            alerts.append({
                "type": "high_response_time",
                "severity": "warning",
                "message": f"Response time is {current.response_time:.2f}s",
                "value": current.response_time,
                "threshold": 2.0
            })

        return alerts

    def export_metrics(self, format: str = "json") -> str:
        """Export metrics in specified format."""
        if format.lower() == "json":
            return json.dumps([{
                "timestamp": m.timestamp.isoformat(),
                "response_time": m.response_time,
                "throughput": m.throughput,
                "error_rate": m.error_rate,
                "cpu_usage": m.cpu_usage,
                "memory_usage": m.memory_usage,
                "cache_hit_rate": m.cache_hit_rate
            } for m in self.metrics], indent=2)
        else:
            raise ValueError(f"Unsupported format: {format}")

# Global performance monitor
performance_monitor = PerformanceMonitor()

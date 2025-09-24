"""
Auto-recovery system for self-healing applications.
Monitors system health and automatically recovers from failures.
"""

import asyncio
import psutil
import logging
import signal
import os
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

class RecoveryStrategy(Enum):
    RESTART_SERVICE = "restart_service"
    CLEAR_CACHE = "clear_cache"
    RESET_CONNECTIONS = "reset_connections"
    SCALE_RESOURCES = "scale_resources"
    FAILOVER = "failover"

class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"

@dataclass
class HealthCheck:
    name: str
    check_function: Callable
    interval: float = 30.0  # seconds
    timeout: float = 10.0
    critical: bool = False
    recovery_strategy: Optional[RecoveryStrategy] = None

@dataclass
class SystemMetrics:
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_io: Dict[str, float]
    active_connections: int
    error_rate: float
    response_time: float
    timestamp: datetime

class AutoRecoveryManager:
    """
    Auto-recovery system for self-healing applications.
    """

    def __init__(self):
        self.health_checks: Dict[str, HealthCheck] = {}
        self.recovery_strategies: Dict[RecoveryStrategy, Callable] = {}
        self.system_metrics: List[SystemMetrics] = []
        self.is_running = False
        self.logger = logging.getLogger("auto_recovery")
        self._register_default_strategies()

    def _register_default_strategies(self):
        """Register default recovery strategies."""
        self.recovery_strategies[RecoveryStrategy.CLEAR_CACHE] = self._clear_cache
        self.recovery_strategies[RecoveryStrategy.RESET_CONNECTIONS] = self._reset_connections
        self.recovery_strategies[RecoveryStrategy.RESTART_SERVICE] = self._restart_service

    def add_health_check(self, check: HealthCheck):
        """Add a health check."""
        self.health_checks[check.name] = check
        self.logger.info(f"Added health check: {check.name}")

    def remove_health_check(self, name: str):
        """Remove a health check."""
        if name in self.health_checks:
            del self.health_checks[name]
            self.logger.info(f"Removed health check: {name}")

    async def start_monitoring(self):
        """Start the auto-recovery monitoring system."""
        if self.is_running:
            self.logger.warning("Auto-recovery monitoring is already running")
            return

        self.is_running = True
        self.logger.info("Starting auto-recovery monitoring")

        # Start health check tasks
        for check in self.health_checks.values():
            asyncio.create_task(self._run_health_check(check))

        # Start metrics collection
        asyncio.create_task(self._collect_metrics())

        # Start recovery evaluation
        asyncio.create_task(self._evaluate_and_recover())

    async def stop_monitoring(self):
        """Stop the auto-recovery monitoring system."""
        self.is_running = False
        self.logger.info("Stopped auto-recovery monitoring")

    async def _run_health_check(self, check: HealthCheck):
        """Run a single health check periodically."""
        while self.is_running:
            try:
                start_time = datetime.now()
                result = await asyncio.wait_for(check.check_function(), timeout=check.timeout)
                execution_time = (datetime.now() - start_time).total_seconds()

                if result is True:
                    self.logger.debug(f"Health check {check.name} passed in {execution_time:.2f}s")
                else:
                    self.logger.warning(f"Health check {check.name} failed: {result}")
                    await self._handle_health_check_failure(check, result)

            except asyncio.TimeoutError:
                self.logger.error(f"Health check {check.name} timed out after {check.timeout}s")
                await self._handle_health_check_failure(check, "timeout")
            except Exception as e:
                self.logger.error(f"Health check {check.name} raised exception: {e}")
                await self._handle_health_check_failure(check, str(e))

            await asyncio.sleep(check.interval)

    async def _handle_health_check_failure(self, check: HealthCheck, failure_reason: Any):
        """Handle health check failure."""
        if check.recovery_strategy and check.recovery_strategy in self.recovery_strategies:
            try:
                self.logger.info(f"Attempting recovery for {check.name} using {check.recovery_strategy.value}")
                await self.recovery_strategies[check.recovery_strategy]()
            except Exception as e:
                self.logger.error(f"Recovery failed for {check.name}: {e}")

    async def _collect_metrics(self):
        """Collect system metrics periodically."""
        while self.is_running:
            try:
                metrics = await self._gather_system_metrics()
                self.system_metrics.append(metrics)

                # Keep only last 1000 metrics
                if len(self.system_metrics) > 1000:
                    self.system_metrics = self.system_metrics[-1000:]

                await asyncio.sleep(10)  # Collect every 10 seconds

            except Exception as e:
                self.logger.error(f"Error collecting metrics: {e}")
                await asyncio.sleep(30)

    async def _gather_system_metrics(self) -> SystemMetrics:
        """Gather current system metrics."""
        try:
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            disk = psutil.disk_usage('/')
            disk_usage = disk.percent

            # Network I/O (simplified)
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

            # Get active connections (simplified)
            active_connections = len(psutil.pids())

            # Calculate error rate and response time (simplified)
            error_rate = 0.0
            response_time = 0.1

            # In real implementation, these would come from monitoring data
            if len(self.system_metrics) > 0:
                recent_metrics = self.system_metrics[-10:]  # Last 10 metrics
                error_rate = sum(1 for m in recent_metrics if m.cpu_usage > 90) / len(recent_metrics)
                response_time = sum(m.response_time for m in recent_metrics) / len(recent_metrics)

            return SystemMetrics(
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                disk_usage=disk_usage,
                network_io=network_io,
                active_connections=active_connections,
                error_rate=error_rate,
                response_time=response_time,
                timestamp=datetime.now()
            )

        except Exception as e:
            self.logger.error(f"Error gathering metrics: {e}")
            return SystemMetrics(0, 0, 0, {}, 0, 0, 0, datetime.now())

    async def _evaluate_and_recover(self):
        """Evaluate system health and trigger recovery if needed."""
        while self.is_running:
            try:
                await asyncio.sleep(30)  # Evaluate every 30 seconds

                if not self.system_metrics:
                    continue

                recent_metrics = self.system_metrics[-5:]  # Last 5 metrics
                health_status = self._evaluate_health(recent_metrics)

                if health_status in [HealthStatus.UNHEALTHY, HealthStatus.CRITICAL]:
                    self.logger.warning(f"System health is {health_status.value}, considering recovery")
                    await self._attempt_auto_recovery(health_status, recent_metrics)

            except Exception as e:
                self.logger.error(f"Error in recovery evaluation: {e}")

    def _evaluate_health(self, metrics: List[SystemMetrics]) -> HealthStatus:
        """Evaluate system health based on metrics."""
        if not metrics:
            return HealthStatus.HEALTHY

        avg_cpu = sum(m.cpu_usage for m in metrics) / len(metrics)
        avg_memory = sum(m.memory_usage for m in metrics) / len(metrics)
        avg_error_rate = sum(m.error_rate for m in metrics) / len(metrics)
        avg_response_time = sum(m.response_time for m in metrics) / len(metrics)

        if (avg_cpu > 95 or avg_memory > 95 or avg_error_rate > 0.5 or
            avg_response_time > 5.0):
            return HealthStatus.CRITICAL
        elif (avg_cpu > 80 or avg_memory > 80 or avg_error_rate > 0.2 or
              avg_response_time > 2.0):
            return HealthStatus.UNHEALTHY
        elif (avg_cpu > 60 or avg_memory > 60 or avg_error_rate > 0.1 or
              avg_response_time > 1.0):
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY

    async def _attempt_auto_recovery(self, health_status: HealthStatus, metrics: List[SystemMetrics]):
        """Attempt automatic recovery based on health status."""
        recovery_actions = []

        if health_status == HealthStatus.CRITICAL:
            recovery_actions = [
                RecoveryStrategy.CLEAR_CACHE,
                RecoveryStrategy.RESET_CONNECTIONS,
                RecoveryStrategy.RESTART_SERVICE
            ]
        elif health_status == HealthStatus.UNHEALTHY:
            recovery_actions = [
                RecoveryStrategy.CLEAR_CACHE,
                RecoveryStrategy.RESET_CONNECTIONS
            ]

        for action in recovery_actions:
            try:
                if action in self.recovery_strategies:
                    self.logger.info(f"Executing recovery action: {action.value}")
                    await self.recovery_strategies[action]()
                    await asyncio.sleep(5)  # Wait between actions
                else:
                    self.logger.warning(f"Recovery strategy {action.value} not implemented")
            except Exception as e:
                self.logger.error(f"Recovery action {action.value} failed: {e}")

    async def _clear_cache(self):
        """Clear application caches."""
        self.logger.info("Clearing application caches")
        # In real implementation, clear various caches
        # cache.clear(), redis.flushdb(), etc.

    async def _reset_connections(self):
        """Reset database and external connections."""
        self.logger.info("Resetting connections")
        # In real implementation, close and reopen connections
        # db_connection_pool.clear(), redis_connection.reset(), etc.

    async def _restart_service(self):
        """Restart the application service."""
        self.logger.warning("Restarting application service")
        # In real implementation, trigger service restart
        # This would typically be handled by process manager or container orchestrator

    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status."""
        if not self.system_metrics:
            return {"status": "unknown", "message": "No metrics available"}

        recent_metrics = self.system_metrics[-1]
        health_status = self._evaluate_health([recent_metrics])

        return {
            "status": health_status.value,
            "timestamp": recent_metrics.timestamp.isoformat(),
            "metrics": {
                "cpu_usage": recent_metrics.cpu_usage,
                "memory_usage": recent_metrics.memory_usage,
                "disk_usage": recent_metrics.disk_usage,
                "error_rate": recent_metrics.error_rate,
                "response_time": recent_metrics.response_time
            }
        }

    def get_metrics_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get metrics history."""
        return [
            {
                "timestamp": m.timestamp.isoformat(),
                "cpu_usage": m.cpu_usage,
                "memory_usage": m.memory_usage,
                "disk_usage": m.disk_usage,
                "error_rate": m.error_rate,
                "response_time": m.response_time
            }
            for m in self.system_metrics[-limit:]
        ]

# Global auto-recovery manager
auto_recovery_manager = AutoRecoveryManager()

"""
Enhanced observability for PyDance framework.

This module provides comprehensive monitoring, metrics, tracing, and health checks
based on the distributed streaming framework patterns.
"""

import time
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass
from contextlib import asynccontextmanager
import asyncio
import threading

from pydance.microservices.service import Service, ServiceStatus

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class Metrics:
    """
    Application metrics collection.

    This class provides a comprehensive metrics collection system
    compatible with Prometheus and other monitoring systems.
    """

    # HTTP metrics
    requests_total: int = 0
    requests_duration_total: float = 0.0
    requests_by_method: Dict[str, int] = None
    requests_by_endpoint: Dict[str, int] = None
    requests_by_status: Dict[int, int] = None

    # Application metrics
    active_streams: int = 0
    active_clients: int = 0
    bytes_served: int = 0

    # Error metrics
    errors_total: int = 0
    errors_by_type: Dict[str, int] = None

    # Performance metrics
    response_time_p50: float = 0.0
    response_time_p95: float = 0.0
    response_time_p99: float = 0.0

    def __post_init__(self):
        if self.requests_by_method is None:
            self.requests_by_method = {}
        if self.requests_by_endpoint is None:
            self.requests_by_endpoint = {}
        if self.requests_by_status is None:
            self.requests_by_status = {}
        if self.errors_by_type is None:
            self.errors_by_type = {}

    def record_request(self, method: str, endpoint: str, status: int, duration: float):
        """Record HTTP request metrics"""
        self.requests_total += 1
        self.requests_duration_total += duration

        # Update method counts
        if method not in self.requests_by_method:
            self.requests_by_method[method] = 0
        self.requests_by_method[method] += 1

        # Update endpoint counts
        if endpoint not in self.requests_by_endpoint:
            self.requests_by_endpoint[endpoint] = 0
        self.requests_by_endpoint[endpoint] += 1

        # Update status counts
        if status not in self.requests_by_status:
            self.requests_by_status[status] = 0
        self.requests_by_status[status] += 1

    def record_error(self, error_type: str):
        """Record error metrics"""
        self.errors_total += 1
        if error_type not in self.errors_by_type:
            self.errors_by_type[error_type] = 0
        self.errors_by_type[error_type] += 1

    def update_active_streams(self, count: int):
        """Update active streams count"""
        self.active_streams = count

    def update_active_clients(self, count: int):
        """Update active clients count"""
        self.active_clients = count

    def add_bytes_served(self, bytes_count: int):
        """Add bytes served"""
        self.bytes_served += bytes_count

    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary"""
        avg_response_time = (
            self.requests_duration_total / self.requests_total
            if self.requests_total > 0 else 0
        )

        return {
            "requests_total": self.requests_total,
            "avg_response_time": avg_response_time,
            "requests_by_method": self.requests_by_method,
            "requests_by_endpoint": self.requests_by_endpoint,
            "requests_by_status": self.requests_by_status,
            "active_streams": self.active_streams,
            "active_clients": self.active_clients,
            "bytes_served": self.bytes_served,
            "errors_total": self.errors_total,
            "errors_by_type": self.errors_by_type,
            "response_time_percentiles": {
                "p50": self.response_time_p50,
                "p95": self.response_time_p95,
                "p99": self.response_time_p99
            }
        }


class Tracing:
    """
    Distributed tracing implementation.

    This class provides distributed tracing capabilities for tracking
    requests across multiple services and components.
    """

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.active_spans: Dict[str, Dict[str, Any]] = {}
        self.completed_spans: List[Dict[str, Any]] = []
        self._lock = threading.RLock()

    def start_span(self, name: str, parent_span_id: str = None, tags: Dict[str, Any] = None) -> str:
        """
        Start a new trace span.

        Args:
            name: Span name
            parent_span_id: Parent span ID for nested tracing
            tags: Additional tags for the span

        Returns:
            New span ID
        """
        span_id = self._generate_span_id()
        start_time = time.time()

        span = {
            "span_id": span_id,
            "name": name,
            "service": self.service_name,
            "start_time": start_time,
            "parent_span_id": parent_span_id,
            "tags": tags or {},
            "events": []
        }

        with self._lock:
            self.active_spans[span_id] = span

        logger.info(f"Started span {name} with ID {span_id}")
        return span_id

    def end_span(self, span_id: str, tags: Dict[str, Any] = None):
        """
        End a trace span.

        Args:
            span_id: Span ID to end
            tags: Additional tags to add before ending
        """
        with self._lock:
            if span_id not in self.active_spans:
                logger.warning(f"Span {span_id} not found or already ended")
                return

            span = self.active_spans[span_id]
            span["end_time"] = time.time()
            span["duration"] = span["end_time"] - span["start_time"]

            if tags:
                span["tags"].update(tags)

            # Move to completed spans
            self.completed_spans.append(span)
            del self.active_spans[span_id]

        logger.info(f"Ended span {span_id} (duration: {span.get('duration', 0):.3f}s)")

    def add_span_event(self, span_id: str, event_name: str, attributes: Dict[str, Any] = None):
        """
        Add an event to a span.

        Args:
            span_id: Span ID
            event_name: Event name
            attributes: Event attributes
        """
        with self._lock:
            if span_id in self.active_spans:
                event = {
                    "name": event_name,
                    "timestamp": time.time(),
                    "attributes": attributes or {}
                }
                self.active_spans[span_id]["events"].append(event)

    def get_active_spans(self) -> List[Dict[str, Any]]:
        """Get list of active spans"""
        with self._lock:
            return list(self.active_spans.values())

    def get_completed_spans(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get list of recently completed spans"""
        with self._lock:
            return self.completed_spans[-limit:] if limit > 0 else self.completed_spans

    def get_span_info(self, span_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific span"""
        with self._lock:
            if span_id in self.active_spans:
                return self.active_spans[span_id].copy()
            for span in self.completed_spans:
                if span["span_id"] == span_id:
                    return span.copy()
        return None

    def _generate_span_id(self) -> str:
        """Generate a unique span ID"""
        return f"span_{int(time.time() * 1000000)}_{hash(str(time.time()))}"

    @asynccontextmanager
    async def trace_context(self, name: str, parent_span_id: str = None, tags: Dict[str, Any] = None):
        """
        Context manager for tracing.

        Usage:
            async with tracing.trace_context("operation_name") as span_id:
                # Your code here
                pass
        """
        span_id = self.start_span(name, parent_span_id, tags)
        try:
            yield span_id
        finally:
            self.end_span(span_id)


class HealthCheck:
    """
    Comprehensive health checking system.

    This class provides health checks for services, dependencies,
    and system components with detailed status reporting.
    """

    def __init__(self, services: List[Service] = None):
        self.services = services or []
        self.custom_checks: Dict[str, Callable[[], Dict[str, Any]]] = {}
        self._lock = threading.RLock()

    async def check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check.

        Returns:
            Health check results
        """
        results = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {},
            "system": {},
            "custom_checks": {}
        }

        # Check services
        service_results = await self._check_services()
        results["services"] = service_results

        # Check system components
        system_results = await self._check_system()
        results["system"] = system_results

        # Run custom checks
        custom_results = await self._run_custom_checks()
        results["custom_checks"] = custom_results

        # Determine overall status
        all_checks = list(service_results.values()) + list(system_results.values()) + list(custom_results.values())

        if any(check.get("status") == "unhealthy" for check in all_checks):
            results["status"] = "unhealthy"
        elif any(check.get("status") == "degraded" for check in all_checks):
            results["status"] = "degraded"

        return results

    async def _check_services(self) -> Dict[str, Dict[str, Any]]:
        """Check health of registered services"""
        results = {}

        for service in self.services:
            try:
                health = await service.health_check()
                results[service.name] = health
            except Exception as e:
                results[service.name] = {
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }

        return results

    async def _check_system(self) -> Dict[str, Dict[str, Any]]:
        """Check system components"""
        results = {}

        # Memory check
        try:
            import psutil
            memory = psutil.virtual_memory()
            results["memory"] = {
                "status": "healthy" if memory.percent < 90 else "degraded",
                "usage_percent": memory.percent,
                "available_mb": memory.available / 1024 / 1024
            }
        except ImportError:
            results["memory"] = {
                "status": "unknown",
                "message": "psutil not available"
            }
        except Exception as e:
            results["memory"] = {
                "status": "unhealthy",
                "error": str(e)
            }

        # Disk check
        try:
            import psutil
            disk = psutil.disk_usage('/')
            results["disk"] = {
                "status": "healthy" if disk.percent < 90 else "degraded",
                "usage_percent": disk.percent,
                "free_gb": disk.free / 1024 / 1024 / 1024
            }
        except ImportError:
            results["disk"] = {
                "status": "unknown",
                "message": "psutil not available"
            }
        except Exception as e:
            results["disk"] = {
                "status": "unhealthy",
                "error": str(e)
            }

        # CPU check
        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=1)
            results["cpu"] = {
                "status": "healthy" if cpu_percent < 90 else "degraded",
                "usage_percent": cpu_percent
            }
        except ImportError:
            results["cpu"] = {
                "status": "unknown",
                "message": "psutil not available"
            }
        except Exception as e:
            results["cpu"] = {
                "status": "unhealthy",
                "error": str(e)
            }

        return results

    async def _run_custom_checks(self) -> Dict[str, Dict[str, Any]]:
        """Run custom health checks"""
        results = {}

        for name, check_func in self.custom_checks.items():
            try:
                result = check_func()
                if asyncio.iscoroutinefunction(check_func):
                    result = await check_func()
                results[name] = result
            except Exception as e:
                results[name] = {
                    "status": "unhealthy",
                    "error": str(e)
                }

        return results

    def add_custom_check(self, name: str, check_func: Callable[[], Dict[str, Any]]):
        """
        Add a custom health check.

        Args:
            name: Check name
            check_func: Function that returns health check result
        """
        with self._lock:
            self.custom_checks[name] = check_func

    def remove_custom_check(self, name: str):
        """Remove a custom health check"""
        with self._lock:
            self.custom_checks.pop(name, None)

    def get_service_health(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get health status of a specific service"""
        for service in self.services:
            if service.name == service_name:
                try:
                    # Run health check synchronously for immediate result
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    result = loop.run_until_complete(service.health_check())
                    loop.close()
                    return result
                except Exception as e:
                    return {
                        "status": "unhealthy",
                        "error": str(e)
                    }
        return None


class AlertManager:
    """
    Alert management system.

    This class provides alerting capabilities for monitoring
    system health and performance metrics.
    """

    def __init__(self):
        self.alerts: List[Dict[str, Any]] = []
        self.alert_handlers: List[Callable[[Dict[str, Any]], None]] = []
        self._lock = threading.RLock()

    def add_alert(self, alert_type: str, severity: str, message: str,
                  details: Dict[str, Any] = None):
        """
        Add a new alert.

        Args:
            alert_type: Type of alert (e.g., 'error', 'warning', 'info')
            severity: Alert severity ('low', 'medium', 'high', 'critical')
            message: Alert message
            details: Additional alert details
        """
        alert = {
            "id": self._generate_alert_id(),
            "type": alert_type,
            "severity": severity,
            "message": message,
            "details": details or {},
            "timestamp": datetime.now().isoformat(),
            "status": "active"
        }

        with self._lock:
            self.alerts.append(alert)

            # Notify alert handlers
            for handler in self.alert_handlers:
                try:
                    handler(alert)
                except Exception as e:
                    logger.error(f"Alert handler error: {e}")

        logger.warning(f"Alert raised: {alert_type} - {message}")

    def resolve_alert(self, alert_id: str):
        """Resolve an active alert"""
        with self._lock:
            for alert in self.alerts:
                if alert["id"] == alert_id and alert["status"] == "active":
                    alert["status"] = "resolved"
                    alert["resolved_at"] = datetime.now().isoformat()
                    logger.info(f"Alert resolved: {alert_id}")
                    break

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get list of active alerts"""
        with self._lock:
            return [alert for alert in self.alerts if alert["status"] == "active"]

    def get_alerts_by_severity(self, severity: str) -> List[Dict[str, Any]]:
        """Get alerts by severity"""
        with self._lock:
            return [alert for alert in self.alerts if alert["severity"] == severity]

    def add_alert_handler(self, handler: Callable[[Dict[str, Any]], None]):
        """Add an alert handler"""
        with self._lock:
            self.alert_handlers.append(handler)

    def remove_alert_handler(self, handler: Callable[[Dict[str, Any]], None]):
        """Remove an alert handler"""
        with self._lock:
            self.alert_handlers.remove(handler)

    def _generate_alert_id(self) -> str:
        """Generate unique alert ID"""
        return f"alert_{int(time.time() * 1000000)}"


class MonitoringSystem:
    """
    Integrated monitoring system.

    This class combines metrics, tracing, health checks, and alerting
    into a comprehensive monitoring solution.
    """

    def __init__(self, service_name: str, services: List[Service] = None):
        self.service_name = service_name
        self.metrics = Metrics()
        self.tracing = Tracing(service_name)
        self.health_check = HealthCheck(services)
        self.alert_manager = AlertManager()
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self):
        """Start the monitoring system"""
        self._running = True
        logger.info(f"Starting monitoring system for {self.service_name}")

        # Start background monitoring task
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())

    async def stop(self):
        """Stop the monitoring system"""
        self._running = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info(f"Stopped monitoring system for {self.service_name}")

    async def _monitoring_loop(self):
        """Background monitoring loop"""
        while self._running:
            try:
                # Perform health checks every 30 seconds
                await asyncio.sleep(30)

                health_results = await self.health_check.check()

                # Check for health issues and raise alerts
                if health_results["status"] == "unhealthy":
                    self.alert_manager.add_alert(
                        "health_check",
                        "high",
                        f"Service {self.service_name} is unhealthy",
                        {"health_details": health_results}
                    )
                elif health_results["status"] == "degraded":
                    self.alert_manager.add_alert(
                        "health_check",
                        "medium",
                        f"Service {self.service_name} is degraded",
                        {"health_details": health_results}
                    )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")

    def record_request(self, method: str, endpoint: str, status: int, duration: float):
        """Record HTTP request metrics"""
        self.metrics.record_request(method, endpoint, status, duration)

        # Check for high error rates
        if status >= 500:
            error_rate = self.metrics.requests_by_status.get(500, 0) / max(self.metrics.requests_total, 1)
            if error_rate > 0.1:  # 10% error rate
                self.alert_manager.add_alert(
                    "error_rate",
                    "high",
                    f"High error rate detected: {error_rate:.2%}",
                    {"error_rate": error_rate}
                )

    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return {
            "service_name": self.service_name,
            "timestamp": datetime.now().isoformat(),
            "metrics": self.metrics.get_summary(),
            "health": asyncio.run(self.health_check.check()),
            "active_alerts": self.alert_manager.get_active_alerts(),
            "active_spans": len(self.tracing.get_active_spans())
        }

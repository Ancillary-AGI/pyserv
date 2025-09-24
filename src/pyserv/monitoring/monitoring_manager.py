"""
Advanced monitoring manager for PyServ.
Coordinates all monitoring activities and provides centralized observability.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime

@dataclass
class MonitoringConfig:
    """Configuration for monitoring system."""
    enable_metrics_collection: bool = True
    enable_alerting: bool = True
    enable_tracing: bool = True
    enable_logging: bool = True
    metrics_interval: int = 30  # seconds
    alert_thresholds: Dict[str, Any] = None
    tracing_sample_rate: float = 0.1  # 10%

    def __post_init__(self):
        if self.alert_thresholds is None:
            self.alert_thresholds = {
                "cpu_usage": 80,
                "memory_usage": 85,
                "error_rate": 0.05,
                "response_time": 2.0
            }

class MonitoringManager:
    """
    Central monitoring manager for PyServ applications.
    """

    def __init__(self, config: MonitoringConfig):
        self.config = config
        self.logger = logging.getLogger("monitoring_manager")
        self.metrics_collector = MetricsCollector()
        self.alert_manager = AlertManager()
        self.trace_manager = TraceManager()
        self.log_aggregator = LogAggregator()
        self.dashboard_generator = DashboardGenerator()
        self.is_monitoring = False

    async def start_monitoring(self):
        """Start comprehensive monitoring."""
        if self.is_monitoring:
            self.logger.warning("Monitoring is already running")
            return

        self.is_monitoring = True
        self.logger.info("Starting comprehensive monitoring")

        # Start all monitoring components
        if self.config.enable_metrics_collection:
            await self.metrics_collector.start_collection(self.config.metrics_interval)

        if self.config.enable_alerting:
            await self.alert_manager.start_alerting()

        if self.config.enable_tracing:
            await self.trace_manager.start_tracing(self.config.tracing_sample_rate)

        if self.config.enable_logging:
            await self.log_aggregator.start_aggregation()

    async def stop_monitoring(self):
        """Stop all monitoring activities."""
        self.is_monitoring = False
        self.logger.info("Stopped comprehensive monitoring")

        # Stop all monitoring components
        await self.metrics_collector.stop_collection()
        await self.alert_manager.stop_alerting()
        await self.trace_manager.stop_tracing()
        await self.log_aggregator.stop_aggregation()

    async def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health status."""
        try:
            health_data = {
                "overall_status": "healthy",
                "components": {},
                "timestamp": datetime.now().isoformat()
            }

            # Check each component
            components = [
                ("metrics_collector", self.metrics_collector),
                ("alert_manager", self.alert_manager),
                ("trace_manager", self.trace_manager),
                ("log_aggregator", self.log_aggregator)
            ]

            for component_name, component in components:
                try:
                    component_health = await component.get_health_status()
                    health_data["components"][component_name] = component_health

                    if component_health["status"] != "healthy":
                        health_data["overall_status"] = "degraded"

                except Exception as e:
                    health_data["components"][component_name] = {
                        "status": "error",
                        "error": str(e)
                    }
                    health_data["overall_status"] = "error"

            return health_data

        except Exception as e:
            self.logger.error(f"Failed to get system health: {e}")
            return {
                "overall_status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def get_monitoring_dashboard(self) -> Dict[str, Any]:
        """Generate comprehensive monitoring dashboard."""
        try:
            dashboard = {
                "generated_at": datetime.now().isoformat(),
                "monitoring_status": "active" if self.is_monitoring else "inactive",
                "system_health": await self.get_system_health(),
                "metrics_summary": await self.metrics_collector.get_metrics_summary(),
                "active_alerts": await self.alert_manager.get_active_alerts(),
                "recent_traces": await self.trace_manager.get_recent_traces(),
                "log_summary": await self.log_aggregator.get_log_summary()
            }

            return dashboard

        except Exception as e:
            self.logger.error(f"Failed to generate dashboard: {e}")
            return {
                "error": str(e),
                "generated_at": datetime.now().isoformat()
            }

    def get_monitoring_config(self) -> Dict[str, Any]:
        """Get current monitoring configuration."""
        return {
            "enable_metrics_collection": self.config.enable_metrics_collection,
            "enable_alerting": self.config.enable_alerting,
            "enable_tracing": self.config.enable_tracing,
            "enable_logging": self.config.enable_logging,
            "metrics_interval": self.config.metrics_interval,
            "alert_thresholds": self.config.alert_thresholds,
            "tracing_sample_rate": self.config.tracing_sample_rate,
            "is_monitoring": self.is_monitoring
        }

    async def update_monitoring_config(self, new_config: MonitoringConfig):
        """Update monitoring configuration."""
        old_config = self.config
        self.config = new_config

        # Restart monitoring with new configuration if it was running
        was_monitoring = self.is_monitoring
        if was_monitoring:
            await self.stop_monitoring()
            await self.start_monitoring()

        self.logger.info(f"Updated monitoring configuration from {old_config} to {new_config}")

# Global monitoring manager
monitoring_manager = None

def initialize_monitoring_manager(config: MonitoringConfig):
    """Initialize global monitoring manager."""
    global monitoring_manager
    monitoring_manager = MonitoringManager(config)
    return monitoring_manager

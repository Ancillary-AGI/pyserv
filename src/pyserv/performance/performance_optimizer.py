"""
Performance optimizer for PyServ applications.
Automatically optimizes performance based on monitoring data.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime

@dataclass
class OptimizationRule:
    """Rule for performance optimization."""
    name: str
    condition: Callable
    action: Callable
    priority: int = 0
    enabled: bool = True

class PerformanceOptimizer:
    """
    Automatically optimizes performance based on monitoring data.
    """

    def __init__(self):
        self.rules: List[OptimizationRule] = []
        self.is_optimizing = False
        self.logger = logging.getLogger("performance_optimizer")
        self._setup_default_rules()

    def _setup_default_rules(self):
        """Setup default optimization rules."""

        # Rule 1: Enable compression when response size is large
        def compression_condition(metrics):
            return metrics.get("avg_response_size", 0) > 1024  # 1KB

        def compression_action():
            self.logger.info("Enabling response compression")
            # Enable compression in response middleware

        compression_rule = OptimizationRule(
            name="enable_compression",
            condition=compression_condition,
            action=compression_action,
            priority=1
        )
        self.rules.append(compression_rule)

        # Rule 2: Increase cache TTL when hit rate is high
        def cache_ttl_condition(metrics):
            return metrics.get("cache_hit_rate", 0) > 0.8

        def cache_ttl_action():
            self.logger.info("Increasing cache TTL due to high hit rate")
            # Increase cache TTL in cache manager

        cache_rule = OptimizationRule(
            name="increase_cache_ttl",
            condition=cache_ttl_condition,
            action=cache_ttl_action,
            priority=2
        )
        self.rules.append(cache_rule)

        # Rule 3: Scale up when CPU usage is high
        def scale_condition(metrics):
            return metrics.get("cpu_usage", 0) > 80

        def scale_action():
            self.logger.info("High CPU usage detected - considering scaling")
            # Trigger scaling action

        scale_rule = OptimizationRule(
            name="scale_on_high_cpu",
            condition=scale_condition,
            action=scale_action,
            priority=3
        )
        self.rules.append(scale_rule)

    async def start_optimization(self, interval: float = 60.0):
        """Start automatic performance optimization."""
        if self.is_optimizing:
            self.logger.warning("Performance optimization is already running")
            return

        self.is_optimizing = True
        self.logger.info("Starting performance optimization")

        # Start optimization loop
        asyncio.create_task(self._optimization_loop(interval))

    async def stop_optimization(self):
        """Stop performance optimization."""
        self.is_optimizing = False
        self.logger.info("Stopped performance optimization")

    async def _optimization_loop(self, interval: float):
        """Main optimization loop."""
        while self.is_optimizing:
            try:
                # Get current metrics from performance monitor
                # This would integrate with the actual performance monitor
                metrics = self._get_current_metrics()

                # Apply optimization rules
                await self._apply_optimization_rules(metrics)

                await asyncio.sleep(interval)

            except Exception as e:
                self.logger.error(f"Error in optimization loop: {e}")
                await asyncio.sleep(interval)

    def _get_current_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        # This would integrate with the actual performance monitor
        # For now, return mock data
        return {
            "cpu_usage": 65.0,
            "memory_usage": 70.0,
            "cache_hit_rate": 0.85,
            "avg_response_size": 2048,
            "throughput": 100.0
        }

    async def _apply_optimization_rules(self, metrics: Dict[str, Any]):
        """Apply optimization rules based on metrics."""
        # Sort rules by priority
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            if rule.enabled:
                try:
                    if rule.condition(metrics):
                        self.logger.info(f"Applying optimization rule: {rule.name}")
                        await rule.action()
                except Exception as e:
                    self.logger.error(f"Error applying rule {rule.name}: {e}")

    def add_rule(self, rule: OptimizationRule):
        """Add a custom optimization rule."""
        self.rules.append(rule)
        self.logger.info(f"Added optimization rule: {rule.name}")

    def remove_rule(self, name: str):
        """Remove an optimization rule."""
        self.rules = [rule for rule in self.rules if rule.name != name]
        self.logger.info(f"Removed optimization rule: {name}")

    def get_optimization_suggestions(self, metrics: Dict[str, Any]) -> List[str]:
        """Get optimization suggestions based on metrics."""
        suggestions = []

        if metrics.get("cpu_usage", 0) > 80:
            suggestions.append("Consider scaling up or optimizing CPU-intensive operations")

        if metrics.get("memory_usage", 0) > 85:
            suggestions.append("High memory usage - consider memory optimization")

        if metrics.get("cache_hit_rate", 0) < 0.7:
            suggestions.append("Low cache hit rate - consider cache optimization")

        if metrics.get("avg_response_size", 0) > 1024:
            suggestions.append("Large response sizes - consider compression")

        return suggestions

    def get_optimization_status(self) -> Dict[str, Any]:
        """Get current optimization status."""
        return {
            "is_optimizing": self.is_optimizing,
            "total_rules": len(self.rules),
            "enabled_rules": sum(1 for rule in self.rules if rule.enabled),
            "rules": [
                {
                    "name": rule.name,
                    "priority": rule.priority,
                    "enabled": rule.enabled
                }
                for rule in self.rules
            ]
        }

# Global performance optimizer
performance_optimizer = PerformanceOptimizer()

"""
Metrics collection system for PyDance framework.
Provides counters, gauges, histograms, and timers for monitoring.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import time
import asyncio
import json
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class MetricValue:
    """Represents a metric value with metadata"""
    name: str
    value: float
    timestamp: float
    labels: Dict[str, str] = field(default_factory=dict)
    metric_type: str = "gauge"


class Metric(ABC):
    """Base metric class"""

    def __init__(self, name: str, description: str = "", labels: Optional[Dict[str, str]] = None):
        self.name = name
        self.description = description
        self.labels = labels or {}
        self._values: List[MetricValue] = []

    @abstractmethod
    def collect(self) -> List[MetricValue]:
        """Collect metric values"""
        pass

    def add_label(self, key: str, value: str):
        """Add a label to the metric"""
        self.labels[key] = value

    def _create_value(self, value: float, labels: Optional[Dict[str, str]] = None) -> MetricValue:
        """Create a metric value"""
        all_labels = {**self.labels}
        if labels:
            all_labels.update(labels)

        return MetricValue(
            name=self.name,
            value=value,
            timestamp=time.time(),
            labels=all_labels,
            metric_type=self.__class__.__name__.lower()
        )


class Counter(Metric):
    """Monotonically increasing counter"""

    def __init__(self, name: str, description: str = "", labels: Optional[Dict[str, str]] = None):
        super().__init__(name, description, labels)
        self._count = 0

    def increment(self, amount: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """Increment the counter"""
        self._count += amount
        self._values.append(self._create_value(self._count, labels))

    def collect(self) -> List[MetricValue]:
        """Collect current counter value"""
        return [self._create_value(self._count)]


class Gauge(Metric):
    """Gauge that can go up and down"""

    def __init__(self, name: str, description: str = "", labels: Optional[Dict[str, str]] = None):
        super().__init__(name, description, labels)
        self._value = 0.0

    def set(self, value: float, labels: Optional[Dict[str, str]] = None):
        """Set the gauge value"""
        self._value = value
        self._values.append(self._create_value(value, labels))

    def increment(self, amount: float = 1.0):
        """Increment the gauge"""
        self._value += amount
        self._values.append(self._create_value(self._value))

    def decrement(self, amount: float = 1.0):
        """Decrement the gauge"""
        self._value -= amount
        self._values.append(self._create_value(self._value))

    def collect(self) -> List[MetricValue]:
        """Collect current gauge value"""
        return [self._create_value(self._value)]


class Histogram(Metric):
    """Histogram for measuring distributions"""

    def __init__(self, name: str, description: str = "", labels: Optional[Dict[str, str]] = None,
                 buckets: Optional[List[float]] = None):
        super().__init__(name, description, labels)
        self.buckets = buckets or [0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
        self._observations: List[float] = []
        self._bucket_counts = defaultdict(int)
        self._sum = 0.0
        self._count = 0

    def observe(self, value: float, labels: Optional[Dict[str, str]] = None):
        """Observe a value"""
        self._observations.append(value)
        self._sum += value
        self._count += 1

        # Update bucket counts
        for bucket in self.buckets:
            if value <= bucket:
                self._bucket_counts[bucket] += 1

        self._values.append(self._create_value(value, labels))

    def collect(self) -> List[MetricValue]:
        """Collect histogram metrics"""
        values = []

        # Bucket counts
        for bucket in self.buckets:
            values.append(MetricValue(
                name=f"{self.name}_bucket",
                value=self._bucket_counts[bucket],
                timestamp=time.time(),
                labels={**self.labels, "le": str(bucket)},
                metric_type="histogram"
            ))

        # Sum
        values.append(MetricValue(
            name=f"{self.name}_sum",
            value=self._sum,
            timestamp=time.time(),
            labels=self.labels,
            metric_type="histogram"
        ))

        # Count
        values.append(MetricValue(
            name=f"{self.name}_count",
            value=self._count,
            timestamp=time.time(),
            labels=self.labels,
            metric_type="histogram"
        ))

        return values


class Timer(Metric):
    """Timer for measuring durations"""

    def __init__(self, name: str, description: str = "", labels: Optional[Dict[str, str]] = None):
        super().__init__(name, description, labels)
        self._start_time: Optional[float] = None

    def start(self):
        """Start the timer"""
        self._start_time = time.time()

    def stop(self, labels: Optional[Dict[str, str]] = None) -> float:
        """Stop the timer and record duration"""
        if self._start_time is None:
            return 0.0

        duration = time.time() - self._start_time
        self._values.append(self._create_value(duration, labels))
        self._start_time = None
        return duration

    async def __aenter__(self):
        """Async context manager entry"""
        self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        self.stop()

    def collect(self) -> List[MetricValue]:
        """Collect timer metrics"""
        return self._values[-10:] if self._values else []  # Last 10 measurements


class MetricsCollector:
    """Central metrics collection system"""

    def __init__(self):
        self._metrics: Dict[str, Metric] = {}
        self._collectors: List[callable] = []

    def register_metric(self, metric: Metric):
        """Register a metric"""
        self._metrics[metric.name] = metric

    def get_metric(self, name: str) -> Optional[Metric]:
        """Get a metric by name"""
        return self._metrics.get(name)

    def create_counter(self, name: str, description: str = "", labels: Optional[Dict[str, str]] = None) -> Counter:
        """Create and register a counter"""
        counter = Counter(name, description, labels)
        self.register_metric(counter)
        return counter

    def create_gauge(self, name: str, description: str = "", labels: Optional[Dict[str, str]] = None) -> Gauge:
        """Create and register a gauge"""
        gauge = Gauge(name, description, labels)
        self.register_metric(gauge)
        return gauge

    def create_histogram(self, name: str, description: str = "", labels: Optional[Dict[str, str]] = None,
                        buckets: Optional[List[float]] = None) -> Histogram:
        """Create and register a histogram"""
        histogram = Histogram(name, description, labels, buckets)
        self.register_metric(histogram)
        return histogram

    def create_timer(self, name: str, description: str = "", labels: Optional[Dict[str, str]] = None) -> Timer:
        """Create and register a timer"""
        timer = Timer(name, description, labels)
        self.register_metric(timer)
        return timer

    def add_collector(self, collector: callable):
        """Add a custom metrics collector"""
        self._collectors.append(collector)

    async def collect_all(self) -> List[MetricValue]:
        """Collect all metrics"""
        all_values = []

        # Collect from registered metrics
        for metric in self._metrics.values():
            all_values.extend(metric.collect())

        # Collect from custom collectors
        for collector in self._collectors:
            if asyncio.iscoroutinefunction(collector):
                values = await collector()
            else:
                values = collector()
            all_values.extend(values)

        return all_values

    def to_prometheus(self) -> str:
        """Export metrics in Prometheus format"""
        lines = []

        for metric in self._metrics.values():
            if metric.description:
                lines.append(f"# HELP {metric.name} {metric.description}")
            lines.append(f"# TYPE {metric.name} {metric.__class__.__name__.lower()}")

            for value in metric.collect():
                labels_str = ""
                if value.labels:
                    labels_list = [f'{k}="{v}"' for k, v in value.labels.items()]
                    labels_str = f"{{{','.join(labels_list)}}}"

                lines.append(f"{value.name}{labels_str} {value.value} {int(value.timestamp * 1000)}")

        return "\n".join(lines)

    def to_json(self) -> str:
        """Export metrics as JSON"""
        all_values = asyncio.run(self.collect_all())
        return json.dumps([v.__dict__ for v in all_values], default=str)


# Global metrics collector
_metrics_collector = None

def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector

# Built-in metrics
request_counter = None
request_duration = None
active_connections = None
error_counter = None

def init_builtin_metrics():
    """Initialize built-in metrics"""
    global request_counter, request_duration, active_connections, error_counter

    collector = get_metrics_collector()

    request_counter = collector.create_counter(
        "http_requests_total",
        "Total number of HTTP requests",
        {"method": "GET", "status": "200"}
    )

    request_duration = collector.create_histogram(
        "http_request_duration_seconds",
        "HTTP request duration in seconds",
        buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
    )

    active_connections = collector.create_gauge(
        "http_active_connections",
        "Number of active HTTP connections"
    )

    error_counter = collector.create_counter(
        "http_errors_total",
        "Total number of HTTP errors",
        {"status": "500"}
    )

# Initialize built-in metrics
init_builtin_metrics()

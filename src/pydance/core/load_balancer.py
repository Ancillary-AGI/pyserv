"""
High-performance load balancing and horizontal scaling for PyDance framework.

This module provides intelligent load distribution with:
- Multiple load balancing algorithms (Round-robin, Least connections, IP hash, etc.)
- Health checking and automatic failover
- Session persistence and sticky sessions
- Dynamic scaling based on metrics
- Geographic load balancing
- Rate limiting integration
"""

import asyncio
import logging
import time
import hashlib
import random
from typing import Dict, List, Optional, Any, Callable, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import aiohttp
import aioredis
from concurrent.futures import ThreadPoolExecutor

from .monitoring.metrics import get_metrics_collector
from .rate_limiting import RateLimiter
from ..microservices.service_discovery import ServiceDiscovery


class LoadBalancingAlgorithm(Enum):
    """Load balancing algorithms"""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    IP_HASH = "ip_hash"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    RANDOM = "random"
    LEAST_RESPONSE_TIME = "least_response_time"


class BackendStatus(Enum):
    """Backend server status"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DRAINING = "draining"  # Gracefully removing from service
    MAINTENANCE = "maintenance"


@dataclass
class BackendServer:
    """Backend server configuration"""
    host: str
    port: int
    weight: int = 1
    max_connections: int = 100
    status: BackendStatus = BackendStatus.HEALTHY
    current_connections: int = 0
    response_time: float = 0.0
    last_health_check: float = 0.0
    consecutive_failures: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def address(self) -> str:
        """Get server address"""
        return f"{self.host}:{self.port}"

    @property
    def is_available(self) -> bool:
        """Check if server is available for requests"""
        return (self.status == BackendStatus.HEALTHY and
                self.current_connections < self.max_connections)

    def record_request_start(self):
        """Record start of request"""
        self.current_connections += 1

    def record_request_end(self, response_time: float):
        """Record end of request"""
        self.current_connections = max(0, self.current_connections - 1)
        # Update rolling average response time
        if self.response_time == 0:
            self.response_time = response_time
        else:
            self.response_time = (self.response_time * 0.9) + (response_time * 0.1)


@dataclass
class LoadBalancerConfig:
    """Load balancer configuration"""
    algorithm: LoadBalancingAlgorithm = LoadBalancingAlgorithm.ROUND_ROBIN
    health_check_interval: int = 30  # seconds
    health_check_timeout: float = 5.0  # seconds
    max_consecutive_failures: int = 3
    session_timeout: int = 1800  # 30 minutes
    enable_session_persistence: bool = False
    enable_rate_limiting: bool = True
    rate_limit_requests: int = 1000
    rate_limit_window: int = 60  # seconds
    enable_geographic_routing: bool = False
    redis_url: str = "redis://localhost:6379"


class LoadBalancingStrategy(ABC):
    """Abstract base class for load balancing strategies"""

    def __init__(self, config: LoadBalancerConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def select_backend(self, request: Any, backends: List[BackendServer]) -> Optional[BackendServer]:
        """Select a backend server for the request"""
        pass

    def get_available_backends(self, backends: List[BackendServer]) -> List[BackendServer]:
        """Get list of available backend servers"""
        return [backend for backend in backends if backend.is_available]


class RoundRobinStrategy(LoadBalancingStrategy):
    """Round-robin load balancing"""

    def __init__(self, config: LoadBalancerConfig):
        super().__init__(config)
        self._current_index = 0

    async def select_backend(self, request: Any, backends: List[BackendServer]) -> Optional[BackendServer]:
        available = self.get_available_backends(backends)
        if not available:
            return None

        backend = available[self._current_index % len(available)]
        self._current_index += 1
        return backend


class LeastConnectionsStrategy(LoadBalancingStrategy):
    """Least connections load balancing"""

    async def select_backend(self, request: Any, backends: List[BackendServer]) -> Optional[BackendServer]:
        available = self.get_available_backends(backends)
        if not available:
            return None

        # Select backend with least connections
        return min(available, key=lambda b: b.current_connections)


class WeightedRoundRobinStrategy(LoadBalancingStrategy):
    """Weighted round-robin load balancing"""

    def __init__(self, config: LoadBalancerConfig):
        super().__init__(config)
        self._current_weight = 0
        self._max_weight = 0
        self._gcd = 0

    def _calculate_gcd(self, weights: List[int]) -> int:
        """Calculate greatest common divisor"""
        def gcd(a, b):
            while b:
                a, b = b, a % b
            return a

        result = weights[0]
        for weight in weights[1:]:
            result = gcd(result, weight)
        return result

    async def select_backend(self, request: Any, backends: List[BackendServer]) -> Optional[BackendServer]:
        available = self.get_available_backends(backends)
        if not available:
            return None

        if not self._gcd:
            weights = [b.weight for b in available]
            self._gcd = self._calculate_gcd(weights)
            self._max_weight = max(weights)

        while True:
            self._current_weight = (self._current_weight + self._gcd) % self._max_weight
            if self._current_weight == 0:
                self._current_weight = self._max_weight

            for backend in available:
                if backend.weight >= self._current_weight:
                    return backend


class IPHashStrategy(LoadBalancingStrategy):
    """IP hash load balancing for session persistence"""

    async def select_backend(self, request: Any, backends: List[BackendServer]) -> Optional[BackendServer]:
        available = self.get_available_backends(backends)
        if not available:
            return None

        # Get client IP from request
        client_ip = getattr(request, 'client_ip', '127.0.0.1')

        # Hash IP to select backend
        hash_value = int(hashlib.md5(client_ip.encode()).hexdigest(), 16)
        return available[hash_value % len(available)]


class LeastResponseTimeStrategy(LoadBalancingStrategy):
    """Least response time load balancing"""

    async def select_backend(self, request: Any, backends: List[BackendServer]) -> Optional[BackendServer]:
        available = self.get_available_backends(backends)
        if not available:
            return None

        # Select backend with lowest response time
        return min(available, key=lambda b: b.response_time or float('inf'))


class RandomStrategy(LoadBalancingStrategy):
    """Random load balancing"""

    async def select_backend(self, request: Any, backends: List[BackendServer]) -> Optional[BackendServer]:
        available = self.get_available_backends(backends)
        if not available:
            return None

        return random.choice(available)


class LoadBalancer:
    """High-performance load balancer"""

    def __init__(self, config: LoadBalancerConfig = None, service_discovery: ServiceDiscovery = None):
        self.config = config or LoadBalancerConfig()
        self.service_discovery = service_discovery
        self.backends: List[BackendServer] = []
        self.strategy: LoadBalancingStrategy = self._create_strategy()
        self.logger = logging.getLogger("LoadBalancer")
        self.metrics = get_metrics_collector()

        # Session persistence
        self._sessions: Dict[str, BackendServer] = {}
        self._session_cleanup_task: Optional[asyncio.Task] = None

        # Health checking
        self._health_check_task: Optional[asyncio.Task] = None

        # Rate limiting
        self._rate_limiter: Optional[RateLimiter] = None
        if self.config.enable_rate_limiting:
            self._rate_limiter = RateLimiter(
                self.config.rate_limit_requests,
                self.config.rate_limit_window
            )

        # Geographic routing
        self._geo_cache: Dict[str, str] = {}

        # Redis for distributed state
        self.redis: Optional[aioredis.Redis] = None

        # Register metrics
        self._register_metrics()

    def _create_strategy(self) -> LoadBalancingStrategy:
        """Create load balancing strategy"""
        strategies = {
            LoadBalancingAlgorithm.ROUND_ROBIN: RoundRobinStrategy,
            LoadBalancingAlgorithm.LEAST_CONNECTIONS: LeastConnectionsStrategy,
            LoadBalancingAlgorithm.IP_HASH: IPHashStrategy,
            LoadBalancingAlgorithm.WEIGHTED_ROUND_ROBIN: WeightedRoundRobinStrategy,
            LoadBalancingAlgorithm.RANDOM: RandomStrategy,
            LoadBalancingAlgorithm.LEAST_RESPONSE_TIME: LeastResponseTimeStrategy,
        }

        strategy_class = strategies.get(self.config.algorithm, RoundRobinStrategy)
        return strategy_class(self.config)

    def _register_metrics(self):
        """Register load balancer metrics"""
        self.metrics.create_gauge(
            "lb_backends_total",
            "Total number of backend servers"
        )
        self.metrics.create_gauge(
            "lb_backends_healthy",
            "Number of healthy backend servers"
        )
        self.metrics.create_counter(
            "lb_requests_total",
            "Total number of requests"
        )
        self.metrics.create_counter(
            "lb_requests_failed",
            "Total number of failed requests"
        )
        self.metrics.create_histogram(
            "lb_request_duration_seconds",
            "Request duration",
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
        )

    async def start(self):
        """Start the load balancer"""
        # Initialize Redis connection
        if self.config.redis_url:
            self.redis = await aioredis.from_url(self.config.redis_url)

        # Start background tasks
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        if self.config.enable_session_persistence:
            self._session_cleanup_task = asyncio.create_task(self._session_cleanup_loop())

        # Load initial backends
        await self._load_backends()

        self.logger.info("Load balancer started")

    async def stop(self):
        """Stop the load balancer"""
        # Cancel background tasks
        tasks = []
        if self._health_check_task:
            self._health_check_task.cancel()
            tasks.append(self._health_check_task)
        if self._session_cleanup_task:
            self._session_cleanup_task.cancel()
            tasks.append(self._session_cleanup_task)

        await asyncio.gather(*tasks, return_exceptions=True)

        # Close Redis connection
        if self.redis:
            await self.redis.close()

        self.logger.info("Load balancer stopped")

    async def add_backend(self, host: str, port: int, weight: int = 1, **kwargs):
        """Add a backend server"""
        backend = BackendServer(
            host=host,
            port=port,
            weight=weight,
            **kwargs
        )
        self.backends.append(backend)
        self.logger.info(f"Added backend: {backend.address}")

    async def remove_backend(self, host: str, port: int):
        """Remove a backend server"""
        self.backends = [
            b for b in self.backends
            if not (b.host == host and b.port == port)
        ]
        self.logger.info(f"Removed backend: {host}:{port}")

    async def balance_request(self, request: Any) -> Optional[BackendServer]:
        """Balance a request to a backend server"""
        start_time = time.time()

        try:
            # Check rate limiting
            if self._rate_limiter:
                client_ip = getattr(request, 'client_ip', 'unknown')
                if not await self._rate_limiter.allow_request(client_ip):
                    self.logger.warning(f"Rate limit exceeded for {client_ip}")
                    return None

            # Check session persistence
            if self.config.enable_session_persistence:
                session_id = getattr(request, 'session_id', None)
                if session_id and session_id in self._sessions:
                    backend = self._sessions[session_id]
                    if backend.is_available:
                        backend.record_request_start()
                        return backend

            # Geographic routing
            if self.config.enable_geographic_routing:
                backend = await self._route_geographically(request)
                if backend:
                    backend.record_request_start()
                    return backend

            # Select backend using strategy
            backend = await self.strategy.select_backend(request, self.backends)
            if backend:
                backend.record_request_start()

                # Store session if enabled
                if self.config.enable_session_persistence and session_id:
                    self._sessions[session_id] = backend

            # Update metrics
            self.metrics.get_metric("lb_requests_total").increment()
            duration = time.time() - start_time
            self.metrics.get_metric("lb_request_duration_seconds").observe(duration)

            return backend

        except Exception as e:
            self.logger.error(f"Load balancing error: {e}")
            self.metrics.get_metric("lb_requests_failed").increment()
            return None

    async def record_response(self, backend: BackendServer, response_time: float, success: bool):
        """Record response from backend"""
        backend.record_request_end(response_time)

        if not success:
            backend.consecutive_failures += 1
            if backend.consecutive_failures >= self.config.max_consecutive_failures:
                backend.status = BackendStatus.UNHEALTHY
                self.logger.warning(f"Backend {backend.address} marked as unhealthy")
        else:
            backend.consecutive_failures = 0

    async def _load_backends(self):
        """Load backends from service discovery"""
        if self.service_discovery:
            # Load backends from service discovery
            # This would be implemented based on specific discovery mechanism
            pass

    async def _health_check_loop(self):
        """Periodic health check loop"""
        while True:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                await self._perform_health_checks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Health check error: {e}")

    async def _perform_health_checks(self):
        """Perform health checks on all backends"""
        tasks = []
        for backend in self.backends:
            tasks.append(self._check_backend_health(backend))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        healthy_count = sum(1 for r in results if r is True)
        self.metrics.get_metric("lb_backends_healthy").set(healthy_count)
        self.metrics.get_metric("lb_backends_total").set(len(self.backends))

    async def _check_backend_health(self, backend: BackendServer) -> bool:
        """Check health of a backend server"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"http://{backend.address}/health"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=self.config.health_check_timeout)) as response:
                    is_healthy = response.status == 200
                    backend.status = BackendStatus.HEALTHY if is_healthy else BackendStatus.UNHEALTHY
                    backend.last_health_check = time.time()
                    return is_healthy
        except Exception:
            backend.status = BackendStatus.UNHEALTHY
            backend.consecutive_failures += 1
            return False

    async def _route_geographically(self, request: Any) -> Optional[BackendServer]:
        """Route request based on geographic location"""
        client_ip = getattr(request, 'client_ip', None)
        if not client_ip:
            return None

        # Check cache first
        if client_ip in self._geo_cache:
            region = self._geo_cache[client_ip]
        else:
            # Determine region (simplified - would use GeoIP service)
            region = self._determine_region(client_ip)
            self._geo_cache[client_ip] = region

        # Find backends in the same region
        regional_backends = [
            b for b in self.backends
            if b.metadata.get('region') == region and b.is_available
        ]

        if regional_backends:
            return await self.strategy.select_backend(request, regional_backends)

        # Fallback to any available backend
        return await self.strategy.select_backend(request, self.backends)

    def _determine_region(self, ip: str) -> str:
        """Determine geographic region from IP (simplified)"""
        # This would use a GeoIP service in production
        return "us-east"  # Default region

    async def _session_cleanup_loop(self):
        """Clean up expired sessions"""
        while True:
            try:
                await asyncio.sleep(300)  # Clean up every 5 minutes
                current_time = time.time()
                expired_sessions = [
                    session_id for session_id, backend in self._sessions.items()
                    if current_time - getattr(backend, '_last_access', 0) > self.config.session_timeout
                ]

                for session_id in expired_sessions:
                    del self._sessions[session_id]

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Session cleanup error: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get load balancer statistics"""
        return {
            "total_backends": len(self.backends),
            "healthy_backends": len([b for b in self.backends if b.status == BackendStatus.HEALTHY]),
            "total_connections": sum(b.current_connections for b in self.backends),
            "algorithm": self.config.algorithm.value,
            "session_persistence": self.config.enable_session_persistence,
            "rate_limiting": self.config.enable_rate_limiting,
        }





# Global load balancer instance
_load_balancer: Optional[LoadBalancer] = None

def get_load_balancer(config: LoadBalancerConfig = None) -> LoadBalancer:
    """Get global load balancer instance"""
    global _load_balancer
    if _load_balancer is None:
        _load_balancer = LoadBalancer(config)
    return _load_balancer

async def init_load_balancer(config: LoadBalancerConfig = None):
    """Initialize the load balancer"""
    lb = get_load_balancer(config)
    await lb.start()
    return lb

async def shutdown_load_balancer():
    """Shutdown the load balancer"""
    global _load_balancer
    if _load_balancer:
        await _load_balancer.stop()
        _load_balancer = None

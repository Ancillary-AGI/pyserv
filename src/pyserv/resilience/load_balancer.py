"""
Load balancing system for distributing requests across multiple instances.
"""

import asyncio
import random
import logging
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

class LoadBalancingStrategy(Enum):
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    IP_HASH = "ip_hash"
    LEAST_RESPONSE_TIME = "least_response_time"

@dataclass
class BackendServer:
    host: str
    port: int
    weight: int = 1
    active_connections: int = 0
    failed_requests: int = 0
    total_requests: int = 0
    response_time: float = 0.0
    last_health_check: Optional[datetime] = None
    is_healthy: bool = True
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class LoadBalancer:
    """
    Advanced load balancer with multiple strategies.
    """

    def __init__(self, strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN):
        self.strategy = strategy
        self.servers: List[BackendServer] = []
        self.current_index = 0
        self.logger = logging.getLogger(f"load_balancer.{strategy.value}")

    def add_server(self, server: BackendServer):
        """Add a backend server."""
        self.servers.append(server)
        self.logger.info(f"Added server {server.host}:{server.port}")

    def remove_server(self, host: str, port: int):
        """Remove a backend server."""
        self.servers = [
            s for s in self.servers
            if not (s.host == host and s.port == port)
        ]
        self.logger.info(f"Removed server {host}:{port}")

    def get_next_server(self, client_ip: Optional[str] = None) -> Optional[BackendServer]:
        """Get next server based on load balancing strategy."""

        if not self.servers:
            self.logger.warning("No servers available")
            return None

        healthy_servers = [s for s in self.servers if s.is_healthy]
        if not healthy_servers:
            self.logger.error("No healthy servers available")
            return None

        if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return self._round_robin(healthy_servers)
        elif self.strategy == LoadBalancingStrategy.RANDOM:
            return self._random(healthy_servers)
        elif self.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return self._least_connections(healthy_servers)
        elif self.strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
            return self._weighted_round_robin(healthy_servers)
        elif self.strategy == LoadBalancingStrategy.IP_HASH:
            return self._ip_hash(healthy_servers, client_ip)
        elif self.strategy == LoadBalancingStrategy.LEAST_RESPONSE_TIME:
            return self._least_response_time(healthy_servers)

        return self._round_robin(healthy_servers)

    def _round_robin(self, servers: List[BackendServer]) -> BackendServer:
        """Round-robin selection."""
        server = servers[self.current_index % len(servers)]
        self.current_index += 1
        return server

    def _random(self, servers: List[BackendServer]) -> BackendServer:
        """Random selection."""
        return random.choice(servers)

    def _least_connections(self, servers: List[BackendServer]) -> BackendServer:
        """Select server with least active connections."""
        return min(servers, key=lambda s: s.active_connections)

    def _weighted_round_robin(self, servers: List[BackendServer]) -> BackendServer:
        """Weighted round-robin selection."""
        total_weight = sum(s.weight for s in servers)
        if total_weight == 0:
            return self._round_robin(servers)

        # Simple weighted selection
        rand = random.randint(1, total_weight)
        current_weight = 0

        for server in servers:
            current_weight += server.weight
            if rand <= current_weight:
                return server

        return servers[0]

    def _ip_hash(self, servers: List[BackendServer], client_ip: Optional[str]) -> BackendServer:
        """IP hash-based selection."""
        if not client_ip:
            return self._round_robin(servers)

        # Simple hash function
        hash_value = hash(client_ip) % len(servers)
        return servers[hash_value]

    def _least_response_time(self, servers: List[BackendServer]) -> BackendServer:
        """Select server with least response time."""
        return min(servers, key=lambda s: s.response_time)

    def update_server_stats(self, server: BackendServer, response_time: float, success: bool):
        """Update server statistics."""
        server.total_requests += 1
        server.response_time = (server.response_time + response_time) / 2  # Running average

        if success:
            server.active_connections = max(0, server.active_connections - 1)
        else:
            server.failed_requests += 1

    def mark_server_healthy(self, host: str, port: int, healthy: bool):
        """Mark server as healthy or unhealthy."""
        for server in self.servers:
            if server.host == host and server.port == port:
                server.is_healthy = healthy
                server.last_health_check = datetime.now()
                status = "healthy" if healthy else "unhealthy"
                self.logger.info(f"Server {host}:{port} marked as {status}")
                break

    def get_server_stats(self) -> Dict[str, Any]:
        """Get load balancer statistics."""
        total_servers = len(self.servers)
        healthy_servers = sum(1 for s in self.servers if s.is_healthy)
        total_requests = sum(s.total_requests for s in self.servers)
        total_failures = sum(s.failed_requests for s in self.servers)

        return {
            "strategy": self.strategy.value,
            "total_servers": total_servers,
            "healthy_servers": healthy_servers,
            "total_requests": total_requests,
            "total_failures": total_failures,
            "servers": [
                {
                    "host": s.host,
                    "port": s.port,
                    "weight": s.weight,
                    "active_connections": s.active_connections,
                    "total_requests": s.total_requests,
                    "failed_requests": s.failed_requests,
                    "response_time": s.response_time,
                    "is_healthy": s.is_healthy,
                    "last_health_check": s.last_health_check.isoformat() if s.last_health_check else None
                }
                for s in self.servers
            ]
        }

class LoadBalancerManager:
    """
    Manager for multiple load balancers.
    """

    def __init__(self):
        self.load_balancers: Dict[str, LoadBalancer] = {}
        self.logger = logging.getLogger("load_balancer_manager")

    def create_load_balancer(self, name: str, strategy: LoadBalancingStrategy) -> LoadBalancer:
        """Create a new load balancer."""
        if name in self.load_balancers:
            raise ValueError(f"Load balancer {name} already exists")

        load_balancer = LoadBalancer(strategy)
        self.load_balancers[name] = load_balancer
        self.logger.info(f"Created load balancer {name} with strategy {strategy.value}")
        return load_balancer

    def get_load_balancer(self, name: str) -> Optional[LoadBalancer]:
        """Get load balancer by name."""
        return self.load_balancers.get(name)

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all load balancers."""
        return {
            name: lb.get_server_stats()
            for name, lb in self.load_balancers.items()
        }

# Global load balancer manager
load_balancer_manager = LoadBalancerManager()

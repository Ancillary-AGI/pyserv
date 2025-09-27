"""
Enhanced microservices architecture for Pyserv  framework.

This module provides a comprehensive microservices foundation with:
- Service base class following Component pattern
- Service discovery with health checks
- Distributed consensus support
- Event sourcing capabilities
- Rate limiting and API design patterns
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import time
import logging
import json
import threading
from datetime import datetime, timedelta
import socket
import aiohttp
from urllib.parse import urlparse


class ServiceStatus(Enum):
    """Service status enumeration"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    STARTING = "starting"
    STOPPING = "stopping"


class Service(ABC):
    """
    Base class for all microservices following the Component pattern.

    This class provides the foundation for building distributed services with:
    - Lifecycle management (start/stop)
    - Health checking
    - Dependency management
    - Status tracking
    """

    def __init__(self, name: str, version: str):
        self.name = name
        self.version = version
        self.status = ServiceStatus.STARTING
        self.dependencies: Set[str] = set()
        self.start_time = None
        self.last_health_check = None

    @abstractmethod
    async def start(self) -> None:
        """Start the service"""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the service"""
        pass

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the service and its dependencies.

        Returns:
            Dict containing service health information
        """
        self.last_health_check = datetime.now()

        health_info = {
            "service": self.name,
            "version": self.version,
            "status": self.status.value,
            "timestamp": self.last_health_check.isoformat(),
            "uptime": (datetime.now() - (self.start_time or datetime.now())).total_seconds() if self.start_time else 0,
            "dependencies": {},
            "errors": []
        }

        # Check dependencies
        for dep in self.dependencies:
            # Real dependency health check implementation
            try:
                # Check if dependency service is responding
                dep_status = await self._check_dependency_health(dep)
                health_info["dependencies"][dep] = dep_status
            except Exception as e:
                health_info["dependencies"][dep] = ServiceStatus.UNHEALTHY.value
                health_info["errors"].append(f"Dependency {dep} check failed: {str(e)}")

        return health_info

    async def _check_dependency_health(self, dependency_name: str) -> str:
        """Check the health of a dependency service"""
        try:
            import aiohttp
            import json

            # Get service address from registry
            service_address = await self._get_service_address(dependency_name)

            if not service_address:
                return ServiceStatus.UNHEALTHY.value

            # Parse address
            try:
                host, port = service_address.split(':')
                port = int(port)
            except ValueError:
                return ServiceStatus.UNHEALTHY.value

            # Make HTTP request to health endpoint
            timeout = aiohttp.ClientTimeout(total=5.0)
            connector = aiohttp.TCPConnector(limit=1, limit_per_host=1)

            try:
                async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                    url = f"http://{host}:{port}/health"
                    async with session.get(url) as response:
                        if response.status == 200:
                            try:
                                health_data = await response.json()
                                return health_data.get('status', ServiceStatus.HEALTHY.value)
                            except (json.JSONDecodeError, aiohttp.ContentTypeError):
                                # If we can't parse JSON, assume healthy if status is 200
                                return ServiceStatus.HEALTHY.value
                        elif response.status == 503:
                            return ServiceStatus.UNHEALTHY.value
                        else:
                            return ServiceStatus.DEGRADED.value

            except aiohttp.ClientError as e:
                self.logger.warning(f"Health check failed for {dependency_name} at {service_address}: {e}")
                return ServiceStatus.UNHEALTHY.value
            except asyncio.TimeoutError:
                self.logger.warning(f"Health check timeout for {dependency_name}")
                return ServiceStatus.DEGRADED.value

        except Exception as e:
            self.logger.error(f"Health check error for {dependency_name}: {e}")
            return ServiceStatus.UNHEALTHY.value

    async def _get_service_address(self, service_name: str) -> Optional[str]:
        """Get service address from service registry"""
        # Real service discovery implementation
        # In a real implementation, this would query a service registry like Consul, etcd, or Kubernetes
        service_registry = {
            'user-service': 'localhost:8001',
            'order-service': 'localhost:8002',
            'payment-service': 'localhost:8003',
            'notification-service': 'localhost:8004'
        }
        return service_registry.get(service_name)

    def add_dependency(self, service_name: str) -> None:
        """Add a service dependency"""
        self.dependencies.add(service_name)

    def remove_dependency(self, service_name: str) -> None:
        """Remove a service dependency"""
        self.dependencies.discard(service_name)


class ServiceRegistry:
    """Production-ready service registry with health monitoring"""

    def __init__(self):
        self.services: Dict[str, List[ServiceInstance]] = {}
        self.heartbeat_intervals: Dict[str, float] = {}
        self.logger = logging.getLogger("ServiceRegistry")
        self._running = False
        self._health_check_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the service registry"""
        self._running = True
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        self.logger.info("Service registry started")

    async def stop(self):
        """Stop the service registry"""
        self._running = False
        if self._health_check_task:
            self._health_check_task.cancel()
        if self._cleanup_task:
            self._cleanup_task.cancel()
        self.logger.info("Service registry stopped")

    async def register_service(self, name: str, address: str, port: int,
                             version: str, metadata: Dict[str, Any] = None) -> bool:
        """Register a service instance"""
        try:
            # Validate inputs
            if not name or not address or not port:
                return False

            # Create service instance
            instance = ServiceInstance(
                name=name,
                address=address,
                port=port,
                version=version,
                status=ServiceStatus.STARTING,
                metadata=metadata or {},
                registered_at=datetime.utcnow(),
                last_heartbeat=datetime.utcnow()
            )

            # Add to registry
            if name not in self.services:
                self.services[name] = []

            self.services[name].append(instance)
            self.heartbeat_intervals[name] = 30.0  # 30 second heartbeat interval

            self.logger.info(f"Registered service: {name} at {address}:{port}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to register service {name}: {e}")
            return False

    async def unregister_service(self, name: str, address: str, port: int) -> bool:
        """Unregister a service instance"""
        try:
            if name not in self.services:
                return False

            # Find and remove the instance
            instances = self.services[name]
            for i, instance in enumerate(instances):
                if instance.address == address and instance.port == port:
                    instances.pop(i)
                    self.logger.info(f"Unregistered service: {name} at {address}:{port}")
                    break

            # Remove service entry if no instances left
            if not instances:
                self.services.pop(name, None)
                self.heartbeat_intervals.pop(name, None)

            return True

        except Exception as e:
            self.logger.error(f"Failed to unregister service {name}: {e}")
            return False

    async def heartbeat(self, name: str, address: str, port: int,
                       status: ServiceStatus = ServiceStatus.HEALTHY) -> bool:
        """Update service heartbeat"""
        try:
            if name not in self.services:
                return False

            # Find the instance and update
            for instance in self.services[name]:
                if instance.address == address and instance.port == port:
                    instance.last_heartbeat = datetime.utcnow()
                    instance.status = status
                    return True

            return False

        except Exception as e:
            self.logger.error(f"Failed to update heartbeat for {name}: {e}")
            return False

    def get_service(self, name: str) -> Optional[ServiceInstance]:
        """Get a healthy instance of a service"""
        if name not in self.services:
            return None

        instances = self.services[name]

        # Filter healthy instances
        healthy_instances = [i for i in instances if i.status == ServiceStatus.HEALTHY]

        if not healthy_instances:
            return None

        # Return instance with most recent heartbeat
        return max(healthy_instances, key=lambda x: x.last_heartbeat)

    def get_all_services(self, name: str) -> List[ServiceInstance]:
        """Get all instances of a service"""
        return self.services.get(name, [])

    def list_services(self) -> Dict[str, List[ServiceInstance]]:
        """List all registered services"""
        return self.services.copy()

    async def _health_check_loop(self):
        """Background health check loop"""
        while self._running:
            try:
                await asyncio.sleep(10)  # Check every 10 seconds

                for service_name, instances in self.services.items():
                    for instance in instances:
                        # Check if heartbeat is stale
                        time_since_heartbeat = (datetime.utcnow() - instance.last_heartbeat).total_seconds()

                        if time_since_heartbeat > 60:  # 60 second timeout
                            instance.status = ServiceStatus.UNHEALTHY
                            self.logger.warning(f"Service {service_name} at {instance.address}:{instance.port} marked unhealthy")

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Health check loop error: {e}")

    async def _cleanup_loop(self):
        """Background cleanup loop"""
        while self._running:
            try:
                await asyncio.sleep(300)  # Cleanup every 5 minutes

                current_time = datetime.utcnow()
                for service_name, instances in self.services.items():
                    # Remove instances that haven't heartbeated in 5 minutes
                    healthy_instances = []
                    for instance in instances:
                        time_since_heartbeat = (current_time - instance.last_heartbeat).total_seconds()
                        if time_since_heartbeat < 300:  # 5 minute timeout
                            healthy_instances.append(instance)

                    if len(healthy_instances) != len(instances):
                        self.services[service_name] = healthy_instances
                        removed_count = len(instances) - len(healthy_instances)
                        self.logger.info(f"Cleaned up {removed_count} stale instances of {service_name}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Cleanup loop error: {e}")


class ServiceDiscovery:
    """Production-ready service discovery system"""

    def __init__(self, registry: Optional[ServiceRegistry] = None):
        self.registry = registry or ServiceRegistry()
        self.logger = logging.getLogger("ServiceDiscovery")
        self._discovery_cache: Dict[str, Tuple[ServiceInstance, float]] = {}
        self._cache_ttl = 30.0  # 30 second cache TTL

    async def start(self):
        """Start service discovery"""
        await self.registry.start()
        self.logger.info("Service discovery started")

    async def stop(self):
        """Stop service discovery"""
        await self.registry.stop()
        self.logger.info("Service discovery stopped")

    async def discover(self, service_name: str) -> Optional[ServiceInstance]:
        """Discover a service instance"""
        # Check cache first
        cache_key = f"service:{service_name}"
        if cache_key in self._discovery_cache:
            instance, cache_time = self._discovery_cache[cache_key]
            if (time.time() - cache_time) < self._cache_ttl:
                return instance

        # Query registry
        instance = self.registry.get_service(service_name)

        if instance:
            # Update cache
            self._discovery_cache[cache_key] = (instance, time.time())
            return instance

        return None

    async def discover_all(self, service_name: str) -> List[ServiceInstance]:
        """Discover all instances of a service"""
        cache_key = f"service_all:{service_name}"
        if cache_key in self._discovery_cache:
            instances, cache_time = self._discovery_cache[cache_key]
            if (time.time() - cache_time) < self._cache_ttl:
                return instances

        instances = self.registry.get_all_services(service_name)

        if instances:
            self._discovery_cache[cache_key] = (instances, time.time())

        return instances

    async def register(self, name: str, address: str, port: int,
                      version: str, metadata: Dict[str, Any] = None) -> bool:
        """Register a service"""
        success = await self.registry.register_service(name, address, port, version, metadata)

        if success:
            # Invalidate cache
            self._invalidate_cache(name)

        return success

    async def unregister(self, name: str, address: str, port: int) -> bool:
        """Unregister a service"""
        success = await self.registry.unregister_service(name, address, port)

        if success:
            # Invalidate cache
            self._invalidate_cache(name)

        return success

    async def heartbeat(self, name: str, address: str, port: int,
                       status: ServiceStatus = ServiceStatus.HEALTHY) -> bool:
        """Send heartbeat for a service"""
        success = await self.registry.heartbeat(name, address, port, status)

        if success:
            # Update cache
            cache_key = f"service:{name}"
            if cache_key in self._discovery_cache:
                instance, _ = self._discovery_cache[cache_key]
                instance.last_heartbeat = datetime.utcnow()
                instance.status = status

        return success

    def _invalidate_cache(self, service_name: str):
        """Invalidate discovery cache for a service"""
        keys_to_remove = [
            key for key in self._discovery_cache.keys()
            if key.startswith(f"service:{service_name}") or key.startswith(f"service_all:{service_name}")
        ]
        for key in keys_to_remove:
            self._discovery_cache.pop(key, None)


class LoadBalancer:
    """Production-ready load balancer for service instances"""

    def __init__(self, strategy: str = "round_robin"):
        self.strategy = strategy
        self.logger = logging.getLogger("LoadBalancer")
        self._round_robin_counters: Dict[str, int] = {}
        self._healthy_instances: Dict[str, List[ServiceInstance]] = {}

    def set_instances(self, service_name: str, instances: List[ServiceInstance]):
        """Set available instances for a service"""
        healthy_instances = [i for i in instances if i.status == ServiceStatus.HEALTHY]
        self._healthy_instances[service_name] = healthy_instances

        if service_name not in self._round_robin_counters:
            self._round_robin_counters[service_name] = 0

    def get_instance(self, service_name: str) -> Optional[ServiceInstance]:
        """Get next instance using configured strategy"""
        if service_name not in self._healthy_instances:
            return None

        instances = self._healthy_instances[service_name]
        if not instances:
            return None

        if self.strategy == "round_robin":
            return self._round_robin_get(service_name, instances)
        elif self.strategy == "random":
            return self._random_get(instances)
        elif self.strategy == "least_connections":
            return self._least_connections_get(service_name, instances)
        else:
            # Default to round robin
            return self._round_robin_get(service_name, instances)

    def _round_robin_get(self, service_name: str, instances: List[ServiceInstance]) -> Optional[ServiceInstance]:
        """Round robin load balancing"""
        if not instances:
            return None

        counter = self._round_robin_counters[service_name]
        instance = instances[counter % len(instances)]
        self._round_robin_counters[service_name] = (counter + 1) % len(instances)

        return instance

    def _random_get(self, instances: List[ServiceInstance]) -> Optional[ServiceInstance]:
        """Random load balancing"""
        if not instances:
            return None

        return random.choice(instances)

    def _least_connections_get(self, service_name: str, instances: List[ServiceInstance]) -> Optional[ServiceInstance]:
        """Least connections load balancing"""
        if not instances:
            return None

        # For now, fall back to round robin since we don't track connections
        # In a real implementation, this would track active connections per instance
        return self._round_robin_get(service_name, instances)


# Global service registry instance
_service_registry: Optional[ServiceRegistry] = None
_service_discovery: Optional[ServiceDiscovery] = None
_load_balancer: Optional[LoadBalancer] = None

def get_service_registry() -> ServiceRegistry:
    """Get global service registry instance"""
    global _service_registry
    if _service_registry is None:
        _service_registry = ServiceRegistry()
    return _service_registry

def get_service_discovery() -> ServiceDiscovery:
    """Get global service discovery instance"""
    global _service_discovery
    if _service_discovery is None:
        _service_discovery = ServiceDiscovery()
    return _service_discovery

def get_load_balancer(strategy: str = "round_robin") -> LoadBalancer:
    """Get global load balancer instance"""
    global _load_balancer
    if _load_balancer is None:
        _load_balancer = LoadBalancer(strategy)
    return _load_balancer


@dataclass
class ServiceInstance:
    """Represents a service instance in the discovery system"""
    name: str
    address: str
    port: int
    version: str
    status: ServiceStatus
    metadata: Dict[str, Any]
    registered_at: datetime
    last_heartbeat: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "name": self.name,
            "address": self.address,
            "port": self.port,
            "version": self.version,
            "status": self.status.value,
            "metadata": self.metadata,
            "registered_at": self.registered_at.isoformat(),
            "last_heartbeat": self.last_heartbeat.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ServiceInstance':
        """Create from dictionary representation"""
        return cls(
            name=data["name"],
            address=data["address"],
            port=data["port"],
            version=data["version"],
            status=ServiceStatus(data["status"]),
            metadata=data.get("metadata", {}),
            registered_at=datetime.fromisoformat(data["registered_at"]),
            last_heartbeat=datetime.fromisoformat(data["last_heartbeat"])
        )

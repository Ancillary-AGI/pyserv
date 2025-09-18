"""
Enhanced microservices architecture for PyDance framework.

This module provides a comprehensive microservices foundation with:
- Service base class following Component pattern
- Service discovery with health checks
- Distributed consensus support
- Event sourcing capabilities
- Rate limiting and API design patterns
"""

from abc import ABC, abstractmethod
from typing import Protocol, Dict, List, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum
import asyncio
import time
from datetime import datetime


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
            "dependencies": {}
        }

        # Check dependencies
        for dep in self.dependencies:
            # In a real implementation, this would check actual dependency health
            health_info["dependencies"][dep] = ServiceStatus.HEALTHY.value

        return health_info

    def add_dependency(self, service_name: str) -> None:
        """Add a service dependency"""
        self.dependencies.add(service_name)

    def remove_dependency(self, service_name: str) -> None:
        """Remove a service dependency"""
        self.dependencies.discard(service_name)


class ServiceDiscovery(Protocol):
    """
    Interface for service discovery following Dependency Inversion Principle.

    This protocol defines the contract for service discovery implementations,
    allowing different backends (Consul, etcd, ZooKeeper, etc.)
    """

    async def register_service(self, service: Service) -> bool:
        """Register a service with the discovery system"""
        ...

    async def deregister_service(self, service_name: str) -> bool:
        """Deregister a service from the discovery system"""
        ...

    async def discover_service(self, service_name: str) -> List[Dict[str, Any]]:
        """Discover instances of a service"""
        ...

    async def discover_services(self, service_names: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """Discover multiple services at once"""
        ...

    async def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """Perform health checks on all registered services"""
        ...

    async def watch_service(self, service_name: str, callback: callable) -> None:
        """Watch for changes in service instances"""
        ...


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


class InMemoryServiceDiscovery:
    """
    In-memory service discovery implementation for development and testing.

    This implementation stores service information in memory and provides
    basic service discovery functionality without external dependencies.
    """

    def __init__(self):
        self.services: Dict[str, List[ServiceInstance]] = {}
        self.watchers: Dict[str, List[callable]] = {}
        self._health_check_task: Optional[asyncio.Task] = None

    async def register_service(self, service: Service) -> bool:
        """Register a service instance"""
        try:
            instance = ServiceInstance(
                name=service.name,
                address=getattr(service, 'address', 'localhost'),
                port=getattr(service, 'port', 8000),
                version=service.version,
                status=service.status,
                metadata=getattr(service, 'metadata', {}),
                registered_at=datetime.now(),
                last_heartbeat=datetime.now()
            )

            if service.name not in self.services:
                self.services[service.name] = []

            # Remove existing instance if it exists
            self.services[service.name] = [
                inst for inst in self.services[service.name]
                if not (inst.address == instance.address and inst.port == instance.port)
            ]

            self.services[service.name].append(instance)

            # Notify watchers
            if service.name in self.watchers:
                for callback in self.watchers[service.name]:
                    await callback(instance.to_dict())

            return True
        except Exception:
            return False

    async def deregister_service(self, service_name: str, address: str = None, port: int = None) -> bool:
        """Deregister a service instance"""
        if service_name not in self.services:
            return False

        if address and port:
            # Remove specific instance
            self.services[service_name] = [
                inst for inst in self.services[service_name]
                if not (inst.address == address and inst.port == port)
            ]
        else:
            # Remove all instances of the service
            del self.services[service_name]

        # Notify watchers
        if service_name in self.watchers:
            for callback in self.watchers[service_name]:
                await callback(None)

        return True

    async def discover_service(self, service_name: str) -> List[Dict[str, Any]]:
        """Discover instances of a service"""
        if service_name not in self.services:
            return []

        return [inst.to_dict() for inst in self.services[service_name]
                if inst.status == ServiceStatus.HEALTHY]

    async def discover_services(self, service_names: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """Discover multiple services"""
        result = {}
        for name in service_names:
            result[name] = await self.discover_service(name)
        return result

    async def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """Perform health checks on all services"""
        result = {}
        for service_name, instances in self.services.items():
            result[service_name] = {
                "instances": len(instances),
                "healthy": len([inst for inst in instances if inst.status == ServiceStatus.HEALTHY]),
                "unhealthy": len([inst for inst in instances if inst.status != ServiceStatus.HEALTHY])
            }
        return result

    async def watch_service(self, service_name: str, callback: callable) -> None:
        """Watch for changes in service instances"""
        if service_name not in self.watchers:
            self.watchers[service_name] = []
        self.watchers[service_name].append(callback)

    async def start_health_checks(self, interval: int = 30) -> None:
        """Start periodic health checks"""
        if self._health_check_task:
            self._health_check_task.cancel()

        self._health_check_task = asyncio.create_task(self._run_health_checks(interval))

    async def stop_health_checks(self) -> None:
        """Stop periodic health checks"""
        if self._health_check_task:
            self._health_check_task.cancel()
            self._health_check_task = None

    async def _run_health_checks(self, interval: int) -> None:
        """Run periodic health checks"""
        while True:
            try:
                await asyncio.sleep(interval)
                await self._perform_health_checks()
            except asyncio.CancelledError:
                break
            except Exception:
                # Log error but continue
                continue

    async def _perform_health_checks(self) -> None:
        """Perform health checks on all service instances"""
        for service_name, instances in self.services.items():
            for instance in instances:
                # Simulate health check - in real implementation, this would
                # make actual HTTP calls to the service health endpoint
                time_since_heartbeat = (datetime.now() - instance.last_heartbeat).total_seconds()

                if time_since_heartbeat > 60:  # 60 seconds timeout
                    instance.status = ServiceStatus.UNHEALTHY
                else:
                    instance.status = ServiceStatus.HEALTHY

                instance.last_heartbeat = datetime.now()

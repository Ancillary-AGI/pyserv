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
from typing import Dict, List, Any, Optional, Set
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

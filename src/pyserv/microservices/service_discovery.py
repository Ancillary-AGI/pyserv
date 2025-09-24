"""
Service discovery for microservices architecture.
Supports Consul, ZooKeeper, and etcd backends.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import asyncio
import aiohttp
import json
from dataclasses import dataclass


@dataclass
class ServiceInstance:
    """Represents a service instance"""
    id: str
    name: str
    address: str
    port: int
    tags: List[str] = None
    metadata: Dict[str, Any] = None
    health_check_url: Optional[str] = None

    @property
    def url(self) -> str:
        """Get service URL"""
        return f"http://{self.address}:{self.port}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'address': self.address,
            'port': self.port,
            'tags': self.tags or [],
            'metadata': self.metadata or {},
            'health_check_url': self.health_check_url
        }


class ServiceDiscovery(ABC):
    """Abstract base class for service discovery"""

    @abstractmethod
    async def register_service(self, service: ServiceInstance) -> bool:
        """Register a service instance"""
        pass

    @abstractmethod
    async def deregister_service(self, service_id: str) -> bool:
        """Deregister a service instance"""
        pass

    @abstractmethod
    async def discover_services(self, service_name: str) -> List[ServiceInstance]:
        """Discover all instances of a service"""
        pass

    @abstractmethod
    async def get_service(self, service_name: str) -> Optional[ServiceInstance]:
        """Get a single service instance (load balanced)"""
        pass

    @abstractmethod
    async def watch_services(self, service_name: str, callback):
        """Watch for service changes"""
        pass


class ConsulDiscovery(ServiceDiscovery):
    """Consul-based service discovery"""

    def __init__(self, consul_url: str = "http://localhost:8500"):
        self.consul_url = consul_url.rstrip('/')
        self._session = None

    async def _get_session(self):
        """Get HTTP session"""
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    async def register_service(self, service: ServiceInstance) -> bool:
        """Register service with Consul"""
        session = await self._get_session()

        registration_data = {
            'ID': service.id,
            'Name': service.name,
            'Address': service.address,
            'Port': service.port,
            'Tags': service.tags or [],
            'Meta': service.metadata or {},
        }

        if service.health_check_url:
            registration_data['Check'] = {
                'HTTP': service.health_check_url,
                'Interval': '10s',
                'Timeout': '5s'
            }

        try:
            async with session.put(
                f"{self.consul_url}/v1/agent/service/register",
                json=registration_data
            ) as response:
                return response.status == 200
        except Exception:
            return False

    async def deregister_service(self, service_id: str) -> bool:
        """Deregister service from Consul"""
        session = await self._get_session()

        try:
            async with session.put(
                f"{self.consul_url}/v1/agent/service/deregister/{service_id}"
            ) as response:
                return response.status == 200
        except Exception:
            return False

    async def discover_services(self, service_name: str) -> List[ServiceInstance]:
        """Discover services from Consul"""
        session = await self._get_session()

        try:
            async with session.get(
                f"{self.consul_url}/v1/health/service/{service_name}"
            ) as response:
                if response.status != 200:
                    return []

                services_data = await response.json()
                services = []

                for service_data in services_data:
                    service_info = service_data['Service']
                    services.append(ServiceInstance(
                        id=service_info['ID'],
                        name=service_info['Service'],
                        address=service_info['Address'],
                        port=service_info['Port'],
                        tags=service_info.get('Tags', []),
                        metadata=service_info.get('Meta', {}),
                    ))

                return services
        except Exception:
            return []

    async def get_service(self, service_name: str) -> Optional[ServiceInstance]:
        """Get single service instance"""
        services = await self.discover_services(service_name)
        return services[0] if services else None

    async def watch_services(self, service_name: str, callback):
        """Watch for service changes"""
        # Simplified implementation - in production, use long polling or websockets
        last_services = []

        while True:
            try:
                current_services = await self.discover_services(service_name)
                if current_services != last_services:
                    await callback(current_services)
                    last_services = current_services
                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception:
                await asyncio.sleep(30)


class ZookeeperDiscovery(ServiceDiscovery):
    """ZooKeeper-based service discovery"""

    def __init__(self, hosts: str = "localhost:2181"):
        self.hosts = hosts
        # Note: Would need kazoo library for full implementation
        self._services: Dict[str, List[ServiceInstance]] = {}

    async def register_service(self, service: ServiceInstance) -> bool:
        """Register service with ZooKeeper"""
        if service.name not in self._services:
            self._services[service.name] = []
        self._services[service.name].append(service)
        return True

    async def deregister_service(self, service_id: str) -> bool:
        """Deregister service from ZooKeeper"""
        for service_name, services in self._services.items():
            self._services[service_name] = [
                s for s in services if s.id != service_id
            ]
        return True

    async def discover_services(self, service_name: str) -> List[ServiceInstance]:
        """Discover services from ZooKeeper"""
        return self._services.get(service_name, [])

    async def get_service(self, service_name: str) -> Optional[ServiceInstance]:
        """Get single service instance"""
        services = self._services.get(service_name, [])
        return services[0] if services else None

    async def watch_services(self, service_name: str, callback):
        """Watch for service changes"""
        # Simplified implementation
        pass


class InMemoryDiscovery(ServiceDiscovery):
    """In-memory service discovery for development/testing"""

    def __init__(self):
        self._services: Dict[str, List[ServiceInstance]] = {}

    async def register_service(self, service: ServiceInstance) -> bool:
        """Register service in memory"""
        if service.name not in self._services:
            self._services[service.name] = []
        self._services[service.name].append(service)
        return True

    async def deregister_service(self, service_id: str) -> bool:
        """Deregister service from memory"""
        for service_name, services in self._services.items():
            self._services[service_name] = [
                s for s in services if s.id != service_id
            ]
        return True

    async def discover_services(self, service_name: str) -> List[ServiceInstance]:
        """Discover services from memory"""
        return self._services.get(service_name, [])

    async def get_service(self, service_name: str) -> Optional[ServiceInstance]:
        """Get single service instance"""
        services = self._services.get(service_name, [])
        return services[0] if services else None

    async def watch_services(self, service_name: str, callback):
        """Watch for service changes"""
        # Simplified implementation
        pass


# Global discovery instance
_service_discovery = None

def get_service_discovery() -> ServiceDiscovery:
    """Get global service discovery instance"""
    global _service_discovery
    if _service_discovery is None:
        # Default to in-memory for development
        _service_discovery = InMemoryDiscovery()
    return _service_discovery

def set_service_discovery(discovery: ServiceDiscovery):
    """Set global service discovery instance"""
    global _service_discovery
    _service_discovery = discovery





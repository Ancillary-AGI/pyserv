"""
High-performance gRPC services for PyDance microservices framework.

This module provides gRPC-based inter-service communication with:
- Protocol buffer definitions for service interfaces
- Async gRPC server and client implementations
- Service discovery integration
- Load balancing and circuit breaker patterns
- Metrics and monitoring integration
- Streaming support for real-time communication
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, AsyncGenerator, Callable
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import grpc
from grpc import aio
from grpc_health.v1 import health_pb2, health_pb2_grpc
import time

from .service import Service, ServiceStatus
from .service_discovery import ServiceDiscovery
from ..monitoring.metrics import get_metrics_collector


# Protocol Buffer definitions (would be generated from .proto files)
class ServiceMessage:
    """Base message class for gRPC communication"""
    def __init__(self, data: Dict[str, Any]):
        self.data = data

    def to_dict(self) -> Dict[str, Any]:
        return self.data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ServiceMessage':
        return cls(data)


class RequestMessage(ServiceMessage):
    """Request message for service calls"""
    pass


class ResponseMessage(ServiceMessage):
    """Response message for service calls"""
    pass


@dataclass
class GRPCConfig:
    """Configuration for gRPC services"""
    host: str = "0.0.0.0"
    port: int = 50051
    max_workers: int = 10
    max_concurrent_streams: int = 100
    keepalive_time_ms: int = 30000
    keepalive_timeout_ms: int = 5000
    max_message_length: int = 4 * 1024 * 1024  # 4MB
    enable_reflection: bool = True
    enable_health_check: bool = True


class GRPCService(ABC):
    """Abstract base class for gRPC services"""

    def __init__(self, name: str, config: GRPCConfig = None):
        self.name = name
        self.config = config or GRPCConfig()
        self.server: Optional[aio.Server] = None
        self._running = False
        self.logger = logging.getLogger(f"grpc.{name}")
        self.metrics = get_metrics_collector()

        # Register metrics
        self._register_metrics()

    def _register_metrics(self):
        """Register gRPC service metrics"""
        self.metrics.create_counter(
            f"grpc_{self.name}_requests_total",
            f"Total gRPC requests for {self.name}"
        )
        self.metrics.create_histogram(
            f"grpc_{self.name}_request_duration_seconds",
            f"gRPC request duration for {self.name}",
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
        )
        self.metrics.create_counter(
            f"grpc_{self.name}_errors_total",
            f"Total gRPC errors for {self.name}"
        )

    @abstractmethod
    async def handle_request(self, request: RequestMessage) -> ResponseMessage:
        """Handle incoming gRPC request"""
        pass

    async def start(self) -> None:
        """Start the gRPC service"""
        try:
            self.server = aio.server(
                options=[
                    ('grpc.max_concurrent_streams', self.config.max_concurrent_streams),
                    ('grpc.keepalive_time_ms', self.config.keepalive_time_ms),
                    ('grpc.keepalive_timeout_ms', self.config.keepalive_timeout_ms),
                    ('grpc.max_message_length', self.config.max_message_length),
                    ('grpc.max_receive_message_length', self.config.max_message_length),
                    ('grpc.max_send_message_length', self.config.max_message_length),
                ]
            )

            # Add service implementations
            await self._add_services()

            # Start server
            address = f"{self.config.host}:{self.config.port}"
            self.server.add_insecure_port(address)
            await self.server.start()

            self._running = True
            self.logger.info(f"gRPC service {self.name} started on {address}")

        except Exception as e:
            self.logger.error(f"Failed to start gRPC service {self.name}: {e}")
            raise

    async def stop(self) -> None:
        """Stop the gRPC service"""
        if self.server:
            await self.server.stop(grace=5.0)
            self.server = None
        self._running = False
        self.logger.info(f"gRPC service {self.name} stopped")

    async def _add_services(self):
        """Add gRPC service implementations to server"""
        # Health check service
        if self.config.enable_health_check:
            health_servicer = HealthCheckServicer(self.name)
            health_pb2_grpc.add_HealthServicer_to_server(health_servicer, self.server)

        # Custom service implementation
        service_servicer = ServiceServicer(self)
        # In real implementation, this would be generated from proto files
        # For now, we'll use a generic implementation

    def is_running(self) -> bool:
        """Check if service is running"""
        return self._running


class ServiceServicer:
    """Generic gRPC service implementation"""

    def __init__(self, grpc_service: GRPCService):
        self.grpc_service = grpc_service

    async def CallService(self, request, context):
        """Handle service calls"""
        start_time = time.time()

        try:
            # Convert request to message
            req_msg = RequestMessage(request.data)

            # Handle request
            response_msg = await self.grpc_service.handle_request(req_msg)

            # Update metrics
            self.grpc_service.metrics.get_metric(f"grpc_{self.grpc_service.name}_requests_total").increment()
            duration = time.time() - start_time
            self.grpc_service.metrics.get_metric(f"grpc_{self.grpc_service.name}_request_duration_seconds").observe(duration)

            return response_msg.to_dict()

        except Exception as e:
            # Update error metrics
            self.grpc_service.metrics.get_metric(f"grpc_{self.grpc_service.name}_errors_total").increment()
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return {}


class HealthCheckServicer(health_pb2_grpc.HealthServicer):
    """Health check service implementation"""

    def __init__(self, service_name: str):
        self.service_name = service_name

    async def Check(self, request, context):
        """Health check implementation"""
        return health_pb2.HealthCheckResponse(
            status=health_pb2.HealthCheckResponse.SERVING
        )

    async def Watch(self, request, context):
        """Health check watch implementation"""
        while True:
            yield health_pb2.HealthCheckResponse(
                status=health_pb2.HealthCheckResponse.SERVING
            )
            await asyncio.sleep(30)  # Check every 30 seconds


class GRPCClient:
    """gRPC client for service communication"""

    def __init__(self, service_name: str, discovery: ServiceDiscovery = None):
        self.service_name = service_name
        self.discovery = discovery
        self.channel: Optional[aio.Channel] = None
        self.stub = None
        self.logger = logging.getLogger(f"grpc_client.{service_name}")
        self.metrics = get_metrics_collector()

        # Circuit breaker
        self._circuit_breaker_failures = 0
        self._circuit_breaker_last_failure = 0
        self._circuit_breaker_timeout = 60  # seconds
        self._circuit_breaker_threshold = 5

    async def connect(self, address: str = None) -> None:
        """Connect to gRPC service"""
        if address is None and self.discovery:
            # Discover service address
            instances = await self.discovery.discover_service(self.service_name)
            if not instances:
                raise ValueError(f"No instances found for service {self.service_name}")
            address = f"{instances[0]['address']}:{instances[0]['port']}"

        if not address:
            raise ValueError("No address provided and no service discovery configured")

        self.channel = aio.insecure_channel(address)
        # In real implementation, stub would be generated from proto
        # self.stub = ServiceStub(self.channel)

    async def disconnect(self) -> None:
        """Disconnect from service"""
        if self.channel:
            await self.channel.close()
            self.channel = None

    async def call_service(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Call remote service"""
        if not self.channel:
            raise ValueError("Client not connected")

        # Circuit breaker check
        if self._is_circuit_breaker_open():
            raise Exception("Circuit breaker is open")

        start_time = time.time()

        try:
            # In real implementation, this would use the generated stub
            # response = await self.stub.CallService(request_data)
            response = await self._make_request(request_data)

            # Update metrics
            duration = time.time() - start_time
            self.metrics.get_metric("grpc_client_request_duration_seconds").observe(duration)

            # Reset circuit breaker
            self._circuit_breaker_failures = 0

            return response

        except Exception as e:
            # Update circuit breaker
            self._circuit_breaker_failures += 1
            self._circuit_breaker_last_failure = time.time()

            # Update error metrics
            self.metrics.get_metric("grpc_client_errors_total").increment()

            raise e

    async def _make_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Make actual gRPC request"""
        # Placeholder implementation
        # In real implementation, this would use protocol buffers
        await asyncio.sleep(0.001)  # Simulate network latency
        return {"result": "success", "data": request_data}

    def _is_circuit_breaker_open(self) -> bool:
        """Check if circuit breaker is open"""
        if self._circuit_breaker_failures >= self._circuit_breaker_threshold:
            if time.time() - self._circuit_breaker_last_failure < self._circuit_breaker_timeout:
                return True
            else:
                # Reset after timeout
                self._circuit_breaker_failures = 0
        return False


class LoadBalancer:
    """Load balancer for gRPC services"""

    def __init__(self, service_name: str, discovery: ServiceDiscovery):
        self.service_name = service_name
        self.discovery = discovery
        self.clients: Dict[str, GRPCClient] = {}
        self._current_index = 0
        self.logger = logging.getLogger(f"load_balancer.{service_name}")

    async def get_client(self) -> GRPCClient:
        """Get next available client using round-robin"""
        instances = await self.discovery.discover_service(self.service_name)
        if not instances:
            raise ValueError(f"No instances available for {self.service_name}")

        # Round-robin selection
        instance = instances[self._current_index % len(instances)]
        self._current_index += 1

        address = f"{instance['address']}:{instance['port']}"
        if address not in self.clients:
            client = GRPCClient(self.service_name, self.discovery)
            await client.connect(address)
            self.clients[address] = client

        return self.clients[address]

    async def call_service(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Call service through load balancer"""
        client = await self.get_client()
        return await client.call_service(request_data)

    async def close(self) -> None:
        """Close all clients"""
        for client in self.clients.values():
            await client.disconnect()
        self.clients.clear()


class StreamingGRPCService(GRPCService):
    """gRPC service with streaming support"""

    async def handle_stream(self, request_iterator) -> AsyncGenerator[Dict[str, Any], None]:
        """Handle streaming requests"""
        async for request in request_iterator:
            try:
                req_msg = RequestMessage(request.data)
                response_msg = await self.handle_request(req_msg)
                yield response_msg.to_dict()
            except Exception as e:
                self.logger.error(f"Streaming error: {e}")
                yield {"error": str(e)}


# Service registry for managing multiple gRPC services
_service_registry: Dict[str, GRPCService] = {}

def register_grpc_service(service: GRPCService) -> None:
    """Register a gRPC service"""
    _service_registry[service.name] = service

def get_grpc_service(name: str) -> Optional[GRPCService]:
    """Get registered gRPC service"""
    return _service_registry.get(name)

async def start_all_grpc_services() -> None:
    """Start all registered gRPC services"""
    tasks = []
    for service in _service_registry.values():
        tasks.append(service.start())
    await asyncio.gather(*tasks)

async def stop_all_grpc_services() -> None:
    """Stop all registered gRPC services"""
    tasks = []
    for service in _service_registry.values():
        tasks.append(service.stop())
    await asyncio.gather(*tasks)

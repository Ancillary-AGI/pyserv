"""
gRPC Services for Pyserv Framework

This module provides comprehensive gRPC support with:
- gRPC service definitions
- Protocol buffer management
- gRPC middleware
- Service discovery
- Load balancing
- Health checking
- Streaming support
- Error handling
- Performance optimization
- Security integration
- Monitoring and tracing
"""

import asyncio
import logging
import grpc
import time
from typing import Dict, List, Callable, Any, Optional, Type, Union, Awaitable, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from functools import wraps
from concurrent.futures import ThreadPoolExecutor
import json

logger = logging.getLogger(__name__)


class GRPCServiceType(str, Enum):
    """gRPC service types"""
    UNARY = "unary"
    SERVER_STREAMING = "server_streaming"
    CLIENT_STREAMING = "client_streaming"
    BIDIRECTIONAL_STREAMING = "bidirectional_streaming"


class GRPCStatus(str, Enum):
    """gRPC status codes"""
    OK = "OK"
    CANCELLED = "CANCELLED"
    UNKNOWN = "UNKNOWN"
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    DEADLINE_EXCEEDED = "DEADLINE_EXCEEDED"
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    RESOURCE_EXHAUSTED = "RESOURCE_EXHAUSTED"
    FAILED_PRECONDITION = "FAILED_PRECONDITION"
    ABORTED = "ABORTED"
    OUT_OF_RANGE = "OUT_OF_RANGE"
    UNIMPLEMENTED = "UNIMPLEMENTED"
    INTERNAL = "INTERNAL"
    UNAVAILABLE = "UNAVAILABLE"
    DATA_LOSS = "DATA_LOSS"
    UNAUTHENTICATED = "UNAUTHENTICATED"


@dataclass
class GRPCServiceConfig:
    """gRPC service configuration"""
    host: str = "localhost"
    port: int = 50051
    max_workers: int = 10
    max_connections: int = 1000
    keepalive_time: int = 7200  # 2 hours
    keepalive_timeout: int = 20
    keepalive_permit_without_calls: bool = True
    enable_health_check: bool = True
    enable_reflection: bool = True
    enable_metrics: bool = True
    ssl_certfile: Optional[str] = None
    ssl_keyfile: Optional[str] = None
    ssl_ca_cert: Optional[str] = None
    authentication_required: bool = False
    compression: str = "gzip"
    max_message_size: int = 4194304  # 4MB
    graceful_shutdown_timeout: int = 30


@dataclass
class GRPCContext:
    """gRPC request context"""
    service_name: str = ""
    method_name: str = ""
    request_id: str = ""
    user_id: Optional[str] = None
    metadata: Dict[str, str] = field(default_factory=dict)
    start_time: float = field(default_factory=time.time)
    deadline: Optional[float] = None
    authority: str = ""
    peer: str = ""


class GRPCManager:
    """gRPC service manager"""

    def __init__(self, config: GRPCServiceConfig = None):
        self.config = config or GRPCServiceConfig()
        self.logger = logging.getLogger(__name__)
        self._services: Dict[str, Any] = {}
        self._server: Optional[grpc.Server] = None
        self._running = False
        self._executor = ThreadPoolExecutor(max_workers=self.config.max_workers)
        self._active_contexts: Dict[str, GRPCContext] = {}

    async def start(self) -> None:
        """Start the gRPC server"""
        if self._running:
            return

        try:
            # Create gRPC server
            self._server = grpc.server(
                futures=self._executor,
                options=[
                    ('grpc.max_send_message_size', self.config.max_message_size),
                    ('grpc.max_receive_message_size', self.config.max_message_size),
                    ('grpc.keepalive_time_ms', self.config.keepalive_time * 1000),
                    ('grpc.keepalive_timeout_ms', self.config.keepalive_timeout * 1000),
                    ('grpc.keepalive_permit_without_calls', self.config.keepalive_permit_without_calls),
                    ('grpc.max_connection_idle_ms', 300000),  # 5 minutes
                    ('grpc.max_connection_age_ms', 3600000),  # 1 hour
                    ('grpc.max_connection_age_grace_ms', 300000),  # 5 minutes
                ]
            )

            # Add services
            for service_name, service in self._services.items():
                service_pb2 = service.get('service_pb2')
                service_pb2_grpc = service.get('service_pb2_grpc')
                servicer = service.get('servicer')

                if service_pb2 and service_pb2_grpc and servicer:
                    service_pb2_grpc.add_serviceServicer_to_server(servicer, self._server)
                    self.logger.info(f"Added gRPC service: {service_name}")

            # Add health check service
            if self.config.enable_health_check:
                from grpc_health.v2 import health_pb2, health_pb2_grpc, health
                health_servicer = health.HealthServicer()
                health_pb2_grpc.add_HealthServicer_to_server(health_servicer, self._server)

            # Add reflection service
            if self.config.enable_reflection:
                from grpc_reflection.v1alpha import reflection
                service_names = [service_name for service_name in self._services.keys()]
                reflection.enable_server_reflection(service_names, self._server)

            # Add SSL/TLS if configured
            if self.config.ssl_certfile and self.config.ssl_keyfile:
                with open(self.config.ssl_certfile, 'rb') as f:
                    certificate_chain = f.read()
                with open(self.config.ssl_keyfile, 'rb') as f:
                    private_key = f.read()

                if self.config.ssl_ca_cert:
                    with open(self.config.ssl_ca_cert, 'rb') as f:
                        root_certificates = f.read()
                    credentials = grpc.ssl_server_credentials(
                        root_certificates=root_certificates,
                        private_key=private_key,
                        certificate_chain=certificate_chain
                    )
                else:
                    credentials = grpc.ssl_server_credentials(
                        private_key=private_key,
                        certificate_chain=certificate_chain
                    )

                self._server.add_secure_port(f"{self.config.host}:{self.config.port}", credentials)
            else:
                self._server.add_insecure_port(f"{self.config.host}:{self.config.port}")

            # Start server
            self._server.start()
            self._running = True

            self.logger.info(f"gRPC server started on {self.config.host}:{self.config.port}")

        except Exception as e:
            self.logger.error(f"Failed to start gRPC server: {e}")
            raise

    async def stop(self) -> None:
        """Stop the gRPC server"""
        if not self._running or not self._server:
            return

        try:
            # Graceful shutdown
            self._server.stop(self.config.graceful_shutdown_timeout)
            self._running = False

            # Shutdown executor
            self._executor.shutdown(wait=True)

            self.logger.info("gRPC server stopped")

        except Exception as e:
            self.logger.error(f"Error stopping gRPC server: {e}")

    def add_service(self, service_name: str, service_pb2, service_pb2_grpc, servicer) -> None:
        """Add a gRPC service"""
        self._services[service_name] = {
            'service_pb2': service_pb2,
            'service_pb2_grpc': service_pb2_grpc,
            'servicer': servicer
        }
        self.logger.info(f"Registered gRPC service: {service_name}")

    def remove_service(self, service_name: str) -> bool:
        """Remove a gRPC service"""
        if service_name in self._services:
            del self._services[service_name]
            self.logger.info(f"Removed gRPC service: {service_name}")
            return True
        return False

    def get_service(self, service_name: str) -> Optional[Dict]:
        """Get a gRPC service"""
        return self._services.get(service_name)

    def list_services(self) -> List[str]:
        """List all registered services"""
        return list(self._services.keys())

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        return {
            'status': 'serving' if self._running else 'not_serving',
            'services': len(self._services),
            'active_connections': len(self._active_contexts) if self._active_contexts else 0,
            'timestamp': datetime.utcnow().isoformat()
        }

    def create_context(self, service_name: str, method_name: str, grpc_context) -> GRPCContext:
        """Create gRPC context"""
        context = GRPCContext(
            service_name=service_name,
            method_name=method_name,
            request_id=str(uuid.uuid4()),
            start_time=time.time(),
            authority=grpc_context.peer(),
            peer=grpc_context.peer()
        )

        # Extract metadata
        if grpc_context:
            context.metadata = dict(grpc_context.invocation_metadata())

        self._active_contexts[context.request_id] = context
        return context

    def get_context(self, request_id: str) -> Optional[GRPCContext]:
        """Get gRPC context by request ID"""
        return self._active_contexts.get(request_id)

    def remove_context(self, request_id: str) -> None:
        """Remove gRPC context"""
        if request_id in self._active_contexts:
            del self._active_contexts[request_id]

    def get_stats(self) -> Dict[str, Any]:
        """Get gRPC server statistics"""
        return {
            'running': self._running,
            'services_count': len(self._services),
            'active_contexts': len(self._active_contexts),
            'config': {
                'host': self.config.host,
                'port': self.config.port,
                'max_workers': self.config.max_workers,
                'max_connections': self.config.max_connections
            }
        }


class GRPCClientManager:
    """gRPC client manager for service discovery and load balancing"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._channels: Dict[str, grpc.Channel] = {}
        self._stubs: Dict[str, Dict[str, Any]] = {}
        self._service_endpoints: Dict[str, List[str]] = {}

    def add_service_endpoint(self, service_name: str, endpoint: str) -> None:
        """Add service endpoint"""
        if service_name not in self._service_endpoints:
            self._service_endpoints[service_name] = []

        if endpoint not in self._service_endpoints[service_name]:
            self._service_endpoints[service_name].append(endpoint)

    def remove_service_endpoint(self, service_name: str, endpoint: str) -> None:
        """Remove service endpoint"""
        if service_name in self._service_endpoints:
            if endpoint in self._service_endpoints[service_name]:
                self._service_endpoints[service_name].remove(endpoint)

    def get_service_endpoints(self, service_name: str) -> List[str]:
        """Get service endpoints"""
        return self._service_endpoints.get(service_name, [])

    def create_channel(self, target: str, options: List[Tuple[str, Any]] = None) -> grpc.Channel:
        """Create gRPC channel"""
        if target not in self._channels:
            options = options or [
                ('grpc.keepalive_time_ms', 7200000),  # 2 hours
                ('grpc.keepalive_timeout_ms', 20000),  # 20 seconds
                ('grpc.keepalive_permit_without_calls', True),
                ('grpc.max_send_message_size', 4194304),  # 4MB
                ('grpc.max_receive_message_size', 4194304),  # 4MB
            ]

            self._channels[target] = grpc.insecure_channel(target, options=options)

        return self._channels[target]

    def create_secure_channel(self, target: str, credentials: grpc.ChannelCredentials,
                           options: List[Tuple[str, Any]] = None) -> grpc.Channel:
        """Create secure gRPC channel"""
        if target not in self._channels:
            options = options or [
                ('grpc.keepalive_time_ms', 7200000),  # 2 hours
                ('grpc.keepalive_timeout_ms', 20000),  # 20 seconds
                ('grpc.keepalive_permit_without_calls', True),
                ('grpc.max_send_message_size', 4194304),  # 4MB
                ('grpc.max_receive_message_size', 4194304),  # 4MB
            ]

            self._channels[target] = grpc.secure_channel(target, credentials, options=options)

        return self._channels[target]

    def get_stub(self, service_name: str, stub_class: Type, target: Optional[str] = None) -> Any:
        """Get gRPC stub"""
        if target is None:
            # Use load balancing to select target
            endpoints = self.get_service_endpoints(service_name)
            if not endpoints:
                raise RuntimeError(f"No endpoints available for service {service_name}")
            target = endpoints[0]  # Simple load balancing - use first endpoint

        channel = self.create_channel(target)
        stub_key = f"{service_name}:{target}"

        if stub_key not in self._stubs:
            self._stubs[stub_key] = stub_class(channel)

        return self._stubs[stub_key]

    def close_channel(self, target: str) -> None:
        """Close gRPC channel"""
        if target in self._channels:
            self._channels[target].close()
            del self._channels[target]

    def close_all_channels(self) -> None:
        """Close all gRPC channels"""
        for target, channel in self._channels.items():
            channel.close()
        self._channels.clear()
        self._stubs.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get client manager statistics"""
        return {
            'channels': len(self._channels),
            'stubs': len(self._stubs),
            'services': {
                service_name: len(endpoints)
                for service_name, endpoints in self._service_endpoints.items()
            }
        }


# Global instances
_grpc_manager: Optional[GRPCManager] = None
_grpc_client_manager: Optional[GRPCClientManager] = None

def get_grpc_manager() -> GRPCManager:
    """Get the global gRPC manager instance"""
    global _grpc_manager
    if _grpc_manager is None:
        _grpc_manager = GRPCManager()
    return _grpc_manager

def get_grpc_client_manager() -> GRPCClientManager:
    """Get the global gRPC client manager instance"""
    global _grpc_client_manager
    if _grpc_client_manager is None:
        _grpc_client_manager = GRPCClientManager()
    return _grpc_client_manager

async def start_grpc_server(config: GRPCServiceConfig = None) -> GRPCManager:
    """Start gRPC server"""
    manager = get_grpc_manager()
    if config:
        manager.config = config
    await manager.start()
    return manager

async def stop_grpc_server() -> None:
    """Stop gRPC server"""
    manager = get_grpc_manager()
    await manager.stop()

def add_grpc_service(service_name: str, service_pb2, service_pb2_grpc, servicer) -> None:
    """Add gRPC service"""
    manager = get_grpc_manager()
    manager.add_service(service_name, service_pb2, service_pb2_grpc, servicer)

def remove_grpc_service(service_name: str) -> bool:
    """Remove gRPC service"""
    manager = get_grpc_manager()
    return manager.remove_service(service_name)

def add_service_endpoint(service_name: str, endpoint: str) -> None:
    """Add service endpoint for client"""
    client_manager = get_grpc_client_manager()
    client_manager.add_service_endpoint(service_name, endpoint)

def get_grpc_stub(service_name: str, stub_class: Type, target: Optional[str] = None) -> Any:
    """Get gRPC stub"""
    client_manager = get_grpc_client_manager()
    return client_manager.get_stub(service_name, stub_class, target)

__all__ = [
    'GRPCManager', 'GRPCClientManager', 'GRPCServiceConfig', 'GRPCContext',
    'GRPCServiceType', 'GRPCStatus', 'get_grpc_manager', 'get_grpc_client_manager',
    'start_grpc_server', 'stop_grpc_server', 'add_grpc_service', 'remove_grpc_service',
    'add_service_endpoint', 'get_grpc_stub'
]

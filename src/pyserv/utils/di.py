"""
Elegant Dependency Injection Container for Pyserv framework.

Provides clean, efficient service registration, resolution, and dependency management.

Features:
- Constructor injection with automatic dependency resolution
- Singleton, transient, and scoped service lifetimes
- Factory functions and custom providers
- Lazy initialization and circular dependency detection
- Async support for service initialization
- Service decorators and metadata
- Thread-safe operations
"""

import asyncio
import inspect
import logging
import threading
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Set, Type, Union

from pyserv.exceptions import DependencyInjectionException

logger = logging.getLogger(__name__)


class ServiceLifetime(Enum):
    """Service lifetime options."""
    TRANSIENT = "transient"  # New instance each time
    SINGLETON = "singleton"  # Single instance shared
    SCOPED = "scoped"       # Instance per scope


@dataclass
class ServiceDescriptor:
    """Service registration descriptor."""
    service_type: Type[Any]
    implementation_type: Optional[Type[Any]] = None
    factory: Optional[Callable[[], Any]] = None
    instance: Optional[Any] = None
    lifetime: ServiceLifetime = ServiceLifetime.SINGLETON
    metadata: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[Type[Any]] = field(default_factory=list)


@dataclass
class ServiceScope:
    """Service scope for scoped services."""
    scope_id: str
    services: Dict[Type[Any], Any] = field(default_factory=dict)
    parent: Optional['ServiceScope'] = None

    def get_service(self, service_type: Type[Any]) -> Optional[Any]:
        """Get service from current scope or parent scopes."""
        if service_type in self.services:
            return self.services[service_type]
        if self.parent:
            return self.parent.get_service(service_type)
        return None

    def set_service(self, service_type: Type[Any], instance: Any) -> None:
        """Set service in current scope."""
        self.services[service_type] = instance


class Container:
    """
    Advanced dependency injection container with full production features.

    Features:
    - Constructor injection with automatic dependency resolution
    - Singleton, transient, and scoped service lifetimes
    - Factory functions and custom providers
    - Lazy initialization and circular dependency detection
    - Async support for service initialization
    - Service decorators and metadata
    - Thread-safe operations
    """

    def __init__(self) -> None:
        self._services: Dict[Type[Any], ServiceDescriptor] = {}
        self._singletons: Dict[Type[Any], Any] = {}
        self._scoped_services: Dict[str, Dict[Type[Any], Any]] = {}
        self._resolving: Set[Type[Any]] = set()
        self._lock = threading.RLock()
        self._performance_stats: Dict[str, float] = {}
        self._root_scope = ServiceScope("root")

    def register(
        self,
        service_type: Type[Any],
        implementation_type: Optional[Type[Any]] = None,
        factory: Optional[Callable[[], Any]] = None,
        instance: Optional[Any] = None,
        lifetime: ServiceLifetime = ServiceLifetime.SINGLETON,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Register a service in the container.

        Args:
            service_type: The service interface/type
            implementation_type: The concrete implementation class
            factory: Factory function to create instances
            instance: Pre-created instance
            lifetime: Service lifetime (singleton, transient, scoped)
            metadata: Additional service metadata
        """
        if implementation_type is None and factory is None and instance is None:
            implementation_type = service_type

        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation_type=implementation_type,
            factory=factory,
            instance=instance,
            lifetime=lifetime,
            metadata=metadata or {},
        )

        with self._lock:
            self._services[service_type] = descriptor

    def register_singleton(
        self,
        service_type: Type[Any],
        instance: Optional[Any] = None,
        implementation_type: Optional[Type[Any]] = None,
    ) -> None:
        """Register a singleton service."""
        if instance is not None:
            self.register(service_type=service_type, instance=instance, lifetime=ServiceLifetime.SINGLETON)
        elif implementation_type is not None:
            self.register(service_type=service_type, implementation_type=implementation_type, lifetime=ServiceLifetime.SINGLETON)
        else:
            self.register(service_type=service_type, lifetime=ServiceLifetime.SINGLETON)

    def register_transient(
        self,
        service_type: Type[Any],
        implementation_type: Optional[Type[Any]] = None,
        factory: Optional[Callable[[], Any]] = None,
    ) -> None:
        """Register a transient service (new instance each time)."""
        self.register(
            service_type=service_type,
            implementation_type=implementation_type,
            factory=factory,
            lifetime=ServiceLifetime.TRANSIENT,
        )

    def register_scoped(
        self,
        service_type: Type[Any],
        implementation_type: Optional[Type[Any]] = None,
        factory: Optional[Callable[[], Any]] = None,
    ) -> None:
        """Register a scoped service (instance per scope)."""
        self.register(
            service_type=service_type,
            implementation_type=implementation_type,
            factory=factory,
            lifetime=ServiceLifetime.SCOPED,
        )

    def get(self, service_type: Type[Any], scope_id: str = "root") -> Any:
        """Resolve a service from the container."""
        start_time = time.time()

        try:
            with self._lock:
                # Check for circular dependencies
                if service_type in self._resolving:
                    raise DependencyInjectionException(f"Circular dependency detected for {service_type}")
                self._resolving.add(service_type)

            # Check singleton cache first
            if service_type in self._singletons:
                return self._singletons[service_type]

            # Get service descriptor
            descriptor = self._services.get(service_type)
            if not descriptor:
                raise DependencyInjectionException(f"Service {service_type} not registered")

            # Handle different lifetimes
            if descriptor.lifetime == ServiceLifetime.SINGLETON:
                if service_type not in self._singletons:
                    instance = self._create_instance(descriptor)
                    self._singletons[service_type] = instance
                return self._singletons[service_type]

            elif descriptor.lifetime == ServiceLifetime.SCOPED:
                scope = self._get_or_create_scope(scope_id)
                if service_type not in scope.services:
                    instance = self._create_instance(descriptor)
                    scope.services[service_type] = instance
                return scope.services[service_type]

            else:  # TRANSIENT
                return self._create_instance(descriptor)

        finally:
            with self._lock:
                self._resolving.discard(service_type)

            # Track performance
            elapsed = time.time() - start_time
            self._performance_stats[f"resolve_{service_type.__name__}"] = elapsed

    def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        """Create a service instance."""
        if descriptor.instance is not None:
            return descriptor.instance
        if descriptor.factory is not None:
            return descriptor.factory()
        if descriptor.implementation_type is not None:
            return self._instantiate(descriptor.implementation_type)
        raise DependencyInjectionException(f"No way to create instance for {descriptor.service_type}")

    def _instantiate(self, cls: Type[Any]) -> Any:
        """Instantiate a class with dependency injection."""
        # Get constructor parameters
        init_signature = inspect.signature(cls.__init__)
        params: Dict[str, Any] = {}

        for param_name, param in init_signature.parameters.items():
            if param_name == "self":
                continue

            # Try to resolve parameter from container
            if param.annotation != inspect.Parameter.empty:
                try:
                    params[param_name] = self.get(param.annotation)
                except DependencyInjectionException:
                    # If resolution fails, use default or skip
                    if param.default != inspect.Parameter.empty:
                        params[param_name] = param.default
                    else:
                        raise
            elif param.default != inspect.Parameter.empty:
                params[param_name] = param.default
            else:
                raise DependencyInjectionException(f"Cannot resolve parameter {param_name} for {cls}")

        return cls(**params)

    def _get_or_create_scope(self, scope_id: str) -> ServiceScope:
        """Get or create a service scope."""
        if scope_id not in self._scoped_services:
            self._scoped_services[scope_id] = ServiceScope(scope_id, parent=self._root_scope)
        return self._scoped_services[scope_id]

    def create_scope(self, scope_id: str) -> ServiceScope:
        """Create a new service scope."""
        return ServiceScope(scope_id, parent=self._root_scope)

    def has(self, service_type: Type[Any]) -> bool:
        """Check if a service type is registered."""
        return service_type in self._services

    def get_service_descriptor(self, service_type: Type[Any]) -> Optional[ServiceDescriptor]:
        """Get service descriptor."""
        return self._services.get(service_type)

    def get_all_services(self) -> Dict[Type[Any], ServiceDescriptor]:
        """Get all registered services."""
        return self._services.copy()

    def clear(self) -> None:
        """Clear all registered services and instances."""
        with self._lock:
            self._services.clear()
            self._singletons.clear()
            self._scoped_services.clear()
            self._resolving.clear()

    def clear_scope(self, scope_id: str) -> None:
        """Clear a specific scope."""
        if scope_id in self._scoped_services:
            del self._scoped_services[scope_id]

    def get_performance_stats(self) -> Dict[str, float]:
        """Get performance statistics."""
        return self._performance_stats.copy()

    async def initialize_async_services(self) -> None:
        """Initialize all async services."""
        async_tasks = []

        for service_type, descriptor in self._services.items():
            if descriptor.implementation_type and hasattr(descriptor.implementation_type, '__ainit__'):
                async_tasks.append(self._initialize_service_async(service_type))

        if async_tasks:
            await asyncio.gather(*async_tasks)

    async def _initialize_service_async(self, service_type: Type[Any]) -> None:
        """Initialize a single async service."""
        try:
            instance = self.get(service_type)
            if hasattr(instance, '__ainit__'):
                await instance.__ainit__()
        except Exception as e:
            logger.error(f"Failed to initialize async service {service_type}: {e}")
            raise


# Global container instance
container = Container()


def inject(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to inject dependencies into functions."""
    sig = inspect.signature(func)
    is_async = inspect.iscoroutinefunction(func)

    @wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        # Inject dependencies for parameters not already provided
        for param_name, param in sig.parameters.items():
            if param_name not in kwargs and param.annotation != inspect.Parameter.empty:
                try:
                    kwargs[param_name] = container.get(param.annotation)
                except DependencyInjectionException:
                    pass  # Skip if dependency cannot be resolved
        return func(*args, **kwargs)

    @wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        # Inject dependencies for parameters not already provided
        for param_name, param in sig.parameters.items():
            if param_name not in kwargs and param.annotation != inspect.Parameter.empty:
                try:
                    kwargs[param_name] = container.get(param.annotation)
                except DependencyInjectionException:
                    pass  # Skip if dependency cannot be resolved
        return await func(*args, **kwargs)

    return async_wrapper if is_async else sync_wrapper


# Service decorators
def service(lifetime: ServiceLifetime = ServiceLifetime.SINGLETON) -> Callable[[Type[Any]], Type[Any]]:
    """Decorator to register a class as a service."""
    def decorator(cls: Type[Any]) -> Type[Any]:
        container.register(cls, lifetime=lifetime)
        return cls
    return decorator


def singleton_service(cls: Type[Any]) -> Type[Any]:
    """Decorator to register a class as a singleton service."""
    container.register_singleton(cls)
    return cls


def transient_service(cls: Type[Any]) -> Type[Any]:
    """Decorator to register a class as a transient service."""
    container.register_transient(cls)
    return cls


def scoped_service(cls: Type[Any]) -> Type[Any]:
    """Decorator to register a class as a scoped service."""
    container.register_scoped(cls)
    return cls


# Context manager for scoped services
@asynccontextmanager
async def service_scope(scope_id: Optional[str] = None) -> Any:
    """Context manager for scoped services."""
    if scope_id is None:
        scope_id = f"scope_{threading.current_thread().ident}_{id(asyncio.current_task())}"

    scope = container.create_scope(scope_id)
    try:
        yield scope
    finally:
        container.clear_scope(scope_id)


# Service discovery and health checks
def get_service_health() -> Dict[str, Any]:
    """Get health status of all registered services."""
    health_info = {
        "total_services": len(container.get_all_services()),
        "singletons": len(container._singletons),
        "performance_stats": container.get_performance_stats(),
        "services": {}
    }

    for service_type, descriptor in container.get_all_services().items():
        service_info = {
            "type": service_type.__name__,
            "lifetime": descriptor.lifetime.value,
            "implementation": descriptor.implementation_type.__name__ if descriptor.implementation_type else None,
            "has_factory": descriptor.factory is not None,
            "has_instance": descriptor.instance is not None,
            "metadata": descriptor.metadata
        }
        health_info["services"][service_type.__name__] = service_info

    return health_info


def is_service_healthy(service_type: Type[Any]) -> bool:
    """Check if a specific service is healthy."""
    try:
        instance = container.get(service_type)
        # Check if service has a health check method
        if hasattr(instance, 'health_check'):
            return instance.health_check()
        return True
    except Exception:
        return False


# Service metadata utilities
def with_metadata(**metadata: Any) -> Callable[[Type[Any]], Type[Any]]:
    """Decorator to add metadata to a service."""
    def decorator(service_class: Type[Any]) -> Type[Any]:
        if not hasattr(service_class, '_service_metadata'):
            service_class._service_metadata = {}
        service_class._service_metadata.update(metadata)
        return service_class
    return decorator


def get_service_metadata(service_type: Type[Any]) -> Dict[str, Any]:
    """Get metadata for a service."""
    descriptor = container.get_service_descriptor(service_type)
    if descriptor:
        return descriptor.metadata
    return {}


# Performance monitoring
def get_container_stats() -> Dict[str, Any]:
    """Get container performance statistics."""
    return {
        "performance_stats": container.get_performance_stats(),
        "service_count": len(container.get_all_services()),
        "singleton_count": len(container._singletons),
        "scope_count": len(container._scoped_services),
        "health": get_service_health()
    }


# Migration utilities for backward compatibility
def register_service(
    service_type: Type[Any],
    implementation: Optional[Type[Any]] = None,
    factory: Optional[Callable[[], Any]] = None,
    singleton: bool = True,
) -> None:
    """Legacy method for backward compatibility."""
    lifetime = ServiceLifetime.SINGLETON if singleton else ServiceLifetime.TRANSIENT
    container.register(service_type, implementation, factory, lifetime=lifetime)


# Export all public API
__all__ = [
    # Core classes
    'Container',
    'ServiceLifetime',
    'ServiceDescriptor',
    'ServiceScope',

    # Registration methods
    'register',
    'register_singleton',
    'register_transient',
    'register_scoped',
    'register_service',  # Legacy

    # Resolution methods
    'get',
    'has',
    'get_service_descriptor',
    'get_all_services',

    # Decorators
    'service',
    'singleton_service',
    'transient_service',
    'scoped_service',
    'inject',
    'with_metadata',

    # Context managers
    'service_scope',

    # Utilities
    'get_service_health',
    'is_service_healthy',
    'get_service_metadata',
    'get_container_stats',

    # Global container instance
    'container',
]

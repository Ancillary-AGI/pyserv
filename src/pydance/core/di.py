"""
PyDance Core DI - Lightweight dependency injection container.
"""

import inspect
from typing import Dict, Any, Callable, Type, Optional, List
from functools import wraps


class Container:
    """
    Lightweight dependency injection container.

    Features:
    - Constructor injection
    - Singleton and transient services
    - Factory functions
    - Lazy resolution
    """

    def __init__(self):
        self._services: Dict[Type, Dict[str, Any]] = {}
        self._singletons: Dict[Type, Any] = {}

    def register(self, service_type: Type, implementation: Optional[Type] = None,
                 factory: Optional[Callable] = None, singleton: bool = True) -> None:
        """
        Register a service in the container.

        Args:
            service_type: The service interface/type
            implementation: The concrete implementation class
            factory: Factory function to create instances
            singleton: Whether to create singleton instances
        """
        if implementation is None and factory is None:
            implementation = service_type

        self._services[service_type] = {
            "implementation": implementation,
            "factory": factory,
            "singleton": singleton
        }

    def register_singleton(self, service_type: Type, instance: Any) -> None:
        """Register a singleton instance directly."""
        self._singletons[service_type] = instance

    def resolve(self, service_type: Type) -> Any:
        """
        Resolve a service from the container.

        Args:
            service_type: The service type to resolve

        Returns:
            Service instance
        """
        # Check for singleton instances first
        if service_type in self._singletons:
            return self._singletons[service_type]

        # Check registered services
        if service_type not in self._services:
            # Try to instantiate directly if it's a concrete class
            if inspect.isclass(service_type):
                return self._instantiate(service_type)
            raise ValueError(f"Service {service_type} not registered")

        service_info = self._services[service_type]

        if service_info["singleton"] and service_type in self._singletons:
            return self._singletons[service_type]

        # Use factory if provided
        if service_info["factory"]:
            instance = service_info["factory"]()
        else:
            implementation = service_info["implementation"]
            instance = self._instantiate(implementation)

        # Cache singleton instances
        if service_info["singleton"]:
            self._singletons[service_type] = instance

        return instance

    def _instantiate(self, cls: Type) -> Any:
        """Instantiate a class with dependency injection."""
        # Get constructor parameters
        init_signature = inspect.signature(cls.__init__)
        params = {}

        for param_name, param in init_signature.parameters.items():
            if param_name == "self":
                continue

            # Try to resolve parameter from container
            if param.annotation != inspect.Parameter.empty:
                try:
                    params[param_name] = self.resolve(param.annotation)
                except ValueError:
                    # If resolution fails, use default or skip
                    if param.default != inspect.Parameter.empty:
                        params[param_name] = param.default
                    else:
                        raise
            elif param.default != inspect.Parameter.empty:
                params[param_name] = param.default
            else:
                raise ValueError(f"Cannot resolve parameter {param_name} for {cls}")

        return cls(**params)

    def resolve_handler(self, handler: Callable) -> Callable:
        """
        Resolve dependencies for a handler function.

        This is a simple implementation that could be enhanced
        with more sophisticated parameter injection.
        """
        return handler


# Example services for common use cases

class DatabaseService:
    """Example database service."""
    def __init__(self, connection_string: str = "sqlite:///default.db"):
        self.connection_string = connection_string

    async def connect(self):
        print(f"Connecting to {self.connection_string}")

    async def disconnect(self):
        print("Disconnecting from database")


class CacheService:
    """Example cache service."""
    def __init__(self, ttl: int = 300):
        self.ttl = ttl
        self._cache = {}

    def get(self, key: str) -> Any:
        return self._cache.get(key)

    def set(self, key: str, value: Any) -> None:
        self._cache[key] = value


class LoggerService:
    """Example logger service."""
    def __init__(self, level: str = "INFO"):
        self.level = level

    def log(self, message: str, level: str = "INFO") -> None:
        print(f"[{level}] {message}")


def setup_default_services(container: Container) -> None:
    """Setup default services in container."""
    container.register(DatabaseService, singleton=True)
    container.register(CacheService, singleton=True)
    container.register(LoggerService, singleton=True)

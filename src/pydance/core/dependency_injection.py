"""
Dependency Injection Container for PyDance framework.
Provides service registration, resolution, and dependency management.
"""

from typing import Type, Any, Dict, get_type_hints, Callable
from .exceptions import DependencyInjectionException


class Container:
    """Dependency injection container"""

    def __init__(self):
        self._services: Dict[Type, Any] = {}
        self._instances: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable] = {}
        self._singletons: set = set()

    def register(self, service_type: Type, implementation: Any = None, singleton: bool = True):
        """Register a service with the container"""
        if implementation is None:
            implementation = service_type

        self._services[service_type] = implementation

        if singleton:
            self._singletons.add(service_type)

    def register_factory(self, service_type: Type, factory: Callable, singleton: bool = True):
        """Register a factory function for service creation"""
        self._factories[service_type] = factory

        if singleton:
            self._singletons.add(service_type)

    def register_instance(self, service_type: Type, instance: Any):
        """Register a pre-created instance"""
        self._instances[service_type] = instance

    def get(self, service_type: Type) -> Any:
        """Resolve a service from the container"""
        # Return existing instance if it's a singleton
        if service_type in self._instances:
            return self._instances[service_type]

        # Check if it's registered
        if service_type not in self._services and service_type not in self._factories:
            raise DependencyInjectionException(f"Service {service_type} not registered")

        # Use factory if available
        if service_type in self._factories:
            instance = self._factories[service_type]()
        else:
            implementation = self._services[service_type]

            # If it's a class, instantiate it with dependencies
            if isinstance(implementation, type):
                instance = self._instantiate(implementation)
            else:
                # If it's already an instance or a function
                instance = implementation

        # Store singleton instances
        if service_type in self._singletons:
            self._instances[service_type] = instance

        return instance

    def _instantiate(self, cls: Type) -> Any:
        """Instantiate a class with dependency injection"""
        try:
            # Get constructor parameters with type hints
            constructor_params = get_type_hints(cls.__init__)

            # Filter out 'self' and 'return'
            dependencies = {}
            for param_name, param_type in constructor_params.items():
                if param_name in ('return', 'self'):
                    continue
                try:
                    dependencies[param_name] = self.get(param_type)
                except DependencyInjectionException:
                    raise DependencyInjectionException(
                        f"Cannot resolve dependency {param_name}: {param_type} for class {cls}"
                    )

            return cls(**dependencies)

        except Exception as e:
            raise DependencyInjectionException(f"Failed to instantiate {cls}: {str(e)}")

    def has(self, service_type: Type) -> bool:
        """Check if a service type is registered"""
        return (service_type in self._services or
                service_type in self._factories or
                service_type in self._instances)

    def clear(self):
        """Clear all registered services and instances"""
        self._services.clear()
        self._instances.clear()
        self._factories.clear()
        self._singletons.clear()


# Global container instance
container = Container()


def inject(func: Callable) -> Callable:
    """Decorator to inject dependencies into functions"""
    async def wrapper(*args, **kwargs):
        # Get function signature
        import inspect
        sig = inspect.signature(func)

        # Inject dependencies for parameters not already provided
        for param_name, param in sig.parameters.items():
            if param_name not in kwargs and param.annotation != inspect.Parameter.empty:
                try:
                    kwargs[param_name] = container.get(param.annotation)
                except DependencyInjectionException:
                    pass  # Skip if dependency cannot be resolved

        return await func(*args, **kwargs) if inspect.iscoroutinefunction(func) else func(*args, **kwargs)

    return wrapper

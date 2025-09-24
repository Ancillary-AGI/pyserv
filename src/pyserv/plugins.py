"""
Plugin System for Pyserv Framework

This module provides a comprehensive plugin system that allows extending
the framework functionality through plugins. Plugins can add new features,
modify existing behavior, and integrate with third-party services.

Key Features:
- Plugin discovery and loading
- Plugin lifecycle management
- Plugin dependency management
- Plugin configuration
- Plugin isolation and sandboxing
- Plugin event integration
- Plugin API for framework extension
"""

import asyncio
import importlib
import inspect
import logging
import pkgutil
import sys
from typing import Dict, List, Callable, Any, Optional, Type, Union, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class PluginState(str, Enum):
    """Plugin states"""
    UNLOADED = "unloaded"
    LOADED = "loaded"
    INITIALIZED = "initialized"
    STARTED = "started"
    STOPPED = "stopped"
    ERROR = "error"


class PluginPriority(int, Enum):
    """Plugin priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class PluginMetadata:
    """Plugin metadata"""
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    dependencies: List[str] = field(default_factory=list)
    hooks: List[str] = field(default_factory=list)
    config_schema: Dict[str, Any] = field(default_factory=dict)
    capabilities: List[str] = field(default_factory=list)


@dataclass
class PluginContext:
    """Plugin execution context"""
    app: Any
    config: Dict[str, Any] = field(default_factory=dict)
    services: Dict[str, Any] = field(default_factory=dict)
    event_bus: Any = None
    logger: logging.Logger = None

    def get_service(self, service_type: Type) -> Any:
        """Get a service from the context"""
        return self.services.get(service_type.__name__)

    def register_service(self, service_type: Type, instance: Any) -> None:
        """Register a service in the context"""
        self.services[service_type.__name__] = instance


class Plugin:
    """Base plugin class"""

    def __init__(self, metadata: PluginMetadata):
        self.metadata = metadata
        self.state = PluginState.UNLOADED
        self.context: Optional[PluginContext] = None
        self._hooks: Dict[str, List[Callable]] = {}
        self._error: Optional[Exception] = None

    async def load(self, context: PluginContext) -> None:
        """Load the plugin"""
        try:
            self.context = context
            self.state = PluginState.LOADED
            logger.info(f"Plugin {self.metadata.name} loaded")
        except Exception as e:
            self.state = PluginState.ERROR
            self._error = e
            logger.error(f"Failed to load plugin {self.metadata.name}: {e}")
            raise

    async def initialize(self) -> None:
        """Initialize the plugin"""
        try:
            if self.state != PluginState.LOADED:
                raise RuntimeError(f"Plugin {self.metadata.name} must be loaded before initialization")

            await self.on_initialize()
            self.state = PluginState.INITIALIZED
            logger.info(f"Plugin {self.metadata.name} initialized")
        except Exception as e:
            self.state = PluginState.ERROR
            self._error = e
            logger.error(f"Failed to initialize plugin {self.metadata.name}: {e}")
            raise

    async def start(self) -> None:
        """Start the plugin"""
        try:
            if self.state != PluginState.INITIALIZED:
                raise RuntimeError(f"Plugin {self.metadata.name} must be initialized before starting")

            await self.on_start()
            self.state = PluginState.STARTED
            logger.info(f"Plugin {self.metadata.name} started")
        except Exception as e:
            self.state = PluginState.ERROR
            self._error = e
            logger.error(f"Failed to start plugin {self.metadata.name}: {e}")
            raise

    async def stop(self) -> None:
        """Stop the plugin"""
        try:
            if self.state == PluginState.STARTED:
                await self.on_stop()
            self.state = PluginState.STOPPED
            logger.info(f"Plugin {self.metadata.name} stopped")
        except Exception as e:
            logger.error(f"Error stopping plugin {self.metadata.name}: {e}")

    async def unload(self) -> None:
        """Unload the plugin"""
        try:
            if self.state != PluginState.STOPPED:
                await self.stop()
            await self.on_unload()
            self.state = PluginState.UNLOADED
            logger.info(f"Plugin {self.metadata.name} unloaded")
        except Exception as e:
            logger.error(f"Error unloading plugin {self.metadata.name}: {e}")

    # Plugin lifecycle hooks (to be overridden by subclasses)
    async def on_initialize(self) -> None:
        """Called during plugin initialization"""
        pass

    async def on_start(self) -> None:
        """Called when plugin is started"""
        pass

    async def on_stop(self) -> None:
        """Called when plugin is stopped"""
        pass

    async def on_unload(self) -> None:
        """Called when plugin is unloaded"""
        pass

    def register_hook(self, hook_name: str, handler: Callable) -> None:
        """Register a hook handler"""
        if hook_name not in self._hooks:
            self._hooks[hook_name] = []
        self._hooks[hook_name].append(handler)

    async def call_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """Call all handlers for a hook"""
        if hook_name not in self._hooks:
            return []

        results = []
        for handler in self._hooks[hook_name]:
            try:
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(*args, **kwargs)
                else:
                    result = handler(*args, **kwargs)
                results.append(result)
            except Exception as e:
                logger.error(f"Error in hook {hook_name} handler: {e}")

        return results

    def get_config(self, key: str, default: Any = None) -> Any:
        """Get plugin configuration"""
        if self.context:
            return self.context.config.get(key, default)
        return default

    def set_config(self, key: str, value: Any) -> None:
        """Set plugin configuration"""
        if self.context:
            self.context.config[key] = value


class PluginManager:
    """Plugin manager for loading and managing plugins"""

    def __init__(self, plugin_dirs: List[str] = None):
        self.plugin_dirs = plugin_dirs or ["plugins"]
        self.plugins: Dict[str, Plugin] = {}
        self.plugin_states: Dict[str, PluginState] = {}
        self.dependencies: Dict[str, List[str]] = {}
        self._plugin_load_order: List[str] = []
        self._running = False

    async def start(self) -> None:
        """Start the plugin manager"""
        if self._running:
            return

        self._running = True

        # Discover plugins
        await self.discover_plugins()

        # Load plugins in dependency order
        await self.load_plugins()

        logger.info("Plugin manager started")

    async def stop(self) -> None:
        """Stop the plugin manager"""
        if not self._running:
            return

        self._running = False

        # Stop plugins in reverse order
        for plugin_name in reversed(self._plugin_load_order):
            if plugin_name in self.plugins:
                await self.plugins[plugin_name].stop()

        logger.info("Plugin manager stopped")

    async def discover_plugins(self) -> None:
        """Discover available plugins"""
        for plugin_dir in self.plugin_dirs:
            await self._discover_plugins_in_dir(plugin_dir)

        # Also discover built-in plugins
        await self._discover_builtin_plugins()

    async def _discover_plugins_in_dir(self, plugin_dir: str) -> None:
        """Discover plugins in a specific directory"""
        try:
            path = Path(plugin_dir)
            if not path.exists():
                return

            for item in path.iterdir():
                if item.is_dir() and (item / "__init__.py").exists():
                    await self._load_plugin_from_dir(item)
                elif item.is_file() and item.suffix == ".py":
                    await self._load_plugin_from_file(item)

        except Exception as e:
            logger.error(f"Error discovering plugins in {plugin_dir}: {e}")

    async def _discover_builtin_plugins(self) -> None:
        """Discover built-in plugins"""
        # This would scan for plugins in the pyserv.plugins package
        pass

    async def _load_plugin_from_dir(self, plugin_path: Path) -> None:
        """Load plugin from directory"""
        try:
            plugin_name = plugin_path.name

            # Check if plugin already loaded
            if plugin_name in self.plugins:
                return

            # Import the plugin module
            module_name = f"plugins.{plugin_name}"
            spec = importlib.util.spec_from_file_location(module_name, plugin_path / "__init__.py")
            if spec is None or spec.loader is None:
                return

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Find plugin class
            plugin_class = None
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and
                    issubclass(obj, Plugin) and
                    obj != Plugin):
                    plugin_class = obj
                    break

            if plugin_class is None:
                logger.warning(f"No plugin class found in {plugin_name}")
                return

            # Create plugin instance
            metadata = PluginMetadata(name=plugin_name)
            plugin = plugin_class(metadata)

            self.plugins[plugin_name] = plugin
            logger.info(f"Discovered plugin: {plugin_name}")

        except Exception as e:
            logger.error(f"Error loading plugin from {plugin_path}: {e}")

    async def _load_plugin_from_file(self, plugin_file: Path) -> None:
        """Load plugin from file"""
        try:
            plugin_name = plugin_file.stem

            # Check if plugin already loaded
            if plugin_name in self.plugins:
                return

            # Import the plugin module
            module_name = f"plugins.{plugin_name}"
            spec = importlib.util.spec_from_file_location(module_name, plugin_file)
            if spec is None or spec.loader is None:
                return

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Find plugin class
            plugin_class = None
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and
                    issubclass(obj, Plugin) and
                    obj != Plugin):
                    plugin_class = obj
                    break

            if plugin_class is None:
                logger.warning(f"No plugin class found in {plugin_name}")
                return

            # Create plugin instance
            metadata = PluginMetadata(name=plugin_name)
            plugin = plugin_class(metadata)

            self.plugins[plugin_name] = plugin
            logger.info(f"Discovered plugin: {plugin_name}")

        except Exception as e:
            logger.error(f"Error loading plugin from {plugin_file}: {e}")

    async def load_plugins(self) -> None:
        """Load all discovered plugins in dependency order"""
        # Build dependency graph
        self._build_dependency_graph()

        # Topological sort to get load order
        load_order = self._topological_sort()

        # Load plugins
        for plugin_name in load_order:
            if plugin_name in self.plugins:
                plugin = self.plugins[plugin_name]

                # Create context
                context = PluginContext(
                    app=None,  # Will be set by application
                    config=self._get_plugin_config(plugin_name),
                    logger=logging.getLogger(f"plugin.{plugin_name}")
                )

                try:
                    await plugin.load(context)
                    await plugin.initialize()
                    await plugin.start()
                    self._plugin_load_order.append(plugin_name)
                except Exception as e:
                    logger.error(f"Failed to load plugin {plugin_name}: {e}")

    def _build_dependency_graph(self) -> None:
        """Build dependency graph for plugins"""
        self.dependencies = {}

        for plugin_name, plugin in self.plugins.items():
            deps = []
            for dep in plugin.metadata.dependencies:
                if dep in self.plugins:
                    deps.append(dep)
            self.dependencies[plugin_name] = deps

    def _topological_sort(self) -> List[str]:
        """Perform topological sort on plugin dependencies"""
        # Kahn's algorithm for topological sorting
        in_degree = {plugin: 0 for plugin in self.plugins}
        for plugin, deps in self.dependencies.items():
            for dep in deps:
                in_degree[dep] += 1

        queue = [plugin for plugin in self.plugins if in_degree[plugin] == 0]
        result = []

        while queue:
            current = queue.pop(0)
            result.append(current)

            for plugin, deps in self.dependencies.items():
                if current in deps:
                    in_degree[plugin] -= 1
                    if in_degree[plugin] == 0:
                        queue.append(plugin)

        if len(result) != len(self.plugins):
            raise RuntimeError("Circular dependency detected in plugins")

        return result

    def _get_plugin_config(self, plugin_name: str) -> Dict[str, Any]:
        """Get configuration for a plugin"""
        # This would load from config files, environment, etc.
        return {}

    async def call_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """Call a hook across all plugins"""
        results = []
        for plugin in self.plugins.values():
            if plugin.state == PluginState.STARTED:
                plugin_results = await plugin.call_hook(hook_name, *args, **kwargs)
                results.extend(plugin_results)
        return results

    def get_plugin(self, name: str) -> Optional[Plugin]:
        """Get a plugin by name"""
        return self.plugins.get(name)

    def get_plugins_by_state(self, state: PluginState) -> List[Plugin]:
        """Get plugins by state"""
        return [plugin for plugin in self.plugins.values() if plugin.state == state]

    def get_plugins_by_capability(self, capability: str) -> List[Plugin]:
        """Get plugins by capability"""
        return [plugin for plugin in self.plugins.values()
                if capability in plugin.metadata.capabilities]

    def get_stats(self) -> Dict[str, Any]:
        """Get plugin manager statistics"""
        stats = {
            'total_plugins': len(self.plugins),
            'running': self._running,
            'plugins_by_state': {},
            'plugins_by_capability': {}
        }

        for state in PluginState:
            stats['plugins_by_state'][state.value] = len(self.get_plugins_by_state(state))

        # Count capabilities
        capabilities = {}
        for plugin in self.plugins.values():
            for capability in plugin.metadata.capabilities:
                capabilities[capability] = capabilities.get(capability, 0) + 1

        stats['plugins_by_capability'] = capabilities
        return stats


# Built-in Plugin Types
class MiddlewarePlugin(Plugin):
    """Plugin that provides middleware"""

    def __init__(self, metadata: PluginMetadata):
        super().__init__(metadata)
        self.middleware: List[Callable] = []

    async def on_initialize(self) -> None:
        """Register middleware with the application"""
        if self.context and self.context.app:
            for middleware in self.middleware:
                self.context.app.add_middleware(middleware)

    def add_middleware(self, middleware: Callable) -> None:
        """Add middleware to this plugin"""
        self.middleware.append(middleware)


class RoutePlugin(Plugin):
    """Plugin that provides routes"""

    def __init__(self, metadata: PluginMetadata):
        super().__init__(metadata)
        self.routes: List[Tuple[str, Callable, Dict]] = []

    async def on_initialize(self) -> None:
        """Register routes with the application"""
        if self.context and self.context.app:
            for path, handler, options in self.routes:
                self.context.app.router.add_route(path, handler, **options)

    def add_route(self, path: str, handler: Callable, **options) -> None:
        """Add route to this plugin"""
        self.routes.append((path, handler, options))


class ServicePlugin(Plugin):
    """Plugin that provides services"""

    def __init__(self, metadata: PluginMetadata):
        super().__init__(metadata)
        self.services: Dict[Type, Any] = {}

    async def on_initialize(self) -> None:
        """Register services with the application"""
        if self.context and self.context.app:
            for service_type, service_instance in self.services.items():
                self.context.app.container.register_singleton(service_type, service_instance)

    def add_service(self, service_type: Type, service_instance: Any) -> None:
        """Add service to this plugin"""
        self.services[service_type] = service_instance


class EventPlugin(Plugin):
    """Plugin that handles events"""

    def __init__(self, metadata: PluginMetadata):
        super().__init__(metadata)
        self.event_handlers: Dict[str, List[Callable]] = {}

    async def on_start(self) -> None:
        """Register event handlers"""
        if self.context and self.context.event_bus:
            for event_type, handlers in self.event_handlers.items():
                for handler in handlers:
                    self.context.event_bus.subscribe(event_type, handler)

    def add_event_handler(self, event_type: str, handler: Callable) -> None:
        """Add event handler to this plugin"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)


# Plugin Manager Instance
_plugin_manager: Optional[PluginManager] = None

def get_plugin_manager() -> PluginManager:
    """Get the global plugin manager instance"""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager

async def load_plugins(plugin_dirs: List[str] = None) -> None:
    """Load plugins from specified directories"""
    manager = get_plugin_manager()
    if plugin_dirs:
        manager.plugin_dirs = plugin_dirs
    await manager.start()

async def unload_plugins() -> None:
    """Unload all plugins"""
    manager = get_plugin_manager()
    await manager.stop()

def get_plugin(name: str) -> Optional[Plugin]:
    """Get a plugin by name"""
    manager = get_plugin_manager()
    return manager.get_plugin(name)

async def call_plugin_hook(hook_name: str, *args, **kwargs) -> List[Any]:
    """Call a hook across all plugins"""
    manager = get_plugin_manager()
    return await manager.call_hook(hook_name, *args, **kwargs)

__all__ = [
    'PluginManager', 'Plugin', 'PluginState', 'PluginPriority',
    'PluginMetadata', 'PluginContext', 'MiddlewarePlugin',
    'RoutePlugin', 'ServicePlugin', 'EventPlugin',
    'get_plugin_manager', 'load_plugins', 'unload_plugins',
    'get_plugin', 'call_plugin_hook'
]

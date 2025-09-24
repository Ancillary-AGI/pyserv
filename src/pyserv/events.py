"""
Event System for Pyserv Framework

This module provides a comprehensive event system for inter-component communication,
pub/sub messaging, and application lifecycle events.

Key Features:
- Event-driven architecture
- Publish/Subscribe pattern
- Async event handling
- Event filtering and routing
- Event persistence and logging
- Performance monitoring
"""

import asyncio
import logging
import uuid
from typing import Dict, List, Callable, Any, Optional, Set, Union, Awaitable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class EventPriority(int, Enum):
    """Event priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Event:
    """Base event class"""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    source: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    priority: EventPriority = EventPriority.NORMAL
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.event_type:
            self.event_type = self.__class__.__name__

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        return {
            'event_id': self.event_id,
            'event_type': self.event_type,
            'data': self.data,
            'source': self.source,
            'timestamp': self.timestamp.isoformat(),
            'priority': self.priority.value,
            'correlation_id': self.correlation_id,
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """Create event from dictionary"""
        return cls(
            event_id=data.get('event_id', str(uuid.uuid4())),
            event_type=data.get('event_type', ''),
            data=data.get('data', {}),
            source=data.get('source', ''),
            timestamp=datetime.fromisoformat(data['timestamp']),
            priority=EventPriority(data.get('priority', EventPriority.NORMAL.value)),
            correlation_id=data.get('correlation_id'),
            metadata=data.get('metadata', {})
        )


class EventHandler:
    """Event handler wrapper with metadata"""

    def __init__(self,
                 handler: Callable,
                 event_types: List[str],
                 priority: EventPriority = EventPriority.NORMAL,
                 async_handler: bool = True,
                 filters: Optional[Dict[str, Any]] = None):
        self.handler = handler
        self.event_types = event_types
        self.priority = priority
        self.async_handler = async_handler
        self.filters = filters or {}
        self.handler_id = str(uuid.uuid4())

    async def can_handle(self, event: Event) -> bool:
        """Check if handler can handle the event"""
        # Check event type
        if event.event_type not in self.event_types:
            return False

        # Check filters
        for key, value in self.filters.items():
            if key not in event.metadata or event.metadata[key] != value:
                return False

        return True

    async def handle(self, event: Event) -> Any:
        """Handle the event"""
        try:
            if self.async_handler:
                if asyncio.iscoroutinefunction(self.handler):
                    return await self.handler(event)
                else:
                    # Run sync handler in thread pool
                    loop = asyncio.get_event_loop()
                    return await loop.run_in_executor(None, self.handler, event)
            else:
                return self.handler(event)
        except Exception as e:
            logger.error(f"Error in event handler {self.handler_id}: {e}")
            raise


class EventBus:
    """Central event bus for the application"""

    def __init__(self):
        self.handlers: Dict[str, List[EventHandler]] = {}
        self.event_history: List[Event] = []
        self.max_history_size = 1000
        self.subscribers: Dict[str, Set[str]] = {}
        self._running = False
        self._event_queue = asyncio.Queue()
        self._processing_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the event bus"""
        if self._running:
            return

        self._running = True
        self._processing_task = asyncio.create_task(self._process_events())
        logger.info("Event bus started")

    async def stop(self):
        """Stop the event bus"""
        if not self._running:
            return

        self._running = False

        # Wait for processing task to complete
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass

        logger.info("Event bus stopped")

    def subscribe(self, event_types: Union[str, List[str]], handler: Callable,
                  priority: EventPriority = EventPriority.NORMAL,
                  filters: Optional[Dict[str, Any]] = None) -> str:
        """Subscribe to events"""
        if isinstance(event_types, str):
            event_types = [event_types]

        event_handler = EventHandler(
            handler=handler,
            event_types=event_types,
            priority=priority,
            filters=filters
        )

        for event_type in event_types:
            if event_type not in self.handlers:
                self.handlers[event_type] = []
            self.handlers[event_type].append(event_handler)

            # Sort handlers by priority (highest first)
            self.handlers[event_type].sort(key=lambda h: h.priority.value, reverse=True)

        logger.info(f"Subscribed handler {event_handler.handler_id} to events: {event_types}")
        return event_handler.handler_id

    def unsubscribe(self, handler_id: str) -> bool:
        """Unsubscribe from events"""
        for event_type, handlers in self.handlers.items():
            for handler in handlers:
                if handler.handler_id == handler_id:
                    handlers.remove(handler)
                    logger.info(f"Unsubscribed handler {handler_id} from {event_type}")
                    return True
        return False

    async def publish(self, event: Event) -> List[Any]:
        """Publish an event to all subscribers"""
        if not self._running:
            logger.warning("Event bus is not running, event will be queued")
            await self._event_queue.put(event)
            return []

        # Add to history
        self.event_history.append(event)
        if len(self.event_history) > self.max_history_size:
            self.event_history.pop(0)

        # Get handlers for this event type
        handlers = self.handlers.get(event.event_type, [])

        # Filter handlers that can handle this event
        applicable_handlers = []
        for handler in handlers:
            if await handler.can_handle(event):
                applicable_handlers.append(handler)

        if not applicable_handlers:
            logger.debug(f"No handlers for event {event.event_type}")
            return []

        # Execute handlers concurrently
        tasks = [handler.handle(event) for handler in applicable_handlers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Log any exceptions
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Exception in event handler: {result}")

        logger.debug(f"Published event {event.event_type} to {len(applicable_handlers)} handlers")
        return [r for r in results if not isinstance(r, Exception)]

    async def publish_async(self, event: Event) -> None:
        """Publish event asynchronously (fire and forget)"""
        asyncio.create_task(self.publish(event))

    async def _process_events(self):
        """Process events from the queue"""
        while self._running:
            try:
                # Wait for event with timeout
                try:
                    event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

                # Process the event
                await self.publish(event)

            except Exception as e:
                logger.error(f"Error processing event: {e}")

    def get_event_history(self, event_type: Optional[str] = None,
                         limit: int = 100) -> List[Event]:
        """Get event history"""
        history = self.event_history[-limit:] if limit > 0 else self.event_history[:]

        if event_type:
            history = [e for e in history if e.event_type == event_type]

        return history

    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics"""
        return {
            'total_handlers': sum(len(handlers) for handlers in self.handlers.values()),
            'event_types': list(self.handlers.keys()),
            'history_size': len(self.event_history),
            'queue_size': self._event_queue.qsize(),
            'running': self._running
        }


# Built-in Events
class ApplicationEvent(Event):
    """Base application event"""
    pass

class StartupEvent(ApplicationEvent):
    """Application startup event"""
    def __init__(self, app_name: str, **kwargs):
        super().__init__(
            event_type="app.startup",
            data=kwargs,
            source=app_name
        )

class ShutdownEvent(ApplicationEvent):
    """Application shutdown event"""
    def __init__(self, app_name: str, **kwargs):
        super().__init__(
            event_type="app.shutdown",
            data=kwargs,
            source=app_name
        )

class RequestEvent(ApplicationEvent):
    """HTTP request event"""
    def __init__(self, method: str, path: str, **kwargs):
        super().__init__(
            event_type="http.request",
            data={"method": method, "path": path, **kwargs},
            source="http"
        )

class ResponseEvent(ApplicationEvent):
    """HTTP response event"""
    def __init__(self, status_code: int, method: str, path: str, **kwargs):
        super().__init__(
            event_type="http.response",
            data={"status_code": status_code, "method": method, "path": path, **kwargs},
            source="http"
        )

class WebSocketEvent(ApplicationEvent):
    """WebSocket event"""
    def __init__(self, event_type: str, connection_id: str, **kwargs):
        super().__init__(
            event_type=f"websocket.{event_type}",
            data=kwargs,
            source=f"websocket:{connection_id}"
        )

class DatabaseEvent(ApplicationEvent):
    """Database event"""
    def __init__(self, operation: str, table: str, **kwargs):
        super().__init__(
            event_type=f"database.{operation}",
            data={"table": table, **kwargs},
            source="database"
        )

class CacheEvent(ApplicationEvent):
    """Cache event"""
    def __init__(self, operation: str, key: str, **kwargs):
        super().__init__(
            event_type=f"cache.{operation}",
            data={"key": key, **kwargs},
            source="cache"
        )

class SecurityEvent(ApplicationEvent):
    """Security event"""
    def __init__(self, event_type: str, severity: str, **kwargs):
        super().__init__(
            event_type=f"security.{event_type}",
            data={"severity": severity, **kwargs},
            source="security",
            priority=EventPriority.HIGH if severity == "high" else EventPriority.NORMAL
        )


# Global event bus instance
_event_bus: Optional[EventBus] = None

def get_event_bus() -> EventBus:
    """Get the global event bus instance"""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus

async def publish_event(event: Event) -> List[Any]:
    """Publish an event to the global event bus"""
    bus = get_event_bus()
    return await bus.publish(event)

async def publish_event_async(event: Event) -> None:
    """Publish an event asynchronously"""
    bus = get_event_bus()
    await bus.publish_async(event)

def subscribe(event_types: Union[str, List[str]],
              handler: Callable,
              priority: EventPriority = EventPriority.NORMAL,
              filters: Optional[Dict[str, Any]] = None) -> str:
    """Subscribe to events on the global event bus"""
    bus = get_event_bus()
    return bus.subscribe(event_types, handler, priority, filters)

def unsubscribe(handler_id: str) -> bool:
    """Unsubscribe from events on the global event bus"""
    bus = get_event_bus()
    return bus.unsubscribe(handler_id)

# Convenience functions for common events
async def emit_startup_event(app_name: str, **kwargs):
    """Emit application startup event"""
    event = StartupEvent(app_name, **kwargs)
    await publish_event(event)

async def emit_shutdown_event(app_name: str, **kwargs):
    """Emit application shutdown event"""
    event = ShutdownEvent(app_name, **kwargs)
    await publish_event(event)

async def emit_request_event(method: str, path: str, **kwargs):
    """Emit HTTP request event"""
    event = RequestEvent(method, path, **kwargs)
    await publish_event_async(event)  # Async to not block request

async def emit_response_event(status_code: int, method: str, path: str, **kwargs):
    """Emit HTTP response event"""
    event = ResponseEvent(status_code, method, path, **kwargs)
    await publish_event_async(event)  # Async to not block response

async def emit_database_event(operation: str, table: str, **kwargs):
    """Emit database event"""
    event = DatabaseEvent(operation, table, **kwargs)
    await publish_event_async(event)

async def emit_cache_event(operation: str, key: str, **kwargs):
    """Emit cache event"""
    event = CacheEvent(operation, key, **kwargs)
    await publish_event_async(event)

async def emit_security_event(event_type: str, severity: str, **kwargs):
    """Emit security event"""
    event = SecurityEvent(event_type, severity, **kwargs)
    await publish_event_async(event)

__all__ = [
    'EventBus', 'Event', 'EventHandler', 'EventPriority',
    'ApplicationEvent', 'StartupEvent', 'ShutdownEvent',
    'RequestEvent', 'ResponseEvent', 'WebSocketEvent',
    'DatabaseEvent', 'CacheEvent', 'SecurityEvent',
    'get_event_bus', 'publish_event', 'publish_event_async',
    'subscribe', 'unsubscribe', 'emit_startup_event',
    'emit_shutdown_event', 'emit_request_event',
    'emit_response_event', 'emit_database_event',
    'emit_cache_event', 'emit_security_event'
]

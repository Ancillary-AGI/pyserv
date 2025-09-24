"""
Event Sourcing and CQRS implementation for Pyserv  framework.

This module provides:
- Event sourcing pattern with event store
- CQRS (Command Query Responsibility Segregation)
- Aggregate pattern for domain objects
- Event serialization and deserialization
"""

import json
import uuid
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable, Type, TypeVar, Generic
from datetime import datetime
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
import asyncio
import threading
from contextlib import asynccontextmanager


T = TypeVar('T')


@dataclass
class Event:
    """
    Base class for all events in the event sourcing system.

    Events are immutable records of state changes in the system.
    They follow the pattern of having an event type, aggregate ID,
    payload, and metadata.
    """

    event_type: str
    aggregate_id: str
    payload: Dict[str, Any]
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    version: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary representation"""
        return {
            'event_id': self.event_id,
            'event_type': self.event_type,
            'aggregate_id': self.aggregate_id,
            'payload': self.payload,
            'timestamp': self.timestamp.isoformat(),
            'version': self.version,
            'metadata': self.metadata
        }

    def to_json(self) -> str:
        """Convert event to JSON string"""
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """Create event from dictionary"""
        return cls(
            event_type=data['event_type'],
            aggregate_id=data['aggregate_id'],
            payload=data['payload'],
            event_id=data.get('event_id', str(uuid.uuid4())),
            timestamp=datetime.fromisoformat(data['timestamp']),
            version=data.get('version', 1),
            metadata=data.get('metadata', {})
        )

    @classmethod
    def from_json(cls, json_str: str) -> 'Event':
        """Create event from JSON string"""
        return cls.from_dict(json.loads(json_str))


class EventStore:
    """
    Store for all events following Event Sourcing pattern.

    The EventStore is responsible for:
    - Storing events durably
    - Retrieving events for aggregates
    - Publishing events to subscribers
    - Maintaining event streams
    """

    def __init__(self, storage_backend: Optional[Any] = None):
        self.events: List[Event] = []
        self.subscribers: Dict[str, List[Callable[[Event], Any]]] = {}
        self.snapshots: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self.storage_backend = storage_backend

    async def append(self, event: Event) -> bool:
        """
        Append event to store and notify subscribers.

        Args:
            event: Event to append

        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            try:
                # Add version based on existing events for this aggregate
                existing_events = [e for e in self.events if e.aggregate_id == event.aggregate_id]
                event.version = len(existing_events) + 1

                self.events.append(event)

                # Persist to storage if available
                if self.storage_backend:
                    await self._persist_event(event)

                # Notify subscribers
                await self._notify_subscribers(event)

                return True
            except Exception as e:
                print(f"Failed to append event: {e}")
                return False

    async def append_events(self, events: List[Event]) -> bool:
        """
        Append multiple events atomically.

        Args:
            events: List of events to append

        Returns:
            True if all events appended successfully
        """
        with self._lock:
            try:
                for event in events:
                    existing_events = [e for e in self.events if e.aggregate_id == event.aggregate_id]
                    event.version = len(existing_events) + 1
                    self.events.append(event)

                    if self.storage_backend:
                        await self._persist_event(event)

                # Notify subscribers for all events
                for event in events:
                    await self._notify_subscribers(event)

                return True
            except Exception as e:
                print(f"Failed to append events: {e}")
                return False

    def get_events(self, aggregate_id: str = None, event_type: str = None,
                   from_version: int = None, to_version: int = None) -> List[Event]:
        """
        Get events, optionally filtered by criteria.

        Args:
            aggregate_id: Filter by aggregate ID
            event_type: Filter by event type
            from_version: Starting version
            to_version: Ending version

        Returns:
            List of matching events
        """
        with self._lock:
            events = self.events.copy()

            if aggregate_id:
                events = [e for e in events if e.aggregate_id == aggregate_id]

            if event_type:
                events = [e for e in events if e.event_type == event_type]

            if from_version is not None:
                events = [e for e in events if e.version >= from_version]

            if to_version is not None:
                events = [e for e in events if e.version <= to_version]

            return sorted(events, key=lambda e: (e.timestamp, e.version))

    def get_aggregate_events(self, aggregate_id: str) -> List[Event]:
        """Get all events for a specific aggregate"""
        return self.get_events(aggregate_id=aggregate_id)

    def get_event_stream(self, aggregate_id: str) -> List[Event]:
        """Get complete event stream for an aggregate"""
        return self.get_aggregate_events(aggregate_id)

    async def subscribe(self, event_type: str, callback: Callable[[Event], Any]) -> None:
        """
        Subscribe to events of a specific type.

        Args:
            event_type: Type of events to subscribe to
            callback: Callback function to handle events
        """
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []

        self.subscribers[event_type].append(callback)

    async def unsubscribe(self, event_type: str, callback: Callable[[Event], Any]) -> None:
        """
        Unsubscribe from events.

        Args:
            event_type: Event type to unsubscribe from
            callback: Callback function to remove
        """
        if event_type in self.subscribers:
            self.subscribers[event_type].remove(callback)
            if not self.subscribers[event_type]:
                del self.subscribers[event_type]

    async def _notify_subscribers(self, event: Event) -> None:
        """Notify all subscribers of an event"""
        if event.event_type in self.subscribers:
            tasks = []
            for callback in self.subscribers[event.event_type]:
                if asyncio.iscoroutinefunction(callback):
                    tasks.append(callback(event))
                else:
                    # Run sync callbacks in thread pool
                    loop = asyncio.get_event_loop()
                    tasks.append(loop.run_in_executor(None, callback, event))

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    async def _persist_event(self, event: Event) -> None:
        """Persist event to storage backend"""
        if self.storage_backend:
            # Implementation depends on storage backend
            pass

    def create_snapshot(self, aggregate_id: str, state: Dict[str, Any], version: int) -> None:
        """
        Create a snapshot of aggregate state.

        Args:
            aggregate_id: ID of the aggregate
            state: Current state of the aggregate
            version: Version at which snapshot was taken
        """
        with self._lock:
            self.snapshots[aggregate_id] = {
                'state': state,
                'version': version,
                'timestamp': datetime.now()
            }

    def get_snapshot(self, aggregate_id: str) -> Optional[Dict[str, Any]]:
        """
        Get latest snapshot for an aggregate.

        Args:
            aggregate_id: ID of the aggregate

        Returns:
            Snapshot data or None if no snapshot exists
        """
        return self.snapshots.get(aggregate_id)

    def get_event_count(self, aggregate_id: str = None) -> int:
        """Get total number of events, optionally for specific aggregate"""
        if aggregate_id:
            return len([e for e in self.events if e.aggregate_id == aggregate_id])
        return len(self.events)


class Aggregate(ABC):
    """
    Base class for aggregates in CQRS pattern.

    Aggregates are the primary units of consistency in event sourcing.
    They encapsulate state and behavior, and are responsible for:
    - Maintaining internal state
    - Validating commands
    - Producing events
    - Applying events to update state
    """

    def __init__(self, aggregate_id: str):
        self.aggregate_id = aggregate_id
        self.version = 0
        self.uncommitted_events: List[Event] = []
        self._event_handlers: Dict[str, Callable[[Event], None]] = {}

    @abstractmethod
    async def handle_command(self, command: Dict[str, Any]) -> List[Event]:
        """
        Handle a command and produce events.

        Args:
            command: Command to handle

        Returns:
            List of events produced by handling the command
        """
        pass

    def apply_event(self, event: Event) -> None:
        """
        Apply an event to update aggregate state.

        Args:
            event: Event to apply
        """
        handler_name = f"apply_{event.event_type.lower()}"
        if hasattr(self, handler_name):
            handler = getattr(self, handler_name)
            handler(event)
            self.version = event.version
        else:
            # Generic event application
            self._apply_generic_event(event)

    def _apply_generic_event(self, event: Event) -> None:
        """Generic event application logic"""
        # Override in subclasses for custom logic
        pass

    async def load_from_events(self, events: List[Event]) -> None:
        """
        Load aggregate state from a list of events.

        Args:
            events: Events to apply to reconstruct state
        """
        for event in events:
            self.apply_event(event)

    async def load_from_history(self, event_store: EventStore) -> None:
        """
        Load aggregate state from event store history.

        Args:
            event_store: Event store to load events from
        """
        events = event_store.get_aggregate_events(self.aggregate_id)
        await self.load_from_events(events)

    def get_uncommitted_events(self) -> List[Event]:
        """Get list of uncommitted events"""
        return self.uncommitted_events.copy()

    def clear_uncommitted_events(self) -> None:
        """Clear uncommitted events after successful persistence"""
        self.uncommitted_events.clear()

    def mark_changes_as_committed(self) -> None:
        """Mark all changes as committed"""
        self.clear_uncommitted_events()


class Command:
    """
    Base class for commands in CQRS pattern.

    Commands represent user intentions to change the state of the system.
    They are processed by aggregates and result in events being produced.
    """

    def __init__(self, aggregate_id: str, **kwargs):
        self.aggregate_id = aggregate_id
        self.timestamp = datetime.now()
        self.metadata = kwargs

    def to_dict(self) -> Dict[str, Any]:
        """Convert command to dictionary"""
        return {
            'command_type': self.__class__.__name__,
            'aggregate_id': self.aggregate_id,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }


class CommandHandler(ABC):
    """
    Base class for command handlers in CQRS pattern.

    Command handlers are responsible for:
    - Loading aggregates from event store
    - Executing commands on aggregates
    - Persisting resulting events
    """

    def __init__(self, event_store: EventStore):
        self.event_store = event_store

    @abstractmethod
    async def handle(self, command: Command) -> List[str]:
        """
        Handle a command.

        Args:
            command: Command to handle

        Returns:
            List of event IDs that were produced
        """
        pass


class Repository(Generic[T]):
    """
    Repository pattern for aggregates.

    Provides a clean interface for loading and saving aggregates,
    abstracting away the event store implementation details.
    """

    def __init__(self, event_store: EventStore, aggregate_class: Type[T]):
        self.event_store = event_store
        self.aggregate_class = aggregate_class

    async def load(self, aggregate_id: str) -> T:
        """
        Load an aggregate from event store.

        Args:
            aggregate_id: ID of the aggregate to load

        Returns:
            Loaded aggregate instance
        """
        aggregate = self.aggregate_class(aggregate_id)
        await aggregate.load_from_history(self.event_store)
        return aggregate

    async def save(self, aggregate: T) -> bool:
        """
        Save an aggregate to event store.

        Args:
            aggregate: Aggregate to save

        Returns:
            True if save was successful
        """
        events = aggregate.get_uncommitted_events()
        if not events:
            return True

        success = await self.event_store.append_events(events)
        if success:
            aggregate.mark_changes_as_committed()

        return success

    async def exists(self, aggregate_id: str) -> bool:
        """
        Check if an aggregate exists.

        Args:
            aggregate_id: ID of the aggregate to check

        Returns:
            True if aggregate exists
        """
        events = self.event_store.get_aggregate_events(aggregate_id)
        return len(events) > 0


class EventPublisher:
    """
    Event publisher for decoupling event production from consumption.

    This class provides a clean interface for publishing events to
    multiple subscribers and handling event routing.
    """

    def __init__(self):
        self.subscribers: Dict[str, List[Callable[[Event], Any]]] = {}
        self._executor = ThreadPoolExecutor(max_workers=4)

    async def publish(self, event: Event) -> None:
        """
        Publish an event to all subscribers.

        Args:
            event: Event to publish
        """
        if event.event_type in self.subscribers:
            tasks = []
            for callback in self.subscribers[event.event_type]:
                if asyncio.iscoroutinefunction(callback):
                    tasks.append(callback(event))
                else:
                    # Run sync callbacks in thread pool
                    loop = asyncio.get_event_loop()
                    tasks.append(loop.run_in_executor(self._executor, callback, event))

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    def subscribe(self, event_type: str, callback: Callable[[Event], Any]) -> None:
        """
        Subscribe to events of a specific type.

        Args:
            event_type: Type of events to subscribe to
            callback: Callback function to handle events
        """
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable[[Event], Any]) -> None:
        """
        Unsubscribe from events.

        Args:
            event_type: Event type to unsubscribe from
            callback: Callback function to remove
        """
        if event_type in self.subscribers:
            self.subscribers[event_type].remove(callback)
            if not self.subscribers[event_type]:
                del self.subscribers[event_type]

    def get_subscriber_count(self, event_type: str = None) -> int:
        """
        Get number of subscribers.

        Args:
            event_type: Specific event type, or None for all

        Returns:
            Number of subscribers
        """
        if event_type:
            return len(self.subscribers.get(event_type, []))
        return sum(len(subs) for subs in self.subscribers.values())

    async def shutdown(self) -> None:
        """Shutdown the event publisher"""
        self._executor.shutdown(wait=True)





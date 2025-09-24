"""
Server-Sent Events (SSE) Support for Pyserv Framework

This module provides comprehensive Server-Sent Events support with:
- SSE endpoint management
- Event stream handling
- Connection management
- Heartbeat support
- Reconnection handling
- Event filtering and routing
- Performance optimization
- Security features
- Monitoring and metrics
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, List, Callable, Any, Optional, Type, Union, Awaitable, Set
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class SSEEventType(str, Enum):
    """SSE event types"""
    MESSAGE = "message"
    ERROR = "error"
    CLOSE = "close"
    HEARTBEAT = "heartbeat"
    RECONNECT = "reconnect"
    CUSTOM = "custom"


class SSEConnectionState(str, Enum):
    """SSE connection states"""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"


@dataclass
class SSEEvent:
    """Server-Sent Event"""
    id: Optional[str] = None
    event: str = SSEEventType.MESSAGE.value
    data: Any = None
    retry: Optional[int] = None
    timestamp: float = field(default_factory=time.time)

    def to_string(self) -> str:
        """Convert event to SSE format"""
        lines = []

        if self.id:
            lines.append(f"id: {self.id}")

        lines.append(f"event: {self.event}")

        if self.retry:
            lines.append(f"retry: {self.retry}")

        # Handle data (can be string, dict, or list)
        if isinstance(self.data, (dict, list)):
            data_str = json.dumps(self.data, ensure_ascii=False)
        else:
            data_str = str(self.data)

        # Split data into multiple lines if needed
        for line in data_str.split('\n'):
            lines.append(f"data: {line}")

        lines.append("")  # Empty line to end event
        return '\n'.join(lines)


@dataclass
class SSEConnection:
    """SSE connection information"""
    connection_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    client_id: Optional[str] = None
    user_id: Optional[str] = None
    channels: Set[str] = field(default_factory=set)
    state: SSEConnectionState = SSEConnectionState.CONNECTING
    last_activity: float = field(default_factory=time.time)
    heartbeat_interval: int = 30  # seconds
    reconnect_delay: int = 3  # seconds
    max_reconnect_attempts: int = 5
    reconnect_attempts: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    response_writer: Optional[Callable] = None

    def add_channel(self, channel: str) -> None:
        """Add channel subscription"""
        self.channels.add(channel)
        self.last_activity = time.time()

    def remove_channel(self, channel: str) -> None:
        """Remove channel subscription"""
        self.channels.discard(channel)
        self.last_activity = time.time()

    def has_channel(self, channel: str) -> bool:
        """Check if subscribed to channel"""
        return channel in self.channels or '*' in self.channels

    def update_activity(self) -> None:
        """Update last activity timestamp"""
        self.last_activity = time.time()


class SSEManager:
    """Server-Sent Events Manager"""

    def __init__(self):
        self.connections: Dict[str, SSEConnection] = {}
        self.channels: Dict[str, Set[str]] = {}  # channel -> set of connection_ids
        self.event_handlers: Dict[str, List[Callable]] = {}
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        self._event_queue: asyncio.Queue[SSEEvent] = asyncio.Queue()
        self._event_history: List[SSEEvent] = []
        self.max_history_size = 1000

    async def start(self) -> None:
        """Start SSE manager"""
        if self._running:
            return

        self._running = True

        # Start background tasks
        self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())

        logger.info("SSE Manager started")

    async def stop(self) -> None:
        """Stop SSE manager"""
        if not self._running:
            return

        self._running = False

        # Cancel background tasks
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass

        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass

        # Close all connections
        for connection in list(self.connections.values()):
            await self.disconnect(connection.connection_id)

        logger.info("SSE Manager stopped")

    async def connect(self, client_id: Optional[str] = None,
                     user_id: Optional[str] = None,
                     channels: Optional[List[str]] = None) -> SSEConnection:
        """Create new SSE connection"""
        connection = SSEConnection(
            client_id=client_id,
            user_id=user_id
        )

        if channels:
            for channel in channels:
                connection.add_channel(channel)
                if channel not in self.channels:
                    self.channels[channel] = set()
                self.channels[channel].add(connection.connection_id)

        self.connections[connection.connection_id] = connection

        # Send welcome event
        welcome_event = SSEEvent(
            event=SSEEventType.MESSAGE.value,
            data={
                'type': 'connection_established',
                'connection_id': connection.connection_id,
                'channels': list(connection.channels),
                'timestamp': connection.last_activity
            }
        )

        await self._send_to_connection(connection.connection_id, welcome_event)

        logger.info(f"SSE connection established: {connection.connection_id}")
        return connection

    async def disconnect(self, connection_id: str) -> None:
        """Disconnect SSE connection"""
        if connection_id not in self.connections:
            return

        connection = self.connections[connection_id]

        # Send disconnect event
        disconnect_event = SSEEvent(
            event=SSEEventType.CLOSE.value,
            data={
                'type': 'connection_closed',
                'reason': 'server_disconnect',
                'timestamp': time.time()
            }
        )

        await self._send_to_connection(connection_id, disconnect_event)

        # Remove from channels
        for channel in list(connection.channels):
            if channel in self.channels:
                self.channels[channel].discard(connection_id)

        # Remove connection
        del self.connections[connection_id]

        logger.info(f"SSE connection disconnected: {connection_id}")

    async def send_to_connection(self, connection_id: str, event: SSEEvent) -> bool:
        """Send event to specific connection"""
        if connection_id not in self.connections:
            return False

        connection = self.connections[connection_id]
        connection.update_activity()

        return await self._send_to_connection(connection_id, event)

    async def send_to_channel(self, channel: str, event: SSEEvent,
                            filter_func: Optional[Callable] = None) -> int:
        """Send event to all connections in a channel"""
        if channel not in self.channels:
            return 0

        sent_count = 0
        connection_ids = list(self.channels[channel])

        for connection_id in connection_ids:
            if connection_id in self.connections:
                connection = self.connections[connection_id]

                # Apply filter if provided
                if filter_func and not filter_func(connection):
                    continue

                if connection.has_channel(channel):
                    if await self._send_to_connection(connection_id, event):
                        sent_count += 1

        return sent_count

    async def send_to_user(self, user_id: str, event: SSEEvent) -> int:
        """Send event to all connections of a user"""
        sent_count = 0

        for connection in self.connections.values():
            if connection.user_id == user_id:
                if await self._send_to_connection(connection.connection_id, event):
                    sent_count += 1

        return sent_count

    async def broadcast(self, event: SSEEvent,
                       filter_func: Optional[Callable] = None) -> int:
        """Broadcast event to all connections"""
        sent_count = 0

        for connection_id in list(self.connections.keys()):
            connection = self.connections[connection_id]

            # Apply filter if provided
            if filter_func and not filter_func(connection):
                continue

            if await self._send_to_connection(connection_id, event):
                sent_count += 1

        return sent_count

    async def subscribe(self, connection_id: str, channel: str) -> bool:
        """Subscribe connection to channel"""
        if connection_id not in self.connections:
            return False

        connection = self.connections[connection_id]
        connection.add_channel(channel)

        if channel not in self.channels:
            self.channels[channel] = set()
        self.channels[channel].add(connection_id)

        # Send subscription confirmation
        event = SSEEvent(
            event=SSEEventType.MESSAGE.value,
            data={
                'type': 'subscribed',
                'channel': channel,
                'timestamp': time.time()
            }
        )

        await self._send_to_connection(connection_id, event)
        return True

    async def unsubscribe(self, connection_id: str, channel: str) -> bool:
        """Unsubscribe connection from channel"""
        if connection_id not in self.connections:
            return False

        connection = self.connections[connection_id]
        connection.remove_channel(channel)

        if channel in self.channels:
            self.channels[channel].discard(connection_id)

        # Send unsubscription confirmation
        event = SSEEvent(
            event=SSEEventType.MESSAGE.value,
            data={
                'type': 'unsubscribed',
                'channel': channel,
                'timestamp': time.time()
            }
        )

        await self._send_to_connection(connection_id, event)
        return True

    async def add_event_handler(self, event_type: str, handler: Callable) -> None:
        """Add event handler"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)

    async def remove_event_handler(self, event_type: str, handler: Callable) -> None:
        """Remove event handler"""
        if event_type in self.event_handlers:
            try:
                self.event_handlers[event_type].remove(handler)
            except ValueError:
                pass

    async def _send_to_connection(self, connection_id: str, event: SSEEvent) -> bool:
        """Send event to specific connection"""
        if connection_id not in self.connections:
            return False

        connection = self.connections[connection_id]

        try:
            if connection.response_writer:
                event_str = event.to_string()
                await connection.response_writer(event_str)

                # Store in history
                self._add_to_history(event)

                return True

        except Exception as e:
            logger.error(f"Error sending SSE event to {connection_id}: {e}")

        return False

    def _add_to_history(self, event: SSEEvent) -> None:
        """Add event to history"""
        self._event_history.append(event)

        # Trim history if needed
        if len(self._event_history) > self.max_history_size:
            self._event_history = self._event_history[-self.max_history_size:]

    async def _heartbeat_loop(self) -> None:
        """Send heartbeat events to connections"""
        while self._running:
            try:
                await asyncio.sleep(30)  # Heartbeat every 30 seconds

                heartbeat_event = SSEEvent(
                    event=SSEEventType.HEARTBEAT.value,
                    data={
                        'type': 'heartbeat',
                        'timestamp': time.time(),
                        'connections': len(self.connections)
                    }
                )

                await self.broadcast(heartbeat_event)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")

    async def _cleanup_loop(self) -> None:
        """Clean up inactive connections"""
        while self._running:
            try:
                await asyncio.sleep(60)  # Cleanup every minute

                current_time = time.time()
                inactive_timeout = 300  # 5 minutes

                inactive_connections = []
                for connection_id, connection in self.connections.items():
                    if current_time - connection.last_activity > inactive_timeout:
                        inactive_connections.append(connection_id)

                for connection_id in inactive_connections:
                    logger.info(f"Cleaning up inactive SSE connection: {connection_id}")
                    await self.disconnect(connection_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get SSE manager statistics"""
        return {
            'connections': len(self.connections),
            'channels': len(self.channels),
            'event_handlers': len(self.event_handlers),
            'event_history_size': len(self._event_history),
            'running': self._running,
            'channel_subscriptions': {
                channel: len(connections)
                for channel, connections in self.channels.items()
            }
        }

    def get_connection(self, connection_id: str) -> Optional[SSEConnection]:
        """Get connection by ID"""
        return self.connections.get(connection_id)

    def get_connections_for_user(self, user_id: str) -> List[SSEConnection]:
        """Get all connections for a user"""
        return [
            connection for connection in self.connections.values()
            if connection.user_id == user_id
        ]

    def get_connections_for_channel(self, channel: str) -> List[SSEConnection]:
        """Get all connections subscribed to a channel"""
        if channel not in self.channels:
            return []

        return [
            self.connections[connection_id]
            for connection_id in self.channels[channel]
            if connection_id in self.connections
        ]


# Global SSE Manager
_sse_manager: Optional[SSEManager] = None

def get_sse_manager() -> SSEManager:
    """Get the global SSE manager instance"""
    global _sse_manager
    if _sse_manager is None:
        _sse_manager = SSEManager()
    return _sse_manager

async def start_sse_manager() -> SSEManager:
    """Start the global SSE manager"""
    manager = get_sse_manager()
    await manager.start()
    return manager

async def stop_sse_manager() -> None:
    """Stop the global SSE manager"""
    manager = get_sse_manager()
    await manager.stop()

def create_sse_event(event_type: str, data: Any, event_id: Optional[str] = None,
                    retry: Optional[int] = None) -> SSEEvent:
    """Create SSE event"""
    return SSEEvent(
        id=event_id,
        event=event_type,
        data=data,
        retry=retry
    )

__all__ = [
    'SSEManager', 'SSEConnection', 'SSEEvent', 'SSEEventType',
    'SSEConnectionState', 'get_sse_manager', 'start_sse_manager',
    'stop_sse_manager', 'create_sse_event'
]

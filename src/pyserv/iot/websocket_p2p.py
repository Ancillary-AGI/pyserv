"""
WebSocket P2P communication for IoT devices with Django Channels-like features.
Provides peer-to-peer communication through WebSocket with channel layers and consumers.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, Callable, List, Set
from dataclasses import dataclass
from abc import ABC, abstractmethod

@dataclass
class P2PConfig:
    """Configuration for P2P communication."""
    signaling_server: str = "ws://localhost:8080"
    enable_stun: bool = True
    stun_servers: List[str] = None
    enable_turn: bool = False
    turn_servers: List[str] = None
    max_peers: int = 10
    heartbeat_interval: int = 30

    def __post_init__(self):
        if self.stun_servers is None:
            self.stun_servers = ["stun:stun.l.google.com:19302"]

class ChannelLayer(ABC):
    """
    Abstract channel layer interface similar to Django Channels.
    """

    @abstractmethod
    async def send(self, channel: str, message: Any):
        """Send message to a channel."""
        pass

    @abstractmethod
    async def receive(self, channel: str) -> Any:
        """Receive message from a channel."""
        pass

    @abstractmethod
    async def group_send(self, group: str, message: Any):
        """Send message to all channels in a group."""
        pass

    @abstractmethod
    async def group_add(self, channel: str, group: str):
        """Add channel to a group."""
        pass

    @abstractmethod
    async def group_discard(self, channel: str, group: str):
        """Remove channel from a group."""
        pass


class InMemoryChannelLayer(ChannelLayer):
    """
    In-memory channel layer for development and testing.
    """

    def __init__(self):
        self.channels: Dict[str, asyncio.Queue] = {}
        self.groups: Dict[str, Set[str]] = {}

    async def send(self, channel: str, message: Any):
        """Send message to a channel."""
        if channel not in self.channels:
            self.channels[channel] = asyncio.Queue()
        await self.channels[channel].put(message)

    async def receive(self, channel: str) -> Any:
        """Receive message from a channel."""
        if channel not in self.channels:
            self.channels[channel] = asyncio.Queue()
        return await self.channels[channel].get()

    async def group_send(self, group: str, message: Any):
        """Send message to all channels in a group."""
        if group in self.groups:
            for channel in self.groups[group]:
                await self.send(channel, message)

    async def group_add(self, channel: str, group: str):
        """Add channel to a group."""
        if group not in self.groups:
            self.groups[group] = set()
        self.groups[group].add(channel)

    async def group_discard(self, channel: str, group: str):
        """Remove channel from a group."""
        if group in self.groups and channel in self.groups[group]:
            self.groups[group].remove(channel)


class WebSocketConsumer(ABC):
    """
    Base WebSocket consumer class similar to Django Channels.
    """

    def __init__(self, scope: Dict[str, Any]):
        self.scope = scope
        self.channel_layer: Optional[ChannelLayer] = None
        self.channel_name: Optional[str] = None

    async def connect(self):
        """Called when WebSocket connects."""
        pass

    async def disconnect(self, close_code: int):
        """Called when WebSocket disconnects."""
        pass

    async def receive(self, text_data: str = None, bytes_data: bytes = None):
        """Called when WebSocket receives a message."""
        pass

    async def send(self, text_data: str = None, bytes_data: bytes = None):
        """Send message through WebSocket."""
        pass

    async def accept(self):
        """Accept the WebSocket connection."""
        pass

    async def close(self, close_code: int = 1000):
        """Close the WebSocket connection."""
        pass

    async def group_send(self, group: str, message: Any):
        """Send message to a group."""
        if self.channel_layer:
            await self.channel_layer.group_send(group, message)

    async def group_add(self, group: str):
        """Add to a group."""
        if self.channel_layer and self.channel_name:
            await self.channel_layer.group_add(self.channel_name, group)

    async def group_discard(self, group: str):
        """Remove from a group."""
        if self.channel_layer and self.channel_name:
            await self.channel_layer.group_discard(self.channel_name, group)


class P2PConsumer(WebSocketConsumer):
    """
    P2P WebSocket consumer with channel layer support.
    """

    def __init__(self, scope: Dict[str, Any]):
        super().__init__(scope)
        self.groups: Set[str] = set()

    async def connect(self):
        """Accept P2P connection."""
        await self.accept()
        self.channel_name = f"p2p_{id(self)}"

        # Add to default groups
        await self.group_add("p2p")
        await self.group_add("broadcast")

    async def disconnect(self, close_code: int):
        """Handle P2P disconnection."""
        # Remove from all groups
        for group in self.groups:
            await self.group_discard(group)

    async def receive(self, text_data: str = None, bytes_data: bytes = None):
        """Handle incoming P2P messages."""
        if text_data:
            try:
                data = json.loads(text_data)
                message_type = data.get('type', 'message')

                if message_type == 'join_group':
                    group = data.get('group')
                    if group:
                        await self.group_add(group)
                        self.groups.add(group)
                        await self.send(text_data=json.dumps({
                            'type': 'group_joined',
                            'group': group
                        }))

                elif message_type == 'leave_group':
                    group = data.get('group')
                    if group and group in self.groups:
                        await self.group_discard(group)
                        self.groups.remove(group)
                        await self.send(text_data=json.dumps({
                            'type': 'group_left',
                            'group': group
                        }))

                elif message_type == 'broadcast':
                    message = data.get('message', {})
                    await self.group_send("broadcast", {
                        'type': 'broadcast_message',
                        'message': message,
                        'from': self.channel_name
                    })

                else:
                    # Echo message back
                    await self.send(text_data=json.dumps({
                        'type': 'echo',
                        'message': data
                    }))

            except json.JSONDecodeError:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Invalid JSON'
                }))


class WebSocketP2P:
    """
    WebSocket-based P2P communication for IoT devices with Django Channels-like features.
    """

    def __init__(self, config: P2PConfig):
        self.config = config
        self.logger = logging.getLogger("websocket_p2p")
        self.websocket = None
        self.is_connected = False
        self.peers: Dict[str, Dict[str, Any]] = {}
        self.message_handlers: List[Callable] = []
        self.channel_layer: ChannelLayer = InMemoryChannelLayer()
        self.consumers: Dict[str, WebSocketConsumer] = {}

    async def connect(self) -> bool:
        """Connect to signaling server."""
        try:
            self.logger.info(f"Connecting to signaling server: {self.config.signaling_server}")
            self.is_connected = True

            # In real implementation, this would establish WebSocket connection
            await asyncio.sleep(0.5)

            self.logger.info("P2P signaling connected successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to connect to signaling server: {e}")
            return False

    async def disconnect(self):
        """Disconnect from signaling server."""
        try:
            self.is_connected = False
            self.peers.clear()
            self.logger.info("P2P signaling disconnected")
        except Exception as e:
            self.logger.error(f"Error disconnecting P2P: {e}")

    async def connect_to_peer(self, peer_id: str) -> bool:
        """Connect to a specific peer."""
        try:
            if peer_id in self.peers:
                self.logger.warning(f"Already connected to peer: {peer_id}")
                return True

            # In real implementation, this would establish P2P connection
            self.peers[peer_id] = {
                "id": peer_id,
                "connected_at": asyncio.get_event_loop().time(),
                "status": "connected"
            }

            self.logger.info(f"Connected to peer: {peer_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to connect to peer {peer_id}: {e}")
            return False

    async def send_to_peer(self, peer_id: str, message: Any) -> bool:
        """Send message to specific peer."""
        try:
            if peer_id not in self.peers:
                self.logger.warning(f"Peer {peer_id} not connected")
                return False

            # Convert message to JSON if needed
            if not isinstance(message, str):
                message = json.dumps(message)

            # In real implementation, this would send via P2P connection
            self.logger.info(f"Sending to peer {peer_id}: {message}")

            return True

        except Exception as e:
            self.logger.error(f"Failed to send message to peer {peer_id}: {e}")
            return False

    async def broadcast(self, message: Any) -> int:
        """Broadcast message to all connected peers."""
        try:
            if not isinstance(message, str):
                message = json.dumps(message)

            sent_count = 0
            for peer_id in self.peers:
                if await self.send_to_peer(peer_id, message):
                    sent_count += 1

            self.logger.info(f"Broadcast to {sent_count}/{len(self.peers)} peers")
            return sent_count

        except Exception as e:
            self.logger.error(f"Failed to broadcast message: {e}")
            return 0

    def add_message_handler(self, handler: Callable):
        """Add message handler."""
        self.message_handlers.append(handler)

    def remove_message_handler(self, handler: Callable):
        """Remove message handler."""
        if handler in self.message_handlers:
            self.message_handlers.remove(handler)

    async def get_peers(self) -> List[Dict[str, Any]]:
        """Get list of connected peers."""
        return list(self.peers.values())

    async def get_status(self) -> Dict[str, Any]:
        """Get P2P status."""
        return {
            "connected": self.is_connected,
            "signaling_server": self.config.signaling_server,
            "peer_count": len(self.peers),
            "peers": list(self.peers.keys()),
            "max_peers": self.config.max_peers
        }

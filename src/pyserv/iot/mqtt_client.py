"""
MQTT Client for IoT communication.
Provides MQTT protocol support for device communication.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from datetime import datetime

@dataclass
class MQTTConfig:
    """Configuration for MQTT client."""
    broker_host: str = "localhost"
    broker_port: int = 1883
    client_id: str = ""
    username: Optional[str] = None
    password: Optional[str] = None
    keep_alive: int = 60
    qos: int = 1  # 0, 1, or 2
    retain: bool = False
    clean_session: bool = True
    reconnect_delay: float = 5.0
    max_reconnect_attempts: int = 10

class MQTTClient:
    """
    MQTT client for IoT device communication.
    """

    def __init__(self, config: MQTTConfig):
        self.config = config
        self.logger = logging.getLogger("mqtt_client")
        self.client = None
        self.is_connected = False
        self.subscriptions: Dict[str, Callable] = {}
        self.message_handlers: List[Callable] = []

    async def connect(self) -> bool:
        """Connect to MQTT broker."""
        try:
            # In real implementation, this would use paho-mqtt or similar
            self.logger.info(f"Connecting to MQTT broker at {self.config.broker_host}:{self.config.broker_port}")

            # Simulate connection
            await asyncio.sleep(1)

            self.is_connected = True
            self.logger.info("MQTT client connected successfully")

            # Start message loop
            asyncio.create_task(self._message_loop())

            return True

        except Exception as e:
            self.logger.error(f"Failed to connect to MQTT broker: {e}")
            return False

    async def disconnect(self):
        """Disconnect from MQTT broker."""
        try:
            self.is_connected = False
            self.logger.info("MQTT client disconnected")
        except Exception as e:
            self.logger.error(f"Error disconnecting MQTT client: {e}")

    async def publish(self, topic: str, message: Any, qos: Optional[int] = None) -> bool:
        """Publish message to topic."""
        try:
            if not self.is_connected:
                self.logger.warning("MQTT client not connected")
                return False

            # Convert message to JSON if it's not a string
            if not isinstance(message, str):
                message = json.dumps(message)

            # In real implementation, this would publish via MQTT
            self.logger.info(f"Publishing to {topic}: {message}")

            # Simulate publish
            await asyncio.sleep(0.01)

            return True

        except Exception as e:
            self.logger.error(f"Failed to publish message: {e}")
            return False

    async def subscribe(self, topic: str, handler: Callable) -> bool:
        """Subscribe to topic with handler."""
        try:
            if not self.is_connected:
                self.logger.warning("MQTT client not connected")
                return False

            self.subscriptions[topic] = handler
            self.logger.info(f"Subscribed to topic: {topic}")

            # In real implementation, this would subscribe via MQTT
            return True

        except Exception as e:
            self.logger.error(f"Failed to subscribe to topic: {e}")
            return False

    async def unsubscribe(self, topic: str) -> bool:
        """Unsubscribe from topic."""
        try:
            if topic in self.subscriptions:
                del self.subscriptions[topic]
                self.logger.info(f"Unsubscribed from topic: {topic}")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Failed to unsubscribe from topic: {e}")
            return False

    async def _message_loop(self):
        """Internal message loop for handling incoming messages."""
        while self.is_connected:
            try:
                # In real implementation, this would listen for MQTT messages
                await asyncio.sleep(0.1)

                # Simulate incoming messages for demo
                for topic, handler in self.subscriptions.items():
                    # This would be replaced with actual MQTT message handling
                    pass

            except Exception as e:
                self.logger.error(f"Error in MQTT message loop: {e}")
                await asyncio.sleep(1)

    def add_message_handler(self, handler: Callable):
        """Add a global message handler."""
        self.message_handlers.append(handler)

    def remove_message_handler(self, handler: Callable):
        """Remove a global message handler."""
        if handler in self.message_handlers:
            self.message_handlers.remove(handler)

    async def get_status(self) -> Dict[str, Any]:
        """Get MQTT client status."""
        return {
            "connected": self.is_connected,
            "broker_host": self.config.broker_host,
            "broker_port": self.config.broker_port,
            "client_id": self.config.client_id,
            "subscriptions": list(self.subscriptions.keys()),
            "message_handlers": len(self.message_handlers)
        }

# Global MQTT client
mqtt_client = None

def initialize_mqtt_client(config: MQTTConfig):
    """Initialize global MQTT client."""
    global mqtt_client
    mqtt_client = MQTTClient(config)
    return mqtt_client

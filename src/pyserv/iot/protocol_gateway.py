"""
Protocol gateway for IoT communication.
Provides unified interface for different IoT protocols.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass

@dataclass
class ProtocolGatewayConfig:
    """Configuration for protocol gateway."""
    enable_mqtt: bool = True
    enable_coap: bool = True
    enable_websocket: bool = True
    enable_http: bool = True
    default_protocol: str = "mqtt"
    message_queue_size: int = 1000
    enable_message_persistence: bool = False

class ProtocolGateway:
    """
    Unified gateway for IoT protocols.
    Provides a single interface for multiple IoT protocols.
    """

    def __init__(self, config: ProtocolGatewayConfig):
        self.config = config
        self.logger = logging.getLogger("protocol_gateway")
        self.mqtt_client = None
        self.coap_server = None
        self.websocket_p2p = None
        self.device_manager = None
        self.message_queue = asyncio.Queue(maxsize=config.message_queue_size)
        self.is_running = False
        self.protocol_handlers: Dict[str, Callable] = {}

    async def start(self) -> bool:
        """Start the protocol gateway."""
        try:
            self.logger.info("Starting IoT Protocol Gateway")
            self.is_running = True

            # Start enabled protocols
            if self.config.enable_mqtt and self.mqtt_client:
                await self.mqtt_client.connect()

            if self.config.enable_coap and self.coap_server:
                await self.coap_server.start()

            if self.config.enable_websocket and self.websocket_p2p:
                await self.websocket_p2p.connect()

            # Start message processing
            asyncio.create_task(self._process_messages())

            self.logger.info("Protocol Gateway started successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to start Protocol Gateway: {e}")
            return False

    async def stop(self):
        """Stop the protocol gateway."""
        try:
            self.is_running = False

            if self.mqtt_client:
                await self.mqtt_client.disconnect()

            if self.coap_server:
                await self.coap_server.stop()

            if self.websocket_p2p:
                await self.websocket_p2p.disconnect()

            self.logger.info("Protocol Gateway stopped")

        except Exception as e:
            self.logger.error(f"Error stopping Protocol Gateway: {e}")

    async def send_message(self, device_id: str, message: Any,
                          protocol: Optional[str] = None) -> bool:
        """Send message to device using specified or default protocol."""
        try:
            protocol = protocol or self.config.default_protocol

            if protocol == "mqtt" and self.mqtt_client:
                topic = f"devices/{device_id}/commands"
                return await self.mqtt_client.publish(topic, message)

            elif protocol == "coap" and self.coap_server:
                # CoAP would use different addressing
                return True

            elif protocol == "websocket" and self.websocket_p2p:
                return await self.websocket_p2p.send_to_peer(device_id, message)

            else:
                self.logger.warning(f"Unsupported protocol: {protocol}")
                return False

        except Exception as e:
            self.logger.error(f"Failed to send message via {protocol}: {e}")
            return False

    async def broadcast_message(self, device_type: str, message: Any,
                              protocol: Optional[str] = None) -> int:
        """Broadcast message to all devices of a type."""
        try:
            protocol = protocol or self.config.default_protocol
            sent_count = 0

            if protocol == "mqtt" and self.mqtt_client:
                topic = f"devices/{device_type}/broadcast"
                if await self.mqtt_client.publish(topic, message):
                    # In real implementation, count would be determined by subscribers
                    sent_count = 1

            elif protocol == "websocket" and self.websocket_p2p:
                sent_count = await self.websocket_p2p.broadcast(message)

            return sent_count

        except Exception as e:
            self.logger.error(f"Failed to broadcast message: {e}")
            return 0

    def register_protocol_handler(self, protocol: str, handler: Callable):
        """Register handler for a specific protocol."""
        self.protocol_handlers[protocol] = handler
        self.logger.info(f"Registered handler for protocol: {protocol}")

    def unregister_protocol_handler(self, protocol: str):
        """Unregister handler for a specific protocol."""
        if protocol in self.protocol_handlers:
            del self.protocol_handlers[protocol]
            self.logger.info(f"Unregistered handler for protocol: {protocol}")

    async def _process_messages(self):
        """Process incoming messages from all protocols."""
        while self.is_running:
            try:
                # In real implementation, this would collect messages from all protocols
                await asyncio.sleep(0.1)

                # Process any queued messages
                while not self.message_queue.empty():
                    try:
                        message = self.message_queue.get_nowait()
                        await self._handle_message(message)
                    except asyncio.QueueEmpty:
                        break

            except Exception as e:
                self.logger.error(f"Error in message processing loop: {e}")
                await asyncio.sleep(1)

    async def _handle_message(self, message: Dict[str, Any]):
        """Handle incoming message."""
        try:
            protocol = message.get("protocol", "unknown")
            device_id = message.get("device_id")
            payload = message.get("payload")

            if protocol in self.protocol_handlers:
                handler = self.protocol_handlers[protocol]
                await handler(device_id, payload)
            else:
                self.logger.warning(f"No handler for protocol: {protocol}")

        except Exception as e:
            self.logger.error(f"Error handling message: {e}")

    async def get_status(self) -> Dict[str, Any]:
        """Get gateway status."""
        status = {
            "running": self.is_running,
            "default_protocol": self.config.default_protocol,
            "enabled_protocols": [],
            "message_queue_size": self.message_queue.qsize(),
            "registered_handlers": list(self.protocol_handlers.keys())
        }

        if self.config.enable_mqtt:
            status["enabled_protocols"].append("mqtt")
            if self.mqtt_client:
                mqtt_status = await self.mqtt_client.get_status()
                status["mqtt"] = mqtt_status

        if self.config.enable_coap:
            status["enabled_protocols"].append("coap")
            if self.coap_server:
                coap_status = await self.coap_server.get_status()
                status["coap"] = coap_status

        if self.config.enable_websocket:
            status["enabled_protocols"].append("websocket")
            if self.websocket_p2p:
                p2p_status = await self.websocket_p2p.get_status()
                status["websocket"] = p2p_status

        return status

    def set_mqtt_client(self, client):
        """Set MQTT client instance."""
        self.mqtt_client = client

    def set_coap_server(self, server):
        """Set CoAP server instance."""
        self.coap_server = server

    def set_websocket_p2p(self, p2p):
        """Set WebSocket P2P instance."""
        self.websocket_p2p = p2p

    def set_device_manager(self, manager):
        """Set device manager instance."""
        self.device_manager = manager

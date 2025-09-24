"""
Device manager for IoT devices.
Manages device registration, authentication, and communication.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime

@dataclass
class DeviceConfig:
    """Configuration for device management."""
    enable_registration: bool = True
    enable_authentication: bool = True
    max_devices: int = 1000
    device_timeout: int = 300  # seconds
    heartbeat_interval: int = 60

@dataclass
class IoTDevice:
    """IoT device information."""
    id: str
    name: str
    device_type: str
    location: Optional[str] = None
    capabilities: List[str] = None
    registered_at: datetime = None
    last_seen: datetime = None
    is_online: bool = False
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []
        if self.metadata is None:
            self.metadata = {}
        if self.registered_at is None:
            self.registered_at = datetime.now()

class DeviceManager:
    """
    Manages IoT devices and their connections.
    """

    def __init__(self, config: DeviceConfig):
        self.config = config
        self.logger = logging.getLogger("device_manager")
        self.devices: Dict[str, IoTDevice] = {}
        self.device_handlers: Dict[str, List[callable]] = {}

    async def register_device(self, device_id: str, name: str, device_type: str,
                            location: Optional[str] = None,
                            capabilities: Optional[List[str]] = None) -> IoTDevice:
        """Register a new IoT device."""
        try:
            if device_id in self.devices:
                raise ValueError(f"Device {device_id} already registered")

            if len(self.devices) >= self.config.max_devices:
                raise ValueError("Maximum number of devices reached")

            device = IoTDevice(
                id=device_id,
                name=name,
                device_type=device_type,
                location=location,
                capabilities=capabilities or [],
                registered_at=datetime.now(),
                last_seen=datetime.now(),
                is_online=True
            )

            self.devices[device_id] = device
            self.logger.info(f"Registered device: {device_id} ({name})")

            return device

        except Exception as e:
            self.logger.error(f"Failed to register device {device_id}: {e}")
            raise

    async def unregister_device(self, device_id: str) -> bool:
        """Unregister an IoT device."""
        try:
            if device_id in self.devices:
                del self.devices[device_id]
                self.logger.info(f"Unregistered device: {device_id}")
                return True
            return False

        except Exception as e:
            self.logger.error(f"Failed to unregister device {device_id}: {e}")
            return False

    async def update_device_status(self, device_id: str, is_online: bool,
                                 metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Update device online status and metadata."""
        try:
            if device_id not in self.devices:
                return False

            device = self.devices[device_id]
            device.is_online = is_online
            device.last_seen = datetime.now()

            if metadata:
                device.metadata.update(metadata)

            return True

        except Exception as e:
            self.logger.error(f"Failed to update device {device_id}: {e}")
            return False

    async def get_device(self, device_id: str) -> Optional[IoTDevice]:
        """Get device by ID."""
        return self.devices.get(device_id)

    async def get_devices_by_type(self, device_type: str) -> List[IoTDevice]:
        """Get all devices of a specific type."""
        return [device for device in self.devices.values()
                if device.device_type == device_type]

    async def get_online_devices(self) -> List[IoTDevice]:
        """Get all online devices."""
        return [device for device in self.devices.values() if device.is_online]

    async def send_command(self, device_id: str, command: str,
                          parameters: Optional[Dict[str, Any]] = None) -> bool:
        """Send command to device."""
        try:
            if device_id not in self.devices:
                return False

            device = self.devices[device_id]
            if not device.is_online:
                self.logger.warning(f"Device {device_id} is offline")
                return False

            # In real implementation, this would send command via MQTT/CoAP
            command_data = {
                "command": command,
                "parameters": parameters or {},
                "timestamp": datetime.now().isoformat()
            }

            self.logger.info(f"Sending command to {device_id}: {command_data}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to send command to {device_id}: {e}")
            return False

    async def broadcast_command(self, device_type: str, command: str,
                              parameters: Optional[Dict[str, Any]] = None) -> int:
        """Broadcast command to all devices of a type."""
        try:
            devices = await self.get_devices_by_type(device_type)
            online_devices = [d for d in devices if d.is_online]

            sent_count = 0
            for device in online_devices:
                if await self.send_command(device.id, command, parameters):
                    sent_count += 1

            self.logger.info(f"Broadcast command '{command}' to {sent_count}/{len(online_devices)} devices")
            return sent_count

        except Exception as e:
            self.logger.error(f"Failed to broadcast command: {e}")
            return 0

    def add_device_handler(self, device_type: str, handler: callable):
        """Add handler for device events."""
        if device_type not in self.device_handlers:
            self.device_handlers[device_type] = []
        self.device_handlers[device_type].append(handler)

    def remove_device_handler(self, device_type: str, handler: callable):
        """Remove handler for device events."""
        if device_type in self.device_handlers:
            if handler in self.device_handlers[device_type]:
                self.device_handlers[device_type].remove(handler)

    async def get_device_stats(self) -> Dict[str, Any]:
        """Get device statistics."""
        total_devices = len(self.devices)
        online_devices = len(await self.get_online_devices())
        devices_by_type = {}

        for device in self.devices.values():
            device_type = device.device_type
            devices_by_type[device_type] = devices_by_type.get(device_type, 0) + 1

        return {
            "total_devices": total_devices,
            "online_devices": online_devices,
            "offline_devices": total_devices - online_devices,
            "devices_by_type": devices_by_type,
            "max_devices": self.config.max_devices
        }

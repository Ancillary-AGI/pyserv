"""
CoAP Server for IoT communication.
Provides Constrained Application Protocol support.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass

@dataclass
class CoAPConfig:
    """Configuration for CoAP server."""
    host: str = "0.0.0.0"
    port: int = 5683
    enable_dtls: bool = False
    cert_file: Optional[str] = None
    key_file: Optional[str] = None

class CoAPServer:
    """
    CoAP server for IoT device communication.
    """

    def __init__(self, config: CoAPConfig):
        self.config = config
        self.logger = logging.getLogger("coap_server")
        self.server = None
        self.is_running = False
        self.resources: Dict[str, Callable] = {}

    async def start(self) -> bool:
        """Start CoAP server."""
        try:
            self.logger.info(f"Starting CoAP server on {self.config.host}:{self.config.port}")
            self.is_running = True

            # In real implementation, this would start a CoAP server
            # For demo purposes, simulate server startup
            await asyncio.sleep(0.5)

            self.logger.info("CoAP server started successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to start CoAP server: {e}")
            return False

    async def stop(self):
        """Stop CoAP server."""
        try:
            self.is_running = False
            self.logger.info("CoAP server stopped")
        except Exception as e:
            self.logger.error(f"Error stopping CoAP server: {e}")

    def add_resource(self, path: str, handler: Callable):
        """Add a CoAP resource."""
        self.resources[path] = handler
        self.logger.info(f"Added CoAP resource: {path}")

    def remove_resource(self, path: str):
        """Remove a CoAP resource."""
        if path in self.resources:
            del self.resources[path]
            self.logger.info(f"Removed CoAP resource: {path}")

    async def handle_request(self, method: str, path: str, payload: bytes) -> bytes:
        """Handle CoAP request."""
        try:
            if path in self.resources:
                handler = self.resources[path]
                # In real implementation, this would call the handler
                return b"OK"
            else:
                return b"NOT_FOUND"

        except Exception as e:
            self.logger.error(f"Error handling CoAP request: {e}")
            return b"ERROR"

    async def get_status(self) -> Dict[str, Any]:
        """Get CoAP server status."""
        return {
            "running": self.is_running,
            "host": self.config.host,
            "port": self.config.port,
            "resources": list(self.resources.keys()),
            "dtls_enabled": self.config.enable_dtls
        }

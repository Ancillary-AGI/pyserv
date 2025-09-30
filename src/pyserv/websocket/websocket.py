import json
from typing import Dict, Any, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from pyserv.server.application import Application

from pyserv.exceptions import WebSocketException

class WebSocket:
    def __init__(self, scope, receive, send, app: "Application"):
        self.scope = scope
        self.receive = receive
        self.send = send
        self.app = app
        self.path = scope["path"]
        self.headers = self._parse_headers(scope["headers"])
        self.query_params = self._parse_query_params(scope.get("query_string", b""))
        self.path_params: Dict[str, Any] = {}
        self.state: Dict[str, Any] = {}
        self.connected = False
        self._close_code: Optional[int] = None
    
    def _parse_headers(self, headers: list) -> Dict[str, str]:
        return {key.decode().lower(): value.decode() for key, value in headers}
    
    def _parse_query_params(self, query_string: bytes) -> Dict[str, List[str]]:
        from urllib.parse import parse_qs
        return parse_qs(query_string.decode())
    
    async def accept(self, subprotocol: Optional[str] = None, headers: Optional[Dict[str, str]] = None) -> None:
        """Accept the WebSocket connection"""
        response_headers = []
        if headers:
            for key, value in headers.items():
                response_headers.append((key.lower().encode(), value.encode()))
        
        if subprotocol:
            response_headers.append((b"sec-websocket-protocol", subprotocol.encode()))
        
        await self.send({
            "type": "websocket.accept",
            "subprotocol": subprotocol,
            "headers": response_headers
        })
        self.connected = True
    
    async def receive_message(self) -> Dict[str, Any]:
        """Receive a WebSocket message"""
        if not self.connected:
            raise WebSocketException("WebSocket is not connected")
        
        message = await self.receive()
        
        if message["type"] == "websocket.disconnect":
            self.connected = False
            raise WebSocketException("WebSocket disconnected", code=1000)
        
        return message
    
    async def receive_text(self) -> str:
        """Receive text message"""
        message = await self.receive_message()
        if message["type"] != "websocket.receive" or "text" not in message:
            raise WebSocketException("Expected text message")
        return message["text"]
    
    async def receive_bytes(self) -> bytes:
        """Receive binary message"""
        message = await self.receive_message()
        if message["type"] != "websocket.receive" or "bytes" not in message:
            raise WebSocketException("Expected binary message")
        return message["bytes"]
    
    async def receive_json(self) -> Any:
        """Receive and parse JSON message"""
        text = await self.receive_text()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            raise WebSocketException("Invalid JSON received")
    
    async def send_text(self, text: str) -> None:
        """Send text message"""
        if not self.connected:
            raise WebSocketException("WebSocket is not connected")
        
        await self.send({
            "type": "websocket.send",
            "text": text
        })
    
    async def send_bytes(self, data: bytes) -> None:
        """Send binary message"""
        if not self.connected:
            raise WebSocketException("WebSocket is not connected")
        
        await self.send({
            "type": "websocket.send",
            "bytes": data
        })
    
    async def send_json(self, data: Any) -> None:
        """Send JSON message"""
        text = json.dumps(data)
        await self.send_text(text)
    
    async def close(self, code: int = 1000, reason: Optional[str] = None) -> None:
        """Close the WebSocket connection"""
        if self.connected:
            await self.send({
                "type": "websocket.close",
                "code": code,
                "reason": reason
            })
            self.connected = False
            self._close_code = code
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.connected:
            await self.close()





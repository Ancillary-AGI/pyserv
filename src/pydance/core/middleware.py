# server_framework/core/middleware.py
from abc import ABC, abstractmethod
from typing import Callable, List, Any, Coroutine, Optional, Union
from dataclasses import dataclass

from .request import Request
from .response import Response
from .websocket import WebSocket

class BaseMiddleware(ABC):
    """Abstract base class for all middleware"""
    
    @abstractmethod
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        pass

class HTTPMiddleware(BaseMiddleware):
    """Abstract base class for HTTP middleware"""
    
    @abstractmethod
    async def process_request(self, request: Request) -> Request:
        pass
        
    @abstractmethod
    async def process_response(self, request: Request, response: Response) -> Response:
        pass
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        request = await self.process_request(request)
        response = await call_next(request)
        return await self.process_response(request, response)

class WebSocketMiddleware(BaseMiddleware):
    """Abstract base class for WebSocket middleware"""
    
    @abstractmethod
    async def process_websocket(self, websocket: WebSocket) -> Optional[WebSocket]:
        pass

# Type aliases
MiddlewareCallable = Callable[[Request, Callable], Coroutine[Any, Any, Response]]
MiddlewareType = Union[MiddlewareCallable, type[HTTPMiddleware], type[WebSocketMiddleware]]
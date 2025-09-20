# server_framework/core/middleware_manager.py
from typing import Callable, List, Optional, Union
from .http.request import Request
from .http.response import Response
from .websocket import WebSocket
from .middleware import HTTPMiddleware, MiddlewareType, WebSocketMiddleware, MiddlewareCallable

class MiddlewareManager:
    """Manages middleware processing for the application"""
    
    def __init__(self):
        self.middleware: List[MiddlewareType] = []
    
    def add(self, middleware: MiddlewareType):
        """Add middleware to the manager"""
        self.middleware.append(middleware)
    
    async def process_http_request(self, request: Request) -> Request:
        """Process HTTP request through all middleware"""
        for middleware in self.middleware:
            if isinstance(middleware, HTTPMiddleware) or hasattr(middleware, 'process_request'):
                request = await middleware.process_request(request)
        return request
    
    async def process_http_response(self, request: Request, response: Response) -> Response:
        """Process HTTP response through all middleware"""
        for middleware in reversed(self.middleware):
            if isinstance(middleware, HTTPMiddleware) or hasattr(middleware, 'process_response'):
                response = await middleware.process_response(request, response)
        return response
    
    async def process_websocket(self, websocket: WebSocket) -> Optional[WebSocket]:
        """Process WebSocket through all middleware"""
        for middleware in self.middleware:
            if isinstance(middleware, WebSocketMiddleware) or hasattr(middleware, 'process_websocket'):
                result = await middleware.process_websocket(websocket)
                if result is None:
                    return None  # Connection rejected
                websocket = result
        return websocket
    
    async def execute_http_chain(self, request: Request, final_handler: Callable) -> Response:
        """Execute the complete HTTP middleware chain"""
        async def dispatch(index: int, req: Request) -> Response:
            if index >= len(self.middleware):
                return await final_handler(req)
            
            middleware = self.middleware[index]
            
            if isinstance(middleware, HTTPMiddleware):
                # Use the __call__ method for consistent interface
                async def call_next(next_req: Request) -> Response:
                    return await dispatch(index + 1, next_req)
                return await middleware(req, call_next)
            
            elif callable(middleware):
                # Function-based middleware
                async def call_next(next_req: Request) -> Response:
                    return await dispatch(index + 1, next_req)
                return await middleware(req, call_next)
            
            else:
                # Skip middleware that can't handle HTTP
                return await dispatch(index + 1, req)
        
        return await dispatch(0, request)

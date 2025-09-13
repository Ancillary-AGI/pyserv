import asyncio
import inspect
import json
from typing import Dict, List, Callable, Any, Optional, Type
from functools import wraps
from contextlib import asynccontextmanager

from .config import AppConfig
from .routing import Router, Route, WebSocketRoute
from .middleware import Middleware, WebSocketMiddleware
from .exceptions import HTTPException
from .templating import TemplateEngineManager
from ..security.middleware import SecurityMiddleware, CSRFMiddleware
from .database import DatabaseConfig, DatabaseConnection
from .request import Request
from .response import Response
from .websocket import WebSocket
from .server import Server
from .middleware_manager import MiddlewareManager
from .middleware import HTTPMiddleware, WebSocketMiddleware, MiddlewareCallable, MiddlewareType 

class Application:
    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or AppConfig()
        self.router = Router()
        self.middleware_manager = MiddlewareManager()
        self.state: Dict[str, Any] = {}
        self.template_engine: Optional[TemplateEngineManager] = None
        self.db_connection: Optional[DatabaseConnection] = None
        self._startup_events: List[Callable] = []
        self._shutdown_events: List[Callable] = []
        self._exception_handlers: Dict[Type[Exception], Callable] = {}
        self._server: Optional[Server] = None
        self._is_running = False
        
        # Default middleware
        self.add_middleware(SecurityMiddleware)
        self.add_middleware(CSRFMiddleware)
    
    def create_server(self) -> Server:
        """Create a server instance for this application"""
        if self._server is None:
            from .server import Server
            self._server = Server(self, self.config)
        return self._server
    
    async def serve(self, **kwargs) -> None:
        """Start serving requests (non-blocking)"""
        if self._server is None:
            self._server = Server(self, self.config)
        
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        
        self._is_running = True
        await self._server.start()
    
    async def stop(self) -> None:
        """Stop the server"""
        if self._server:
            await self._server.shutdown()
        self._is_running = False
    
    def run(self, **kwargs) -> None:
        """Run the server (blocking)"""
        server = self.create_server()
        
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        
        server.run()
    
    def add_middleware(self, middleware: MiddlewareType, **options) -> None:
        if isinstance(middleware, type) and (
            issubclass(middleware, HTTPMiddleware) or 
            issubclass(middleware, WebSocketMiddleware)
        ):
            self.middleware_manager.add(middleware(**options))
        else:
            if options:
                wrapped_middleware = self._wrap_callable_middleware(middleware, options)
                self.middleware_manager.add(wrapped_middleware)
            else:
                self.middleware_manager.add(middleware)
    
    def _wrap_callable_middleware(self, middleware: MiddlewareCallable, options: dict) -> MiddlewareCallable:
        """Wrap callable middleware with options"""
        @wraps(middleware)
        async def wrapped_middleware(request, call_next):
            # Store options in request state
            if not hasattr(request, 'state'):
                request.state = type('State', (), {})()
            request.state.middleware_options = options
            return await middleware(request, call_next)
        return wrapped_middleware
    
    def on_startup(self, func: Callable) -> Callable:
        """Register a startup task"""
        self._startup_events.append(func)
        return func
    
    def on_shutdown(self, func: Callable) -> Callable:
        """Register a shutdown task"""
        self._shutdown_events.append(func)
        return func
    
    def exception_handler(self, exc_class: Type[Exception]) -> Callable:
        def decorator(func: Callable) -> Callable:
            self._exception_handlers[exc_class] = func
            return func
        return decorator
    
    def route(self, path: str, methods: Optional[List[str]] = None, **kwargs) -> Callable:
        def decorator(func: Callable) -> Callable:
            self.router.add_route(path, func, methods, **kwargs)
            return func
        return decorator
    
    def websocket_route(self, path: str, **kwargs) -> Callable:
        def decorator(func: Callable) -> Callable:
            self.router.add_websocket_route(path, func, **kwargs)
            return func
        return decorator
    
    def mount(self, path: str, app: 'Application') -> None:
        self.router.mount(path, app.router)
    
    async def startup(self) -> None:
        # Initialize database
        if self.config.database_url:
            db_config = DatabaseConfig(self.config.database_url)
            self.db_connection = DatabaseConnection.get_instance(db_config)
            await self.db_connection.connect()
        
        # Initialize template engine
        self.template_engine = TemplateEngineManager(self.config.template_dir)
        
        # Run startup events
        for event in self._startup_events:
            if inspect.iscoroutinefunction(event):
                await event(self)
            else:
                event(self)
    
    async def shutdown(self) -> None:
        # Run shutdown events
        for event in self._shutdown_events:
            if inspect.iscoroutinefunction(event):
                await event(self)
            else:
                event(self)
        
        # Close database connection
        if self.db_connection:
            await self.db_connection.disconnect()
    
    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] == "lifespan":
            await self.handle_lifespan(scope, receive, send)
        elif scope["type"] == "http":
            await self.handle_http(scope, receive, send)
        elif scope["type"] == "websocket":
            await self.handle_websocket(scope, receive, send)
    
    async def handle_lifespan(self, scope, receive, send) -> None:
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                try:
                    await self.startup()
                    await send({"type": "lifespan.startup.complete"})
                except Exception as e:
                    await send({"type": "lifespan.startup.failed", "message": str(e)})
            elif message["type"] == "lifespan.shutdown":
                try:
                    await self.shutdown()
                    await send({"type": "lifespan.shutdown.complete"})
                except Exception as e:
                    await send({"type": "lifespan.shutdown.failed", "message": str(e)})
                break
    
    async def handle_http(self, scope, receive, send) -> None:
        """Handle HTTP requests using middleware manager"""
        try:
            request = Request(scope, receive, send, self)
            
            # Process request through middleware
            request = await self.middleware_manager.process_http_request(request)
            
            # Execute middleware chain
            async def final_handler(req: Request) -> Response:
                route, path_params = self.router.match(req.method, req.path)
                if not route:
                    from .exceptions import HTTPException
                    raise HTTPException(404, "Not Found")
                
                req.path_params = path_params
                return await route.handler(req)
            
            response = await self.middleware_manager.execute_http_chain(request, final_handler)
            
            # Process response through middleware
            response = await self.middleware_manager.process_http_response(request, response)
            
            await response(scope, receive, send)
            
        except Exception as exc:
            await self.handle_exception(exc, scope, receive, send)
    
    async def handle_websocket(self, scope, receive, send) -> None:
        """Handle WebSocket connections using middleware manager"""
        try:
            websocket = WebSocket(scope, receive, send, self)
            
            # Process WebSocket through middleware
            websocket = await self.middleware_manager.process_websocket(websocket)
            if websocket is None:
                await send({"type": "websocket.close", "code": 1008})
                return
            
            # Route and handle WebSocket
            route, path_params = self.router.match_websocket(websocket.path)
            if not route:
                await websocket.close(1008, "No route found")
                return
            
            websocket.path_params = path_params or {}
            await route.handler(websocket)
            
        except Exception as exc:
            await self.handle_websocket_exception(exc, scope, receive, send)
    
    async def handle_exception(self, exc: Exception, scope, receive, send) -> None:
        handler = self._exception_handlers.get(type(exc))
        if handler:
            response = await handler(exc)
            await response(scope, receive, send)
        else:
            if isinstance(exc, HTTPException):
                response = Response(exc.detail, status_code=exc.status_code)
            else:
                response = Response("Internal Server Error", status_code=500)
            await response(scope, receive, send)

    async def handle_websocket_exception(self, exc: Exception, scope, receive, send) -> None:
        """Handle WebSocket exceptions gracefully"""
        try:
            websocket = WebSocket(scope, receive, send, self)
            
            # Only try to handle if we're not already connected
            if not websocket.connected:
                try:
                    await websocket.accept()  # Accept first to send close message
                except Exception:
                    pass  # If we can't accept, we'll try to close directly
            
            # Check if we have a custom exception handler
            handler = self._exception_handlers.get(type(exc))
            if handler:
                try:
                    await handler(exc, websocket)
                    return
                except Exception:
                    # Fall through to default handling if custom handler fails
                    pass
            
            # Default WebSocket exception handling
            if isinstance(exc, WebSocketException):
                await websocket.close(exc.ws_code, str(exc.detail))
            elif isinstance(exc, HTTPException):
                await websocket.close(1008, f"HTTP Error: {exc.detail}")
            elif isinstance(exc, WebSocketDisconnect):
                await websocket.close(exc.code, exc.reason)
            else:
                # Generic server error
                error_msg = str(exc) if self.debug else "Internal server error"
                await websocket.close(1011, error_msg)
                
        except Exception:
            # Final fallback - try to close the connection
            try:
                await send({"type": "websocket.close", "code": 1011})
            except Exception:
                pass  # We've done all we can
    
    @property
    def debug(self) -> bool:
        return self.config.debug

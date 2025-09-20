"""
PyDance Core Types - Type definitions for the framework.
"""

from typing import Dict, List, Any, Callable, Awaitable, Union

# ASGI types
Scope = Dict[str, Any]
Message = Dict[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]

# Handler types
Handler = Callable[..., Any]
AsyncHandler = Callable[..., Awaitable[Any]]

# Middleware types
Middleware = Callable[[Handler], Handler]
AsyncMiddleware = Callable[[AsyncHandler], AsyncHandler]

# Dependency injection types
ServiceFactory = Callable[[], Any]
ServiceLifetime = str

# Route types
RouteHandler = Union[Handler, AsyncHandler]
RouteMethods = List[str]
RouteParams = Dict[str, Any]

# Config types
ConfigValue = Union[str, int, float, bool, List[Any], Dict[str, Any]]

from typing import Dict, Any, Callable, Optional, Union, List

# WebSocket route type
WebSocketRouteType = Callable[..., Any]

# Middleware type
MiddlewareType = Callable[..., Any]

# Handler type
HandlerType = Callable[..., Any]

# Path parameter type
PathParams = Dict[str, Any]

# Query parameter type
QueryParams = Dict[str, str]

# Header type
Headers = Dict[str, str]

# Cookie type
Cookies = Dict[str, str]

# Request body type
RequestBody = Union[str, bytes, Dict[str, Any], List[Any], None]

# Response body type
ResponseBody = Union[str, bytes, Dict[str, Any], List[Any], None]

# ASGI scope type
Scope = Dict[str, Any]

# ASGI receive callable
Receive = Callable[[], Any]

# ASGI send callable
Send = Callable[[Dict[str, Any]], None]

# ASGI app type
ASGIApp = Callable[[Scope, Receive, Send], None]

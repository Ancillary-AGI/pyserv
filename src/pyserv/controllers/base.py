"""
Base controller classes for Pyserv  MVC framework.
"""

import asyncio
from typing import Dict, Any, Optional, Callable, List, Union
import inspect

from pyserv.http.request import Request
from pyserv.http.response import Response
from pyserv.server.application import Application

from pyserv.middleware.resolver import middleware_resolver


class BaseController:
    """Base controller class with common functionality"""

    def __init__(self, app: Application):
        self.app = app
        self.request: Optional[Request] = None
        self._before_actions: Dict[str, list] = {}
        self._after_actions: Dict[str, list] = {}

    def before_action(self, action_name: str, func: Callable):
        """Register a before action hook"""
        if action_name not in self._before_actions:
            self._before_actions[action_name] = []
        self._before_actions[action_name].append(func)

    def after_action(self, action_name: str, func: Callable):
        """Register an after action hook"""
        if action_name not in self._after_actions:
            self._after_actions[action_name] = []
        self._after_actions[action_name].append(func)

    async def _execute_before_actions(self, action_name: str):
        """Execute before action hooks"""
        if action_name in self._before_actions:
            for func in self._before_actions[action_name]:
                if inspect.iscoroutinefunction(func):
                    await func(self)
                else:
                    func(self)

    async def _execute_after_actions(self, action_name: str, response):
        """Execute after action hooks"""
        if action_name in self._after_actions:
            for func in self._after_actions[action_name]:
                if inspect.iscoroutinefunction(func):
                    await func(self, response)
                else:
                    func(self, response)

    def render(self, template: str, **context) -> Response:
        """Render a template"""
        if self.app.template_engine:
            content = self.app.template_engine.render(template, **context)
            return Response.html(content)
        else:
            return Response.text(f"Template engine not configured: {template}", status_code=500)

    def json(self, data: Any, status_code: int = 200) -> Response:
        """Return JSON response"""
        return Response.json(data, status_code=status_code)

    def redirect(self, url: str, status_code: int = 302) -> Response:
        """Redirect to URL"""
        return Response.redirect(url, status_code)

    def not_found(self, message: str = "Not Found") -> Response:
        """Return 404 response"""
        return Response.json({"error": message}, status_code=404)

    def bad_request(self, message: str = "Bad Request") -> Response:
        """Return 400 response"""
        return Response.json({"error": message}, status_code=400)

    def unauthorized(self, message: str = "Unauthorized") -> Response:
        """Return 401 response"""
        return Response.json({"error": message}, status_code=401)

    def forbidden(self, message: str = "Forbidden") -> Response:
        """Return 403 response"""
        return Response.json({"error": message}, status_code=403)

    def server_error(self, message: str = "Internal Server Error") -> Response:
        """Return 500 response"""
        return Response.json({"error": message}, status_code=500)


class Controller(BaseController):
    """Main controller class with automatic routing and middleware support"""

    # Class-level middleware (applied to all routes in this controller)
    middleware: List[Union[str, Callable]] = []

    @classmethod
    def register_routes(cls, app: Application, prefix: str = ""):
        """Automatically register routes for controller methods with middleware support"""
        controller_name = cls.__name__.lower().replace('controller', '')

        # Resolve controller-level middleware
        controller_middleware = middleware_resolver.resolve_list(cls.middleware)

        for method_name in dir(cls):
            if not method_name.startswith('_') and callable(getattr(cls, method_name)):
                method = getattr(cls, method_name)

                # Check for HTTP method decorators
                if hasattr(method, '_http_methods'):
                    http_methods = method._http_methods
                    route_path = f"{prefix}/{controller_name}/{method_name}"

                    # Combine controller middleware with any method-specific middleware
                    method_middleware = getattr(method, '_middleware', [])
                    resolved_method_middleware = middleware_resolver.resolve_list(method_middleware)
                    combined_middleware = controller_middleware + resolved_method_middleware

                    # Create route handler with middleware pipeline
                    async def route_handler(request):
                        # Apply middleware pipeline
                        async def execute_controller_logic(req):
                            controller_instance = cls(app)
                            controller_instance.request = req

                            # Execute before actions
                            await controller_instance._execute_before_actions(method_name)

                            # Execute action
                            if inspect.iscoroutinefunction(method):
                                result = await method(controller_instance)
                            else:
                                result = method(controller_instance)

                            # Convert result to response (if not already a Response)
                            if isinstance(result, Response):
                                response = result
                            elif isinstance(result, dict):
                                response = Response.json(result)
                            else:
                                response = Response.text(str(result))

                            # Execute after actions
                            await controller_instance._execute_after_actions(method_name, response)

                            return response

                        # Execute middleware pipeline
                        if combined_middleware:
                            # Apply middleware in reverse order (last middleware wraps first)
                            handler = execute_controller_logic
                            for middleware_func in reversed(combined_middleware):
                                if asyncio.iscoroutinefunction(middleware_func):
                                    async def middleware_wrapper(req, next_handler=handler, mw=middleware_func):
                                        return await mw(req, next_handler)
                                    handler = middleware_wrapper
                                else:
                                    def middleware_wrapper(req, next_handler=handler, mw=middleware_func):
                                        return mw(req, next_handler)
                                    handler = middleware_wrapper

                            return await handler(request)
                        else:
                            # No middleware, execute directly
                            return await execute_controller_logic(request)

                    # Register route for each HTTP method
                    for http_method in http_methods:
                        app.router.add_route(route_path, route_handler, [http_method], middleware=combined_middleware)


def http_method(*methods: str):
    """Decorator to specify HTTP methods for controller actions"""
    def decorator(func: Callable) -> Callable:
        func._http_methods = methods
        return func
    return decorator


# HTTP method decorators
def get(func: Callable) -> Callable:
    """GET method decorator"""
    return http_method('GET')(func)

def post(func: Callable) -> Callable:
    """POST method decorator"""
    return http_method('POST')(func)

def put(func: Callable) -> Callable:
    """PUT method decorator"""
    return http_method('PUT')(func)

def delete(func: Callable) -> Callable:
    """DELETE method decorator"""
    return http_method('DELETE')(func)

def patch(func: Callable) -> Callable:
    """PATCH method decorator"""
    return http_method('PATCH')(func)


def middleware(*middleware_specs: Union[str, Callable]):
    """Decorator to apply middleware to controller methods"""
    def decorator(func: Callable) -> Callable:
        if not hasattr(func, '_middleware'):
            func._middleware = []
        # Resolve middleware specs and store them
        func._middleware.extend(middleware_specs)
        return func
    return decorator

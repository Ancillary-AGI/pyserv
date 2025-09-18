"""
Base controller classes for PyDance MVC framework.
"""

from typing import Dict, Any, Optional, Callable, Type, Union
from functools import wraps
import inspect

from ..core.request import Request
from ..core.response import Response
from ..core.server.application import Application
from ..core.exceptions import HTTPException, BadRequest, Unauthorized, Forbidden, NotFound, InternalServerError


class ControllerResponse:
    """Response wrapper for controllers"""

    def __init__(self, data: Any = None, status_code: int = 200,
                 headers: Optional[Dict[str, str]] = None,
                 template: Optional[str] = None):
        self.data = data
        self.status_code = status_code
        self.headers = headers or {}
        self.template = template

    def to_response(self, app: Application) -> Response:
        """Convert to framework Response object"""
        if self.template and app.template_engine:
            # Render template
            content = app.template_engine.render(self.template, **self.data)
            return Response(content, status_code=self.status_code,
                          headers=self.headers, content_type='text/html')
        elif isinstance(self.data, dict):
            # JSON response
            import json
            return Response(json.dumps(self.data), status_code=self.status_code,
                          headers=self.headers, content_type='application/json')
        else:
            # Plain response
            return Response(str(self.data), status_code=self.status_code,
                          headers=self.headers)


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

    def render(self, template: str, **context) -> ControllerResponse:
        """Render a template"""
        return ControllerResponse(context, template=template)

    def json(self, data: Any, status_code: int = 200) -> ControllerResponse:
        """Return JSON response"""
        return ControllerResponse(data, status_code=status_code)

    def redirect(self, url: str, status_code: int = 302) -> ControllerResponse:
        """Redirect to URL"""
        return ControllerResponse("", status_code=status_code,
                                headers={"Location": url})

    def not_found(self, message: str = "Not Found") -> ControllerResponse:
        """Return 404 response"""
        return ControllerResponse({"error": message}, status_code=404)

    def bad_request(self, message: str = "Bad Request") -> ControllerResponse:
        """Return 400 response"""
        return ControllerResponse({"error": message}, status_code=400)

    def unauthorized(self, message: str = "Unauthorized") -> ControllerResponse:
        """Return 401 response"""
        return ControllerResponse({"error": message}, status_code=401)

    def forbidden(self, message: str = "Forbidden") -> ControllerResponse:
        """Return 403 response"""
        return ControllerResponse({"error": message}, status_code=403)

    def server_error(self, message: str = "Internal Server Error") -> ControllerResponse:
        """Return 500 response"""
        return ControllerResponse({"error": message}, status_code=500)


class Controller(BaseController):
    """Main controller class with automatic routing"""

    @classmethod
    def register_routes(cls, app: Application, prefix: str = ""):
        """Automatically register routes for controller methods"""
        controller_name = cls.__name__.lower().replace('controller', '')

        for method_name in dir(cls):
            if not method_name.startswith('_') and callable(getattr(cls, method_name)):
                method = getattr(cls, method_name)

                # Check for HTTP method decorators
                if hasattr(method, '_http_methods'):
                    http_methods = method._http_methods
                    route_path = f"{prefix}/{controller_name}/{method_name}"

                    # Create route handler
                    async def route_handler(request):
                        controller_instance = cls(app)
                        controller_instance.request = request

                        # Execute before actions
                        await controller_instance._execute_before_actions(method_name)

                        # Execute action
                        if inspect.iscoroutinefunction(method):
                            result = await method(controller_instance)
                        else:
                            result = method(controller_instance)

                        # Convert result to response
                        if isinstance(result, ControllerResponse):
                            response = result.to_response(app)
                        elif isinstance(result, dict):
                            response = ControllerResponse(result).to_response(app)
                        else:
                            response = ControllerResponse(str(result)).to_response(app)

                        # Execute after actions
                        await controller_instance._execute_after_actions(method_name, response)

                        return response

                    # Register route for each HTTP method
                    for http_method in http_methods:
                        app.router.add_route(route_path, route_handler, [http_method])


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

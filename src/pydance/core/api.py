"""
REST API development tools for PyDance framework.
Provides resource controllers, serialization, versioning, and API documentation.
"""

import json
import inspect
from typing import Dict, List, Any, Optional, Union, Type, Callable, get_type_hints
from functools import wraps
from datetime import datetime
from urllib.parse import urlparse, parse_qs

from ..core.response import Response
from ..core.request import Request
from ..core.exceptions import HTTPException, ValidationError, PermissionDenied, NotFound, APIException
from ..core.pagination import Pagination, PageNumberPagination, LimitOffsetPagination
from ..models.base import BaseModel
from ..core.auth import login_required, permission_required


class Serializer:
    """Base serializer class"""

    def __init__(self, instance=None, data=None, many=False, **kwargs):
        self.instance = instance
        self.data = data or {}
        self.many = many
        self.errors = {}
        self.validated_data = {}

    def serialize(self, instance) -> Dict[str, Any]:
        """Convert instance to dictionary"""
        if hasattr(instance, 'to_dict'):
            return instance.to_dict()
        return dict(instance) if hasattr(instance, '__dict__') else {}

    def deserialize(self, data: Dict[str, Any]) -> Any:
        """Convert dictionary to instance"""
        raise NotImplementedError

    def is_valid(self) -> bool:
        """Validate the data"""
        try:
            self.validated_data = self.deserialize(self.data)
            return True
        except Exception as e:
            self.errors['non_field_errors'] = [str(e)]
            return False

    def save(self) -> Any:
        """Save the validated data"""
        if not self.is_valid():
            raise ValueError("Data is not valid")

        if self.instance:
            # Update existing instance
            for key, value in self.validated_data.items():
                if hasattr(self.instance, key):
                    setattr(self.instance, key, value)
            return self.instance
        else:
            # Create new instance
            return self.validated_data


class ModelSerializer(Serializer):
    """Serializer for model instances"""

    class Meta:
        model = None
        fields = None
        exclude = None
        read_only_fields = None

    def __init__(self, instance=None, data=None, many=False, **kwargs):
        super().__init__(instance, data, many, **kwargs)

        # Get fields from Meta class
        self.model = getattr(self.Meta, 'model', None)
        self.fields = getattr(self.Meta, 'fields', None)
        self.exclude = getattr(self.Meta, 'exclude', None)
        self.read_only_fields = getattr(self.Meta, 'read_only_fields', None) or []

    def serialize(self, instance) -> Dict[str, Any]:
        """Convert model instance to dictionary"""
        if self.model and hasattr(instance, 'to_dict'):
            data = instance.to_dict()
        else:
            data = super().serialize(instance)

        # Apply field filtering
        if self.fields:
            data = {k: v for k, v in data.items() if k in self.fields}
        elif self.exclude:
            data = {k: v for k, v in data.items() if k not in self.exclude}

        return data

    def deserialize(self, data: Dict[str, Any]) -> Any:
        """Convert dictionary to model instance"""
        if not self.model:
            return data

        # Remove read-only fields
        for field in self.read_only_fields:
            data.pop(field, None)

        # Create or update instance
        if self.instance:
            for key, value in data.items():
                if hasattr(self.instance, key):
                    setattr(self.instance, key, value)
            return self.instance
        else:
            return self.model(**data)


class APIView:
    """Base API view class"""

    def __init__(self):
        self.request = None

    def dispatch(self, request: Request) -> Response:
        """Dispatch request to appropriate handler"""
        self.request = request
        method = request.method.lower()

        if hasattr(self, method):
            handler = getattr(self, method)
            return handler(request)
        else:
            return Response("Method not allowed", status_code=405)

    def get(self, request: Request) -> Response:
        """Handle GET request"""
        return Response("Method not implemented", status_code=501)

    def post(self, request: Request) -> Response:
        """Handle POST request"""
        return Response("Method not implemented", status_code=501)

    def put(self, request: Request) -> Response:
        """Handle PUT request"""
        return Response("Method not implemented", status_code=501)

    def patch(self, request: Request) -> Response:
        """Handle PATCH request"""
        return Response("Method not implemented", status_code=501)

    def delete(self, request: Request) -> Response:
        """Handle DELETE request"""
        return Response("Method not implemented", status_code=501)


class GenericAPIView(APIView):
    """Generic API view with common functionality"""

    queryset = None
    serializer_class = None
    lookup_field = 'id'
    lookup_url_kwarg = None

    def get_queryset(self):
        """Get the queryset for this view"""
        return self.queryset

    def get_serializer_class(self):
        """Get the serializer class for this view"""
        return self.serializer_class

    def get_serializer(self, *args, **kwargs):
        """Get serializer instance"""
        serializer_class = self.get_serializer_class()
        if serializer_class:
            return serializer_class(*args, **kwargs)
        return None

    def get_object(self):
        """Get object for detail views"""
        queryset = self.get_queryset()
        if not queryset:
            raise HTTPException(404, "Not found")

        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_value = self.request.path_params.get(lookup_url_kwarg)

        if not lookup_value:
            raise HTTPException(404, "Not found")

        # This would need to be implemented based on the queryset type
        # For now, return None
        return None


class ListAPIView(GenericAPIView):
    """API view for listing objects"""

    def get(self, request: Request) -> Response:
        """List objects"""
        queryset = self.get_queryset()
        if not queryset:
            return Response([])

        # Apply pagination
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))

        # This would need proper queryset implementation
        # For now, return empty list
        data = []

        serializer = self.get_serializer(data, many=True)
        if serializer:
            data = serializer.serialize(data)

        return Response(data)


class CreateAPIView(GenericAPIView):
    """API view for creating objects"""

    def post(self, request: Request) -> Response:
        """Create new object"""
        serializer = self.get_serializer(data=request.data)
        if serializer and serializer.is_valid():
            instance = serializer.save()
            response_data = serializer.serialize(instance)
            return Response(response_data, status_code=201)
        else:
            return Response(serializer.errors if serializer else {}, status_code=400)


class RetrieveAPIView(GenericAPIView):
    """API view for retrieving single object"""

    def get(self, request: Request) -> Response:
        """Retrieve object"""
        instance = self.get_object()
        if not instance:
            return Response({"error": "Not found"}, status_code=404)

        serializer = self.get_serializer(instance)
        if serializer:
            data = serializer.serialize(instance)
            return Response(data)
        return Response(instance)


class UpdateAPIView(GenericAPIView):
    """API view for updating objects"""

    def put(self, request: Request) -> Response:
        """Update object"""
        instance = self.get_object()
        if not instance:
            return Response({"error": "Not found"}, status_code=404)

        serializer = self.get_serializer(instance, data=request.data)
        if serializer and serializer.is_valid():
            instance = serializer.save()
            response_data = serializer.serialize(instance)
            return Response(response_data)
        else:
            return Response(serializer.errors if serializer else {}, status_code=400)

    def patch(self, request: Request) -> Response:
        """Partial update object"""
        return self.put(request)


class DestroyAPIView(GenericAPIView):
    """API view for deleting objects"""

    def delete(self, request: Request) -> Response:
        """Delete object"""
        instance = self.get_object()
        if not instance:
            return Response({"error": "Not found"}, status_code=404)

        # This would need proper deletion implementation
        return Response(status_code=204)


class ListCreateAPIView(ListAPIView, CreateAPIView):
    """API view for listing and creating objects"""
    pass


class RetrieveUpdateAPIView(RetrieveAPIView, UpdateAPIView):
    """API view for retrieving and updating objects"""
    pass


class RetrieveUpdateDestroyAPIView(RetrieveUpdateAPIView, DestroyAPIView):
    """API view for retrieving, updating and deleting objects"""
    pass


class ViewSet:
    """ViewSet for grouping related views"""

    def __init__(self):
        self.basename = None
        self.detail = None

    def get_queryset(self):
        """Get queryset for this viewset"""
        return getattr(self, 'queryset', None)

    def get_serializer_class(self):
        """Get serializer class for this viewset"""
        return getattr(self, 'serializer_class', None)

    @classmethod
    def as_view(cls, actions=None, **kwargs):
        """Create view functions from viewset"""
        actions = actions or {}

        def view_func(request, *args, **kwargs):
            viewset = cls()
            viewset.request = request
            viewset.kwargs = kwargs

            action = actions.get(request.method.lower())
            if action and hasattr(viewset, action):
                method = getattr(viewset, action)
                return method(request, *args, **kwargs)
            else:
                return Response("Method not allowed", status_code=405)

        return view_func


class ModelViewSet(ViewSet):
    """Model ViewSet with default CRUD operations"""

    def list(self, request):
        """List objects"""
        queryset = self.get_queryset()
        serializer_class = self.get_serializer_class()

        # This would need proper implementation
        data = []
        if serializer_class:
            serializer = serializer_class(data, many=True)
            data = serializer.serialize(data)

        return Response(data)

    def create(self, request):
        """Create object"""
        serializer_class = self.get_serializer_class()
        if serializer_class:
            serializer = serializer_class(data=request.data)
            if serializer.is_valid():
                instance = serializer.save()
                response_data = serializer.serialize(instance)
                return Response(response_data, status_code=201)
            else:
                return Response(serializer.errors, status_code=400)
        return Response({"error": "No serializer"}, status_code=500)

    def retrieve(self, request, pk=None):
        """Retrieve object"""
        # This would need proper implementation
        return Response({"error": "Not found"}, status_code=404)

    def update(self, request, pk=None):
        """Update object"""
        # This would need proper implementation
        return Response({"error": "Not found"}, status_code=404)

    def destroy(self, request, pk=None):
        """Delete object"""
        # This would need proper implementation
        return Response({"error": "Not found"}, status_code=404)


class APIRouter:
    """Router for API endpoints"""

    def __init__(self):
        self.routes = []

    def add_api_view(self, path: str, view_class: Type[APIView], name: str = None):
        """Add API view to router"""
        self.routes.append({
            'path': path,
            'view_class': view_class,
            'name': name,
            'type': 'view'
        })

    def add_viewset(self, prefix: str, viewset_class: Type[ViewSet], basename: str = None):
        """Add viewset to router"""
        self.routes.append({
            'prefix': prefix,
            'viewset_class': viewset_class,
            'basename': basename,
            'type': 'viewset'
        })

    def get_routes(self):
        """Get all routes"""
        return self.routes





class APIVersioning:
    """API versioning"""

    def __init__(self, default_version: str = 'v1'):
        self.default_version = default_version

    def get_version(self, request: Request) -> str:
        """Get API version from request"""
        # Try different methods to get version
        version = None

        # From URL path
        if 'version' in request.path_params:
            version = request.path_params['version']

        # From Accept header
        accept = request.headers.get('Accept', '')
        if 'version=' in accept:
            version = accept.split('version=')[1].split(';')[0]

        # From query parameter
        if not version:
            version = request.query_params.get('version')

        return version or self.default_version





class Throttling:
    """API throttling"""

    def __init__(self, rate: str = '100/hour'):
        self.rate = rate
        self.parse_rate()

    def parse_rate(self):
        """Parse rate string"""
        # Simple parsing: "100/hour" -> 100 requests per hour
        if '/' in self.rate:
            num, period = self.rate.split('/')
            self.requests = int(num)
            self.period = period
        else:
            self.requests = 100
            self.period = 'hour'

    def allow_request(self, request: Request) -> bool:
        """Check if request is allowed"""
        # This would need proper implementation with caching
        # For now, always allow
        return True


class APIResponse(Response):
    """API response with additional features"""

    def __init__(self, data=None, status_code: int = 200, headers: Dict[str, str] = None):
        if isinstance(data, dict):
            content = json.dumps(data)
            headers = headers or {}
            headers['Content-Type'] = 'application/json'
        else:
            content = data

        super().__init__(content, status_code, headers)


# Decorators
def api_view(http_method_names: List[str] = None):
    """Decorator for API views"""
    def decorator(func: Callable) -> Callable:
        func.http_method_names = http_method_names or ['GET']
        func.api_view = True

        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            if request.method.upper() not in func.http_method_names:
                return APIResponse({"error": "Method not allowed"}, 405)

            try:
                result = await func(request, *args, **kwargs) if inspect.iscoroutinefunction(func) else func(request, *args, **kwargs)
                return APIResponse(result)
            except APIException as e:
                return APIResponse({"error": e.detail, "code": e.code}, e.status_code)
            except Exception as e:
                return APIResponse({"error": str(e)}, 500)

        return wrapper
    return decorator


# Global instances
api_router = APIRouter()
pagination = PageNumberPagination()
versioning = APIVersioning()

__all__ = [
    'Serializer', 'ModelSerializer', 'APIView', 'GenericAPIView',
    'ListAPIView', 'CreateAPIView', 'RetrieveAPIView', 'UpdateAPIView', 'DestroyAPIView',
    'ListCreateAPIView', 'RetrieveUpdateAPIView', 'RetrieveUpdateDestroyAPIView',
    'ViewSet', 'ModelViewSet', 'APIRouter', 'Pagination', 'PageNumberPagination',
    'LimitOffsetPagination', 'APIVersioning', 'APIException', 'ValidationError',
    'PermissionDenied', 'NotFound', 'Throttling', 'APIResponse',
    'api_view', 'api_router', 'pagination', 'versioning'
]

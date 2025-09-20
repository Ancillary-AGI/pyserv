"""
API Resource Controllers for PyDance framework.
Provides RESTful API controllers with automatic CRUD operations.
"""

from typing import Dict, Any, Optional, List, Type, Union, Generic, TypeVar
from abc import ABC, abstractmethod
import json

from .base import Controller, ControllerResponse, get, post, put, delete, patch
from ..core.http.request import Request
from ..core.http.response import Response
from ..core.exceptions import HTTPException, BadRequest, NotFound, RateLimitExceeded
from ..core.rate_limiting import RateLimiter, default_rate_limiter
from ..core.pagination import PaginationParams, PageNumberPaginator, paginate
from ..models.base import BaseModel
from ..core.form_validation import Form, ValidationError
from ..docs import api_endpoint, APIEndpoint, APISchema, get_api_docs

T = TypeVar('T', bound=BaseModel)


class APIResourceController(Controller, Generic[T]):
    """Base API resource controller with CRUD operations"""

    model_class: Type[T] = None
    serializer_class = None
    queryset = None
    pagination_class = None
    filter_backends = []
    permission_classes = []
    authentication_classes = []

    def __init__(self, app):
        super().__init__(app)
        if not self.model_class:
            raise ValueError("model_class must be defined")

    def get_queryset(self):
        """Get the queryset for this controller"""
        if self.queryset is not None:
            return self.queryset
        return self.model_class.query()

    def get_object(self, pk):
        """Get a single object by primary key"""
        queryset = self.get_queryset()
        obj = queryset.filter(id=pk).first()
        if not obj:
            raise NotFound(f"{self.model_class.__name__} not found")
        return obj

    def get_serializer(self, instance=None, data=None, many=False):
        """Get serializer instance"""
        if self.serializer_class:
            return self.serializer_class(instance=instance, data=data, many=many)
        return None

    def serialize(self, instance, many=False):
        """Serialize model instance(s)"""
        if isinstance(instance, list) or many:
            return [obj.to_dict() for obj in instance] if instance else []
        return instance.to_dict() if instance else None

    def paginate_queryset(self, queryset, request):
        """Paginate queryset if pagination is enabled"""
        if not self.pagination_class:
            return queryset

        paginator = self.pagination_class()
        return paginator.paginate_queryset(queryset, request)

    def filter_queryset(self, queryset, request):
        """Filter queryset based on request parameters"""
        for backend in self.filter_backends:
            queryset = backend().filter_queryset(request, queryset, self)
        return queryset

    @get
    async def list(self):
        """List all objects"""
        queryset = self.get_queryset()
        queryset = self.filter_queryset(queryset, self.request)

        # Pagination
        page = self.paginate_queryset(queryset, self.request)
        if page is not None:
            data = self.serialize(page, many=True)
            return self.json({
                'results': data,
                'count': page.paginator.count,
                'next': page.next_page_number() if page.has_next() else None,
                'previous': page.previous_page_number() if page.has_previous() else None
            })

        # No pagination
        objects = await queryset.all()
        data = self.serialize(objects, many=True)
        return self.json(data)

    @get
    async def retrieve(self, id: int):
        """Retrieve a single object"""
        obj = await self.get_object(id)
        data = self.serialize(obj)
        return self.json(data)

    @post
    async def create(self):
        """Create a new object"""
        data = await self.request.json()

        # Validate data
        serializer = self.get_serializer(data=data)
        if serializer:
            if not serializer.is_valid():
                return self.json({'errors': serializer.errors}, 400)

        # Create object
        try:
            obj = await self.model_class.create(**data)
            data = self.serialize(obj)
            return self.json(data, 201)
        except Exception as e:
            return self.json({'error': str(e)}, 400)

    @put
    async def update(self, id: int):
        """Update an existing object"""
        obj = await self.get_object(id)
        data = await self.request.json()

        # Validate data
        serializer = self.get_serializer(instance=obj, data=data)
        if serializer:
            if not serializer.is_valid():
                return self.json({'errors': serializer.errors}, 400)

        # Update object
        for key, value in data.items():
            if hasattr(obj, key):
                setattr(obj, key, value)

        await obj.save()
        data = self.serialize(obj)
        return self.json(data)

    @patch
    async def partial_update(self, id: int):
        """Partially update an existing object"""
        obj = await self.get_object(id)
        data = await self.request.json()

        # Update only provided fields
        for key, value in data.items():
            if hasattr(obj, key):
                setattr(obj, key, value)

        await obj.save()
        data = self.serialize(obj)
        return self.json(data)

    @delete
    async def destroy(self, id: int):
        """Delete an object"""
        obj = await self.get_object(id)
        await obj.delete()
        return self.json({'message': 'Deleted successfully'}, 204)


class APIView(Controller):
    """Base API view class"""

    def __init__(self, app):
        super().__init__(app)
        self.allowed_methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD']

    def options(self):
        """Handle OPTIONS request"""
        return self.json({}, headers={
            'Allow': ', '.join(self.allowed_methods),
            'Access-Control-Allow-Methods': ', '.join(self.allowed_methods),
            'Access-Control-Allow-Headers': 'Content-Type, Authorization'
        })


class Serializer:
    """Base serializer class"""

    def __init__(self, instance=None, data=None, many=False, **kwargs):
        self.instance = instance
        self.data = data or {}
        self.many = many
        self.errors = {}
        self.validated_data = {}

    def is_valid(self) -> bool:
        """Validate the data"""
        try:
            self.validated_data = self.validate(self.data)
            return True
        except ValidationError as e:
            self.errors = {e.field: [e.message]}
            return False

    def validate(self, data):
        """Validate data - override in subclasses"""
        return data

    def save(self):
        """Save the validated data"""
        if self.instance:
            return self.update(self.instance, self.validated_data)
        return self.create(self.validated_data)

    def create(self, validated_data):
        """Create a new instance - override in subclasses"""
        raise NotImplementedError("create() must be implemented")

    def update(self, instance, validated_data):
        """Update an existing instance - override in subclasses"""
        raise NotImplementedError("update() must be implemented")


class ModelSerializer(Serializer):
    """Model serializer"""

    model_class = None
    fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.model_class:
            raise ValueError("model_class must be defined")

    def get_fields(self):
        """Get serializer fields"""
        if self.fields == '__all__':
            # Get all fields from model
            return list(self.model_class._fields.keys())
        return self.fields

    def validate(self, data):
        """Validate data against model fields"""
        validated_data = {}
        fields = self.get_fields()

        for field_name in fields:
            if field_name in data:
                value = data[field_name]
                # Basic validation - could be enhanced
                validated_data[field_name] = value

        return validated_data

    def create(self, validated_data):
        """Create model instance"""
        return self.model_class(**validated_data)

    def update(self, instance, validated_data):
        """Update model instance"""
        for key, value in validated_data.items():
            setattr(instance, key, value)
        return instance





class FilterBackend:
    """Base filter backend"""

    def filter_queryset(self, request, queryset, view):
        """Filter the queryset"""
        return queryset


class OrderingFilter(FilterBackend):
    """Ordering filter"""

    ordering_param = 'ordering'
    ordering_fields = []

    def filter_queryset(self, request, queryset, view):
        """Apply ordering to queryset"""
        ordering = request.query_params.get(self.ordering_param, [''])[0]
        if ordering:
            # This is a simplified implementation
            # In a real implementation, you'd use database ORDER BY
            pass
        return queryset


class SearchFilter(FilterBackend):
    """Search filter"""

    search_param = 'search'
    search_fields = []

    def filter_queryset(self, request, queryset, view):
        """Apply search to queryset"""
        search_term = request.query_params.get(self.search_param, [''])[0]
        if search_term and self.search_fields:
            # This is a simplified implementation
            # In a real implementation, you'd use database LIKE queries
            pass
        return queryset


# API versioning
class APIVersioning:
    """Base API versioning class"""

    def get_version(self, request):
        """Get API version from request"""
        return request.headers.get('Accept', '').split('version=')[-1] or '1.0'


class URLPathVersioning(APIVersioning):
    """URL path versioning (e.g., /api/v1/users/)"""

    def get_version(self, request):
        """Get version from URL path"""
        path_parts = request.path.strip('/').split('/')
        if len(path_parts) >= 2 and path_parts[0] == 'api' and path_parts[1].startswith('v'):
            return path_parts[1][1:]  # Remove 'v' prefix
        return '1.0'


class HeaderVersioning(APIVersioning):
    """Header-based versioning"""

    def get_version(self, request):
        """Get version from header"""
        return request.headers.get('X-API-Version', '1.0')





# API documentation helpers
def api_view(methods: List[str] = None):
    """Decorator for API views"""
    if methods is None:
        methods = ['GET']

    def decorator(func):
        func._api_methods = methods
        return func
    return decorator


def api_schema(request_schema: Dict = None, response_schema: Dict = None, tags: List[str] = None):
    """Decorator to add OpenAPI schema to API views"""
    def decorator(func):
        func._api_schema = {
            'request': request_schema,
            'response': response_schema,
            'tags': tags or ['api']
        }
        return func
    return decorator


# Example API controller
class UserAPIController(APIResourceController):
    """Example user API controller"""

    model_class = None  # Would be set to User model

    @get
    async def me(self):
        """Get current user info"""
        # This would get the authenticated user
        return self.json({'message': 'Current user info'})

    @post
    async def change_password(self):
        """Change user password"""
        data = await self.request.json()
        # Password change logic here
        return self.json({'message': 'Password changed successfully'})


# Export common classes
__all__ = [
    'APIResourceController',
    'APIView',
    'Serializer',
    'ModelSerializer',
    'FilterBackend',
    'OrderingFilter',
    'SearchFilter',
    'APIVersioning',
    'URLPathVersioning',
    'HeaderVersioning',
    'api_view',
    'api_schema',
    'UserAPIController'
]

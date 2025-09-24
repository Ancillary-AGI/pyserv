"""
Base view classes for Pyserv  framework.
Provides class-based views with template rendering and context processing.
"""

from typing import Dict, Any, Optional, Type, List, Union
from abc import ABC, abstractmethod
import inspect

from pyserv.http.request import Request
from pyserv.http.response import Response
from pyserv.server.application import Application
from pyserv.exceptions import HTTPException, NotFound


class View(ABC):
    """Base view class"""

    http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']

    def __init__(self, app: Application, **kwargs):
        self.app = app
        self.request: Optional[Request] = None
        for key, value in kwargs.items():
            setattr(self, key, value)

    @classmethod
    def as_view(cls, app: Application, **initkwargs):
        """Create a view function from the class"""
        async def view(request):
            self = cls(app, **initkwargs)
            self.request = request

            # Get the HTTP method
            method = request.method.lower()

            # Check if method is allowed
            if method not in cls.http_method_names:
                return Response("Method not allowed", status_code=405)

            # Get the handler method
            handler = getattr(self, method, None)
            if handler is None:
                return Response("Method not allowed", status_code=405)

            # Call the handler
            if inspect.iscoroutinefunction(handler):
                return await handler()
            else:
                return handler()

        return view

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """Get context data for template rendering"""
        context = {}
        if self.request:
            context['request'] = self.request
        context.update(kwargs)
        return context

    def render_to_response(self, context: Dict[str, Any],
                          template_name: Optional[str] = None) -> Response:
        """Render context to response"""
        if template_name and self.app.template_engine:
            content = self.app.template_engine.render(template_name, **context)
            return Response(content, content_type='text/html')
        else:
            # JSON response by default
            import json
            return Response(json.dumps(context), content_type='application/json')


class TemplateView(View):
    """View that renders a template"""

    template_name: Optional[str] = None
    content_type: str = 'text/html'

    def get(self):
        """Handle GET request"""
        context = self.get_context_data()
        return self.render_to_response(context, self.template_name)

    def get_template_names(self) -> List[str]:
        """Get template names to try"""
        if self.template_name:
            return [self.template_name]
        return []

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """Get context with additional data"""
        context = super().get_context_data(**kwargs)
        context['view'] = self
        return context


class ListView(TemplateView):
    """View for displaying a list of objects"""

    model = None
    queryset = None
    template_name: Optional[str] = None
    context_object_name: str = 'object_list'
    paginate_by: Optional[int] = None
    ordering: Optional[str] = None

    def get_queryset(self):
        """Get the queryset"""
        if self.queryset is not None:
            return self.queryset
        elif self.model is not None:
            return self.model.all()
        else:
            raise ValueError("ListView needs either a queryset or a model")

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """Get context with object list"""
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()

        # Apply ordering
        if self.ordering:
            queryset = queryset.order_by(self.ordering)

        # Apply pagination
        if self.paginate_by:
            page = int(self.request.query_params.get('page', 1))
            offset = (page - 1) * self.paginate_by
            context['page_obj'] = {
                'number': page,
                'has_next': True,  # Simplified
                'has_previous': page > 1
            }
            object_list = queryset[offset:offset + self.paginate_by]
        else:
            object_list = queryset

        context[self.context_object_name] = object_list
        return context


class DetailView(TemplateView):
    """View for displaying a single object"""

    model = None
    queryset = None
    template_name: Optional[str] = None
    context_object_name: str = 'object'
    slug_field: str = 'slug'
    slug_url_kwarg: str = 'slug'

    def get_object(self):
        """Get the object"""
        queryset = self.get_queryset()

        # Get lookup parameters
        if self.request.path_params:
            # Try slug first
            slug = self.request.path_params.get(self.slug_url_kwarg)
            if slug:
                return queryset.filter(**{self.slug_field: slug}).first()

            # Try pk
            pk = self.request.path_params.get('pk')
            if pk:
                return queryset.filter(pk=pk).first()

        raise NotFound("Object not found")

    def get_queryset(self):
        """Get the queryset"""
        if self.queryset is not None:
            return self.queryset
        elif self.model is not None:
            return self.model.all()
        else:
            raise ValueError("DetailView needs either a queryset or a model")

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """Get context with object"""
        context = super().get_context_data(**kwargs)
        context[self.context_object_name] = self.get_object()
        return context


class FormView(TemplateView):
    """View for handling forms"""

    form_class = None
    template_name: Optional[str] = None
    success_url: Optional[str] = None
    initial: Dict[str, Any] = {}

    def get_form_class(self):
        """Get the form class"""
        return self.form_class

    def get_form(self, form_class=None):
        """Get form instance"""
        if form_class is None:
            form_class = self.get_form_class()

        if self.request.method == 'POST':
            # Handle form submission
            form_data = self.request.form_data if hasattr(self.request, 'form_data') else {}
            return form_class(form_data)
        else:
            return form_class(initial=self.initial)

    def form_valid(self, form):
        """Handle valid form"""
        return self.render_to_response(self.get_context_data(form=form))

    def form_invalid(self, form):
        """Handle invalid form"""
        return self.render_to_response(self.get_context_data(form=form))

    def get_success_url(self):
        """Get success URL"""
        if self.success_url:
            return self.success_url
        return self.request.path

    def get(self):
        """Handle GET request"""
        form = self.get_form()
        return self.render_to_response(self.get_context_data(form=form))

    def post(self):
        """Handle POST request"""
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """Get context with form"""
        context = super().get_context_data(**kwargs)
        if 'form' not in context:
            context['form'] = self.get_form()
        return context


# Function-based view utilities
def render_to(template_name: str):
    """Decorator to render function result to template"""
    def decorator(func):
        async def wrapper(request, *args, **kwargs):
            from pyserv.server.application import Application
            app = Application()

            result = await func(request, *args, **kwargs) if inspect.iscoroutinefunction(func) else func(request, *args, **kwargs)

            if isinstance(result, dict):
                context = result
                content = app.template_engine.render(template_name, **context)
                return Response(content, content_type='text/html')
            elif isinstance(result, Response):
                return result
            else:
                return Response(str(result))

        return wrapper
    return decorator


def ajax_required(func):
    """Decorator to require AJAX requests"""
    async def wrapper(request, *args, **kwargs):
        if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return Response("AJAX request required", status_code=400)

        return await func(request, *args, **kwargs) if inspect.iscoroutinefunction(func) else func(request, *args, **kwargs)
    return wrapper


def login_required(func):
    """Decorator to require authentication"""
    async def wrapper(request, *args, **kwargs):
        # Simplified authentication check
        if not hasattr(request, 'user') or not request.user:
            return Response("Authentication required", status_code=401)

        return await func(request, *args, **kwargs) if inspect.iscoroutinefunction(func) else func(request, *args, **kwargs)
    return wrapper

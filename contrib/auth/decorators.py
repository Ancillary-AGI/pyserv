"""
Authentication decorators for route protection.
"""

from functools import wraps
from typing import Optional, List, Callable, Any

from ...core.request import Request
from ...core.response import Response
from ...core.exceptions import Unauthorized, Forbidden
from ...models.user import BaseUser


def login_required(auth_instance=None):
    """
    Decorator to require user authentication.

    Args:
        auth_instance: Auth instance to use. If None, looks for 'auth' in app state.

    Usage:
        @app.route('/protected')
        @login_required()
        async def protected(request):
            return {'message': 'You are authenticated!'}
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Get auth instance
            auth = auth_instance
            if auth is None and hasattr(request.app, 'state') and 'auth' in request.app.state:
                auth = request.app.state['auth']

            if auth is None:
                raise Unauthorized("Authentication system not configured")

            # Get user from request
            user = await auth.get_user_from_request(request)
            if user is None:
                raise Unauthorized("Authentication required")

            # Add user to request state
            request.state.user = user

            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


def permission_required(permission: str, auth_instance=None):
    """
    Decorator to require specific permission.

    Args:
        permission: Permission string required
        auth_instance: Auth instance to use. If None, looks for 'auth' in app state.

    Usage:
        @app.route('/admin')
        @permission_required('manage_users')
        async def admin_panel(request):
            return {'message': 'Admin access granted!'}
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Get auth instance
            auth = auth_instance
            if auth is None and hasattr(request.app, 'state') and 'auth' in request.app.state:
                auth = request.app.state['auth']

            if auth is None:
                raise Unauthorized("Authentication system not configured")

            # Get user from request
            user = await auth.get_user_from_request(request)
            if user is None:
                raise Unauthorized("Authentication required")

            # Check permission
            if not await user.has_permission(permission):
                raise Forbidden(f"Permission '{permission}' required")

            # Add user to request state
            request.state.user = user

            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


def role_required(role: str, auth_instance=None):
    """
    Decorator to require specific role.

    Args:
        role: Role string required
        auth_instance: Auth instance to use. If None, looks for 'auth' in app state.

    Usage:
        @app.route('/moderator')
        @role_required('moderator')
        async def moderator_panel(request):
            return {'message': 'Moderator access granted!'}
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Get auth instance
            auth = auth_instance
            if auth is None and hasattr(request.app, 'state') and 'auth' in request.app.state:
                auth = request.app.state['auth']

            if auth is None:
                raise Unauthorized("Authentication system not configured")

            # Get user from request
            user = await auth.get_user_from_request(request)
            if user is None:
                raise Unauthorized("Authentication required")

            # Check role
            if user.role != role:
                raise Forbidden(f"Role '{role}' required")

            # Add user to request state
            request.state.user = user

            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


def admin_required(auth_instance=None):
    """
    Decorator to require admin role.

    Args:
        auth_instance: Auth instance to use. If None, looks for 'auth' in app state.

    Usage:
        @app.route('/super-admin')
        @admin_required()
        async def super_admin_panel(request):
            return {'message': 'Super admin access granted!'}
    """
    return role_required('admin', auth_instance)


def staff_required(auth_instance=None):
    """
    Decorator to require staff status.

    Args:
        auth_instance: Auth instance to use. If None, looks for 'auth' in app state.

    Usage:
        @app.route('/staff-only')
        @staff_required()
        async def staff_panel(request):
            return {'message': 'Staff access granted!'}
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Get auth instance
            auth = auth_instance
            if auth is None and hasattr(request.app, 'state') and 'auth' in request.app.state:
                auth = request.app.state['auth']

            if auth is None:
                raise Unauthorized("Authentication system not configured")

            # Get user from request
            user = await auth.get_user_from_request(request)
            if user is None:
                raise Unauthorized("Authentication required")

            # Check staff status
            if not user.is_staff:
                raise Forbidden("Staff access required")

            # Add user to request state
            request.state.user = user

            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

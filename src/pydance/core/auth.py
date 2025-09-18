"""
Authentication and Authorization system for PyDance framework.
Provides session management, token authentication, OAuth, and RBAC.
"""

import hashlib
import hmac
import secrets
import jwt
import time
from typing import Dict, List, Any, Optional, Union, Callable, Type
from datetime import datetime, timedelta
from functools import wraps

from ..models.user import BaseUser
from ..core.form_validation import EmailField, CharField
from ..utils.types import ValidationError
from ..core.caching import get_cache_manager
from ..core.security import get_security_manager

# Use BaseUser from models/user.py instead of creating a duplicate
User = BaseUser


class SessionStore:
    """Session storage backend"""

    def __init__(self, cache_manager=None):
        self.cache = cache_manager or get_cache_manager()

    def get(self, session_key: str) -> Optional[Dict[str, Any]]:
        """Get session data"""
        return self.cache.get(f"session:{session_key}")

    def set(self, session_key: str, data: Dict[str, Any], ttl: int = 3600):
        """Set session data"""
        self.cache.set(f"session:{session_key}", data, ttl)

    def delete(self, session_key: str):
        """Delete session"""
        self.cache.delete(f"session:{session_key}")

    def exists(self, session_key: str) -> bool:
        """Check if session exists"""
        return self.cache.exists(f"session:{session_key}")


class Session:
    """Session management"""

    def __init__(self, session_key: str = None, store: SessionStore = None):
        self.store = store or SessionStore()
        self.session_key = session_key or self._generate_key()
        self._data = {}
        self.modified = False

    def _generate_key(self) -> str:
        """Generate a new session key"""
        return secrets.token_hex(32)

    def load(self):
        """Load session data from store"""
        if self.session_key:
            data = self.store.get(self.session_key)
            if data:
                self._data = data

    def save(self):
        """Save session data to store"""
        if self.modified:
            self.store.set(self.session_key, self._data)
            self.modified = False

    def __getitem__(self, key: str) -> Any:
        return self._data.get(key)

    def __setitem__(self, key: str, value: Any):
        self._data[key] = value
        self.modified = True

    def __delitem__(self, key: str):
        if key in self._data:
            del self._data[key]
            self.modified = True

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def clear(self):
        """Clear all session data"""
        self._data.clear()
        self.modified = True

    def flush(self):
        """Delete session from store"""
        if self.session_key:
            self.store.delete(self.session_key)
        self._data.clear()
        self.session_key = self._generate_key()
        self.modified = True


class AuthBackend:
    """Base authentication backend"""

    def authenticate(self, request, username: str = None, password: str = None,
                    **kwargs) -> Optional[User]:
        """Authenticate user"""
        raise NotImplementedError

    def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        raise NotImplementedError


class ModelBackend(AuthBackend):
    """Authentication backend using database models"""

    def authenticate(self, request, username: str = None, password: str = None,
                    **kwargs) -> Optional[User]:
        """Authenticate user against database"""
        if not username or not password:
            return None

        # This would typically query the database
        # For now, return a mock user
        if username == "admin" and password == "password":
            user = User(
                id=1,
                username=username,
                email=f"{username}@example.com",
                roles=["admin", "user"]
            )
            user.set_password(password)
            return user

        return None

    def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        # This would typically query the database
        if user_id == 1:
            return User(
                id=user_id,
                username="admin",
                email="admin@example.com",
                roles=["admin", "user"]
            )
        return None


class JWTBackend(AuthBackend):
    """JWT token authentication backend"""

    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm

    def authenticate(self, request, token: str = None, **kwargs) -> Optional[User]:
        """Authenticate using JWT token"""
        if not token:
            return None

        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # Check if token is expired
            if payload.get('exp', 0) < time.time():
                return None

            user_id = payload.get('user_id')
            if user_id:
                return self.get_user(user_id)

        except jwt.InvalidTokenError:
            pass

        return None

    def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        # This would typically query the database
        return User(id=user_id, username=f"user_{user_id}", roles=["user"])


class OAuthBackend(AuthBackend):
    """OAuth authentication backend"""

    def __init__(self, client_id: str, client_secret: str, provider_url: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.provider_url = provider_url

    def authenticate(self, request, code: str = None, **kwargs) -> Optional[User]:
        """Authenticate using OAuth code"""
        if not code:
            return None

        # Exchange code for access token
        # This would make HTTP requests to OAuth provider
        # For now, return mock user
        return User(
            id=2,
            username="oauth_user",
            email="oauth@example.com",
            roles=["user"]
        )

    def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return User(id=user_id, username=f"oauth_{user_id}", roles=["user"])


class Permission:
    """Permission class for RBAC"""

    def __init__(self, codename: str, name: str = None):
        self.codename = codename
        self.name = name or codename.replace('_', ' ').title()


class Role:
    """Role class for RBAC"""

    def __init__(self, name: str, permissions: List[str] = None):
        self.name = name
        self.permissions = permissions or []


# Global permission and role registries
_permissions: Dict[str, Permission] = {}
_roles: Dict[str, Role] = {}


def register_permission(codename: str, name: str = None):
    """Register a permission"""
    _permissions[codename] = Permission(codename, name)


def register_role(name: str, permissions: List[str] = None):
    """Register a role"""
    _roles[name] = Role(name, permissions)


def get_role_permissions(role_name: str) -> List[str]:
    """Get permissions for a role"""
    role = _roles.get(role_name)
    return role.permissions if role else []


def get_user_permissions(user_id: int) -> List[str]:
    """Get user-specific permissions"""
    # This would typically query the database
    return []


class AuthManager:
    """Main authentication and authorization manager"""

    def __init__(self):
        self.backends: List[AuthBackend] = []
        self.session_store = SessionStore()

    def add_backend(self, backend: AuthBackend):
        """Add authentication backend"""
        self.backends.append(backend)

    def authenticate(self, request, **credentials) -> Optional[User]:
        """Try to authenticate user with all backends"""
        for backend in self.backends:
            user = backend.authenticate(request, **credentials)
            if user:
                return user
        return None

    def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID using first available backend"""
        for backend in self.backends:
            user = backend.get_user(user_id)
            if user:
                return user
        return None

    def login(self, request, user: User) -> str:
        """Log in user and create session"""
        session = Session(store=self.session_store)
        session['user_id'] = user.id
        session['username'] = user.username
        session['roles'] = user.roles
        session.save()

        # Update user's last login
        user.last_login = datetime.now()

        return session.session_key

    def logout(self, request, session_key: str):
        """Log out user"""
        session = Session(session_key, self.session_store)
        session.flush()

    def get_user_from_session(self, session_key: str) -> Optional[User]:
        """Get user from session"""
        session = Session(session_key, self.session_store)
        session.load()

        user_id = session.get('user_id')
        if user_id:
            return self.get_user(user_id)
        return None

    def has_perm(self, user: User, permission: str) -> bool:
        """Check if user has permission"""
        return user.has_perm(permission)

    def has_role(self, user: User, role: str) -> bool:
        """Check if user has role"""
        return user.has_role(role)


# Password hashing utilities
def hash_password(password: str) -> str:
    """Hash password using PBKDF2"""
    salt = secrets.token_hex(16)
    hash_obj = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode(),
        salt.encode(),
        100000
    )
    return f"pbkdf2_sha256$100000${salt}${hash_obj.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    try:
        method, iterations, salt, hash_value = hashed.split('$', 3)
        iterations = int(iterations)

        computed_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode(),
            salt.encode(),
            iterations
        )

        return hmac.compare_digest(hash_value, computed_hash.hex())
    except (ValueError, TypeError):
        return False


# JWT utilities
def generate_jwt_token(user: User, secret_key: str, expires_in: int = 3600) -> str:
    """Generate JWT token for user"""
    payload = {
        'user_id': user.id,
        'username': user.username,
        'roles': user.roles,
        'exp': time.time() + expires_in,
        'iat': time.time()
    }

    return jwt.encode(payload, secret_key, algorithm='HS256')


def verify_jwt_token(token: str, secret_key: str) -> Optional[Dict[str, Any]]:
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# Decorators
def login_required(func: Callable) -> Callable:
    """Decorator to require user login"""
    @wraps(func)
    async def wrapper(request, *args, **kwargs):
        if not hasattr(request, 'user') or not request.user:
            # Return 401 Unauthorized
            from ..core.response import Response
            return Response("Authentication required", status_code=401)

        return await func(request, *args, **kwargs)
    return wrapper


def permission_required(permission: str) -> Callable:
    """Decorator to require specific permission"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(request, *args, **kwargs):
            if not hasattr(request, 'user') or not request.user:
                from ..core.response import Response
                return Response("Authentication required", status_code=401)

            if not request.user.has_perm(permission):
                from ..core.response import Response
                return Response("Permission denied", status_code=403)

            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


def role_required(role: str) -> Callable:
    """Decorator to require specific role"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(request, *args, **kwargs):
            if not hasattr(request, 'user') or not request.user:
                from ..core.response import Response
                return Response("Authentication required", status_code=401)

            if not request.user.has_role(role):
                from ..core.response import Response
                return Response("Role required", status_code=403)

            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


# Middleware
class AuthenticationMiddleware:
    """Middleware for handling authentication"""

    def __init__(self, auth_manager: AuthManager):
        self.auth_manager = auth_manager

    async def __call__(self, request, call_next):
        # Try to get user from session
        session_key = request.cookies.get('session_id')
        if session_key:
            request.user = self.auth_manager.get_user_from_session(session_key)
        else:
            request.user = None

        # Try to get user from JWT token
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            # This would need to be implemented with JWT backend
            pass

        response = await call_next(request)
        return response


class AuthorizationMiddleware:
    """Middleware for handling authorization"""

    def __init__(self, auth_manager: AuthManager):
        self.auth_manager = auth_manager

    async def __call__(self, request, call_next):
        # Add authorization helpers to request
        request.has_perm = lambda perm: (
            hasattr(request, 'user') and
            request.user and
            self.auth_manager.has_perm(request.user, perm)
        )

        request.has_role = lambda role: (
            hasattr(request, 'user') and
            request.user and
            self.auth_manager.has_role(request.user, role)
        )

        response = await call_next(request)
        return response


# Forms
class LoginForm:
    """Login form"""

    username = CharField(required=True, max_length=150)
    password = CharField(required=True, widget="password")

    def __init__(self, data=None):
        self.data = data or {}
        self.errors = {}

    def is_valid(self):
        # Basic validation
        if not self.data.get('username'):
            self.errors['username'] = ['Username is required']
        if not self.data.get('password'):
            self.errors['password'] = ['Password is required']
        return len(self.errors) == 0


class RegistrationForm:
    """User registration form"""

    username = CharField(required=True, min_length=3, max_length=150)
    email = EmailField(required=True)
    password = CharField(required=True, min_length=8)
    password_confirm = CharField(required=True)

    def __init__(self, data=None):
        self.data = data or {}
        self.errors = {}

    def is_valid(self):
        # Basic validation
        if not self.data.get('username'):
            self.errors['username'] = ['Username is required']
        if not self.data.get('email'):
            self.errors['email'] = ['Email is required']
        if not self.data.get('password'):
            self.errors['password'] = ['Password is required']
        if self.data.get('password') != self.data.get('password_confirm'):
            self.errors['password_confirm'] = ['Passwords do not match']
        return len(self.errors) == 0


# Initialize default permissions and roles
register_permission('view_user', 'Can view user')
register_permission('add_user', 'Can add user')
register_permission('change_user', 'Can change user')
register_permission('delete_user', 'Can delete user')

register_role('admin', ['view_user', 'add_user', 'change_user', 'delete_user'])
register_role('user', ['view_user'])

# Global auth manager instance
auth_manager = AuthManager()
auth_manager.add_backend(ModelBackend())

__all__ = [
    'User', 'Session', 'AuthBackend', 'ModelBackend', 'JWTBackend', 'OAuthBackend',
    'Permission', 'Role', 'AuthManager', 'AuthenticationMiddleware', 'AuthorizationMiddleware',
    'login_required', 'permission_required', 'role_required',
    'LoginForm', 'RegistrationForm', 'auth_manager'
]

"""
Authentication and Authorization system for Pyserv  framework.
Provides session management, token authentication, OAuth, and RBAC.
"""

import hashlib
import hmac
import secrets
import jwt
import time
import re
from typing import Dict, List, Any, Optional, Union, Callable, Type
from datetime import datetime, timedelta
from functools import wraps
from dataclasses import dataclass
from enum import Enum

from pyserv.models.user import BaseUser
from pyserv.utils.form_validation import EmailField, CharField
from pyserv.utils.types import ValidationError
from pyserv.caching import get_cache_manager
from pyserv.security import get_security_manager
from pyserv.exceptions import HTTPException

# Use BaseUser from models/user.py instead of creating a duplicate
User = BaseUser


class AuthMethod(str, Enum):
    """Authentication methods"""
    JWT = "jwt"
    SESSION = "session"
    API_KEY = "api_key"
    BASIC = "basic"
    BEARER = "bearer"
    OAUTH = "oauth"


class SecurityLevel(str, Enum):
    """Security levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    MAXIMUM = "maximum"


@dataclass
class SecurityContext:
    """Security context for requests"""
    request_ip: str
    user_agent: str
    timestamp: float
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    roles: List[str] = None
    permissions: List[str] = None
    is_authenticated: bool = False
    auth_method: Optional[AuthMethod] = None
    csrf_token: Optional[str] = None


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
            from pyserv.http.response import Response
            return Response("Authentication required", status_code=401)

        return await func(request, *args, **kwargs)
    return wrapper


def permission_required(permission: str) -> Callable:
    """Decorator to require specific permission"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(request, *args, **kwargs):
            if not hasattr(request, 'user') or not request.user:
                from pyserv.http.response import Response
                return Response("Authentication required", status_code=401)

            if not request.user.has_perm(permission):
                from pyserv.http.response import Response
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
                from pyserv.core.http.response import Response
                return Response("Authentication required", status_code=401)

            if not request.user.has_role(role):
                from pyserv.http.response import Response
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


class AdvancedSecurityMiddleware:
    """
    Advanced security middleware with comprehensive protection features.
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)

        # Security settings
        self.max_login_attempts = self.config.get('max_login_attempts', 5)
        self.lockout_duration = self.config.get('lockout_duration', 300)  # 5 minutes
        self.session_timeout = self.config.get('session_timeout', 3600)  # 1 hour
        self.require_https = self.config.get('require_https', True)
        self.allowed_hosts = self.config.get('allowed_hosts', ['localhost', '127.0.0.1'])

        # Failed login tracking
        self._failed_attempts: Dict[str, Dict[str, Any]] = {}
        self._active_sessions: Dict[str, Dict[str, Any]] = {}

    async def __call__(self, request, call_next):
        """Advanced security middleware handler."""
        # Create security context
        security_context = SecurityContext(
            request_ip=self._get_client_ip(request),
            user_agent=request.headers.get('User-Agent', ''),
            timestamp=time.time()
        )

        # Add security context to request
        request.security_context = security_context

        try:
            # Pre-request security checks
            await self._pre_request_security(request, security_context)

            # Authenticate request
            await self._authenticate_request(request, security_context)

            # Authorize request
            await self._authorize_request(request, security_context)

            # Process request
            response = await call_next(request)

            # Post-response security processing
            response = await self._post_response_security(request, response, security_context)

            return response

        except Exception as e:
            # Security error handling
            return await self._handle_security_error(e, request, security_context)

    async def _pre_request_security(self, request, context: SecurityContext):
        """Pre-request security checks."""
        # Check allowed hosts
        if not self._is_allowed_host(request):
            from pyserv.exceptions import HTTPException
            raise HTTPException(403, "Host not allowed")

        # Rate limiting
        if self.config.get('enable_rate_limiting', True):
            await self._check_rate_limit(request, context)

        # Basic security headers validation
        await self._validate_security_headers(request)

        # Check for suspicious patterns
        await self._check_suspicious_activity(request, context)

    async def _authenticate_request(self, request, context: SecurityContext):
        """Authenticate the request with multiple methods."""
        # Try different authentication methods in order of preference
        auth_methods = [
            self._authenticate_jwt,
            self._authenticate_session,
            self._authenticate_api_key,
            self._authenticate_basic,
            self._authenticate_bearer
        ]

        for auth_method in auth_methods:
            try:
                await auth_method(request, context)
                if context.is_authenticated:
                    break
            except Exception as e:
                self.logger.debug(f"Authentication method failed: {e}")
                continue

    async def _authorize_request(self, request, context: SecurityContext):
        """Authorize the request."""
        if not context.is_authenticated:
            return  # Skip authorization for unauthenticated requests

        # Check permissions
        required_permissions = self._get_required_permissions(request)
        if required_permissions:
            if not self._has_permissions(context, required_permissions):
                from pyserv.exceptions import HTTPException
                raise HTTPException(403, "Insufficient permissions")

        # Check roles
        required_roles = self._get_required_roles(request)
        if required_roles:
            if not self._has_roles(context, required_roles):
                from pyserv.exceptions import HTTPException
                raise HTTPException(403, "Insufficient roles")

    async def _post_response_security(self, request, response, context: SecurityContext):
        """Post-response security processing."""
        # Add security headers
        await self._add_security_headers(response)

        # Add CSRF token if needed
        if context.is_authenticated:
            await self._add_csrf_token(response, context)

        # Log security event
        await self._log_security_event(request, response, context)

        return response

    async def _handle_security_error(self, error, request, context: SecurityContext):
        """Handle security errors."""
        self.logger.warning(f"Security error: {error}")

        # Log security event
        await self._log_security_event(request, None, context, error=str(error))

        # Return appropriate error response
        from pyserv.exceptions import HTTPException
        if isinstance(error, HTTPException):
            return error.get_response()
        else:
            return HTTPException(500, "Security error occurred").get_response()

    def _get_client_ip(self, request) -> str:
        """Get real client IP considering proxies."""
        # Check for X-Forwarded-For header
        forwarded_for = request.headers.get('X-Forwarded-For', '')
        if forwarded_for and self.config.get('trusted_proxies'):
            # Use the first IP that's not a trusted proxy
            ips = [ip.strip() for ip in forwarded_for.split(',')]
            for ip in ips:
                if ip not in self.config.get('trusted_proxies', []):
                    return ip

        # Check for X-Real-IP header
        real_ip = request.headers.get('X-Real-IP', '')
        if real_ip:
            return real_ip

        # Fall back to remote address
        return getattr(request, 'remote_addr', 'unknown')

    def _is_allowed_host(self, request) -> bool:
        """Check if host is allowed."""
        host = request.headers.get('Host', '')
        if not host:
            return False

        # Remove port if present
        if ':' in host:
            host = host.split(':')[0]

        return host in self.allowed_hosts or '*' in self.allowed_hosts

    async def _check_rate_limit(self, request, context: SecurityContext):
        """Check rate limiting."""
        client_key = context.request_ip
        current_time = time.time()

        if client_key not in self._failed_attempts:
            self._failed_attempts[client_key] = {'count': 0, 'last_attempt': current_time}

        attempts = self._failed_attempts[client_key]

        # Reset counter if enough time has passed
        if current_time - attempts['last_attempt'] > 60:  # 1 minute window
            attempts['count'] = 0

        attempts['last_attempt'] = current_time

        if attempts['count'] >= self.max_login_attempts:
            from pyserv.exceptions import HTTPException
            raise HTTPException(429, "Too many requests")

    async def _validate_security_headers(self, request):
        """Validate security headers."""
        # Check Content-Type for suspicious content
        content_type = request.headers.get('Content-Type', '')
        if content_type and 'script' in content_type.lower():
            # Log suspicious content type
            self.logger.warning(f"Suspicious Content-Type: {content_type}")

    async def _check_suspicious_activity(self, request, context: SecurityContext):
        """Check for suspicious activity patterns."""
        # Check for rapid requests from same IP
        # Check for unusual user agents
        # Check for suspicious URL patterns
        # Check for SQL injection patterns
        pass

    async def _authenticate_jwt(self, request, context: SecurityContext):
        """JWT authentication."""
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return

        token = auth_header[7:]  # Remove 'Bearer '
        try:
            import jwt
            payload = jwt.decode(token, self.config.get('jwt_secret', 'secret'), algorithms=[self.config.get('jwt_algorithm', 'HS256')])

            context.user_id = payload.get('user_id')
            context.session_id = payload.get('session_id')
            context.roles = payload.get('roles', [])
            context.permissions = payload.get('permissions', [])
            context.is_authenticated = True
            context.auth_method = AuthMethod.JWT

        except jwt.ExpiredSignatureError:
            raise HTTPException(401, "Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(401, "Invalid token")

    async def _authenticate_session(self, request, context: SecurityContext):
        """Session authentication."""
        session_id = request.cookies.get('session_id')
        if not session_id:
            return

        if session_id in self._active_sessions:
            session_data = self._active_sessions[session_id]
            if time.time() < session_data['expires_at']:
                context.user_id = session_data['user_id']
                context.session_id = session_id
                context.roles = session_data.get('roles', [])
                context.permissions = session_data.get('permissions', [])
                context.is_authenticated = True
                context.auth_method = AuthMethod.SESSION

    async def _authenticate_api_key(self, request, context: SecurityContext):
        """API key authentication."""
        api_key = request.headers.get('X-API-Key', '')
        if not api_key:
            return

        # Simple API key validation (in production, use database)
        if self._validate_api_key(api_key):
            context.user_id = "api_user"
            context.is_authenticated = True
            context.auth_method = AuthMethod.API_KEY

    async def _authenticate_basic(self, request, context: SecurityContext):
        """Basic authentication."""
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Basic '):
            return

        try:
            import base64
            credentials = base64.b64decode(auth_header[6:]).decode('utf-8')
            username, password = credentials.split(':', 1)

            # Validate credentials (in production, use database)
            if self._validate_credentials(username, password):
                context.user_id = username
                context.is_authenticated = True
                context.auth_method = AuthMethod.BASIC

        except Exception:
            pass

    async def _authenticate_bearer(self, request, context: SecurityContext):
        """Bearer token authentication (OAuth2)."""
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return

        token = auth_header[7:]
        # OAuth2 token validation would go here
        # For now, treat as API key
        if len(token) > 20:
            context.user_id = "oauth_user"
            context.is_authenticated = True
            context.auth_method = AuthMethod.BEARER

    def _validate_api_key(self, api_key: str) -> bool:
        """Validate API key."""
        # Simple validation - in production, check against database
        return len(api_key) >= 20 and api_key.startswith('sk-')

    def _validate_credentials(self, username: str, password: str) -> bool:
        """Validate user credentials."""
        # Simple validation - in production, check against database
        return len(username) >= 3 and len(password) >= 8

    def _get_required_permissions(self, request) -> List[str]:
        """Get required permissions for the request."""
        # This would typically be determined by the route or endpoint
        # For now, return empty list (no specific permissions required)
        return []

    def _get_required_roles(self, request) -> List[str]:
        """Get required roles for the request."""
        # This would typically be determined by the route or endpoint
        return []

    def _has_permissions(self, context: SecurityContext, required_permissions: List[str]) -> bool:
        """Check if user has required permissions."""
        if not required_permissions:
            return True

        return any(perm in context.permissions for perm in required_permissions)

    def _has_roles(self, context: SecurityContext, required_roles: List[str]) -> bool:
        """Check if user has required roles."""
        if not required_roles:
            return True

        return any(role in context.roles for role in required_roles)

    async def _add_security_headers(self, response):
        """Add security headers to response."""
        headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Permissions-Policy': 'geolocation=(), microphone=(), camera=()',
            'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
        }

        # Add custom security headers
        headers.update(self.config.get('security_headers', {}))

        # Add headers to response
        if hasattr(response, 'headers'):
            for key, value in headers.items():
                response.headers[key] = value

    async def _add_csrf_token(self, response, context: SecurityContext):
        """Add CSRF token to response."""
        if not context.csrf_token:
            context.csrf_token = secrets.token_hex(32)

        if hasattr(response, 'headers'):
            response.headers['X-CSRF-Token'] = context.csrf_token

        # Also set as cookie for JavaScript access
        if hasattr(response, 'set_cookie'):
            response.set_cookie(
                'csrf_token',
                context.csrf_token,
                httponly=False,
                samesite='Strict',
                max_age=3600
            )

    async def _log_security_event(self, request, response, context: SecurityContext, **extra):
        """Log security events."""
        # Only log significant events
        if context.is_authenticated or extra:
            self.logger.info(f"Security event: {context.auth_method} from {context.request_ip}", extra={
                'user_id': context.user_id,
                'request_ip': context.request_ip,
                'user_agent': context.user_agent,
                'method': request.method,
                'path': request.path,
                'status_code': getattr(response, 'status_code', 200) if response else None,
                **extra
            })

    def create_session(self, user_id: str, roles: List[str] = None, permissions: List[str] = None) -> str:
        """Create a new session."""
        session_id = secrets.token_hex(32)
        expires_at = time.time() + self.session_timeout

        self._active_sessions[session_id] = {
            'user_id': user_id,
            'roles': roles or [],
            'permissions': permissions or [],
            'created_at': time.time(),
            'expires_at': expires_at
        }

        return session_id

    def destroy_session(self, session_id: str):
        """Destroy a session."""
        if session_id in self._active_sessions:
            del self._active_sessions[session_id]

    def generate_jwt_token(self, user_id: str, roles: List[str] = None, permissions: List[str] = None) -> str:
        """Generate JWT token."""
        import jwt
        from datetime import datetime, timedelta

        payload = {
            'user_id': user_id,
            'roles': roles or [],
            'permissions': permissions or [],
            'exp': datetime.utcnow() + timedelta(minutes=self.config.get('jwt_expire_minutes', 60)),
            'iat': datetime.utcnow(),
            'iss': 'pyserv',
            'aud': 'pyserv-users'
        }

        return jwt.encode(payload, self.config.get('jwt_secret', 'secret'), algorithm=self.config.get('jwt_algorithm', 'HS256'))

    def validate_password(self, password: str) -> bool:
        """Validate password strength."""
        min_length = self.config.get('password_min_length', 8)
        require_uppercase = self.config.get('require_uppercase', True)
        require_numbers = self.config.get('require_numbers', True)
        require_special_chars = self.config.get('require_special_chars', True)

        if len(password) < min_length:
            return False

        if require_uppercase and not re.search(r'[A-Z]', password):
            return False

        if require_numbers and not re.search(r'\d', password):
            return False

        if require_special_chars and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False

        return True

    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt."""
        import bcrypt
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password: str, hashed: str) -> bool:
        """Check password against hash."""
        import bcrypt
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception:
            return False


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
    'AdvancedSecurityMiddleware', 'AuthMethod', 'SecurityLevel', 'SecurityContext',
    'login_required', 'permission_required', 'role_required',
    'LoginForm', 'RegistrationForm', 'auth_manager'
]

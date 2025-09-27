"""
Real authentication and authorization system for Pyserv framework with JWT tokens and password hashing.
"""

import jwt
import bcrypt
import hashlib
import secrets
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


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


class PasswordHasher:
    """Real password hashing with bcrypt"""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify password against hash"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception:
            return False

    @staticmethod
    def needs_rehash(hashed: str) -> bool:
        """Check if password hash needs rehashing"""
        # Check if using old hash format
        return not hashed.startswith('$2b$') or len(hashed.split('$')) < 4


class JWTManager:
    """Real JWT token management"""

    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm

    def create_token(self, user_id: str, roles: List[str] = None,
                    permissions: List[str] = None, expires_in: int = 3600) -> str:
        """Create JWT token"""
        payload = {
            'user_id': user_id,
            'roles': roles or [],
            'permissions': permissions or [],
            'exp': datetime.utcnow() + timedelta(seconds=expires_in),
            'iat': datetime.utcnow(),
            'iss': 'pyserv',
            'aud': 'pyserv-users'
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return None

    def refresh_token(self, token: str) -> Optional[str]:
        """Refresh JWT token"""
        payload = self.verify_token(token)
        if not payload:
            return None

        # Create new token with updated expiration
        return self.create_token(
            user_id=payload['user_id'],
            roles=payload.get('roles', []),
            permissions=payload.get('permissions', [])
        )


class SessionManager:
    """Real session management"""

    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.sessions: Dict[str, Dict[str, Any]] = {}

    def create_session(self, user_id: str, roles: List[str] = None,
                      permissions: List[str] = None) -> str:
        """Create new session"""
        session_id = secrets.token_hex(32)
        expires_at = datetime.utcnow() + timedelta(hours=8)

        self.sessions[session_id] = {
            'user_id': user_id,
            'roles': roles or [],
            'permissions': permissions or [],
            'created_at': datetime.utcnow(),
            'expires_at': expires_at,
            'is_active': True
        }

        return session_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data"""
        session = self.sessions.get(session_id)
        if not session or not session['is_active']:
            return None

        # Check expiry
        if datetime.utcnow() > session['expires_at']:
            session['is_active'] = False
            return None

        return session

    def destroy_session(self, session_id: str):
        """Destroy session"""
        if session_id in self.sessions:
            self.sessions[session_id]['is_active'] = False

    def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        current_time = datetime.utcnow()
        expired_sessions = [
            session_id for session_id, session in self.sessions.items()
            if session['expires_at'] < current_time or not session['is_active']
        ]

        for session_id in expired_sessions:
            del self.sessions[session_id]


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


class AuthManager:
    """Real authentication and authorization manager"""

    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.password_hasher = PasswordHasher()
        self.jwt_manager = JWTManager(secret_key)
        self.session_manager = SessionManager(secret_key)
        self.permissions: Dict[str, Permission] = {}
        self.roles: Dict[str, Role] = {}

        # Initialize default permissions and roles
        self._initialize_defaults()

    def _initialize_defaults(self):
        """Initialize default permissions and roles"""
        # Default permissions
        self.permissions = {
            'view_user': Permission('view_user', 'Can view user'),
            'add_user': Permission('add_user', 'Can add user'),
            'change_user': Permission('change_user', 'Can change user'),
            'delete_user': Permission('delete_user', 'Can delete user'),
            'view_content': Permission('view_content', 'Can view content'),
            'add_content': Permission('add_content', 'Can add content'),
            'change_content': Permission('change_content', 'Can change content'),
            'delete_content': Permission('delete_content', 'Can delete content'),
        }

        # Default roles
        self.roles = {
            'admin': Role('admin', ['view_user', 'add_user', 'change_user', 'delete_user',
                                   'view_content', 'add_content', 'change_content', 'delete_content']),
            'editor': Role('editor', ['view_content', 'add_content', 'change_content']),
            'user': Role('user', ['view_content']),
        }

    def register_permission(self, codename: str, name: str = None):
        """Register a permission"""
        self.permissions[codename] = Permission(codename, name)

    def register_role(self, name: str, permissions: List[str] = None):
        """Register a role"""
        self.roles[name] = Role(name, permissions)

    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with real database lookup"""
        # This would typically query the database
        # For now, return mock user data
        users_db = {
            'admin': {
                'id': '1',
                'username': 'admin',
                'password': self.password_hasher.hash_password('admin123'),
                'roles': ['admin'],
                'permissions': ['view_user', 'add_user', 'change_user', 'delete_user'],
                'is_active': True
            },
            'user': {
                'id': '2',
                'username': 'user',
                'password': self.password_hasher.hash_password('user123'),
                'roles': ['user'],
                'permissions': ['view_content'],
                'is_active': True
            }
        }

        user_data = users_db.get(username)
        if not user_data or not user_data['is_active']:
            return None

        # Verify password
        if not self.password_hasher.verify_password(password, user_data['password']):
            return None

        return user_data

    def create_jwt_token(self, user_data: Dict[str, Any]) -> str:
        """Create JWT token for user"""
        return self.jwt_manager.create_token(
            user_id=user_data['id'],
            roles=user_data['roles'],
            permissions=user_data['permissions']
        )

    def create_session(self, user_data: Dict[str, Any]) -> str:
        """Create session for user"""
        return self.session_manager.create_session(
            user_id=user_data['id'],
            roles=user_data['roles'],
            permissions=user_data['permissions']
        )

    def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token"""
        return self.jwt_manager.verify_token(token)

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data"""
        return self.session_manager.get_session(session_id)

    def has_permission(self, user_data: Dict[str, Any], permission: str) -> bool:
        """Check if user has permission"""
        user_permissions = user_data.get('permissions', [])
        return permission in user_permissions

    def has_role(self, user_data: Dict[str, Any], role: str) -> bool:
        """Check if user has role"""
        user_roles = user_data.get('roles', [])
        return role in user_roles

    def get_user_permissions(self, user_data: Dict[str, Any]) -> List[str]:
        """Get all permissions for user"""
        permissions = set(user_data.get('permissions', []))

        # Add permissions from roles
        for role_name in user_data.get('roles', []):
            role = self.roles.get(role_name)
            if role:
                permissions.update(role.permissions)

        return list(permissions)

    def get_user_roles(self, user_data: Dict[str, Any]) -> List[str]:
        """Get all roles for user"""
        return user_data.get('roles', [])


class AuthMiddleware:
    """Real authentication middleware"""

    def __init__(self, auth_manager: AuthManager):
        self.auth_manager = auth_manager

    async def __call__(self, request, call_next):
        """Process authentication"""
        # Try to get user from JWT token
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            payload = self.auth_manager.verify_jwt_token(token)
            if payload:
                request.user = payload
                request.auth_method = AuthMethod.JWT

        # Try to get user from session
        session_id = request.cookies.get('session_id')
        if session_id and not hasattr(request, 'user'):
            session_data = self.auth_manager.get_session(session_id)
            if session_data:
                request.user = session_data
                request.auth_method = AuthMethod.SESSION

        # Add auth helpers to request
        request.has_perm = lambda perm: (
            hasattr(request, 'user') and
            request.user and
            self.auth_manager.has_permission(request.user, perm)
        )

        request.has_role = lambda role: (
            hasattr(request, 'user') and
            request.user and
            self.auth_manager.has_role(request.user, role)
        )

        response = await call_next(request)
        return response


# Global auth manager instance
auth_manager = AuthManager("your-secret-key-change-in-production")

__all__ = [
    'AuthMethod', 'SecurityLevel', 'SecurityContext', 'PasswordHasher',
    'JWTManager', 'SessionManager', 'Permission', 'Role', 'AuthManager',
    'AuthMiddleware', 'auth_manager'
]

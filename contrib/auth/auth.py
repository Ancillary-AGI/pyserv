"""
Authentication and authorization system for Pydance framework.
"""

import secrets
import jwt
import json
from typing import Optional, Dict, Any, List, Union, Type
from datetime import datetime, timedelta
from abc import ABC, abstractmethod

from ...core.request import Request
from ...core.response import Response
from ...core.exceptions import HTTPException, Unauthorized, Forbidden
from ...models.user import BaseUser
from .backends import SessionBackend, TokenBackend


class UserSession:
    """User session management"""

    def __init__(self,
                 session_id: str,
                 user_id: str,
                 user: Optional[BaseUser] = None,
                 data: Optional[Dict[str, Any]] = None,
                 created_at: Optional[datetime] = None,
                 expires_at: Optional[datetime] = None):
        self.session_id = session_id
        self.user_id = user_id
        self.user = user
        self.data = data or {}
        self.created_at = created_at or datetime.utcnow()
        self.expires_at = expires_at

    @property
    def is_expired(self) -> bool:
        """Check if session is expired"""
        return self.expires_at and datetime.utcnow() > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'data': self.data,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
        }


class AuthToken:
    """Authentication token management"""

    def __init__(self,
                 token: str,
                 user_id: str,
                 token_type: str = 'access',
                 user: Optional[BaseUser] = None,
                 data: Optional[Dict[str, Any]] = None,
                 created_at: Optional[datetime] = None,
                 expires_at: Optional[datetime] = None):
        self.token = token
        self.user_id = user_id
        self.token_type = token_type
        self.user = user
        self.data = data or {}
        self.created_at = created_at or datetime.utcnow()
        self.expires_at = expires_at

    @property
    def is_expired(self) -> bool:
        """Check if token is expired"""
        return self.expires_at and datetime.utcnow() > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'token': self.token,
            'user_id': self.user_id,
            'token_type': self.token_type,
            'data': self.data,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
        }


class Auth:
    """Main authentication class"""

    def __init__(self,
                 user_model: Type[BaseUser],
                 secret_key: Optional[str] = None,
                 session_backend: Optional[SessionBackend] = None,
                 token_backend: Optional[TokenBackend] = None,
                 jwt_algorithm: str = 'HS256',
                 access_token_expiry: timedelta = timedelta(hours=1),
                 refresh_token_expiry: timedelta = timedelta(days=7),
                 session_expiry: timedelta = timedelta(hours=24)):
        self.user_model = user_model
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        self.session_backend = session_backend or SessionBackend()
        self.token_backend = token_backend or TokenBackend()
        self.jwt_algorithm = jwt_algorithm
        self.access_token_expiry = access_token_expiry
        self.refresh_token_expiry = refresh_token_expiry
        self.session_expiry = session_expiry

    async def authenticate_user(self, identifier: str, password: str) -> Optional[BaseUser]:
        """Authenticate user with identifier and password"""
        return await self.user_model.authenticate(identifier, password)

    async def get_user_from_request(self, request: Request) -> Optional[BaseUser]:
        """Get user from request (session, token, etc.)"""
        # Try session first
        user = await self.get_user_from_session(request)
        if user:
            return user

        # Try token
        user = await self.get_user_from_token(request)
        if user:
            return user

        return None

    async def get_user_from_session(self, request: Request) -> Optional[BaseUser]:
        """Get user from session"""
        session_id = self._get_session_id_from_request(request)
        if not session_id:
            return None

        session = await self.session_backend.get_session(session_id)
        if not session or session.is_expired:
            return None

        # Get user
        user = await self.user_model.get(session.user_id)
        if user and user.is_active:
            session.user = user
            return user

        return None

    async def get_user_from_token(self, request: Request) -> Optional[BaseUser]:
        """Get user from JWT token"""
        token = self._extract_token_from_request(request)
        if not token:
            return None

        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.jwt_algorithm])
            user_id = payload.get('sub')
            if not user_id:
                return None

            user = await self.user_model.get(user_id)
            if user and user.is_active:
                return user

        except jwt.ExpiredSignatureError:
            pass
        except jwt.InvalidTokenError:
            pass

        return None

    def _get_session_id_from_request(self, request: Request) -> Optional[str]:
        """Extract session ID from request"""
        # Try cookie first
        session_id = request.cookies.get('session_id')
        if session_id:
            return session_id

        # Try header
        session_id = request.headers.get('x-session-id')
        if session_id:
            return session_id

        # Try query parameter
        session_id = request.query_params.get('session_id', [None])[0]
        return session_id

    def _extract_token_from_request(self, request: Request) -> Optional[str]:
        """Extract JWT token from request"""
        # Try Authorization header
        auth_header = request.headers.get('authorization', '')
        if auth_header.startswith('Bearer '):
            return auth_header[7:].strip()

        # Try custom header
        token = request.headers.get('x-auth-token')
        if token:
            return token

        # Try cookie
        token = request.cookies.get('auth_token')
        if token:
            return token

        # Try query parameter
        token = request.query_params.get('token', [None])[0]
        return token

    async def create_session(self, user: BaseUser, request: Request) -> UserSession:
        """Create a new session for user"""
        session_id = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + self.session_expiry

        session = UserSession(
            session_id=session_id,
            user_id=str(user.id),
            user=user,
            expires_at=expires_at
        )

        await self.session_backend.save_session(session)
        return session

    async def destroy_session(self, session_id: str):
        """Destroy a session"""
        await self.session_backend.delete_session(session_id)

    def create_access_token(self, user: BaseUser, data: Optional[Dict[str, Any]] = None) -> str:
        """Create JWT access token"""
        payload = {
            'sub': str(user.id),
            'type': 'access',
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + self.access_token_expiry,
        }

        if data:
            payload.update(data)

        return jwt.encode(payload, self.secret_key, algorithm=self.jwt_algorithm)

    def create_refresh_token(self, user: BaseUser) -> str:
        """Create JWT refresh token"""
        payload = {
            'sub': str(user.id),
            'type': 'refresh',
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + self.refresh_token_expiry,
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.jwt_algorithm)

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.jwt_algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    async def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """Refresh access token using refresh token"""
        payload = self.verify_token(refresh_token)
        if not payload or payload.get('type') != 'refresh':
            return None

        user_id = payload.get('sub')
        if not user_id:
            return None

        user = await self.user_model.get(user_id)
        if not user or not user.is_active:
            return None

        return self.create_access_token(user)

    async def logout(self, request: Request):
        """Logout user by destroying session and tokens"""
        # Destroy session
        session_id = self._get_session_id_from_request(request)
        if session_id:
            await self.destroy_session(session_id)

        # For tokens, we rely on client-side token removal
        # In a production system, you might want to maintain a blacklist

    def get_login_url(self) -> str:
        """Get login URL"""
        return '/auth/login'

    def get_logout_url(self) -> str:
        """Get logout URL"""
        return '/auth/logout'

    def get_register_url(self) -> str:
        """Get registration URL"""
        return '/auth/register'

    def get_profile_url(self) -> str:
        """Get profile URL"""
        return '/auth/profile'

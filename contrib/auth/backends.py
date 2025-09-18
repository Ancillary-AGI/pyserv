"""
Authentication backends for session and token storage.
"""

import json
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
from datetime import datetime

from .auth import UserSession, AuthToken


class SessionBackend(ABC):
    """Abstract base class for session storage"""

    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[UserSession]:
        """Get session by ID"""
        pass

    @abstractmethod
    async def save_session(self, session: UserSession):
        """Save session"""
        pass

    @abstractmethod
    async def delete_session(self, session_id: str):
        """Delete session"""
        pass

    @abstractmethod
    async def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        pass


class TokenBackend(ABC):
    """Abstract base class for token storage"""

    @abstractmethod
    async def get_token(self, token: str) -> Optional[AuthToken]:
        """Get token by value"""
        pass

    @abstractmethod
    async def save_token(self, token: AuthToken):
        """Save token"""
        pass

    @abstractmethod
    async def delete_token(self, token: str):
        """Delete token"""
        pass

    @abstractmethod
    async def cleanup_expired_tokens(self):
        """Clean up expired tokens"""
        pass


class InMemorySessionBackend(SessionBackend):
    """In-memory session storage (for development/testing)"""

    def __init__(self):
        self.sessions: Dict[str, UserSession] = {}

    async def get_session(self, session_id: str) -> Optional[UserSession]:
        """Get session by ID"""
        session = self.sessions.get(session_id)
        if session and not session.is_expired:
            return session
        elif session and session.is_expired:
            # Clean up expired session
            await self.delete_session(session_id)
        return None

    async def save_session(self, session: UserSession):
        """Save session"""
        self.sessions[session.session_id] = session

    async def delete_session(self, session_id: str):
        """Delete session"""
        self.sessions.pop(session_id, None)

    async def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        expired_ids = [
            session_id for session_id, session in self.sessions.items()
            if session.is_expired
        ]
        for session_id in expired_ids:
            await self.delete_session(session_id)


class InMemoryTokenBackend(TokenBackend):
    """In-memory token storage (for development/testing)"""

    def __init__(self):
        self.tokens: Dict[str, AuthToken] = {}

    async def get_token(self, token: str) -> Optional[AuthToken]:
        """Get token by value"""
        auth_token = self.tokens.get(token)
        if auth_token and not auth_token.is_expired:
            return auth_token
        elif auth_token and auth_token.is_expired:
            # Clean up expired token
            await self.delete_token(token)
        return None

    async def save_token(self, token: AuthToken):
        """Save token"""
        self.tokens[token.token] = token

    async def delete_token(self, token: str):
        """Delete token"""
        self.tokens.pop(token, None)

    async def cleanup_expired_tokens(self):
        """Clean up expired tokens"""
        expired_tokens = [
            token for token, auth_token in self.tokens.items()
            if auth_token.is_expired
        ]
        for token in expired_tokens:
            await self.delete_token(token)


class DatabaseSessionBackend(SessionBackend):
    """Database-backed session storage"""

    def __init__(self, session_model=None):
        # This would use a session model from the database
        # For now, we'll use a placeholder
        self.session_model = session_model

    async def get_session(self, session_id: str) -> Optional[UserSession]:
        """Get session by ID"""
        # Implementation would query database
        # For now, return None
        return None

    async def save_session(self, session: UserSession):
        """Save session"""
        # Implementation would save to database
        pass

    async def delete_session(self, session_id: str):
        """Delete session"""
        # Implementation would delete from database
        pass

    async def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        # Implementation would delete expired sessions from database
        pass


class DatabaseTokenBackend(TokenBackend):
    """Database-backed token storage"""

    def __init__(self, token_model=None):
        # This would use a token model from the database
        self.token_model = token_model

    async def get_token(self, token: str) -> Optional[AuthToken]:
        """Get token by value"""
        # Implementation would query database
        return None

    async def save_token(self, token: AuthToken):
        """Save token"""
        # Implementation would save to database
        pass

    async def delete_token(self, token: str):
        """Delete token"""
        # Implementation would delete from database
        pass

    async def cleanup_expired_tokens(self):
        """Clean up expired tokens"""
        # Implementation would delete expired tokens from database
        pass


# Default backends
SessionBackend = InMemorySessionBackend
TokenBackend = InMemoryTokenBackend
DatabaseBackend = DatabaseSessionBackend  # Alias for backward compatibility

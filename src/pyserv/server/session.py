"""
Session Management System for Pyserv Framework

This module provides comprehensive session management with:
- Server-side session storage with multiple backends
- Client-side session handling with secure cookies
- Session encryption and integrity verification
- Session lifecycle management
- Session middleware for automatic handling
- Session stores (memory, database, redis, etc.)
- Session security features
- Session monitoring and cleanup
"""

import asyncio
import json
import logging
import secrets
import time
import uuid
from typing import Dict, List, Callable, Any, Optional, Type, Union, Awaitable, Set
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class SessionState(str, Enum):
    """Session states"""
    ACTIVE = "active"
    EXPIRED = "expired"
    INVALIDATED = "invalidated"
    ABANDONED = "abandoned"


class SessionBackend(str, Enum):
    """Session storage backends"""
    MEMORY = "memory"
    DATABASE = "database"
    REDIS = "redis"
    FILESYSTEM = "filesystem"
    CUSTOM = "custom"


@dataclass
class SessionConfig:
    """Session configuration"""
    secret_key: str = field(default_factory=lambda: secrets.token_hex(32))
    session_name: str = "pyserv_session"
    max_age: int = 3600  # 1 hour in seconds
    secure: bool = True
    http_only: bool = True
    same_site: str = "Lax"
    domain: Optional[str] = None
    path: str = "/"
    backend: SessionBackend = SessionBackend.MEMORY
    redis_url: Optional[str] = None
    database_table: str = "sessions"
    cleanup_interval: int = 300  # 5 minutes
    max_sessions_per_user: int = 10
    session_timeout: int = 1800  # 30 minutes of inactivity
    enable_encryption: bool = True
    compression_enabled: bool = True
    cookie_max_age: Optional[int] = None


@dataclass
class SessionData:
    """Session data container"""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    state: SessionState = SessionState.ACTIVE
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if session is expired"""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def touch(self) -> None:
        """Update last activity timestamp"""
        self.updated_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'data': self.data,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'expires_at': self.expires_at,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'state': self.state.value,
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionData':
        """Create from dictionary"""
        session = cls()
        session.session_id = data.get('session_id', session.session_id)
        session.user_id = data.get('user_id')
        session.data = data.get('data', {})
        session.created_at = data.get('created_at', session.created_at)
        session.updated_at = data.get('updated_at', session.updated_at)
        session.expires_at = data.get('expires_at')
        session.ip_address = data.get('ip_address')
        session.user_agent = data.get('user_agent')
        session.state = SessionState(data.get('state', SessionState.ACTIVE.value))
        session.metadata = data.get('metadata', {})
        return session


class SessionStore(ABC):
    """Abstract session store"""

    @abstractmethod
    async def get(self, session_id: str) -> Optional[SessionData]:
        """Get session data"""
        pass

    @abstractmethod
    async def set(self, session: SessionData) -> None:
        """Set session data"""
        pass

    @abstractmethod
    async def delete(self, session_id: str) -> None:
        """Delete session"""
        pass

    @abstractmethod
    async def cleanup(self) -> int:
        """Clean up expired sessions"""
        pass

    @abstractmethod
    async def get_user_sessions(self, user_id: str) -> List[SessionData]:
        """Get all sessions for a user"""
        pass


class MemorySessionStore(SessionStore):
    """In-memory session store"""

    def __init__(self):
        self.sessions: Dict[str, SessionData] = {}
        self.user_sessions: Dict[str, Set[str]] = {}

    async def get(self, session_id: str) -> Optional[SessionData]:
        """Get session data"""
        session = self.sessions.get(session_id)
        if session and session.is_expired():
            await self.delete(session_id)
            return None
        return session

    async def set(self, session: SessionData) -> None:
        """Set session data"""
        self.sessions[session.session_id] = session

        if session.user_id:
            if session.user_id not in self.user_sessions:
                self.user_sessions[session.user_id] = set()
            self.user_sessions[session.user_id].add(session.session_id)

    async def delete(self, session_id: str) -> None:
        """Delete session"""
        session = self.sessions.get(session_id)
        if session and session.user_id:
            self.user_sessions[session.user_id].discard(session_id)
            if not self.user_sessions[session.user_id]:
                del self.user_sessions[session.user_id]

        self.sessions.pop(session_id, None)

    async def cleanup(self) -> int:
        """Clean up expired sessions"""
        expired_count = 0
        current_time = time.time()

        expired_sessions = []
        for session_id, session in self.sessions.items():
            if session.is_expired():
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            await self.delete(session_id)
            expired_count += 1

        return expired_count

    async def get_user_sessions(self, user_id: str) -> List[SessionData]:
        """Get all sessions for a user"""
        session_ids = self.user_sessions.get(user_id, set())
        sessions = []

        for session_id in session_ids:
            session = await self.get(session_id)
            if session:
                sessions.append(session)

        return sessions


class DatabaseSessionStore(SessionStore):
    """Database session store"""

    def __init__(self, db_connection):
        self.db = db_connection
        self.table_name = "sessions"

    async def get(self, session_id: str) -> Optional[SessionData]:
        """Get session data"""
        try:
            query = f"SELECT * FROM {self.table_name} WHERE session_id = $1"
            result = await self.db.fetch_one(query, (session_id,))

            if result:
                session_data = SessionData.from_dict(result)
                if session_data.is_expired():
                    await self.delete(session_id)
                    return None
                return session_data

        except Exception as e:
            logger.error(f"Error getting session {session_id}: {e}")

        return None

    async def set(self, session: SessionData) -> None:
        """Set session data"""
        try:
            data = session.to_dict()
            columns = ', '.join(data.keys())
            placeholders = ', '.join([f'${i+1}' for i in range(len(data))])
            values = tuple(data.values())

            query = f"""
                INSERT INTO {self.table_name} ({columns})
                VALUES ({placeholders})
                ON CONFLICT (session_id)
                DO UPDATE SET {', '.join([f'{k} = ${i+1}' for i, k in enumerate(data.keys())])}
            """

            await self.db.execute(query, values)

        except Exception as e:
            logger.error(f"Error setting session {session.session_id}: {e}")

    async def delete(self, session_id: str) -> None:
        """Delete session"""
        try:
            query = f"DELETE FROM {self.table_name} WHERE session_id = $1"
            await self.db.execute(query, (session_id,))
        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {e}")

    async def cleanup(self) -> int:
        """Clean up expired sessions"""
        try:
            current_time = time.time()
            query = f"DELETE FROM {self.table_name} WHERE expires_at IS NOT NULL AND expires_at < $1"
            result = await self.db.execute(query, (current_time,))
            return result.row_count if hasattr(result, 'row_count') else 0
        except Exception as e:
            logger.error(f"Error cleaning up sessions: {e}")
            return 0

    async def get_user_sessions(self, user_id: str) -> List[SessionData]:
        """Get all sessions for a user"""
        try:
            query = f"SELECT * FROM {self.table_name} WHERE user_id = $1"
            results = await self.db.fetch_all(query, (user_id,))

            sessions = []
            for result in results:
                session_data = SessionData.from_dict(result)
                if not session_data.is_expired():
                    sessions.append(session_data)

            return sessions

        except Exception as e:
            logger.error(f"Error getting user sessions for {user_id}: {e}")
            return []


class SessionManager:
    """Session manager with encryption and integrity"""

    def __init__(self, config: SessionConfig, store: SessionStore):
        self.config = config
        self.store = store
        self.crypto = SessionCrypto(config.secret_key)
        self.cleanup_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        """Start session manager"""
        if self._running:
            return

        self._running = True
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Session manager started")

    async def stop(self) -> None:
        """Stop session manager"""
        if not self._running:
            return

        self._running = False

        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass

        logger.info("Session manager stopped")

    async def create_session(self, user_id: Optional[str] = None,
                           data: Optional[Dict[str, Any]] = None,
                           ip_address: Optional[str] = None,
                           user_agent: Optional[str] = None) -> SessionData:
        """Create new session"""
        session = SessionData(
            user_id=user_id,
            data=data or {},
            ip_address=ip_address,
            user_agent=user_agent
        )

        if self.config.max_age:
            session.expires_at = time.time() + self.config.max_age

        await self.store.set(session)
        logger.info(f"Created session {session.session_id} for user {user_id}")
        return session

    async def get_session(self, session_id: str) -> Optional[SessionData]:
        """Get session by ID"""
        session = await self.store.get(session_id)
        if session:
            session.touch()
            await self.store.set(session)
        return session

    async def update_session(self, session_id: str, data: Dict[str, Any]) -> Optional[SessionData]:
        """Update session data"""
        session = await self.store.get(session_id)
        if session:
            session.data.update(data)
            session.touch()
            await self.store.set(session)
            logger.debug(f"Updated session {session_id}")
        return session

    async def delete_session(self, session_id: str) -> None:
        """Delete session"""
        await self.store.delete(session_id)
        logger.info(f"Deleted session {session_id}")

    async def get_user_sessions(self, user_id: str) -> List[SessionData]:
        """Get all sessions for a user"""
        return await self.store.get_user_sessions(user_id)

    async def invalidate_user_sessions(self, user_id: str) -> int:
        """Invalidate all sessions for a user"""
        sessions = await self.store.get_user_sessions(user_id)
        invalidated_count = 0

        for session in sessions:
            session.state = SessionState.INVALIDATED
            await self.store.set(session)
            invalidated_count += 1

        logger.info(f"Invalidated {invalidated_count} sessions for user {user_id}")
        return invalidated_count

    async def cleanup_sessions(self) -> int:
        """Clean up expired sessions"""
        return await self.store.cleanup()

    async def _cleanup_loop(self) -> None:
        """Background cleanup task"""
        while self._running:
            try:
                await asyncio.sleep(self.config.cleanup_interval)
                cleaned_count = await self.cleanup_sessions()
                if cleaned_count > 0:
                    logger.info(f"Cleaned up {cleaned_count} expired sessions")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in session cleanup loop: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get session manager statistics"""
        return {
            'running': self._running,
            'cleanup_interval': self.config.cleanup_interval,
            'max_sessions_per_user': self.config.max_sessions_per_user,
            'session_timeout': self.config.session_timeout
        }


class SessionCrypto:
    """Session encryption and integrity verification"""

    def __init__(self, secret_key: str):
        self.secret_key = secret_key.encode()

    def encrypt(self, data: Dict[str, Any]) -> str:
        """Encrypt session data"""
        import base64
        import hashlib
        import hmac
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

        # Generate encryption key from secret
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'pyserv_session_salt',
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.secret_key))
        fernet = Fernet(key)

        # Serialize data
        json_data = json.dumps(data, sort_keys=True)

        # Encrypt
        encrypted = fernet.encrypt(json_data.encode())

        # Add HMAC for integrity
        hmac_digest = hmac.new(self.secret_key, encrypted, hashlib.sha256).hexdigest()

        return f"{base64.urlsafe_b64encode(encrypted).decode()}.{hmac_digest}"

    def decrypt(self, encrypted_data: str) -> Dict[str, Any]:
        """Decrypt session data"""
        import base64
        import hashlib
        import hmac
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

        try:
            # Split data and HMAC
            parts = encrypted_data.split('.')
            if len(parts) != 2:
                raise ValueError("Invalid encrypted data format")

            encrypted = base64.urlsafe_b64decode(parts[0])
            provided_hmac = parts[1]

            # Verify HMAC
            expected_hmac = hmac.new(self.secret_key, encrypted, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(provided_hmac, expected_hmac):
                raise ValueError("Session data integrity check failed")

            # Generate decryption key
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'pyserv_session_salt',
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(self.secret_key))
            fernet = Fernet(key)

            # Decrypt
            decrypted = fernet.decrypt(encrypted).decode()
            return json.loads(decrypted)

        except Exception as e:
            logger.error(f"Error decrypting session data: {e}")
            raise ValueError("Failed to decrypt session data")


class SessionMiddleware:
    """Session middleware for automatic session handling"""

    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager

    async def __call__(self, request, call_next):
        """Process request with session handling"""
        # Get session ID from cookie
        session_id = request.cookies.get(self.session_manager.config.session_name)

        # Load session if exists
        session = None
        if session_id:
            try:
                session = await self.session_manager.get_session(session_id)
            except Exception as e:
                logger.warning(f"Error loading session {session_id}: {e}")

        # Attach session to request
        request.session = SessionInterface(session, self.session_manager)

        # Process request
        response = await call_next(request)

        # Save session if modified
        if hasattr(request.session, '_modified') and request.session._modified:
            await request.session.save()

        # Set session cookie if new session
        if session and not session_id:
            response.set_cookie(
                self.session_manager.config.session_name,
                session.session_id,
                max_age=self.session_manager.config.max_age,
                secure=self.session_manager.config.secure,
                httponly=self.session_manager.config.http_only,
                samesite=self.session_manager.config.same_site,
                domain=self.session_manager.config.domain,
                path=self.session_manager.config.path
            )

        return response


class SessionInterface:
    """Session interface for request handling"""

    def __init__(self, session: Optional[SessionData], session_manager: SessionManager):
        self._session = session
        self._session_manager = session_manager
        self._modified = False

    def __getitem__(self, key: str) -> Any:
        """Get session value"""
        if not self._session:
            raise KeyError(f"Session not available for key: {key}")
        return self._session.data.get(key)

    def __setitem__(self, key: str, value: Any) -> None:
        """Set session value"""
        if not self._session:
            raise RuntimeError("Session not available")
        self._session.data[key] = value
        self._modified = True

    def __delitem__(self, key: str) -> None:
        """Delete session value"""
        if not self._session:
            raise RuntimeError("Session not available")
        if key in self._session.data:
            del self._session.data[key]
            self._modified = True

    def __contains__(self, key: str) -> bool:
        """Check if key exists in session"""
        if not self._session:
            return False
        return key in self._session.data

    def get(self, key: str, default: Any = None) -> Any:
        """Get session value with default"""
        if not self._session:
            return default
        return self._session.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set session value"""
        self[key] = value

    def delete(self, key: str) -> None:
        """Delete session value"""
        del self[key]

    def clear(self) -> None:
        """Clear all session data"""
        if self._session:
            self._session.data.clear()
            self._modified = True

    def flush(self) -> None:
        """Flush session (mark for deletion)"""
        if self._session:
            self._session.state = SessionState.INVALIDATED
            self._modified = True

    async def save(self) -> None:
        """Save session"""
        if self._session and self._modified:
            await self._session_manager.store.set(self._session)
            self._modified = False

    async def cycle_key(self) -> None:
        """Cycle session key (invalidate old session)"""
        if self._session:
            old_session_id = self._session.session_id
            self._session.session_id = str(uuid.uuid4())
            self._modified = True
            await self.save()
            await self._session_manager.delete_session(old_session_id)

    @property
    def session_id(self) -> Optional[str]:
        """Get session ID"""
        return self._session.session_id if self._session else None

    @property
    def user_id(self) -> Optional[str]:
        """Get user ID"""
        return self._session.user_id if self._session else None

    @user_id.setter
    def user_id(self, value: str) -> None:
        """Set user ID"""
        if self._session:
            self._session.user_id = value
            self._modified = True

    def keys(self):
        """Get session keys"""
        if not self._session:
            return []
        return self._session.data.keys()

    def values(self):
        """Get session values"""
        if not self._session:
            return []
        return self._session.data.values()

    def items(self):
        """Get session items"""
        if not self._session:
            return []
        return self._session.data.items()


# Global session manager
_session_manager: Optional[SessionManager] = None

def get_session_manager(config: Optional[SessionConfig] = None) -> SessionManager:
    """Get the global session manager instance"""
    global _session_manager
    if _session_manager is None:
        if config is None:
            config = SessionConfig()
        store = MemorySessionStore()
        _session_manager = SessionManager(config, store)
    return _session_manager

async def start_session_manager(config: Optional[SessionConfig] = None) -> SessionManager:
    """Start the global session manager"""
    manager = get_session_manager(config)
    await manager.start()
    return manager

async def stop_session_manager() -> None:
    """Stop the global session manager"""
    global _session_manager
    if _session_manager:
        await _session_manager.stop()
        _session_manager = None

__all__ = [
    'SessionManager', 'SessionStore', 'SessionData', 'SessionConfig',
    'SessionInterface', 'SessionMiddleware', 'SessionCrypto',
    'MemorySessionStore', 'DatabaseSessionStore', 'SessionState',
    'SessionBackend', 'get_session_manager', 'start_session_manager',
    'stop_session_manager'
]

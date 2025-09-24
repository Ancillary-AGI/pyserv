"""
CSRF (Cross-Site Request Forgery) protection system.
"""

import secrets
import hashlib
import time
from typing import Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

@dataclass
class CSRFToken:
    token: str
    created_at: datetime
    expires_at: datetime
    used: bool = False
    session_id: Optional[str] = None

class CSRFProtection:
    """
    Comprehensive CSRF protection system.
    """

    def __init__(self, secret_key: str, token_expiry: int = 3600):
        self.secret_key = secret_key
        self.token_expiry = token_expiry  # seconds
        self.tokens: Dict[str, CSRFToken] = {}  # token -> CSRFToken
        self.session_tokens: Dict[str, str] = {}  # session_id -> token
        self.logger = logging.getLogger(__name__)

    def generate_token(self, session_id: Optional[str] = None) -> str:
        """Generate a new CSRF token."""
        # Create a random token
        random_part = secrets.token_urlsafe(32)

        # Add timestamp and secret for additional security
        timestamp = str(int(time.time()))
        combined = f"{random_part}.{timestamp}.{self.secret_key}"

        # Create hash for verification
        token_hash = hashlib.sha256(combined.encode()).hexdigest()

        # Create full token
        full_token = f"{random_part}.{timestamp}.{token_hash}"

        # Store token
        expires_at = datetime.now() + timedelta(seconds=self.token_expiry)
        csrf_token = CSRFToken(
            token=full_token,
            created_at=datetime.now(),
            expires_at=expires_at,
            session_id=session_id
        )

        self.tokens[full_token] = csrf_token

        if session_id:
            self.session_tokens[session_id] = full_token

        self.logger.debug(f"Generated CSRF token for session {session_id}")
        return full_token

    def validate_token(self, token: str, session_id: Optional[str] = None) -> bool:
        """Validate a CSRF token."""
        if not token:
            return False

        csrf_token = self.tokens.get(token)
        if not csrf_token:
            return False

        # Check if token has expired
        if datetime.now() > csrf_token.expires_at:
            self.logger.warning(f"Expired CSRF token used: {token}")
            return False

        # Check if token has already been used
        if csrf_token.used:
            self.logger.warning(f"Used CSRF token reused: {token}")
            return False

        # Verify token format and hash
        if not self._verify_token_format(token):
            return False

        # Check session binding
        if session_id and csrf_token.session_id != session_id:
            self.logger.warning(f"CSRF token used with wrong session: {token}")
            return False

        # Mark token as used
        csrf_token.used = True

        self.logger.debug(f"Validated CSRF token for session {session_id}")
        return True

    def _verify_token_format(self, token: str) -> bool:
        """Verify the format and hash of a CSRF token."""
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return False

            random_part, timestamp, token_hash = parts

            # Verify hash
            combined = f"{random_part}.{timestamp}.{self.secret_key}"
            expected_hash = hashlib.sha256(combined.encode()).hexdigest()

            return token_hash == expected_hash

        except Exception:
            return False

    def get_token_for_session(self, session_id: str) -> Optional[str]:
        """Get the current CSRF token for a session."""
        return self.session_tokens.get(session_id)

    def refresh_token(self, session_id: str) -> str:
        """Refresh the CSRF token for a session."""
        # Invalidate old token
        old_token = self.session_tokens.get(session_id)
        if old_token and old_token in self.tokens:
            self.tokens[old_token].used = True

        # Generate new token
        new_token = self.generate_token(session_id)
        return new_token

    def invalidate_session_tokens(self, session_id: str):
        """Invalidate all tokens for a session."""
        if session_id in self.session_tokens:
            token = self.session_tokens[session_id]
            if token in self.tokens:
                self.tokens[token].used = True
            del self.session_tokens[session_id]

        self.logger.info(f"Invalidated all CSRF tokens for session {session_id}")

    def cleanup_expired_tokens(self):
        """Clean up expired tokens."""
        current_time = datetime.now()
        expired_tokens = []

        for token, csrf_token in self.tokens.items():
            if current_time > csrf_token.expires_at:
                expired_tokens.append(token)

        for token in expired_tokens:
            del self.tokens[token]

        # Also clean up session tokens that point to expired tokens
        expired_sessions = []
        for session_id, token in self.session_tokens.items():
            if token not in self.tokens:
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            del self.session_tokens[session_id]

        if expired_tokens or expired_sessions:
            self.logger.debug(f"Cleaned up {len(expired_tokens)} expired tokens and {len(expired_sessions)} expired sessions")

    def get_token_info(self, token: str) -> Optional[Dict[str, Any]]:
        """Get information about a CSRF token."""
        csrf_token = self.tokens.get(token)
        if not csrf_token:
            return None

        return {
            "token": token,
            "created_at": csrf_token.created_at.isoformat(),
            "expires_at": csrf_token.expires_at.isoformat(),
            "used": csrf_token.used,
            "session_id": csrf_token.session_id
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get CSRF protection statistics."""
        total_tokens = len(self.tokens)
        used_tokens = sum(1 for token in self.tokens.values() if token.used)
        expired_tokens = sum(1 for token in self.tokens.values()
                           if datetime.now() > token.expires_at)

        return {
            "total_tokens": total_tokens,
            "used_tokens": used_tokens,
            "expired_tokens": expired_tokens,
            "active_tokens": total_tokens - used_tokens - expired_tokens,
            "total_sessions": len(self.session_tokens)
        }

    def rotate_secret_key(self, new_secret_key: str):
        """Rotate the secret key (invalidates all existing tokens)."""
        self.secret_key = new_secret_key
        self.tokens.clear()
        self.session_tokens.clear()
        self.logger.warning("Rotated CSRF secret key - all existing tokens invalidated")

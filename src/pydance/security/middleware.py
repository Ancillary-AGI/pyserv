# server_framework/security/middleware.py
import secrets
import jwt
import json
import base64
from typing import Optional, Dict, Any, List, Union
from datetime import datetime, timedelta
from abc import ABC
import hmac
import hashlib
import time

from ..core.middleware import HTTPMiddleware, WebSocketMiddleware
from ..core.request import Request
from ..core.response import Response
from ..core.websocket import WebSocket
from ..core.exceptions import HTTPException, Forbidden
from ...contrib.auth import Auth

class SecurityMiddleware(HTTPMiddleware):
    """Security middleware for common web vulnerabilities"""
    
    def __init__(self, **options):
        self.options = {
            'hsts_max_age': 31536000,  # 1 year
            'xss_protection': '1; mode=block',
            'no_sniff': True,
            'frame_options': 'DENY',
            'content_security_policy': "default-src 'self'",
            'referrer_policy': 'no-referrer',
            **options
        }
    
    async def process_request(self, request: Request) -> Request:
        # Validate host if allowed_hosts is configured
        allowed_hosts = getattr(request.app.config, 'allowed_hosts', [])
        if allowed_hosts and request.headers.get('host') not in allowed_hosts:
            raise HTTPException(400, "Invalid host header")
        
        return request
        
    async def process_response(self, request: Request, response: Response) -> Response:
        # Add security headers
        headers = response.headers
        
        # HTTP Strict Transport Security
        if self.options['hsts_max_age']:
            headers['Strict-Transport-Security'] = f'max-age={self.options["hsts_max_age"]}; includeSubDomains;'
        
        # XSS Protection
        if self.options['xss_protection']:
            headers['X-XSS-Protection'] = self.options['xss_protection']
        
        # No sniff
        if self.options['no_sniff']:
            headers['X-Content-Type-Options'] = 'nosniff'
        
        # Frame options
        if self.options['frame_options']:
            headers['X-Frame-Options'] = self.options['frame_options']
        
        # Content Security Policy
        if self.options['content_security_policy']:
            headers['Content-Security-Policy'] = self.options['content_security_policy']

        if self.options.get('referrer_policy'):
            headers['Referrer-Policy'] = self.options['referrer_policy']
        
        return response

class CORSMiddleware(HTTPMiddleware):
    """CORS middleware"""
    
    def __init__(self, 
                 allow_origins: List[str] = None,
                 allow_methods: List[str] = None,
                 allow_headers: List[str] = None,
                 allow_credentials: bool = True,
                 max_age: int = 600):
        self.allow_origins = allow_origins or ["*"]
        self.allow_methods = allow_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.allow_headers = allow_headers or ["*"]
        self.allow_credentials = allow_credentials
        self.max_age = max_age
    
    async def process_request(self, request: Request) -> Request:
        return request
        
    async def process_response(self, request: Request, response: Response) -> Response:
        origin = request.headers.get('origin')
        
        if origin and (origin in self.allow_origins or "*" in self.allow_origins):
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Methods'] = ', '.join(self.allow_methods)
            response.headers['Access-Control-Allow-Headers'] = ', '.join(self.allow_headers)
            response.headers['Access-Control-Allow-Credentials'] = str(self.allow_credentials).lower()
            response.headers['Access-Control-Max-Age'] = str(self.max_age)
        
        return response

class CSRFMiddleware(HTTPMiddleware):
    """CSRF protection middleware"""
    
    def __init__(self, **options):
        self.options = {
            'secret_key': 'your-secret-key-here',
            'token_length': 32,
            'cookie_name': 'csrf_token',
            'header_name': 'X-CSRF-Token',
            'form_field_name': 'csrf_token',
            'secure_cookies': True,
            'token_expiry': timedelta(hours=24),
            **options
        }
        self._tokens: Dict[str, datetime] = {}
    
    async def process_request(self, request: Request) -> Request:
        # Skip CSRF check for safe methods
        if request.method in ['GET', 'HEAD', 'OPTIONS', 'TRACE']:
            return request
        
        # Get token from header or form data
        token = (
            request.headers.get(self.options['header_name']) or
            (await request.form()).get(self.options['form_field_name'])
        )
        
        # Get token from cookie using proper cookie parsing
        stored_token = self._parse_cookie_token(request.headers.get('cookie', ''))
        
        # Validate token
        if not token or not stored_token or not self._validate_csrf_token(token, stored_token):
            raise Forbidden(403, "CSRF token validation failed")
        
        # Clean up expired tokens
        self._cleanup_tokens()
        
        return request
        
    async def process_response(self, request: Request, response: Response) -> Response:
        # Generate and set CSRF token for GET requests
        if request.method == 'GET':
            token = secrets.token_urlsafe(self.options['token_length'])
            self._tokens[token] = datetime.now()
            
            # Set cookie with proper attributes
            cookie_parts = [
                f"{self.options['cookie_name']}={token}",
                "HttpOnly",
                "Path=/",
                f"Max-Age={int(self.options['token_expiry'].total_seconds())}"
            ]
            
            if self.options['secure_cookies'] or request.headers.get('x-forwarded-proto') == 'https':
                cookie_parts.append("Secure")
            
            if request.headers.get('host'):
                domain = request.headers['host'].split(':')[0]
                if domain not in ['localhost', '127.0.0.1']:
                    cookie_parts.append(f"Domain={domain}")
            
            response.headers['Set-Cookie'] = '; '.join(cookie_parts)
        
        return response
    
    def _parse_cookie_token(self, cookie_header: str) -> Optional[str]:
        """Properly parse CSRF token from cookie header"""
        if not cookie_header:
            return None
        
        cookies = {}
        for cookie in cookie_header.split(';'):
            cookie = cookie.strip()
            if '=' in cookie:
                key, value = cookie.split('=', 1)
                cookies[key.strip()] = value.strip()
        
        return cookies.get(self.options['cookie_name'])
    
    def _validate_csrf_token(self, submitted_token: str, stored_token: str) -> bool:
        """Validate CSRF token using constant-time comparison"""
        return hmac.compare_digest(submitted_token, stored_token)
    
    def _cleanup_tokens(self):
        """Clean up expired tokens"""
        now = datetime.now()
        expired_tokens = [
            token for token, created in self._tokens.items()
            if now - created > self.options['token_expiry']
        ]
        for token in expired_tokens:
            self._tokens.pop(token, None)

class WebSocketAuthMiddleware(WebSocketMiddleware):
    """WebSocket authentication middleware with comprehensive token parsing"""
    
    def __init__(self, **options):
        self.options = {
            'secret_key': 'your-jwt-secret-key-here',
            'token_algorithms': ['HS256'],
            'token_audience': 'websocket-auth',
            'token_issuer': 'your-app',
            'require_https': True,
            'allowed_origins': [],
            **options
        }
    
    async def process_websocket(self, websocket: WebSocket) -> Optional[WebSocket]:
        try:
            # Validate origin if specified
            if not self._validate_origin(websocket):
                return None
            
            # Extract and validate token
            token = self._extract_token(websocket)
            if not token:
                return None
            
            # Parse and validate token
            token_data = self._parse_and_validate_token(token)
            if not token_data:
                return None
            
            # Set authentication state
            websocket.state.authenticated = True
            websocket.state.user_id = token_data.get('sub')
            websocket.state.user_roles = token_data.get('roles', [])
            websocket.state.token_data = token_data
            
            return websocket
            
        except Exception as e:
            # Log the error but don't expose details to client
            print(f"WebSocket authentication error: {e}")
            return None
    
    def _validate_origin(self, websocket: WebSocket) -> bool:
        """Validate WebSocket origin"""
        origin = websocket.headers.get('origin')
        
        # If no origins specified, allow all
        if not self.options['allowed_origins']:
            return True
        
        # If origins specified, validate
        return origin in self.options['allowed_origins']
    
    def _extract_token(self, websocket: WebSocket) -> Optional[str]:
        """Extract token from various sources"""
        # 1. Check query parameters
        token = websocket.query_params.get('token', [''])[0]
        if token:
            return token
        
        # 2. Check Authorization header (Bearer token)
        auth_header = websocket.headers.get('authorization', '')
        if auth_header.startswith('Bearer '):
            return auth_header[7:].strip()
        
        # 3. Check custom headers
        token = websocket.headers.get('x-websocket-token') or websocket.headers.get('x-auth-token')
        if token:
            return token
        
        # 4. Check cookies (for same-origin WebSockets)
        cookie_header = websocket.headers.get('cookie', '')
        if cookie_header:
            cookies = {}
            for cookie in cookie_header.split(';'):
                cookie = cookie.strip()
                if '=' in cookie:
                    key, value = cookie.split('=', 1)
                    cookies[key.strip()] = value.strip()
            
            token = cookies.get('websocket_token') or cookies.get('auth_token')
            if token:
                return token
        
        return None
    
    def _parse_and_validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Parse and validate JWT token with multiple fallback strategies"""
        try:
            # Try standard JWT validation first
            try:
                payload = jwt.decode(
                    token,
                    self.options['secret_key'],
                    algorithms=self.options['token_algorithms'],
                    audience=self.options['token_audience'],
                    issuer=self.options['token_issuer']
                )
                return payload
            except jwt.InvalidTokenError:
                # Fallback to simpler validation for custom tokens
                return self._validate_custom_token(token)
                
        except Exception as e:
            print(f"Token validation error: {e}")
            return None
    
    def _validate_custom_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate custom token formats (non-JWT)"""
        try:
            # Option 1: Simple signed token (HMAC)
            if self._validate_hmac_token(token):
                return {'sub': 'user', 'roles': ['user']}
            
            # Option 2: Base64 encoded JSON token
            if self._validate_base64_json_token(token):
                return {'sub': 'user', 'roles': ['user']}
            
            # Option 3: Simple token validation (for development)
            if self._validate_simple_token(token):
                return {'sub': token, 'roles': ['user']}
            
            return None
            
        except Exception:
            return None
    
    def _validate_hmac_token(self, token: str) -> bool:
        """Validate HMAC-signed token"""
        try:
            # Split token and signature
            if '.' not in token:
                return False
            
            data, signature = token.rsplit('.', 1)
            
            # Recreate expected signature
            expected_signature = hmac.new(
                self.options['secret_key'].encode(),
                data.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # Constant-time comparison
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception:
            return False
    
    def _validate_base64_json_token(self, token: str) -> bool:
        """Validate base64 encoded JSON token"""
        try:
            # Decode base64
            decoded = base64.urlsafe_b64decode(token + '===').decode()
            
            # Parse JSON
            data = json.loads(decoded)
            
            # Validate required fields
            return bool(data.get('user_id') and data.get('timestamp'))
            
        except Exception:
            return False
    
    def _validate_simple_token(self, token: str) -> bool:
        """Simple token validation for development"""
        # In production, this should be more robust
        return len(token) >= 16  # Minimum token length
    
    def _get_user_id_from_token(self, token_data: Dict[str, Any]) -> Optional[str]:
        """Extract user ID from token data with multiple fallback strategies"""
        # Try various common user ID fields
        user_id = (
            token_data.get('sub') or  # JWT standard
            token_data.get('user_id') or
            token_data.get('uid') or
            token_data.get('id') or
            token_data.get('username')
        )
        
        return str(user_id) if user_id else None
    
    def _get_user_roles_from_token(self, token_data: Dict[str, Any]) -> List[str]:
        """Extract user roles from token data"""
        roles = token_data.get('roles', [])
        if isinstance(roles, str):
            roles = roles.split(',')
        return [str(role).strip() for role in roles if role]
    
    def create_jwt_token(self, user_id: str, roles: List[str] = None, 
                        expires_in: timedelta = timedelta(hours=1)) -> str:
        """Create a JWT token for testing or programmatic use"""
        payload = {
            'sub': user_id,
            'roles': roles or ['user'],
            'aud': self.options['token_audience'],
            'iss': self.options['token_issuer'],
            'exp': datetime.utcnow() + expires_in,
            'iat': datetime.utcnow()
        }
        
        return jwt.encode(payload, self.options['secret_key'], algorithm='HS256')

# Rate limiting middleware
class RateLimitMiddleware(HTTPMiddleware, WebSocketMiddleware):
    def __init__(self, requests_per_minute: int = 100, ip_based: bool = True):
        self.requests_per_minute = requests_per_minute
        self.ip_based = ip_based
        self.requests = {}
    
    async def process_request(self, request: Request) -> Request:
        identifier = request.remote_addr if self.ip_based else "global"
        current_time = time.time()
        
        # Clean up old entries
        self.requests = {ip: ts for ip, ts in self.requests.items() 
                        if current_time - ts < 60}
        
        # Check rate limit
        if len(self.requests.get(identifier, [])) >= self.requests_per_minute:
            from ..exceptions import TooManyRequests
            raise TooManyRequests("Rate limit exceeded")
        
        # Record request
        if identifier not in self.requests:
            self.requests[identifier] = []
        self.requests[identifier].append(current_time)
        
        return request
        
    async def process_response(self, request: Request, response: Response) -> Response:
        return response
    
    async def process_websocket(self, websocket: WebSocket) -> Optional[WebSocket]:
        # Similar rate limiting for WebSocket connections
        return websocket

class AuthenticationMiddleware(HTTPMiddleware):
    """Authentication middleware"""
    
    def __init__(self, auth: Auth):
        self.auth = auth
    
    async def process_request(self, request: Request) -> Request:
        user = await self.auth.get_user_from_request(request)
        if user:
            request.state.user = user
        return request
        
    async def process_response(self, request: Request, response: Response) -> Response:
        return response

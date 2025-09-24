"""
Pyserv  Unified Security Middleware
Single comprehensive security system replacing multiple redundant implementations
"""

import re
import hashlib
import time
import gzip
import zlib
import secrets
import jwt
import base64
import hmac
from typing import Dict, List, Optional, Any, Callable, Tuple, Union
from collections import defaultdict, deque
import asyncio
import threading
from urllib.parse import unquote
from datetime import datetime, timedelta
import html


# Security Exceptions
class SecurityError(Exception):
    """Base security exception"""
    pass

class XSSAttack(SecurityError):
    """XSS attack detected"""
    pass

class SQLInjection(SecurityError):
    """SQL injection attempt detected"""
    pass

class DoSAttack(SecurityError):
    """DoS attack detected"""
    pass

class RateLimitExceeded(SecurityError):
    """Rate limit exceeded"""
    pass

class CSRFAttack(SecurityError):
    """CSRF attack detected"""
    pass


class SecurityConfig:
    """Unified security configuration"""

    def __init__(self):
        # Core security features
        self.xss_protection = True
        self.sql_injection_protection = True
        self.csrf_protection = True
        self.rate_limiting = True
        self.dos_protection = True
        self.input_validation = True
        self.gzip_compression = True

        # HTTP Security Headers
        self.hsts_max_age = 31536000  # 1 year
        self.xss_protection_header = '1; mode=block'
        self.no_sniff = True
        self.frame_options = 'DENY'
        self.referrer_policy = 'strict-origin-when-cross-origin'

        # Content Security Policy
        self.csp_enabled = True
        self.csp_directives = {
            'default-src': "'self'",
            'script-src': "'self' 'unsafe-inline'",
            'style-src': "'self' 'unsafe-inline'",
            'img-src': "'self' data:",
            'font-src': "'self'",
            'connect-src': "'self'",
            'media-src': "'self'",
            'object-src': "'none'",
        }

        # CORS settings
        self.cors_allow_origins = ["*"]
        self.cors_allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.cors_allow_headers = ["*"]
        self.cors_allow_credentials = True
        self.cors_max_age = 600

        # Attack patterns
        self.xss_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'vbscript:',
            r'on\w+\s*=',
            r'<iframe[^>]*>.*?</iframe>',
            r'<object[^>]*>.*?</object>',
            r'<embed[^>]*>.*?</embed>',
        ]

        self.sql_patterns = [
            r';\s*(drop|delete|update|insert|alter|create|truncate)\s',
            r'union\s+select',
            r'--',
            r'/\*.*?\*/',
            r'xp_cmdshell',
            r'exec\s*\(',
        ]

        # Rate limiting
        self.rate_limit_requests = 100  # requests per window
        self.rate_limit_window = 60     # seconds
        self.dos_threshold = 1000       # requests per minute for DoS detection

        # CSRF settings
        self.csrf_secret_key = 'your-secret-key-here'
        self.csrf_token_length = 32
        self.csrf_cookie_name = 'csrf_token'
        self.csrf_header_name = 'X-CSRF-Token'
        self.csrf_form_field_name = 'csrf_token'
        self.csrf_secure_cookies = True
        self.csrf_token_expiry = timedelta(hours=24)

        # WebSocket security
        self.ws_require_auth = True
        self.ws_secret_key = 'your-ws-jwt-secret-key-here'
        self.ws_token_algorithms = ['HS256']
        self.ws_token_audience = 'websocket-auth'
        self.ws_token_issuer = 'your-app'
        self.ws_require_https = True
        self.ws_allowed_origins = []
        self.ws_channel_timeout = 300  # 5 minutes


class XSSProtector:
    """XSS attack prevention"""

    def __init__(self, config: SecurityConfig):
        self.config = config
        self.xss_regexes = [re.compile(pattern, re.IGNORECASE | re.DOTALL)
                           for pattern in config.xss_patterns]

    def sanitize_input(self, data: str) -> str:
        """Sanitize input to prevent XSS"""
        if not isinstance(data, str):
            return data

        # HTML escape
        data = html.escape(data, quote=True)

        # Check for XSS patterns
        for regex in self.xss_regexes:
            if regex.search(data):
                raise XSSAttack(f"XSS pattern detected: {regex.pattern}")

        return data

    def sanitize_html(self, html_content: str) -> str:
        """Sanitize HTML content"""
        # Remove dangerous tags and attributes
        dangerous_tags = ['script', 'iframe', 'object', 'embed', 'form', 'input']
        dangerous_attrs = ['on\w+', 'javascript:', 'vbscript:', 'data:']

        for tag in dangerous_tags:
            html_content = re.sub(rf'<{tag}[^>]*>.*?</{tag}>', '', html_content, flags=re.IGNORECASE | re.DOTALL)
            html_content = re.sub(rf'<{tag}[^>]*/>', '', html_content, flags=re.IGNORECASE)

        for attr in dangerous_attrs:
            html_content = re.sub(rf'\s{attr}[^>\s]*', '', html_content, flags=re.IGNORECASE)

        return html_content


class SQLInjectionProtector:
    """SQL injection prevention"""

    def __init__(self, config: SecurityConfig):
        self.config = config
        self.sql_regexes = [re.compile(pattern, re.IGNORECASE)
                           for pattern in config.sql_patterns]

    def check_query(self, query: str) -> None:
        """Check SQL query for injection patterns"""
        for regex in self.sql_regexes:
            if regex.search(query):
                raise SQLInjection(f"SQL injection pattern detected: {regex.pattern}")

    def sanitize_query(self, query: str) -> str:
        """Sanitize SQL query parameters"""
        return query.replace("'", "''").replace('"', '""')


class RateLimiter:
    """Rate limiting implementation"""

    def __init__(self, config: SecurityConfig):
        self.config = config
        self.requests = defaultdict(lambda: deque(maxlen=config.rate_limit_requests))
        self.lock = threading.RLock()

    def check_rate_limit(self, client_id: str) -> bool:
        """Check if client exceeds rate limit"""
        with self.lock:
            now = time.time()
            request_times = self.requests[client_id]

            # Remove old requests outside the window
            while request_times and now - request_times[0] > self.config.rate_limit_window:
                request_times.popleft()

            # Check if limit exceeded
            if len(request_times) >= self.config.rate_limit_requests:
                return False

            # Add current request
            request_times.append(now)
            return True

    def get_client_id(self, request) -> str:
        """Extract client identifier from request"""
        return getattr(request, 'client_ip', getattr(request, 'remote_addr', 'unknown'))


class DoSProtector:
    """DoS attack prevention"""

    def __init__(self, config: SecurityConfig):
        self.config = config
        self.request_counts = defaultdict(int)
        self.last_reset = time.time()
        self.lock = threading.RLock()

    def check_dos_attack(self, client_id: str) -> bool:
        """Check for DoS attack patterns"""
        with self.lock:
            now = time.time()

            # Reset counters every minute
            if now - self.last_reset > 60:
                self.request_counts.clear()
                self.last_reset = now

            self.request_counts[client_id] += 1

            # Check if client exceeds DoS threshold
            if self.request_counts[client_id] > self.config.dos_threshold:
                return True

            return False


class CSRFProtector:
    """CSRF attack prevention"""

    def __init__(self, config: SecurityConfig):
        self.config = config
        self._tokens: Dict[str, datetime] = {}
        self._lock = threading.RLock()

    def generate_token(self, session_id: str) -> str:
        """Generate CSRF token"""
        data = f"{session_id}:{time.time()}"
        return hashlib.sha256(data.encode()).hexdigest()

    def validate_token(self, token: str, session_id: str) -> bool:
        """Validate CSRF token"""
        expected = self.generate_token(session_id)
        return hmac.compare_digest(token, expected)

    def create_secure_token(self, session_id: str) -> str:
        """Create cryptographically secure CSRF token"""
        token = secrets.token_urlsafe(self.config.csrf_token_length)
        with self._lock:
            self._tokens[token] = datetime.now()
        return token

    def validate_secure_token(self, token: str) -> bool:
        """Validate secure CSRF token"""
        with self._lock:
            if token not in self._tokens:
                return False

            created = self._tokens[token]
            if datetime.now() - created > self.config.csrf_token_expiry:
                del self._tokens[token]
                return False

            return True


class InputValidator:
    """Input validation and sanitization"""

    def __init__(self, config: SecurityConfig):
        self.config = config

    def validate_email(self, email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    def validate_url(self, url: str) -> bool:
        """Validate URL format"""
        pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        return bool(re.match(pattern, url))

    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for security"""
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        filename = filename.replace('..', '')
        return filename[:255]


class GZipCompressor:
    """GZip response compression"""

    def __init__(self, config: SecurityConfig):
        self.config = config
        self.min_size = 1024

    def should_compress(self, content: bytes, accept_encoding: str) -> bool:
        """Check if response should be compressed"""
        if not self.config.gzip_compression:
            return False

        if 'gzip' not in accept_encoding:
            return False

        if len(content) < self.min_size:
            return False

        return True

    def compress(self, content: bytes) -> bytes:
        """Compress content using gzip"""
        return gzip.compress(content, compresslevel=6)


class CORSMiddleware:
    """CORS handling"""

    def __init__(self, config: SecurityConfig):
        self.config = config

    async def process_request(self, request) -> None:
        """Handle CORS preflight requests"""
        if request.method == 'OPTIONS':
            # Handle preflight request
            pass

    async def process_response(self, response) -> None:
        """Add CORS headers to response"""
        origin = getattr(response, '_request_origin', None)
        if origin and (origin in self.config.cors_allow_origins or "*" in self.config.cors_allow_origins):
            headers = getattr(response, 'headers', {})
            headers['Access-Control-Allow-Origin'] = origin
            headers['Access-Control-Allow-Methods'] = ', '.join(self.config.cors_allow_methods)
            headers['Access-Control-Allow-Headers'] = ', '.join(self.config.cors_allow_headers)
            headers['Access-Control-Allow-Credentials'] = str(self.config.cors_allow_credentials).lower()
            headers['Access-Control-Max-Age'] = str(self.config.cors_max_age)


class UnifiedSecurityMiddleware:
    """Unified security middleware combining all security features"""

    def __init__(self, config: Optional[SecurityConfig] = None):
        self.config = config or SecurityConfig()

        # Initialize all security components
        self.xss_protector = XSSProtector(self.config)
        self.sql_protector = SQLInjectionProtector(self.config)
        self.rate_limiter = RateLimiter(self.config)
        self.dos_protector = DoSProtector(self.config)
        self.csrf_protector = CSRFProtector(self.config)
        self.input_validator = InputValidator(self.config)
        self.gzip_compressor = GZipCompressor(self.config)
        self.cors_middleware = CORSMiddleware(self.config)

    async def process_request(self, request) -> None:
        """Process incoming request for security threats"""
        # Rate limiting
        if self.config.rate_limiting:
            client_id = self.rate_limiter.get_client_id(request)
            if not self.rate_limiter.check_rate_limit(client_id):
                raise RateLimitExceeded("Rate limit exceeded")

        # DoS protection
        if self.config.dos_protection:
            client_id = self.rate_limiter.get_client_id(request)
            if self.dos_protector.check_dos_attack(client_id):
                raise DoSAttack("DoS attack detected")

        # Input validation
        if self.config.input_validation:
            await self._validate_request_input(request)

        # XSS protection
        if self.config.xss_protection:
            await self._check_request_xss(request)

        # CORS handling
        await self.cors_middleware.process_request(request)

    async def process_response(self, response) -> None:
        """Process outgoing response"""
        # Add security headers
        self._add_security_headers(response)

        # CORS headers
        await self.cors_middleware.process_response(response)

        # Compression
        if hasattr(response, 'body') and hasattr(response, 'headers'):
            accept_encoding = getattr(response, '_accept_encoding', '')
            if self.gzip_compressor.should_compress(response.body, accept_encoding):
                compressed = self.gzip_compressor.compress(response.body)
                response.body = compressed
                response.headers['Content-Encoding'] = 'gzip'
                response.headers['Content-Length'] = str(len(compressed))

    def _add_security_headers(self, response) -> None:
        """Add security headers to response"""
        headers = getattr(response, 'headers', {})

        # HTTP Strict Transport Security
        if self.config.hsts_max_age:
            headers['Strict-Transport-Security'] = f'max-age={self.config.hsts_max_age}; includeSubDomains;'

        # XSS Protection
        if self.config.xss_protection_header:
            headers['X-XSS-Protection'] = self.config.xss_protection_header

        # Content Type Options
        if self.config.no_sniff:
            headers['X-Content-Type-Options'] = 'nosniff'

        # Frame Options
        if self.config.frame_options:
            headers['X-Frame-Options'] = self.config.frame_options

        # Referrer Policy
        if self.config.referrer_policy:
            headers['Referrer-Policy'] = self.config.referrer_policy

        # Content Security Policy
        if self.config.csp_enabled:
            csp_value = '; '.join(f"{k} {v}" for k, v in self.config.csp_directives.items())
            headers['Content-Security-Policy'] = csp_value

    async def _validate_request_input(self, request) -> None:
        """Validate request input data"""
        # Validate query parameters
        if hasattr(request, 'query_params'):
            for key, value in request.query_params.items():
                if isinstance(value, str):
                    if '..' in value or '<script' in value.lower():
                        raise SecurityError(f"Suspicious input in query parameter: {key}")

        # Validate form data
        if hasattr(request, 'form_data'):
            for key, value in request.form_data.items():
                if isinstance(value, str):
                    if len(value) > 10000:
                        raise SecurityError(f"Input too large for field: {key}")

    async def _check_request_xss(self, request) -> None:
        """Check request data for XSS attacks"""
        # Check query parameters
        if hasattr(request, 'query_params'):
            for key, value in request.query_params.items():
                if isinstance(value, str):
                    try:
                        self.xss_protector.sanitize_input(value)
                    except XSSAttack:
                        raise

        # Check form data
        if hasattr(request, 'form_data'):
            for key, value in request.form_data.items():
                if isinstance(value, str):
                    try:
                        self.xss_protector.sanitize_input(value)
                    except XSSAttack:
                        raise

    # Public API methods
    def sanitize_template_output(self, content: str) -> str:
        """Sanitize template output for XSS prevention"""
        if self.config.xss_protection:
            return self.xss_protector.sanitize_html(content)
        return content

    def validate_sql_query(self, query: str) -> None:
        """Validate SQL query for injection attacks"""
        if self.config.sql_injection_protection:
            self.sql_protector.check_query(query)

    def generate_csrf_token(self, session_id: str) -> str:
        """Generate CSRF token"""
        return self.csrf_protector.generate_token(session_id)

    def validate_csrf_token(self, token: str, session_id: str) -> bool:
        """Validate CSRF token"""
        return self.csrf_protector.validate_token(token, session_id)

    def create_secure_csrf_token(self, session_id: str) -> str:
        """Create cryptographically secure CSRF token"""
        return self.csrf_protector.create_secure_token(session_id)

    def validate_secure_csrf_token(self, token: str) -> bool:
        """Validate secure CSRF token"""
        return self.csrf_protector.validate_secure_token(token)


# Global security middleware instance
_security_middleware: Optional[UnifiedSecurityMiddleware] = None

def get_security_middleware(config: Optional[SecurityConfig] = None) -> UnifiedSecurityMiddleware:
    """Get global security middleware instance"""
    global _security_middleware
    if _security_middleware is None:
        _security_middleware = UnifiedSecurityMiddleware(config)
    return _security_middleware

def init_security(config: Optional[SecurityConfig] = None) -> UnifiedSecurityMiddleware:
    """Initialize security system"""
    return get_security_middleware(config)

# Quantum Security Integration
try:
    from pyserv.security.quantum_security import (
        get_quantum_security_manager,
        QuantumAlgorithm,
        quantum_authenticate,
        establish_secure_channel
    )

    class QuantumSecurityProtector:
        """Quantum-resistant security features"""

        def __init__(self, config: SecurityConfig):
            self.config = config
            self.quantum_manager = get_quantum_security_manager()

        async def validate_quantum_authentication(self, request) -> None:
            """Validate quantum-resistant authentication"""
            quantum_token = request.headers.get('X-Quantum-Auth')
            if not quantum_token:
                raise SecurityError("Quantum authentication required")

            identity = self._extract_identity(request)
            try:
                auth_result = await quantum_authenticate(identity)
                request.state.quantum_auth = auth_result
                request.state.quantum_authenticated = True
            except Exception as e:
                raise SecurityError(f"Quantum authentication failed: {str(e)}")

        async def ensure_secure_channel(self, request) -> None:
            """Ensure a quantum-secure channel is established"""
            channel_id = request.headers.get('X-Secure-Channel')

            if channel_id:
                request.state.quantum_channel = {'channel_id': channel_id, 'valid': True}
            else:
                try:
                    channel_info = await establish_secure_channel()
                    request.state.quantum_channel = channel_info
                except Exception as e:
                    # Log but don't fail - allow fallback to classical crypto
                    print(f"Failed to establish quantum channel: {e}")

        def _extract_identity(self, request) -> str:
            """Extract user identity from request"""
            return (
                getattr(request.state, 'user_id', None) or
                request.headers.get('X-User-ID') or
                request.query_params.get('user_id', [''])[0] or
                'anonymous'
            )

    # Add quantum features to UnifiedSecurityMiddleware
    _quantum_protector = None

    def _get_quantum_protector(self):
        global _quantum_protector
        if _quantum_protector is None:
            _quantum_protector = QuantumSecurityProtector(self.config)
        return _quantum_protector

    async def validate_quantum_auth(self, request) -> None:
        """Validate quantum authentication"""
        protector = self._get_quantum_protector()
        await protector.validate_quantum_authentication(request)

    async def ensure_quantum_channel(self, request) -> None:
        """Ensure quantum secure channel"""
        protector = self._get_quantum_protector()
        await protector.ensure_secure_channel(request)

    # Extend process_request to include quantum features
    original_process_request = UnifiedSecurityMiddleware.process_request

    async def enhanced_process_request(self, request) -> None:
        await original_process_request(self, request)

        # Add quantum security if enabled
        if hasattr(self.config, 'quantum_auth_enabled') and self.config.quantum_auth_enabled:
            await self.validate_quantum_auth(request)

        if hasattr(self.config, 'quantum_channel_enabled') and self.config.quantum_channel_enabled:
            await self.ensure_quantum_channel(request)

    UnifiedSecurityMiddleware.process_request = enhanced_process_request

    # Extend process_response to include quantum headers
    original_process_response = UnifiedSecurityMiddleware.process_response

    async def enhanced_process_response(self, response) -> None:
        await original_process_response(self, response)

        # Add quantum security headers
        headers = getattr(response, 'headers', {})
        headers['X-Quantum-Security'] = 'enabled'
        headers['X-Supported-Algorithms'] = ','.join(
            [alg.value for alg in get_quantum_security_manager().providers.keys()]
        )

        if hasattr(response, '_request') and hasattr(response._request.state, 'quantum_channel'):
            channel = response._request.state.quantum_channel
            if isinstance(channel, dict):
                headers['X-Secure-Channel-ID'] = channel.get('channel_id', '')

    UnifiedSecurityMiddleware.process_response = enhanced_process_response

except ImportError:
    # Quantum security not available
    pass

# Backward compatibility aliases
SecurityMiddleware = UnifiedSecurityMiddleware





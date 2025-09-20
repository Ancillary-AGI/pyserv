"""
PyDance HTTP Request Handler - ASGI-compliant request processing with advanced features.

This module provides comprehensive HTTP request handling with support for:
- ASGI scope and lifecycle management
- Header parsing and normalization
- Query parameter extraction
- Request body processing (JSON, form data, streaming)
- Path parameter handling
- Request state management
- Content type detection
- Security features (XSS protection, etc.)
"""

import json
import asyncio
from typing import Dict, List, Any, AsyncGenerator, Optional, Union, TYPE_CHECKING
from urllib.parse import parse_qs, unquote
from email.utils import parsedate_to_datetime
from datetime import datetime

if TYPE_CHECKING:
    from ..server.application import Application

from ..exceptions import BadRequest, UnsupportedMediaType
from ..i18n import _


class Request:
    """
    Enhanced HTTP Request class with comprehensive ASGI support.

    Features:
    - ASGI scope and lifecycle management
    - Automatic header parsing and normalization
    - Query parameter extraction with type conversion
    - Request body processing (JSON, form data, raw bytes, streaming)
    - Path parameter handling
    - Request state management for middleware
    - Content type detection and validation
    - Security features and validation
    """

    def __init__(self, scope: Dict[str, Any], receive: callable, send: callable, app: "Application"):
        self.scope = scope
        self.receive = receive
        self.send = send
        self.app = app

        # Core request attributes
        self.method = scope["method"]
        self.path = unquote(scope["path"])
        self.raw_path = scope["path"]
        self.query_string = scope.get("query_string", b"").decode()

        # Parsed data
        self.headers = self._parse_headers(scope.get("headers", []))
        self.query_params = self._parse_query_params()
        self.path_params: Dict[str, Any] = {}
        self.state: Dict[str, Any] = {}

        # Body handling
        self._body: Optional[bytes] = None
        self._json_cache: Optional[Any] = None
        self._form_cache: Optional[Dict[str, Any]] = None

        # Request metadata
        self.content_type = self.headers.get("content-type", "").lower()
        self.content_length = self._parse_content_length()
        self.user_agent = self.headers.get("user-agent", "")
        self.accept = self.headers.get("accept", "")
        self.accept_language = self.headers.get("accept-language", "")

        # Security and validation
        self.is_secure = scope.get("scheme") == "https"
        self.host = self._get_host()
        self.remote_addr = self._get_remote_addr()

    def _parse_headers(self, headers: List[List[bytes]]) -> Dict[str, str]:
        """Parse and normalize HTTP headers."""
        parsed = {}
        for key_bytes, value_bytes in headers:
            key = key_bytes.decode().lower()
            value = value_bytes.decode()
            # Handle multiple headers with same name
            if key in parsed:
                if isinstance(parsed[key], list):
                    parsed[key].append(value)
                else:
                    parsed[key] = [parsed[key], value]
            else:
                parsed[key] = value
        return parsed

    def _parse_query_params(self) -> Dict[str, List[str]]:
        """Parse query parameters from URL."""
        if not self.query_string:
            return {}
        return parse_qs(self.query_string, keep_blank_values=True)

    def _parse_content_length(self) -> Optional[int]:
        """Parse Content-Length header."""
        content_length = self.headers.get("content-length")
        if content_length:
            try:
                return int(content_length)
            except ValueError:
                pass
        return None

    def _get_host(self) -> str:
        """Get the request host."""
        host = self.headers.get("host", "")
        if not host:
            server = self.scope.get("server")
            if server:
                host = f"{server[0]}:{server[1]}"
        return host

    def _get_remote_addr(self) -> str:
        """Get the remote client address."""
        # Check X-Forwarded-For header first (for proxies)
        x_forwarded_for = self.headers.get("x-forwarded-for")
        if x_forwarded_for:
            # Take the first (original client) IP
            return x_forwarded_for.split(",")[0].strip()

        # Fall back to direct client
        client = self.scope.get("client")
        if client:
            return client[0]
        return "unknown"

    async def body(self) -> bytes:
        """
        Get the raw request body.

        Returns:
            The complete request body as bytes
        """
        if self._body is None:
            self._body = b""
            more_body = True

            while more_body:
                try:
                    message = await self.receive()
                    body_chunk = message.get("body", b"")
                    self._body += body_chunk
                    more_body = message.get("more_body", False)

                    # Prevent excessive memory usage
                    if len(self._body) > 100 * 1024 * 1024:  # 100MB limit
                        raise BadRequest(_("request_entity_too_large"))

                except asyncio.TimeoutError:
                    raise BadRequest(_("request_timeout"))

        return self._body

    async def json(self) -> Any:
        """
        Parse request body as JSON.

        Returns:
            Parsed JSON data

        Raises:
            BadRequest: If JSON parsing fails
        """
        if self._json_cache is not None:
            return self._json_cache

        if not self._is_json_content_type():
            raise UnsupportedMediaType(_("content_type_not_json"))

        body = await self.body()
        if not body:
            raise BadRequest(_("empty_request_body"))

        try:
            self._json_cache = json.loads(body.decode())
            return self._json_cache
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise BadRequest(_("invalid_json_format", error=str(e)))

    async def form(self) -> Dict[str, Any]:
        """
        Parse request body as form data.

        Returns:
            Dictionary of form field names to values
        """
        if self._form_cache is not None:
            return self._form_cache

        if not self._is_form_content_type():
            raise UnsupportedMediaType(_("content_type_not_form"))

        body = await self.body()
        if not body:
            return {}

        try:
            parsed = parse_qs(body.decode(), keep_blank_values=True)
            # Convert single values to strings, multiple values to lists
            self._form_cache = {
                key: value[0] if len(value) == 1 else value
                for key, value in parsed.items()
            }
            return self._form_cache
        except Exception as e:
            raise BadRequest(_("invalid_form_data", error=str(e)))

    async def stream(self) -> AsyncGenerator[bytes, None]:
        """
        Stream the request body as an async generator.

        Yields:
            Chunks of the request body as bytes
        """
        more_body = True
        while more_body:
            try:
                message = await self.receive()
                chunk = message.get("body", b"")
                if chunk:  # Only yield non-empty chunks
                    yield chunk
                more_body = message.get("more_body", False)
            except asyncio.TimeoutError:
                raise BadRequest(_("request_timeout"))

    def _is_json_content_type(self) -> bool:
        """Check if content type is JSON."""
        return "application/json" in self.content_type or self.content_type.endswith("+json")

    def _is_form_content_type(self) -> bool:
        """Check if content type is form data."""
        return (
            "application/x-www-form-urlencoded" in self.content_type or
            "multipart/form-data" in self.content_type
        )

    def get_header(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """Get a header value by name (case-insensitive)."""
        return self.headers.get(name.lower(), default)

    def get_query_param(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """Get a query parameter value."""
        values = self.query_params.get(name)
        if values:
            return values[0] if len(values) == 1 else values
        return default

    def get_path_param(self, name: str, default: Optional[Any] = None) -> Optional[Any]:
        """Get a path parameter value."""
        return self.path_params.get(name, default)

    def is_method(self, method: str) -> bool:
        """Check if request method matches."""
        return self.method.upper() == method.upper()

    def accepts(self, content_type: str) -> bool:
        """Check if client accepts the given content type."""
        return content_type in self.accept

    def accepts_language(self, language: str) -> bool:
        """Check if client accepts the given language."""
        return language in self.accept_language

    @property
    def url(self) -> str:
        """Get the full request URL."""
        scheme = self.scope.get("scheme", "http")
        return f"{scheme}://{self.host}{self.path}"

    @property
    def base_url(self) -> str:
        """Get the base URL (without path and query)."""
        scheme = self.scope.get("scheme", "http")
        return f"{scheme}://{self.host}"

    @property
    def cookies(self) -> Dict[str, str]:
        """Get parsed cookies."""
        cookie_header = self.headers.get("cookie", "")
        if not cookie_header:
            return {}

        cookies = {}
        for item in cookie_header.split(";"):
            if "=" in item:
                name, value = item.strip().split("=", 1)
                cookies[name] = value
        return cookies

    @property
    def if_modified_since(self) -> Optional[datetime]:
        """Get If-Modified-Since header as datetime."""
        header = self.headers.get("if-modified-since")
        if header:
            try:
                return parsedate_to_datetime(header)
            except (ValueError, TypeError):
                pass
        return None

    @property
    
    def if_none_match(self) -> Optional[str]:
        """Get If-None-Match header."""
        return self.headers.get("if-none-match")

    def __repr__(self) -> str:
        return f"<Request {self.method} {self.path}>"

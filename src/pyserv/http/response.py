"""
Pyserv  HTTP Response Handler - ASGI-compliant response processing with advanced features.

This module provides comprehensive HTTP response handling with support for:
- ASGI response lifecycle management
- Content type detection and validation
- Response streaming and chunking
- Background task execution
- HTTP status code management
- Header manipulation and validation
- Content encoding and compression
- Caching headers and ETags
"""

import asyncio
import inspect
import json
import hashlib
import gzip
import zlib
from typing import Any, Dict, List, Callable, Optional, Union, AsyncGenerator
from datetime import datetime, timedelta
from email.utils import format_datetime


class Response:
    """
    Enhanced HTTP Response class with comprehensive ASGI support.

    Features:
    - ASGI response lifecycle management
    - Automatic content type detection
    - Response streaming and chunking
    - Background task execution
    - HTTP status code management
    - Header manipulation and validation
    - Content encoding and compression
    - Caching headers and ETags
    - Security headers
    """

    # Common HTTP status codes
    STATUS_CODES = {
        100: "Continue",
        101: "Switching Protocols",
        102: "Processing",
        200: "OK",
        201: "Created",
        202: "Accepted",
        203: "Non-Authoritative Information",
        204: "No Content",
        205: "Reset Content",
        206: "Partial Content",
        207: "Multi-Status",
        208: "Already Reported",
        226: "IM Used",
        300: "Multiple Choices",
        301: "Moved Permanently",
        302: "Found",
        303: "See Other",
        304: "Not Modified",
        305: "Use Proxy",
        307: "Temporary Redirect",
        308: "Permanent Redirect",
        400: "Bad Request",
        401: "Unauthorized",
        402: "Payment Required",
        403: "Forbidden",
        404: "Not Found",
        405: "Method Not Allowed",
        406: "Not Acceptable",
        407: "Proxy Authentication Required",
        408: "Request Timeout",
        409: "Conflict",
        410: "Gone",
        411: "Length Required",
        412: "Precondition Failed",
        413: "Payload Too Large",
        414: "URI Too Long",
        415: "Unsupported Media Type",
        416: "Range Not Satisfiable",
        417: "Expectation Failed",
        418: "I'm a teapot",
        421: "Misdirected Request",
        422: "Unprocessable Entity",
        423: "Locked",
        424: "Failed Dependency",
        425: "Too Early",
        426: "Upgrade Required",
        428: "Precondition Required",
        429: "Too Many Requests",
        431: "Request Header Fields Too Large",
        451: "Unavailable For Legal Reasons",
        500: "Internal Server Error",
        501: "Not Implemented",
        502: "Bad Gateway",
        503: "Service Unavailable",
        504: "Gateway Timeout",
        505: "HTTP Version Not Supported",
        506: "Variant Also Negotiates",
        507: "Insufficient Storage",
        508: "Loop Detected",
        510: "Not Extended",
        511: "Network Authentication Required",
    }

    def __init__(
        self,
        content: Any = None,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        media_type: Optional[str] = None,
        charset: str = "utf-8",
        background_tasks: Optional[List[Callable]] = None,
        compression: Optional[str] = None
    ):
        self.status_code = status_code
        self.headers = headers or {}
        self.background_tasks = background_tasks or []
        self.content = content
        self.charset = charset
        self.compression = compression

        # Streaming support
        self._streaming = asyncio.Queue() if content is None else None
        self._stream_ended = False

        # Content type detection
        self.media_type = self._detect_media_type(content, media_type)

        # Content processing
        self._processed_content: Optional[bytes] = None
        self._etag: Optional[str] = None

        # Set default headers
        self._set_default_headers()

    def _detect_media_type(self, content: Any, media_type: Optional[str]) -> str:
        """Detect the appropriate media type for the content."""
        if media_type:
            return media_type

        if isinstance(content, (dict, list)):
            return "application/json"
        elif isinstance(content, str):
            # Check if it's HTML
            if content.strip().startswith("<") and ("<html" in content.lower() or "<!doctype" in content.lower()):
                return "text/html"
            else:
                return "text/plain"
        elif isinstance(content, bytes):
            return "application/octet-stream"
        else:
            return "text/plain"

    def _set_default_headers(self) -> None:
        """Set default response headers."""
        # Content-Type header
        if "content-type" not in self.headers:
            content_type = self.media_type
            if self.charset and "charset" not in content_type:
                content_type += f"; charset={self.charset}"
            self.headers["content-type"] = content_type

        # Server header
        if "server" not in self.headers:
            self.headers["server"] = "Pyserv "

        # Date header
        if "date" not in self.headers:
            self.headers["date"] = format_datetime(datetime.utcnow())

        # Security headers
        if "x-content-type-options" not in self.headers:
            self.headers["x-content-type-options"] = "nosniff"

    def set_header(self, name: str, value: str) -> None:
        """Set a response header."""
        self.headers[name.lower()] = value

    def get_header(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """Get a response header."""
        return self.headers.get(name.lower(), default)

    def delete_header(self, name: str) -> None:
        """Delete a response header."""
        self.headers.pop(name.lower(), None)

    def set_cookie(
        self,
        name: str,
        value: str,
        max_age: Optional[int] = None,
        expires: Optional[datetime] = None,
        path: str = "/",
        domain: Optional[str] = None,
        secure: bool = False,
        httponly: bool = False,
        samesite: Optional[str] = None
    ) -> None:
        """Set a response cookie."""
        cookie_parts = [f"{name}={value}"]

        if max_age is not None:
            cookie_parts.append(f"Max-Age={max_age}")
        if expires is not None:
            cookie_parts.append(f"Expires={format_datetime(expires)}")
        if path:
            cookie_parts.append(f"Path={path}")
        if domain:
            cookie_parts.append(f"Domain={domain}")
        if secure:
            cookie_parts.append("Secure")
        if httponly:
            cookie_parts.append("HttpOnly")
        if samesite:
            cookie_parts.append(f"SameSite={samesite}")

        cookie_value = "; ".join(cookie_parts)
        self.set_header("set-cookie", cookie_value)

    def delete_cookie(self, name: str, path: str = "/", domain: Optional[str] = None) -> None:
        """Delete a response cookie."""
        cookie_parts = [f"{name}=; Max-Age=0"]

        if path:
            cookie_parts.append(f"Path={path}")
        if domain:
            cookie_parts.append(f"Domain={domain}")

        cookie_value = "; ".join(cookie_parts)
        self.set_header("set-cookie", cookie_value)

    def set_cache_control(self, directive: str, max_age: Optional[int] = None) -> None:
        """Set Cache-Control header."""
        cache_control = directive
        if max_age is not None:
            cache_control += f", max-age={max_age}"
        self.set_header("cache-control", cache_control)

    def set_etag(self, etag: Optional[str] = None) -> None:
        """Set ETag header."""
        if etag is None:
            if self._etag is None:
                content = self._get_content_bytes()
                self._etag = f'"{hashlib.md5(content).hexdigest()}"'
            etag = self._etag
        self.set_header("etag", etag)

    def set_last_modified(self, dt: datetime) -> None:
        """Set Last-Modified header."""
        self.set_header("last-modified", format_datetime(dt))

    def set_expires(self, dt: datetime) -> None:
        """Set Expires header."""
        self.set_header("expires", format_datetime(dt))

    def enable_cors(
        self,
        allow_origins: Union[str, List[str]] = "*",
        allow_methods: Union[str, List[str]] = "*",
        allow_headers: Union[str, List[str]] = "*",
        allow_credentials: bool = False,
        max_age: int = 86400
    ) -> None:
        """Enable CORS for the response."""
        if isinstance(allow_origins, list):
            allow_origins = ", ".join(allow_origins)
        if isinstance(allow_methods, list):
            allow_methods = ", ".join(allow_methods)
        if isinstance(allow_headers, list):
            allow_headers = ", ".join(allow_headers)

        self.set_header("access-control-allow-origin", str(allow_origins))
        self.set_header("access-control-allow-methods", str(allow_methods))
        self.set_header("access-control-allow-headers", str(allow_headers))
        if allow_credentials:
            self.set_header("access-control-allow-credentials", "true")
        self.set_header("access-control-max-age", str(max_age))

    async def stream_data(self, data: bytes) -> None:
        """Stream data to the response."""
        if self._streaming is None:
            raise ValueError("Response is not configured for streaming")
        if self._stream_ended:
            raise ValueError("Stream has already ended")

        await self._streaming.put(data)

    async def end_stream(self) -> None:
        """End the response stream."""
        if self._streaming is not None and not self._stream_ended:
            await self._streaming.put(None)
            self._stream_ended = True

    async def stream_generator(self, generator: AsyncGenerator[bytes, None]) -> None:
        """Stream data from an async generator."""
        if self._streaming is None:
            raise ValueError("Response is not configured for streaming")

        try:
            async for chunk in generator:
                await self.stream_data(chunk)
        finally:
            await self.end_stream()

    def _get_content_bytes(self) -> bytes:
        """Get the response content as bytes."""
        if self._processed_content is not None:
            return self._processed_content

        if self.content is None:
            return b""

        if isinstance(self.content, bytes):
            content = self.content
        elif isinstance(self.content, str):
            content = self.content.encode(self.charset)
        elif isinstance(self.content, (dict, list)):
            content = json.dumps(self.content, ensure_ascii=False).encode(self.charset)
        else:
            content = str(self.content).encode(self.charset)

        # Apply compression if requested
        if self.compression:
            content = self._compress_content(content)

        self._processed_content = content
        return content

    def _compress_content(self, content: bytes) -> bytes:
        """Compress response content."""
        if self.compression == "gzip":
            return gzip.compress(content)
        elif self.compression == "deflate":
            return zlib.compress(content)
        else:
            return content

    async def __call__(self, scope: Dict[str, Any], receive: callable, send: callable) -> None:
        """ASGI response callable."""
        # Prepare headers
        headers = [
            [key.encode(), value.encode()]
            for key, value in self.headers.items()
        ]

        # Add content-length if we have content
        if self.content is not None and "content-length" not in self.headers:
            content_bytes = self._get_content_bytes()
            headers.append([b"content-length", str(len(content_bytes)).encode()])

        # Send response start
        await send({
            "type": "http.response.start",
            "status": self.status_code,
            "headers": headers,
        })

        # Handle streaming response
        if self._streaming is not None:
            while True:
                try:
                    data = await asyncio.wait_for(self._streaming.get(), timeout=30.0)
                    if data is None:
                        break
                    await send({
                        "type": "http.response.body",
                        "body": data,
                        "more_body": True,
                    })
                except asyncio.TimeoutError:
                    # End stream on timeout
                    break

            await send({
                "type": "http.response.body",
                "body": b"",
                "more_body": False,
            })

        # Handle regular response
        elif self.content is not None:
            content_bytes = self._get_content_bytes()
            await send({
                "type": "http.response.body",
                "body": content_bytes,
                "more_body": False,
            })

        # Execute background tasks
        for task in self.background_tasks:
            if inspect.iscoroutinefunction(task):
                asyncio.create_task(task())
            else:
                # Run sync tasks in thread pool
                loop = asyncio.get_event_loop()
                loop.run_in_executor(None, task)

    @classmethod
    def json(
        cls,
        content: Any,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> 'Response':
        """Create a JSON response."""
        return cls(
            content=content,
            status_code=status_code,
            headers=headers,
            media_type="application/json",
            **kwargs
        )

    @classmethod
    def html(
        cls,
        content: str,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> 'Response':
        """Create an HTML response."""
        return cls(
            content=content,
            status_code=status_code,
            headers=headers,
            media_type="text/html",
            **kwargs
        )

    @classmethod
    def text(
        cls,
        content: str,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> 'Response':
        """Create a plain text response."""
        return cls(
            content=content,
            status_code=status_code,
            headers=headers,
            media_type="text/plain",
            **kwargs
        )

    @classmethod
    def redirect(
        cls,
        url: str,
        status_code: int = 302,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> 'Response':
        """Create a redirect response."""
        headers = headers or {}
        headers["location"] = url
        return cls(
            content="",
            status_code=status_code,
            headers=headers,
            **kwargs
        )

    @classmethod
    def file(
        cls,
        path: str,
        filename: Optional[str] = None,
        media_type: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> 'Response':
        """Create a file response."""
        import os
        import mimetypes

        if not os.path.exists(path):
            return cls(status_code=404, content="File not found")

        if filename is None:
            filename = os.path.basename(path)

        if media_type is None:
            media_type, _ = mimetypes.guess_type(filename)

        headers = headers or {}
        headers["content-disposition"] = f'attachment; filename="{filename}"'

        with open(path, 'rb') as f:
            content = f.read()

        return cls(
            content=content,
            headers=headers,
            media_type=media_type or "application/octet-stream",
            **kwargs
        )

    def __repr__(self) -> str:
        return f"<Response {self.status_code} {self.STATUS_CODES.get(self.status_code, 'Unknown')}>"


# Convenience functions for common responses
def JSONResponse(content: Any, status_code: int = 200, **kwargs) -> Response:
    """Create a JSON response (legacy compatibility)."""
    return Response.json(content, status_code, **kwargs)

def HTMLResponse(content: str, status_code: int = 200, **kwargs) -> Response:
    """Create an HTML response (legacy compatibility)."""
    return Response.html(content, status_code, **kwargs)

def PlainTextResponse(content: str, status_code: int = 200, **kwargs) -> Response:
    """Create a plain text response (legacy compatibility)."""
    return Response.text(content, status_code, **kwargs)

def RedirectResponse(url: str, status_code: int = 302, **kwargs) -> Response:
    """Create a redirect response (legacy compatibility)."""
    return Response.redirect(url, status_code, **kwargs)

def FileResponse(path: str, **kwargs) -> Response:
    """Create a file response (legacy compatibility)."""
    return Response.file(path, **kwargs)





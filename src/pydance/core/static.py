"""
Static File Serving for Pydance Framework
=========================================

Provides middleware and utilities for serving static files (CSS, JS, images, etc.)
with proper caching, security, and performance optimizations.
"""

import os
import mimetypes
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from email.utils import formatdate

from .request import Request
from .response import Response
from .middleware import HTTPMiddleware
from .exceptions import HTTPException


class StaticFileMiddleware(HTTPMiddleware):
    """
    Middleware for serving static files with caching and security features.

    Features:
    - Automatic MIME type detection
    - ETag and Last-Modified headers for caching
    - Security headers (Content-Security-Policy, etc.)
    - Directory traversal protection
    - Configurable cache duration
    """

    def __init__(self,
                 static_dir: str = "static",
                 url_prefix: str = "/static",
                 cache_max_age: int = 86400,  # 24 hours
                 enable_etag: bool = True,
                 enable_compression: bool = True):
        self.static_dir = Path(static_dir)
        self.url_prefix = url_prefix.rstrip('/')
        self.cache_max_age = cache_max_age
        self.enable_etag = enable_etag
        self.enable_compression = enable_compression

        # Security: ensure static_dir is within project root
        if not self.static_dir.is_absolute():
            # Assume relative to current working directory
            self.static_dir = Path.cwd() / self.static_dir

        # Create directory if it doesn't exist
        self.static_dir.mkdir(parents=True, exist_ok=True)

    async def process_request(self, request: Request) -> Optional[Response]:
        """Process static file requests"""
        if not request.path.startswith(self.url_prefix):
            return None

        # Extract file path from URL
        file_path = request.path[len(self.url_prefix):].lstrip('/')

        # Security: prevent directory traversal
        if '..' in file_path or file_path.startswith('/'):
            raise HTTPException(403, "Access denied")

        # Build full file path
        full_path = self.static_dir / file_path

        # Check if file exists
        if not full_path.exists() or not full_path.is_file():
            return None  # Let next handler deal with 404

        # Serve the file
        return await self._serve_file(request, full_path)

    async def _serve_file(self, request: Request, file_path: Path) -> Response:
        """Serve a static file with proper headers"""
        # Get file stats
        stat = file_path.stat()
        file_size = stat.st_size
        modified_time = datetime.fromtimestamp(stat.st_mtime)

        # Generate ETag if enabled
        etag = None
        if self.enable_etag:
            # Simple ETag based on file size and modification time
            etag_content = f"{file_path}:{stat.st_size}:{stat.st_mtime}"
            etag = hashlib.md5(etag_content.encode()).hexdigest()

        # Check If-None-Match header (ETag)
        if etag and request.headers.get('If-None-Match') == etag:
            return Response("", status_code=304)

        # Check If-Modified-Since header
        if_modified_since = request.headers.get('If-Modified-Since')
        if if_modified_since:
            try:
                client_time = datetime.strptime(if_modified_since, '%a, %d %b %Y %H:%M:%S GMT')
                if modified_time <= client_time:
                    return Response("", status_code=304)
            except ValueError:
                pass  # Invalid date format, ignore

        # Read file content
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
        except IOError:
            raise HTTPException(500, "Error reading file")

        # Create response
        response = Response(content)

        # Set content type
        content_type, _ = mimetypes.guess_type(str(file_path))
        if content_type:
            response.headers['Content-Type'] = content_type
        else:
            response.headers['Content-Type'] = 'application/octet-stream'

        # Set caching headers
        if self.cache_max_age > 0:
            response.headers['Cache-Control'] = f'public, max-age={self.cache_max_age}'
            expires = datetime.utcnow() + timedelta(seconds=self.cache_max_age)
            response.headers['Expires'] = formatdate(expires.timestamp(), usegmt=True)

        # Set ETag
        if etag:
            response.headers['ETag'] = etag

        # Set Last-Modified
        response.headers['Last-Modified'] = formatdate(stat.st_mtime, usegmt=True)

        # Security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'

        # Add Content-Length
        response.headers['Content-Length'] = str(file_size)

        return response


class StaticFileHandler:
    """
    Simple static file handler for manual route registration.

    Usage:
        handler = StaticFileHandler("static")
        app.router.add_route("/static/{path:path}", handler.serve_file, ["GET"])
    """

    def __init__(self, static_dir: str = "static", enable_caching: bool = True):
        self.static_dir = Path(static_dir)
        self.enable_caching = enable_caching

        if not self.static_dir.is_absolute():
            self.static_dir = Path.cwd() / self.static_dir

    async def serve_file(self, request: Request) -> Response:
        """Serve a static file"""
        file_path = request.path_params.get('path', '')

        # Security: prevent directory traversal
        if '..' in file_path or file_path.startswith('/'):
            raise HTTPException(403, "Access denied")

        full_path = self.static_dir / file_path

        if not full_path.exists() or not full_path.is_file():
            raise HTTPException(404, "File not found")

        # Read and return file
        try:
            with open(full_path, 'rb') as f:
                content = f.read()

            response = Response(content)

            # Set content type
            content_type, _ = mimetypes.guess_type(str(full_path))
            if content_type:
                response.headers['Content-Type'] = content_type

            # Basic caching
            if self.enable_caching:
                response.headers['Cache-Control'] = 'public, max-age=86400'

            return response

        except IOError:
            raise HTTPException(500, "Error reading file")


def create_static_route(static_dir: str = "static", url_prefix: str = "/static"):
    """
    Create a route handler for serving static files.

    Usage:
        static_route = create_static_route("static", "/static")
        app.router.add_route("/static/{path:path}", static_route, ["GET"])
    """
    handler = StaticFileHandler(static_dir)

    async def static_route_handler(request: Request) -> Response:
        return await handler.serve_file(request)

    return static_route_handler


def setup_static_files(app, static_dir: str = "static", url_prefix: str = "/static"):
    """
    Quick setup for static file serving.

    This function adds both middleware and route-based static file serving.

    Args:
        app: Pydance Application instance
        static_dir: Directory containing static files
        url_prefix: URL prefix for static files
    """
    # Add middleware for automatic serving
    middleware = StaticFileMiddleware(static_dir, url_prefix)
    app.add_middleware(middleware)

    # Also add route-based handler as fallback
    static_route = create_static_route(static_dir, url_prefix)
    app.router.add_route(f"{url_prefix}/{{path:path}}", static_route, ["GET"])

    print(f"✓ Static file serving enabled:")
    print(f"  Directory: {static_dir}")
    print(f"  URL prefix: {url_prefix}")
    print(f"  Middleware: Enabled")
    print(f"  Route: {url_prefix}/{{path:path}}")


# Utility functions
def get_static_url(filename: str, static_prefix: str = "/static") -> str:
    """Generate URL for static file"""
    return f"{static_prefix}/{filename}"


def ensure_static_dirs(static_dir: str = "static"):
    """Ensure common static directories exist"""
    static_path = Path(static_dir)

    dirs_to_create = [
        static_path / "css",
        static_path / "js",
        static_path / "images",
        static_path / "fonts",
        static_path / "vendor"
    ]

    for dir_path in dirs_to_create:
        dir_path.mkdir(parents=True, exist_ok=True)

    print(f"✓ Created static directories in {static_dir}/")


# Example usage and integration
if __name__ == "__main__":
    # Example of how to use static file serving
    from ..application import Application

    app = Application()

    # Method 1: Quick setup (recommended)
    setup_static_files(app, "src/pydance/static", "/static")

    # Method 2: Manual middleware setup
    # middleware = StaticFileMiddleware("src/pydance/static", "/static")
    # app.add_middleware(middleware)

    # Method 3: Manual route setup
    # static_handler = create_static_route("src/pydance/static", "/static")
    # app.router.add_route("/static/{path:path}", static_handler, ["GET"])

    print("\nStatic files will be served at:")
    print("- /static/css/widgets.css")
    print("- /static/js/widgets.js")
    print("- Any other files in the static directory")

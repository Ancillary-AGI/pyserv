"""
Logging middleware for request/response logging.
"""

from typing import Optional
from datetime import datetime

from ...core.request import Request
from ...core.response import Response
from ...core.middleware import HTTPMiddleware
from .logger import get_logger


class LoggingMiddleware(HTTPMiddleware):
    """Middleware for logging HTTP requests and responses"""

    def __init__(self,
                 logger_name: str = 'http',
                 log_requests: bool = True,
                 log_responses: bool = True,
                 log_errors: bool = True,
                 exclude_paths: Optional[list] = None):
        self.logger_name = logger_name
        self.log_requests = log_requests
        self.log_responses = log_responses
        self.log_errors = log_errors
        self.exclude_paths = exclude_paths or ['/health', '/favicon.ico']
        self.logger = get_logger(logger_name)

    async def process_request(self, request: Request) -> Request:
        """Log incoming requests"""
        if not self.log_requests:
            return request

        # Skip excluded paths
        if request.path in self.exclude_paths:
            return request

        # Add request start time
        request.state.request_start_time = datetime.utcnow()

        # Log request
        self.logger.info(
            f"Request: {request.method} {request.path}",
            extra={
                'method': request.method,
                'path': request.path,
                'query': dict(request.query_params),
                'headers': dict(request.headers),
                'remote_addr': getattr(request, 'remote_addr', None),
                'user_agent': request.headers.get('user-agent'),
            }
        )

        return request

    async def process_response(self, request: Request, response: Response) -> Response:
        """Log outgoing responses"""
        if not self.log_responses:
            return response

        # Skip excluded paths
        if request.path in self.exclude_paths:
            return response

        # Calculate response time
        response_time = None
        if hasattr(request.state, 'request_start_time'):
            start_time = request.state.request_start_time
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000  # ms

        # Determine log level based on status code
        if response.status_code >= 500:
            log_level = 'error'
        elif response.status_code >= 400:
            log_level = 'warning'
        else:
            log_level = 'info'

        # Log response
        log_method = getattr(self.logger, log_level)
        log_method(
            f"Response: {response.status_code} for {request.method} {request.path}",
            extra={
                'status_code': response.status_code,
                'method': request.method,
                'path': request.path,
                'response_time_ms': response_time,
                'content_length': response.headers.get('content-length'),
                'content_type': response.headers.get('content-type'),
            }
        )

        return response

    async def process_exception(self, request: Request, exception: Exception) -> Optional[Response]:
        """Log exceptions"""
        if not self.log_errors:
            return None

        # Log the exception
        self.logger.error(
            f"Exception in {request.method} {request.path}: {str(exception)}",
            extra={
                'method': request.method,
                'path': request.path,
                'exception_type': type(exception).__name__,
                'exception_message': str(exception),
            },
            exc_info=True
        )

        return None

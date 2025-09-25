"""
Testing framework for Pyserv .
Provides comprehensive testing utilities for unit, integration, and performance testing.
"""

import unittest
import time
import json
import asyncio
from typing import Dict, List, Any, Optional, Callable, Type, Union
from unittest.mock import Mock, patch, MagicMock
from functools import wraps
import inspect
import sys
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr
from urllib.parse import urlencode

from pyserv.http.request import Request
from pyserv.http.response import Response
from pyserv.server.application import Application
from pyserv.database import AbstractDatabaseConnection
from pyserv.caching import get_cache_manager


class PyservTestCase(unittest.TestCase):
    """Base test case for Pyserv  applications"""

    def setUp(self):
        """Set up test environment"""
        super().setUp()
        self.app = None
        self.client = None

    def tearDown(self):
        """Clean up test environment"""
        super().tearDown()
        if self.app:
            # Clean up app resources
            pass

    def create_app(self, config: Dict[str, Any] = None) -> Application:
        """Create test application"""
        from pyserv.server.application import Application
        app = Application()

        # Configure for testing
        app.config.debug = True
        app.config.testing = True

        if config:
            for key, value in config.items():
                setattr(app.config, key, value)

        self.app = app
        return app

    def create_client(self, app: Application = None):
        """Create test client"""
        if app is None:
            app = self.app or self.create_app()

        client = TestClient(app)
        self.client = client
        return client


class TestClient:
    """Test client for making HTTP requests"""

    def __init__(self, app: Application):
        self.app = app

    def get(self, path: str, headers: Dict[str, str] = None, **kwargs) -> TestResponse:
        """Make GET request"""
        return self._make_request('GET', path, headers=headers, **kwargs)

    def post(self, path: str, data: Any = None, headers: Dict[str, str] = None, **kwargs) -> TestResponse:
        """Make POST request"""
        return self._make_request('POST', path, data=data, headers=headers, **kwargs)

    def put(self, path: str, data: Any = None, headers: Dict[str, str] = None, **kwargs) -> TestResponse:
        """Make PUT request"""
        return self._make_request('PUT', path, data=data, headers=headers, **kwargs)

    def patch(self, path: str, data: Any = None, headers: Dict[str, str] = None, **kwargs) -> TestResponse:
        """Make PATCH request"""
        return self._make_request('PATCH', path, data=data, headers=headers, **kwargs)

    def delete(self, path: str, headers: Dict[str, str] = None, **kwargs) -> TestResponse:
        """Make DELETE request"""
        return self._make_request('DELETE', path, headers=headers, **kwargs)

    def _make_request(self, method: str, path: str, data: Any = None,
                     headers: Dict[str, str] = None, **kwargs) -> TestResponse:
        """Make HTTP request to test application"""

        # Create ASGI scope
        scope = {
            'type': 'http',
            'method': method,
            'path': path,
            'query_string': b'',
            'headers': self._prepare_headers(headers),
            'server': ('testserver', 80),
            'client': ('127.0.0.1', 12345),
        }

        # Prepare request body
        body = b''
        if data is not None:
            if isinstance(data, dict):
                body = json.dumps(data).encode()
                scope['headers'].append([b'content-type', b'application/json'])
            elif isinstance(data, str):
                body = data.encode()
            elif isinstance(data, bytes):
                body = data

        # Create mock receive function
        async def receive():
            return {
                'type': 'http.request',
                'body': body,
                'more_body': False,
            }

        # Create mock send function
        sent_messages = []
        async def send(message):
            sent_messages.append(message)

        # Make request - call ASGI app directly as coroutine
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.app(scope, receive, send))
            finally:
                loop.close()
        except Exception as e:
            # Handle synchronous apps or other errors
            pass

        return TestResponse(sent_messages)

    def _prepare_headers(self, headers: Dict[str, str] = None) -> List[List[bytes]]:
        """Prepare headers for ASGI scope"""
        prepared = []
        if headers:
            for key, value in headers.items():
                prepared.append([key.lower().encode(), value.encode()])
        return prepared


class AsyncTestClient:
    """
    Async test client for making HTTP requests to Pyserv  applications without starting a server.
    """

    def __init__(self, app: Application):
        self.app = app

    async def get(self, path: str, params: Optional[Dict[str, Any]] = None,
                  headers: Optional[Dict[str, str]] = None) -> 'AsyncTestResponse':
        """Make a GET request."""
        return await self._make_request("GET", path, params=params, headers=headers)

    async def post(self, path: str, data: Optional[Dict[str, Any]] = None,
                   json_data: Optional[Dict[str, Any]] = None,
                   headers: Optional[Dict[str, str]] = None) -> 'AsyncTestResponse':
        """Make a POST request."""
        return await self._make_request("POST", path, data=data, json_data=json_data, headers=headers)

    async def put(self, path: str, data: Optional[Dict[str, Any]] = None,
                  json_data: Optional[Dict[str, Any]] = None,
                  headers: Optional[Dict[str, str]] = None) -> 'AsyncTestResponse':
        """Make a PUT request."""
        return await self._make_request("PUT", path, data=data, json_data=json_data, headers=headers)

    async def delete(self, path: str, headers: Optional[Dict[str, str]] = None) -> 'AsyncTestResponse':
        """Make a DELETE request."""
        return await self._make_request("DELETE", path, headers=headers)

    async def _make_request(self, method: str, path: str,
                           params: Optional[Dict[str, Any]] = None,
                           data: Optional[Dict[str, Any]] = None,
                           json_data: Optional[Dict[str, Any]] = None,
                           headers: Optional[Dict[str, str]] = None) -> 'AsyncTestResponse':
        """Make an HTTP request to the application."""
        # Build query string
        query_string = ""
        if params:
            query_string = "?" + urlencode(params)

        # Prepare headers
        request_headers = headers or {}
        request_headers.setdefault("host", "testserver")
        request_headers.setdefault("user-agent", "AsyncTestClient")

        # Prepare body
        body = b""
        if json_data is not None:
            body = json.dumps(json_data).encode('utf-8')
            request_headers.setdefault("content-type", "application/json")
        elif data is not None:
            body = urlencode(data).encode('utf-8')
            request_headers.setdefault("content-type", "application/x-www-form-urlencoded")

        # Create ASGI scope
        scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": method,
            "path": path,
            "raw_path": path.encode(),
            "query_string": query_string.encode()[1:] if query_string else b"",  # Remove leading '?'
            "root_path": "",
            "headers": [[k.lower().encode(), v.encode()] for k, v in request_headers.items()],
            "server": ("testserver", 80),
            "client": ("127.0.0.1", 0),
        }

        # Create mock receive and send functions
        messages = []
        body_sent = False

        async def receive():
            nonlocal body_sent
            if not body_sent:
                body_sent = True
                return {
                    "type": "http.request",
                    "body": body,
                    "more_body": False,
                }
            else:
                # Keep alive for potential additional receives
                await asyncio.sleep(0)  # Allow other tasks to run
                return {"type": "http.disconnect"}

        async def send(message):
            messages.append(message)

        # Call the ASGI application
        await self.app(scope, receive, send)

        # Process the response messages
        return AsyncTestResponse.from_asgi_messages(messages)


class AsyncTestResponse:
    """
    Response object returned by AsyncTestClient requests.
    """

    def __init__(self, response):
        self.response = response
        self.status_code = response.status_code
        self.headers = response.headers
        if isinstance(response.content, (dict, list)):
            self.content = json.dumps(response.content)
        elif isinstance(response.content, str):
            self.content = response.content
        elif isinstance(response.content, bytes):
            self.content = response.content.decode('utf-8')
        else:
            self.content = str(response.content)

    @classmethod
    def from_asgi_messages(cls, messages: List[Dict[str, Any]]) -> 'AsyncTestResponse':
        """Create AsyncTestResponse from ASGI messages."""
        status_code = 200
        headers = {}
        body_parts = []

        for message in messages:
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = {k.decode(): v.decode() for k, v in message.get("headers", [])}
            elif message["type"] == "http.response.body":
                body_parts.append(message.get("body", b""))

        body = b"".join(body_parts)
        content = body.decode('utf-8') if body else ""

        # Create a mock Response object
        class MockResponse:
            def __init__(self, status_code, headers, content):
                self.status_code = status_code
                self.headers = headers
                self.content = content

        mock_response = MockResponse(status_code, headers, content)
        return cls(mock_response)

    @property
    def json(self) -> Dict[str, Any]:
        """Parse response content as JSON."""
        return json.loads(self.content)

    def __str__(self):
        return f"AsyncTestResponse(status={self.status_code}, content={self.content})"


class TestResponse:
    """Test response object"""

    def __init__(self, messages: List[Dict[str, Any]]):
        self.messages = messages
        self.status_code = None
        self.headers = {}
        self.body = b''
        self.text = ''
        self.json_data = None

        self._parse_messages()

    def _parse_messages(self):
        """Parse ASGI messages"""
        for message in self.messages:
            if message['type'] == 'http.response.start':
                self.status_code = message['status']
                # Handle headers properly - they come as list of [key, value] pairs
                headers_list = message.get('headers', [])
                self.headers = {}
                for key_bytes, value_bytes in headers_list:
                    key = key_bytes.decode('utf-8').lower()
                    value = value_bytes.decode('utf-8')
                    self.headers[key] = value
            elif message['type'] == 'http.response.body':
                self.body += message.get('body', b'')

        # Decode body
        try:
            self.text = self.body.decode('utf-8') if self.body else ''
            # Try to parse as JSON
            try:
                if self.text.strip():
                    self.json_data = json.loads(self.text)
            except json.JSONDecodeError:
                pass
        except UnicodeDecodeError:
            self.text = str(self.body)

    def json(self):
        """Get JSON data"""
        return self.json_data

    @property
    def content(self):
        """Get response content"""
        return self.body

    def __str__(self):
        return f"TestResponse(status={self.status_code}, body={self.text[:100]}...)"

    def __repr__(self):
        return self.__str__()


class DatabaseTestCase(PyservTestCase):
    """Test case with database setup/teardown"""

    def setUp(self):
        super().setUp()
        self.db_connection = None

    def tearDown(self):
        super().tearDown()
        if self.db_connection:
            # Clean up database
            pass

    def create_database(self, config: Dict[str, Any] = None):
        """Create test database"""
        default_config = {
            'database_url': 'mongodb://localhost:27017/test_db'
        }
        if config:
            default_config.update(config)

        # This would create a test database connection
        # For now, just mock it
        self.db_connection = Mock()
        return self.db_connection


class APITestCase(PyservTestCase):
    """Test case for API testing"""

    def setUp(self):
        super().setUp()
        self.api_client = None

    def create_api_client(self, app: Application = None):
        """Create API test client"""
        if app is None:
            app = self.app or self.create_app()

        self.api_client = APIClient(app)
        return self.api_client


class APIClient(TestClient):
    """API test client with additional features"""

    def authenticate(self, token: str = None, username: str = None, password: str = None):
        """Authenticate client"""
        if token:
            self.default_headers = {'Authorization': f'Bearer {token}'}
        elif username and password:
            # This would perform authentication
            pass

    def force_authenticate(self, user):
        """Force authentication for testing"""
        self.user = user

    def get_authenticated(self, path: str, **kwargs):
        """Make authenticated GET request"""
        return self.get(path, **kwargs)

    def post_authenticated(self, path: str, data=None, **kwargs):
        """Make authenticated POST request"""
        return self.post(path, data=data, **kwargs)


class PerformanceTestCase(unittest.TestCase):
    """Base class for performance testing"""

    def setUp(self):
        super().setUp()
        self.start_time = None
        self.end_time = None

    def start_timer(self):
        """Start performance timer"""
        self.start_time = time.time()

    def stop_timer(self):
        """Stop performance timer"""
        self.end_time = time.time()

    @property
    def elapsed_time(self):
        """Get elapsed time"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0

    def assert_performance(self, max_time: float, operation: Callable):
        """Assert operation completes within time limit"""
        self.start_timer()
        result = operation()
        self.stop_timer()

        self.assertLess(self.elapsed_time, max_time,
                       f"Operation took {self.elapsed_time:.2f}s, expected < {max_time}s")
        return result

    def benchmark(self, operation: Callable, iterations: int = 100) -> Dict[str, float]:
        """Benchmark operation"""
        times = []

        for _ in range(iterations):
            self.start_timer()
            operation()
            self.stop_timer()
            times.append(self.elapsed_time)

        return {
            'min': min(times),
            'max': max(times),
            'avg': sum(times) / len(times),
            'total': sum(times)
        }


class LoadTestCase(PerformanceTestCase):
    """Test case for load testing"""

    def setUp(self):
        super().setUp()
        self.concurrency = 10
        self.requests_per_second = 100

    def simulate_load(self, operation: Callable, duration: int = 60):
        """Simulate load on operation"""
        import threading
        import time

        results = []
        errors = []

        def worker():
            end_time = time.time() + duration
            while time.time() < end_time:
                try:
                    self.start_timer()
                    operation()
                    self.stop_timer()
                    results.append(self.elapsed_time)
                except Exception as e:
                    errors.append(str(e))
                time.sleep(1.0 / self.requests_per_second)

        threads = []
        for _ in range(self.concurrency):
            thread = threading.Thread(target=worker)
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()

        return {
            'total_requests': len(results),
            'errors': len(errors),
            'avg_response_time': sum(results) / len(results) if results else 0,
            'min_response_time': min(results) if results else 0,
            'max_response_time': max(results) if results else 0,
            'requests_per_second': len(results) / duration
        }


class MockTestCase(unittest.TestCase):
    """Test case with mocking utilities"""

    def setUp(self):
        super().setUp()
        self.mocks = []

    def tearDown(self):
        super().tearDown()
        # Clean up mocks
        for mock in self.mocks:
            mock.stop() if hasattr(mock, 'stop') else None

    def mock_function(self, target: str, return_value: Any = None):
        """Mock a function"""
        patcher = patch(target, return_value=return_value)
        mock = patcher.start()
        self.mocks.append(patcher)
        return mock

    def mock_object(self, target: str, **kwargs):
        """Mock an object"""
        patcher = patch(target, **kwargs)
        mock = patcher.start()
        self.mocks.append(patcher)
        return mock

    def create_mock(self, **kwargs):
        """Create a mock object"""
        mock = Mock(**kwargs)
        self.mocks.append(mock)
        return mock


class IntegrationTestCase(PyservTestCase):
    """Test case for integration testing"""

    def setUp(self):
        super().setUp()
        self.external_services = {}

    def mock_external_service(self, service_name: str, responses: Dict[str, Any]):
        """Mock external service"""
        self.external_services[service_name] = responses

    def call_external_service(self, service_name: str, endpoint: str, **kwargs):
        """Call mocked external service"""
        if service_name in self.external_services:
            return self.external_services[service_name].get(endpoint, {})
        raise Exception(f"External service {service_name} not mocked")


class TestSuite:
    """Custom test suite with additional features"""

    def __init__(self, name: str = "Pyserv  Test Suite"):
        self.name = name
        self.tests = []
        self.results = {}

    def add_test(self, test_case: Type[unittest.TestCase]):
        """Add test case to suite"""
        self.tests.append(test_case)

    def run(self, verbosity: int = 1) -> unittest.TestResult:
        """Run test suite"""
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()

        for test_case in self.tests:
            suite.addTests(loader.loadTestsFromTestCase(test_case))

        runner = unittest.TextTestRunner(verbosity=verbosity)
        result = runner.run(suite)

        self.results = {
            'tests_run': result.testsRun,
            'failures': len(result.failures),
            'errors': len(result.errors),
            'skipped': len(result.skipped),
            'success': result.wasSuccessful()
        }

        return result

    def get_coverage_report(self):
        """Get test coverage report"""
        try:
            import coverage
            cov = coverage.Coverage()
            cov.start()

            # Run tests
            self.run(verbosity=0)

            cov.stop()
            cov.save()

            return cov.report()
        except ImportError:
            return "Coverage not available (install coverage package)"


class TestUtils:
    """Utility functions for testing"""

    @staticmethod
    def create_test_request(method: str = 'GET', path: str = '/',
                           headers: Dict[str, str] = None, body: bytes = b'') -> Request:
        """Create test request"""
        from pyserv.http.request import Request

        # Create ASGI scope
        scope = {
            'type': 'http',
            'method': method,
            'path': path,
            'query_string': b'',
            'headers': [[k.encode(), v.encode()] for k, v in (headers or {}).items()],
            'server': ('testserver', 80),
            'client': ('127.0.0.1', 12345),
        }

        # Mock receive function
        async def receive():
            return {
                'type': 'http.request',
                'body': body,
                'more_body': False,
            }

        # Mock send function
        async def send(message):
            pass

        return Request(scope, receive, send)

    @staticmethod
    def create_test_user(username: str = 'testuser', email: str = 'test@example.com',
                        is_staff: bool = False) -> 'User':
        """Create test user"""
        from pyserv.auth import User
        return User(
            id=1,
            username=username,
            email=email,
            is_staff=is_staff,
            roles=['user']
        )

    @staticmethod
    def assert_response_status(response: TestResponse, expected_status: int):
        """Assert response status"""
        if response.status_code != expected_status:
            raise AssertionError(f"Expected status {expected_status}, got {response.status_code}")

    @staticmethod
    def assert_response_json(response: TestResponse, expected_data: Dict[str, Any]):
        """Assert response JSON data"""
        if response.json_data != expected_data:
            raise AssertionError(f"Expected JSON {expected_data}, got {response.json_data}")

    @staticmethod
    def capture_output(func: Callable) -> tuple:
        """Capture stdout and stderr"""
        stdout_capture = StringIO()
        stderr_capture = StringIO()

        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            result = func()

        return result, stdout_capture.getvalue(), stderr_capture.getvalue()


# Test discovery and running utilities
def discover_tests(path: str = 'tests') -> List[Type[unittest.TestCase]]:
    """Discover test cases"""
    import importlib
    import pkgutil

    test_cases = []

    # Walk through test directory
    for importer, modname, ispkg in pkgutil.walk_packages([path], path + "."):
        try:
            module = importlib.import_module(modname)

            # Find test cases in module
            for name in dir(module):
                obj = getattr(module, name)
                if (isinstance(obj, type) and
                    issubclass(obj, unittest.TestCase) and
                    obj != unittest.TestCase):
                    test_cases.append(obj)

        except ImportError:
            continue

    return test_cases


def run_tests(test_path: str = 'tests', verbosity: int = 1,
              pattern: str = 'test_*.py') -> unittest.TestResult:
    """Run tests with discovery"""
    # Discover tests
    test_cases = discover_tests(test_path)

    # Create test suite
    suite = TestSuite()
    for test_case in test_cases:
        suite.add_test(test_case)

    # Run tests
    return suite.run(verbosity=verbosity)


# Test fixtures and factories
class TestDataFactory:
    """Factory for creating test data"""

    @staticmethod
    def create_user(**kwargs) -> 'User':
        """Create test user"""
        from pyserv.auth import User
        defaults = {
            'id': 1,
            'username': 'testuser',
            'email': 'test@example.com',
            'is_active': True,
            'roles': ['user']
        }
        defaults.update(kwargs)
        return User(**defaults)

    @staticmethod
    def create_request(**kwargs) -> Request:
        """Create test request"""
        defaults = {
            'method': 'GET',
            'path': '/',
            'headers': {},
            'body': b''
        }
        defaults.update(kwargs)
        return TestUtils.create_test_request(**defaults)


# Performance monitoring
class PerformanceMonitor:
    """Monitor performance during tests"""

    def __init__(self):
        self.metrics = {}

    def start_monitoring(self, name: str):
        """Start monitoring"""
        self.metrics[name] = {
            'start_time': time.time(),
            'memory_start': self._get_memory_usage()
        }

    def stop_monitoring(self, name: str) -> Dict[str, Any]:
        """Stop monitoring and return metrics"""
        if name not in self.metrics:
            return {}

        start_metrics = self.metrics[name]
        end_time = time.time()
        end_memory = self._get_memory_usage()

        metrics = {
            'duration': end_time - start_metrics['start_time'],
            'memory_delta': end_memory - start_metrics['memory_start'],
            'cpu_usage': self._get_cpu_usage()
        }

        del self.metrics[name]
        return metrics

    def _get_memory_usage(self) -> float:
        """Get current memory usage"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024  # MB
        except ImportError:
            return 0.0

    def _get_cpu_usage(self) -> float:
        """Get current CPU usage"""
        try:
            import psutil
            return psutil.cpu_percent(interval=0.1)
        except ImportError:
            return 0.0


# Global test utilities
test_utils = TestUtils()
test_factory = TestDataFactory()
performance_monitor = PerformanceMonitor()

__all__ = [
    'PyservTestCase', 'TestClient', 'TestResponse', 'AsyncTestClient', 'AsyncTestResponse',
    'DatabaseTestCase', 'APITestCase', 'APIClient', 'PerformanceTestCase', 'LoadTestCase',
    'MockTestCase', 'IntegrationTestCase', 'TestSuite', 'TestUtils',
    'TestDataFactory', 'PerformanceMonitor', 'discover_tests', 'run_tests',
    'test_utils', 'test_factory', 'performance_monitor'
]

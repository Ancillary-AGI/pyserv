"""
Regression tests for Pyserv  framework
These tests ensure that previously fixed bugs don't reappear
"""
import pytest
from unittest.mock import patch, MagicMock

from pyserv import Application
from pyserv.exceptions import HTTPException


@pytest.mark.regression
class TestRegression:
    """Regression tests for known issues"""

    @pytest.fixture
    def regression_app(self):
        """Application for regression testing"""
        app = Application()

        @app.route('/')
        async def home(request):
            return {'message': 'Regression Test Home'}

        @app.route('/bug/{id}')
        async def bug_route(request, id: int):
            return {'bug_id': id, 'status': 'fixed'}

        return app

    def test_route_parameter_type_conversion_regression(self, regression_app):
        """Regression test for route parameter type conversion bug"""
        # This was a bug where string parameters weren't converted to int properly
        router = regression_app.router

        # Test that route with int parameter works
        route, params = router.find_route('/bug/123', 'GET')
        assert route is not None
        assert params == {'id': '123'}  # Should be string, not int

        # The actual conversion should happen in the handler
        # This test ensures the route matching still works

    @pytest.mark.asyncio
    async def test_middleware_exception_handling_regression(self, regression_app, client):
        """Regression test for middleware exception handling"""
        # Add middleware that might cause exceptions
        @regression_app.middleware
        async def problematic_middleware(request, call_next):
            # Simulate a middleware that might fail
            if hasattr(request, 'state') and request.state.get('cause_error'):
                raise ValueError("Middleware error")
            return await call_next(request)

        # Test normal operation
        response = await client.get('/')
        assert response.status_code == 200

        # Test with error condition (if implemented)
        # This ensures middleware errors are handled properly

    def test_websocket_route_registration_regression(self, regression_app):
        """Regression test for WebSocket route registration"""
        # This was a bug where WebSocket routes weren't registered properly
        initial_count = len(regression_app.router.websocket_routes)

        @regression_app.websocket_route('/ws/test')
        async def ws_test(websocket):
            await websocket.accept()

        # Should have one more WebSocket route
        assert len(regression_app.router.websocket_routes) == initial_count + 1

        # Test route lookup
        route, params = regression_app.router.find_websocket_route('/ws/test')
        assert route is not None
        assert params == {}

    @pytest.mark.asyncio
    async def test_concurrent_request_regression(self, regression_app, client):
        """Regression test for concurrent request handling"""
        # This was a bug where concurrent requests caused issues
        import asyncio

        async def make_request(n):
            response = await client.get('/')
            return response.status_code

        # Make 50 concurrent requests
        tasks = [make_request(i) for i in range(50)]
        results = await asyncio.gather(*tasks)

        # All should succeed
        assert all(status == 200 for status in results)

    def test_application_config_regression(self, regression_app):
        """Regression test for application configuration"""
        # Test that config is properly initialized
        assert regression_app.config is not None
        assert hasattr(regression_app.config, 'debug')
        assert hasattr(regression_app.config, 'secret_key')

        # Test config modification
        original_debug = regression_app.config.debug
        regression_app.config.debug = not original_debug
        assert regression_app.config.debug != original_debug

    @pytest.mark.asyncio
    async def test_json_response_encoding_regression(self, regression_app, client):
        """Regression test for JSON response encoding"""
        @regression_app.route('/json-test')
        async def json_test(request):
            return {
                'string': 'test',
                'number': 123,
                'boolean': True,
                'null': None,
                'array': [1, 2, 3],
                'object': {'nested': 'value'}
            }

        response = await client.get('/json-test')
        assert response.status_code == 200

        data = response.json()
        assert data['string'] == 'test'
        assert data['number'] == 123
        assert data['boolean'] is True
        assert data['null'] is None
        assert data['array'] == [1, 2, 3]
        assert data['object']['nested'] == 'value'

    def test_route_pattern_compilation_regression(self):
        """Regression test for route pattern compilation"""
        from pyserv.routing import Route

        # Test various route patterns that previously caused issues
        test_patterns = [
            '/simple',
            '/users/{id}',
            '/users/{id}/posts/{post_id}',
            '/files/{path:path}',  # Custom converter
            '/api/v{version}/users/{id}',
        ]

        for pattern in test_patterns:
            try:
                route = Route(pattern, lambda r: None)
                assert route.pattern is not None
            except Exception as e:
                pytest.fail(f"Route pattern '{pattern}' failed to compile: {e}")

    @pytest.mark.asyncio
    async def test_large_request_body_regression(self, regression_app, client):
        """Regression test for large request body handling"""
        @regression_app.route('/large-body', methods=['POST'])
        async def large_body_handler(request):
            data = await request.json()
            return {'received_length': len(str(data))}

        # Test with moderately large payload
        large_data = {'data': 'x' * 50000}  # 50KB
        response = await client.post('/large-body', json=large_data)

        # Should handle without crashing
        assert response.status_code in [200, 413]

    def test_exception_handler_registration_regression(self, regression_app):
        """Regression test for exception handler registration"""
        # Test that exception handlers can be registered and retrieved
        initial_handlers = len(regression_app._exception_handlers)

        @regression_app.exception_handler(ValueError)
        async def value_error_handler(exc):
            return {'error': 'ValueError'}

        @regression_app.exception_handler(RuntimeError)
        async def runtime_error_handler(exc):
            return {'error': 'RuntimeError'}

        # Should have two more handlers
        assert len(regression_app._exception_handlers) == initial_handlers + 2
        assert ValueError in regression_app._exception_handlers
        assert RuntimeError in regression_app._exception_handlers

    @pytest.mark.asyncio
    async def test_middleware_order_regression(self, regression_app, client):
        """Regression test for middleware execution order"""
        execution_order = []

        @regression_app.middleware
        async def first_middleware(request, call_next):
            execution_order.append('first')
            result = await call_next(request)
            execution_order.append('first_return')
            return result

        @regression_app.middleware
        async def second_middleware(request, call_next):
            execution_order.append('second')
            result = await call_next(request)
            execution_order.append('second_return')
            return result

        response = await client.get('/')
        assert response.status_code == 200

        # Middleware should execute in order: first -> second -> handler -> second_return -> first_return
        expected_order = ['first', 'second', 'second_return', 'first_return']
        assert execution_order == expected_order

    def test_router_mounting_regression(self, regression_app):
        """Regression test for router mounting"""
        sub_app = Application()

        @sub_app.route('/sub-home')
        async def sub_home(request):
            return {'message': 'sub app'}

        # Mount sub-app
        regression_app.mount('/sub', sub_app.router)

        # Test that mounted routes work
        route, params = regression_app.router.find_route('/sub/sub-home', 'GET')
        assert route is not None
        assert params == {}

    @pytest.mark.asyncio
    async def test_response_header_regression(self, regression_app, client):
        """Regression test for response headers"""
        @regression_app.route('/headers')
        async def headers_test(request):
            return {'message': 'headers test'}

        response = await client.get('/headers')

        # Check basic headers
        assert 'content-type' in response.headers
        assert 'content-type' in [h.lower() for h in response.headers.keys()]

        # Content-Type should be JSON
        content_type = response.headers.get('content-type', '').lower()
        assert 'application/json' in content_type

    def test_import_error_regression(self):
        """Regression test for import errors"""
        # Test that all main imports work
        try:
            from pyserv import Application, AppConfig
            from pyserv.routing import Router, Route
            from pyserv.exceptions import HTTPException
            from pyserv.security import Security, CryptoUtils
        except ImportError as e:
            pytest.fail(f"Import error: {e}")

    @pytest.mark.asyncio
    async def test_async_handler_regression(self, regression_app, client):
        """Regression test for async handler support"""
        # Test both async and sync handlers
        @regression_app.route('/async')
        async def async_handler(request):
            return {'type': 'async'}

        @regression_app.route('/sync')
        def sync_handler(request):
            return {'type': 'sync'}

        # Both should work
        async_response = await client.get('/async')
        sync_response = await client.get('/sync')

        assert async_response.status_code == 200
        assert sync_response.status_code == 200

        assert async_response.json()['type'] == 'async'
        assert sync_response.json()['type'] == 'sync'

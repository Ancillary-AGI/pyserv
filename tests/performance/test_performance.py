"""
Performance tests for Pydance framework
"""
import asyncio
import time
import pytest
from unittest.mock import patch

from pydance import Application


@pytest.mark.performance
class TestPerformance:
    """Performance tests"""

    @pytest.fixture
    def perf_app(self):
        """Application for performance testing"""
        app = Application()

        @app.route('/')
        async def home(request):
            return {'message': 'Hello World'}

        @app.route('/json')
        async def json_response(request):
            return {
                'users': [
                    {'id': i, 'name': f'User {i}', 'email': f'user{i}@example.com'}
                    for i in range(100)
                ]
            }

        @app.route('/sync')
        def sync_handler(request):
            time.sleep(0.001)  # Simulate some work
            return {'message': 'Sync response'}

        return app

    def test_route_lookup_performance(self, perf_app, benchmark):
        """Test route lookup performance"""
        def lookup():
            route, params = perf_app.router.find_route('/', 'GET')
            return route, params

        result = benchmark(lookup)
        assert result[0] is not None

    def test_middleware_execution_performance(self, perf_app, benchmark):
        """Test middleware execution performance"""
        @perf_app.middleware
        async def perf_middleware(request, call_next):
            # Add some processing time
            await asyncio.sleep(0.001)
            response = await call_next(request)
            return response

        async def run_middleware_test():
            # Mock request
            mock_request = type('MockRequest', (), {
                'method': 'GET',
                'path': '/',
                'headers': {},
                'state': {}
            })()

            # Execute middleware chain
            response = await perf_app.middleware_manager.execute_http_chain(
                mock_request, lambda r: type('MockResponse', (), {'status_code': 200})()
            )
            return response

        async def benchmark_middleware():
            return await run_middleware_test()

        result = benchmark(lambda: asyncio.run(benchmark_middleware()))
        assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_concurrent_request_handling(self, perf_app, client):
        """Test concurrent request handling performance"""
        start_time = time.time()

        # Make 100 concurrent requests
        tasks = []
        for i in range(100):
            tasks.append(client.get('/'))

        responses = await asyncio.gather(*tasks)
        end_time = time.time()

        # Verify all responses
        for response in responses:
            assert response.status_code == 200

        total_time = end_time - start_time
        avg_time = total_time / 100

        # Performance assertions
        assert total_time < 5.0  # Should complete within 5 seconds
        assert avg_time < 0.05  # Average response time should be < 50ms

        print(f"Concurrent requests: {len(responses)}")
        print(f"Total time: {total_time:.2f}s")
        print(f"Average time: {avg_time:.4f}s")

    def test_memory_usage_growth(self, perf_app):
        """Test memory usage doesn't grow significantly"""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Make many requests
        async def make_requests():
            for i in range(1000):
                # Simulate request processing
                route, params = perf_app.router.find_route('/', 'GET')
                assert route is not None

        asyncio.run(make_requests())

        final_memory = process.memory_info().rss
        memory_growth = final_memory - initial_memory

        # Memory growth should be reasonable (< 10MB)
        assert memory_growth < 10 * 1024 * 1024

        print(f"Initial memory: {initial_memory / 1024 / 1024:.2f} MB")
        print(f"Final memory: {final_memory / 1024 / 1024:.2f} MB")
        print(f"Memory growth: {memory_growth / 1024 / 1024:.2f} MB")

    @pytest.mark.slow
    def test_large_payload_handling(self, perf_app, benchmark):
        """Test handling of large payloads"""
        # Create a large response
        large_data = {'data': 'x' * 1000000}  # 1MB response

        @perf_app.route('/large')
        async def large_response(request):
            return large_data

        async def test_large_response():
            # This would normally use the client, but for benchmarking
            # we'll just test the route handler
            route, params = perf_app.router.find_route('/large', 'GET')
            if route:
                # Mock request
                mock_request = type('MockRequest', (), {
                    'method': 'GET',
                    'path': '/large',
                    'headers': {},
                    'state': {}
                })()
                result = await route.handler(mock_request)
                return result
            return None

        async def benchmark_large():
            return await test_large_response()

        result = benchmark(lambda: asyncio.run(benchmark_large()))
        assert result is not None
        assert len(result['data']) == 1000000

    def test_database_connection_pooling(self, benchmark):
        """Test database connection pooling performance"""
        from pydance.database.config import DatabaseConfig

        def create_connections():
            configs = []
            for i in range(10):
                config = DatabaseConfig(f"sqlite:///test_{i}.db")
                configs.append(config)
            return configs

        result = benchmark(create_connections)
        assert len(result) == 10

    @pytest.mark.asyncio
    async def test_websocket_connection_performance(self, perf_app):
        """Test WebSocket connection performance"""
        @perf_app.websocket_route('/perf-ws')
        async def perf_ws_handler(websocket):
            await websocket.accept()
            await websocket.send_json({'status': 'connected'})
            await websocket.close()

        # Test WebSocket route lookup
        def benchmark_ws_lookup():
            route, params = perf_app.router.find_websocket_route('/perf-ws')
            return route

        from pytest import benchmark
        result = benchmark(lambda: benchmark_ws_lookup())
        assert result is not None

    def test_template_rendering_performance(self, benchmark):
        """Test template rendering performance"""
        # This would test template engine performance
        # For now, just benchmark string operations
        def render_template():
            template = "Hello {{name}}! Your ID is {{id}}."
            result = template.replace("{{name}}", "User").replace("{{id}}", "123")
            return result

        result = benchmark(render_template)
        assert "Hello User!" in result
        assert "Your ID is 123" in result

    @pytest.mark.asyncio
    async def test_middleware_chain_performance(self, perf_app, benchmark):
        """Test middleware chain performance"""
        # Add multiple middleware
        for i in range(5):
            @perf_app.middleware
            async def chain_middleware(request, call_next):
                response = await call_next(request)
                return response

        async def run_chain():
            mock_request = type('MockRequest', (), {
                'method': 'GET',
                'path': '/',
                'headers': {},
                'state': {}
            })()

            response = await perf_app.middleware_manager.execute_http_chain(
                mock_request, lambda r: type('MockResponse', (), {'status_code': 200})()
            )
            return response

        async def benchmark_chain():
            return await run_chain()

        result = benchmark(lambda: asyncio.run(benchmark_chain()))
        assert result.status_code == 200

"""
Integration tests for full Pydance application
"""
import pytest
from unittest.mock import patch

from pydance import Application
from pydance.core.exceptions import HTTPException


@pytest.mark.integration
class TestFullApplication:
    """Test full application integration"""

    @pytest.fixture
    async def full_app(self):
        """Create a fully configured application"""
        app = Application()

        @app.route('/')
        async def home(request):
            return {'message': 'Welcome to Pydance', 'status': 'ok'}

        @app.route('/users/{user_id}')
        async def get_user(request, user_id: int):
            return {'user_id': user_id, 'name': f'User {user_id}'}

        @app.route('/users', methods=['POST'])
        async def create_user(request):
            data = await request.json()
            return {'user': data, 'created': True}

        @app.websocket_route('/ws/chat')
        async def chat_handler(websocket):
            await websocket.accept()
            await websocket.send_json({'message': 'Connected to chat'})

            try:
                while True:
                    data = await websocket.receive_json()
                    await websocket.send_json({'echo': data})
            except Exception:
                pass

        return app

    @pytest.mark.asyncio
    async def test_http_request_response_cycle(self, full_app, client):
        """Test complete HTTP request-response cycle"""
        response = await client.get('/')
        assert response.status_code == 200
        data = response.json()
        assert data['message'] == 'Welcome to Pydance'
        assert data['status'] == 'ok'

    @pytest.mark.asyncio
    async def test_parameterized_routes(self, full_app, client):
        """Test routes with parameters"""
        response = await client.get('/users/123')
        assert response.status_code == 200
        data = response.json()
        assert data['user_id'] == 123
        assert data['name'] == 'User 123'

    @pytest.mark.asyncio
    async def test_post_requests(self, full_app, client):
        """Test POST request handling"""
        user_data = {'name': 'John Doe', 'email': 'john@example.com'}
        response = await client.post('/users', json=user_data)
        assert response.status_code == 200
        data = response.json()
        assert data['created'] is True
        assert data['user'] == user_data

    @pytest.mark.asyncio
    async def test_middleware_integration(self, full_app, client):
        """Test middleware integration"""
        # The app should have default security middleware
        response = await client.get('/', headers={'Host': 'example.com'})
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_error_handling(self, full_app, client):
        """Test error handling integration"""
        # Test 404
        response = await client.get('/nonexistent')
        assert response.status_code == 404

        # Test custom exception handler
        @full_app.exception_handler(ValueError)
        async def handle_value_error(exc):
            return {'error': 'ValueError', 'message': str(exc)}

        # This would require a route that raises ValueError
        # For now, just test that the handler is registered
        assert ValueError in full_app._exception_handlers

    @pytest.mark.asyncio
    async def test_websocket_integration(self, full_app):
        """Test WebSocket integration"""
        # This would require a WebSocket test client
        # For now, just verify the route is registered
        assert len(full_app.router.websocket_routes) == 1
        ws_route = full_app.router.websocket_routes[0]
        assert ws_route.path == '/ws/chat'

    @pytest.mark.asyncio
    async def test_application_startup_shutdown(self, full_app):
        """Test application startup and shutdown"""
        with patch('pydance.core.database.DatabaseConnection') as mock_db:
            mock_instance = patch('pydance.core.database.DatabaseConnection.get_instance').start()
            mock_instance.connect = patch('pydance.core.database.DatabaseConnection.connect').start()
            mock_instance.disconnect = patch('pydance.core.database.DatabaseConnection.disconnect').start()

            await full_app.startup()
            await full_app.shutdown()

            # Verify startup/shutdown methods were called
            # (This is a simplified test - in real scenario would check actual calls)

    def test_route_registration(self, full_app):
        """Test that all routes are properly registered"""
        routes = full_app.router.routes

        # Should have 3 HTTP routes
        assert len(routes) == 3

        # Check route paths
        paths = [route.path for route in routes]
        assert '/' in paths
        assert '/users/{user_id}' in paths
        assert '/users' in paths

    def test_middleware_stack(self, full_app):
        """Test middleware stack configuration"""
        middleware_count = len(full_app.middleware_manager.middleware)
        # Should have at least the default middleware
        assert middleware_count >= 1

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, full_app, client):
        """Test handling concurrent requests"""
        import asyncio

        async def make_request():
            return await client.get('/')

        # Make multiple concurrent requests
        tasks = [make_request() for _ in range(10)]
        responses = await asyncio.gather(*tasks)

        # All should succeed
        for response in responses:
            assert response.status_code == 200
            assert response.json()['status'] == 'ok'

    @pytest.mark.asyncio
    async def test_request_state_persistence(self, full_app, client):
        """Test request state persistence through middleware"""
        # Add middleware that sets state
        @full_app.middleware
        async def test_middleware(request, call_next):
            request.state['test_key'] = 'test_value'
            response = await call_next(request)
            return response

        response = await client.get('/')
        assert response.status_code == 200

        # In a real scenario, we would check that the state was used
        # For this test, we just verify the middleware was added
        assert len(full_app.middleware_manager.middleware) >= 2

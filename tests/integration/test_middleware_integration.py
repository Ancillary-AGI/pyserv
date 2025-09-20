"""
Integration tests for middleware functionality
"""
import pytest

from pydance import Application


@pytest.mark.integration
class TestMiddlewareIntegration:
    """Test middleware integration"""

    @pytest.fixture
    async def middleware_app(self):
        """Create an application with middleware"""
        app = Application()

        @app.route('/')
        async def home(request):
            return {'message': 'Home', 'middleware_test': getattr(request.state, 'middleware_applied', False)}

        return app

    @pytest.mark.asyncio
    async def test_default_middleware_stack(self, middleware_app, client):
        """Test default middleware stack"""
        response = await client.get('/', headers={'Host': 'example.com'})
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_custom_middleware(self, middleware_app, client):
        """Test custom middleware functionality"""
        # Add middleware that sets state
        @middleware_app.middleware
        async def test_middleware(request, call_next):
            request.state.middleware_applied = True
            response = await call_next(request)
            return response

        response = await client.get('/')
        assert response.status_code == 200
        data = response.json()
        assert data['middleware_test'] is True

    @pytest.mark.asyncio
    async def test_middleware_stack_size(self, middleware_app):
        """Test middleware stack configuration"""
        middleware_count = len(middleware_app.middleware_manager.middleware)
        # Should have at least the default middleware
        assert middleware_count >= 1

        # Add custom middleware
        @middleware_app.middleware
        async def custom_middleware(request, call_next):
            return await call_next(request)

        # Should have increased
        assert len(middleware_app.middleware_manager.middleware) >= middleware_count + 1

    @pytest.mark.asyncio
    async def test_request_state_persistence(self, middleware_app, client):
        """Test request state persistence through middleware"""
        # Add middleware that sets state
        @middleware_app.middleware
        async def state_middleware(request, call_next):
            request.state['test_key'] = 'test_value'
            response = await call_next(request)
            return response

        response = await client.get('/')
        assert response.status_code == 200

        # Verify middleware was added
        assert len(middleware_app.middleware_manager.middleware) >= 2

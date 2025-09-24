"""
Integration tests for application lifecycle and error handling
"""
import pytest
from unittest.mock import patch

from pyserv import Application
from pyserv.exceptions import HTTPException


@pytest.mark.integration
class TestApplicationLifecycle:
    """Test application lifecycle integration"""

    @pytest.fixture
    async def lifecycle_app(self):
        """Create an application for lifecycle testing"""
        app = Application()

        @app.route('/')
        async def home(request):
            return {'message': 'Home'}

        @app.route('/error')
        async def error_route(request):
            raise ValueError("Test error")

        return app

    @pytest.mark.asyncio
    async def test_application_startup_shutdown(self, lifecycle_app):
        """Test application startup and shutdown"""
        # Mock database connection for startup/shutdown
        with patch('src.pyserv .core.database.DatabaseConnection') as mock_db:
            from unittest.mock import AsyncMock
            mock_instance = AsyncMock()
            mock_db.get_instance.return_value = mock_instance

            await lifecycle_app.startup()
            await lifecycle_app.shutdown()

            mock_instance.connect.assert_called_once()
            mock_instance.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_handling_integration(self, lifecycle_app, client):
        """Test error handling integration"""
        # Test custom exception handler
        @lifecycle_app.exception_handler(ValueError)
        async def handle_value_error(exc):
            return {'error': 'ValueError', 'message': str(exc)}

        # This would require a route that raises ValueError
        # For now, just test that the handler is registered
        assert ValueError in lifecycle_app._exception_handlers

    @pytest.mark.asyncio
    async def test_route_registration(self, lifecycle_app):
        """Test that all routes are properly registered"""
        routes = lifecycle_app.router.routes

        # Should have routes
        assert len(routes) >= 1

        # Check route paths
        paths = [route.path for route in routes]
        assert '/' in paths

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, lifecycle_app, client):
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
            assert response.json()['message'] == 'Home'

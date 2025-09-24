"""
Integration tests for full Pyserv  application
"""
import pytest

from pyserv import Application


@pytest.mark.integration
class TestFullApplication:
    """Test full application integration"""

    @pytest.fixture
    async def full_app(self):
        """Create a fully configured application"""
        app = Application()

        @app.route('/')
        async def home(request):
            return {'message': 'Welcome to Pyserv ', 'status': 'ok'}

        @app.route('/health')
        async def health(request):
            return {'status': 'healthy'}

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
    async def test_full_application_initialization(self, full_app):
        """Test that full application initializes correctly"""
        # Verify routes are registered
        assert len(full_app.router.routes) == 4  # home, health, get_user, create_user
        assert len(full_app.router.websocket_routes) == 1  # ws/chat

        # Verify middleware is configured
        assert len(full_app.middleware_manager.middleware) >= 1

    @pytest.mark.asyncio
    async def test_application_components_integration(self, full_app):
        """Test that all application components work together"""
        # Test that routes have proper handlers
        routes = full_app.router.routes
        for route in routes:
            assert callable(route.handler)

        # Test that WebSocket routes have proper handlers
        ws_routes = full_app.router.websocket_routes
        for route in ws_routes:
            assert callable(route.handler)

    def test_application_configuration(self, full_app):
        """Test application configuration setup"""
        # Verify application has required attributes
        assert hasattr(full_app, 'router')
        assert hasattr(full_app, 'middleware_manager')
        assert hasattr(full_app, 'config')
        assert hasattr(full_app, '_exception_handlers')





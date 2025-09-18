"""
Integration tests for WebSocket functionality
"""
import pytest

from src.pydance import Application


@pytest.mark.integration
class TestWebSocketIntegration:
    """Test WebSocket integration"""

    @pytest.fixture
    async def ws_app(self):
        """Create an application with WebSocket routes"""
        app = Application()

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
    async def test_websocket_route_registration(self, ws_app):
        """Test that WebSocket routes are properly registered"""
        assert len(ws_app.router.websocket_routes) == 1
        ws_route = ws_app.router.websocket_routes[0]
        assert ws_route.path == '/ws/chat'

    @pytest.mark.asyncio
    async def test_websocket_connection(self, ws_app):
        """Test WebSocket connection establishment"""
        # This would require a WebSocket test client
        # For now, just verify the route handler is callable
        ws_route = ws_app.router.websocket_routes[0]
        assert callable(ws_route.handler)

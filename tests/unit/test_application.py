"""
Unit tests for Pydance Application
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from pydance import Application, AppConfig
from pydance.core.exceptions import HTTPException


class TestApplication:
    """Test Application class"""

    def test_application_init(self, config):
        """Test application initialization"""
        app = Application(config)
        assert app.config == config
        assert app.router is not None
        assert app.middleware_manager is not None
        assert isinstance(app.state, dict)
        assert app.template_engine is None
        assert app.db_connection is None

    def test_application_init_default_config(self):
        """Test application with default config"""
        app = Application()
        assert isinstance(app.config, AppConfig)

    @pytest.mark.asyncio
    async def test_startup_shutdown(self, app):
        """Test application startup and shutdown"""
        # Mock database connection
        with patch('pydance.core.database.DatabaseConnection') as mock_db:
            mock_instance = AsyncMock()
            mock_db.get_instance.return_value = mock_instance

            await app.startup()
            await app.shutdown()

            mock_instance.connect.assert_called_once()
            mock_instance.disconnect.assert_called_once()

    def test_route_decorator(self, app):
        """Test route decorator"""
        @app.route('/test', methods=['GET', 'POST'])
        async def test_handler(request):
            return {'message': 'test'}

        # Check that route was added
        assert len(app.router.routes) == 1
        route = app.router.routes[0]
        assert route.path == '/test'
        assert route.methods == ['GET', 'POST']

    def test_websocket_route_decorator(self, app):
        """Test WebSocket route decorator"""
        @app.websocket_route('/ws')
        async def ws_handler(websocket):
            await websocket.accept()

        # Check that WebSocket route was added
        assert len(app.router.websocket_routes) == 1
        route = app.router.websocket_routes[0]
        assert route.path == '/ws'

    def test_middleware_addition(self, app):
        """Test middleware addition"""
        mock_middleware = MagicMock()
        app.add_middleware(mock_middleware)
        assert len(app.middleware_manager.middleware) == 2  # + default middleware

    def test_exception_handler(self, app):
        """Test exception handler registration"""
        @app.exception_handler(ValueError)
        async def handle_value_error(exc):
            return {'error': 'value error'}

        assert ValueError in app._exception_handlers
        assert app._exception_handlers[ValueError] == handle_value_error

    @pytest.mark.asyncio
    async def test_handle_http_request(self, app):
        """Test HTTP request handling"""
        # Mock request and response
        mock_scope = {
            'type': 'http',
            'method': 'GET',
            'path': '/test',
            'headers': []
        }
        mock_receive = AsyncMock()
        mock_send = AsyncMock()

        # Add a test route
        @app.route('/test')
        async def test_handler(request):
            return {'message': 'test'}

        # Mock the response
        with patch('pydance.core.response.Response') as mock_response_class:
            mock_response = MagicMock()
            mock_response_class.return_value = mock_response
            mock_response.__call__ = AsyncMock()

            await app(mock_scope, mock_receive, mock_send)

            mock_response.__call__.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_websocket_request(self, app):
        """Test WebSocket request handling"""
        mock_scope = {
            'type': 'websocket',
            'path': '/ws',
            'headers': []
        }
        mock_receive = AsyncMock()
        mock_send = AsyncMock()

        # Add a test WebSocket route
        @app.websocket_route('/ws')
        async def ws_handler(websocket):
            await websocket.accept()

        # Mock WebSocket
        with patch('pydance.core.websocket.WebSocket') as mock_ws_class:
            mock_ws = AsyncMock()
            mock_ws_class.return_value = mock_ws

            await app(mock_scope, mock_receive, mock_send)

            mock_ws_class.assert_called_once()

    def test_debug_property(self, config):
        """Test debug property"""
        config.debug = True
        app = Application(config)
        assert app.debug is True

        config.debug = False
        app = Application(config)
        assert app.debug is False

    def test_mount_subapp(self, app):
        """Test mounting sub-application"""
        subapp = Application()
        app.mount('/api', subapp)

        # Check that subapp was mounted
        assert '/api' in app.router.mounted_routers
        assert app.router.mounted_routers['/api'] == subapp.router

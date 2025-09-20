"""
Unit tests for Pydance Routing
"""
import pytest

from pydance.core.routing import Router, Route, WebSocketRoute


class TestRoute:
    """Test Route class"""

    def test_route_creation(self):
        """Test route creation"""
        def handler(request):
            return {'message': 'test'}

        route = Route('/test', handler, ['GET', 'POST'])
        assert route.path == '/test'
        assert route.handler == handler
        assert route.methods == ['GET', 'POST']
        assert route.pattern is not None

    def test_route_pattern_compilation(self):
        """Test route pattern compilation"""
        route = Route('/users/{id}', lambda r: None)
        assert route.pattern is not None

        # Test matching
        match = route.match('/users/123')
        assert match == {'id': '123'}

        # Test no match
        match = route.match('/users')
        assert match is None

    def test_route_with_multiple_params(self):
        """Test route with multiple parameters"""
        route = Route('/users/{user_id}/posts/{post_id}', lambda r: None)
        match = route.match('/users/123/posts/456')
        assert match == {'user_id': '123', 'post_id': '456'}


class TestWebSocketRoute:
    """Test WebSocketRoute class"""

    def test_websocket_route_creation(self):
        """Test WebSocket route creation"""
        def handler(ws):
            pass

        route = WebSocketRoute('/ws', handler)
        assert route.path == '/ws'
        assert route.handler == handler
        assert route.pattern is not None

    def test_websocket_route_matching(self):
        """Test WebSocket route matching"""
        route = WebSocketRoute('/ws/{room}', lambda ws: None)
        match = route.match('/ws/lobby')
        assert match == {'room': 'lobby'}


class TestRouter:
    """Test Router class"""

    def test_router_creation(self):
        """Test router creation"""
        router = Router()
        assert router.routes == []
        assert router.websocket_routes == []
        assert router.mounted_routers == {}

    def test_add_route(self):
        """Test adding routes"""
        router = Router()
        def handler(request):
            return {'message': 'test'}

        router.add_route('/test', handler, ['GET'])
        assert len(router.routes) == 1
        assert router.routes[0].path == '/test'

    def test_add_websocket_route(self):
        """Test adding WebSocket routes"""
        router = Router()
        def handler(ws):
            pass

        router.add_websocket_route('/ws', handler)
        assert len(router.websocket_routes) == 1
        assert router.websocket_routes[0].path == '/ws'

    def test_mount_router(self):
        """Test mounting sub-router"""
        router = Router()
        sub_router = Router()

        router.mount('/api', sub_router)
        assert '/api' in router.mounted_routers
        assert router.mounted_routers['/api'] == sub_router

    def test_find_route(self):
        """Test route finding"""
        router = Router()

        def handler(request):
            return {'message': 'test'}

        router.add_route('/test', handler, ['GET'])

        route, params = router.find_route('/test', 'GET')
        assert route is not None
        assert route.path == '/test'
        assert params == {}

    def test_find_route_with_params(self):
        """Test route finding with parameters"""
        router = Router()

        def handler(request):
            return {'message': 'test'}

        router.add_route('/users/{id}', handler, ['GET'])

        route, params = router.find_route('/users/123', 'GET')
        assert route is not None
        assert params == {'id': '123'}

    def test_find_route_method_not_allowed(self):
        """Test route finding with wrong method"""
        router = Router()

        def handler(request):
            return {'message': 'test'}

        router.add_route('/test', handler, ['POST'])

        route, params = router.find_route('/test', 'GET')
        assert route is None
        assert params is None

    def test_find_websocket_route(self):
        """Test WebSocket route finding"""
        router = Router()

        def handler(ws):
            pass

        router.add_websocket_route('/ws', handler)

        route, params = router.find_websocket_route('/ws')
        assert route is not None
        assert route.path == '/ws'
        assert params == {}

    def test_mounted_route_finding(self):
        """Test route finding in mounted routers"""
        router = Router()
        sub_router = Router()

        def handler(request):
            return {'message': 'test'}

        sub_router.add_route('/users', handler, ['GET'])
        router.mount('/api', sub_router)

        route, params = router.find_route('/api/users', 'GET')
        assert route is not None
        assert route.path == '/users'

    def test_route_not_found(self):
        """Test route not found"""
        router = Router()

        route, params = router.find_route('/nonexistent', 'GET')
        assert route is None
        assert params is None

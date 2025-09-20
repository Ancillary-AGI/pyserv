"""
HTTP-related test fixtures and mocks
"""
from typing import AsyncGenerator

import pytest


@pytest.fixture
async def client(app):
    """Test client for making HTTP requests."""
    from httpx import AsyncClient

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        yield client


@pytest.fixture
def mock_request():
    """Mock request object."""
    from pydance.core.http.request import Request

    class MockRequest:
        def __init__(self, method="GET", path="/", headers=None, query_params=None):
            self.method = method
            self.path = path
            self.headers = headers or {}
            self.query_params = query_params or {}
            self.state = {}
            self.app = None

    return MockRequest


@pytest.fixture
def mock_response():
    """Mock response object."""
    from pydance.core.http.response import Response

    class MockResponse:
        def __init__(self, content="", status_code=200, headers=None):
            self.content = content
            self.status_code = status_code
            self.headers = headers or {}

    return MockResponse


@pytest.fixture
def mock_websocket():
    """Mock WebSocket object."""
    from pydance.core.websocket import WebSocket

    class MockWebSocket:
        def __init__(self, path="/", headers=None):
            self.path = path
            self.headers = headers or {}
            self.state = {}
            self.app = None
            self.connected = True
            self.path_params = {}

        async def accept(self):
            pass

        async def send_json(self, data):
            pass

        async def receive_json(self):
            return {"message": "test"}

        async def close(self, code=1000, reason=""):
            pass

    return MockWebSocket

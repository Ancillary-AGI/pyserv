"""
Pydance Test Configuration and Fixtures
"""
import asyncio
import os
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator

import pytest
from faker import Faker

from pydance import Application, AppConfig
from pydance.database.database import DatabaseConnection
from pydance.database.config import DatabaseConfig
from pydance.models.base import BaseModel


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def faker():
    """Faker instance for generating test data."""
    return Faker()


@pytest.fixture
def temp_dir():
    """Temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def config():
    """Test application configuration."""
    return AppConfig(
        debug=True,
        secret_key="test-secret-key",
        host="127.0.0.1",
        port=8000,
        database_url="sqlite:///:memory:",
    )


@pytest.fixture
async def app(config) -> AsyncGenerator[Application, None]:
    """Test application instance."""
    app = Application(config)
    yield app


@pytest.fixture
async def db_connection():
    """Test database connection."""
    config = DatabaseConfig("sqlite:///:memory:")
    connection = DatabaseConnection.get_instance(config)
    await connection.connect()
    yield connection
    await connection.disconnect()


@pytest.fixture
def test_model():
    """Test model class."""

    class TestModel(BaseModel):
        name: str
        age: int
        email: str

        class Meta:
            collection = "test_models"

    return TestModel


@pytest.fixture
async def client(app):
    """Test client for making HTTP requests."""
    from httpx import AsyncClient

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        yield client


@pytest.fixture
def mock_request():
    """Mock request object."""
    from pydance.core.request import Request

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
    from pydance.core.response import Response

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


@pytest.fixture(autouse=True)
def cleanup_test_artifacts():
    """Clean up test artifacts after each test."""
    yield
    # Clean up any test files or artifacts
    for pattern in ["*.db", "*.log", ".pydance.pid"]:
        for file in Path(".").glob(pattern):
            if file.exists():
                file.unlink()


# Custom markers
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "system: System tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "load: Load tests")
    config.addinivalue_line("markers", "stress: Stress tests")
    config.addinivalue_line("markers", "security: Security tests")
    config.addinivalue_line("markers", "regression: Regression tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "database: Database-related tests")

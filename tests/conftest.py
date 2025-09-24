"""
Pyserv  Test Configuration and Fixtures
"""
import asyncio
import os
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator

import pytest
from faker import Faker

from pyserv import Application, AppConfig


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


@pytest.fixture(autouse=True)
def cleanup_test_artifacts():
    """Clean up test artifacts after each test."""
    yield
    # Clean up any test files or artifacts
    for pattern in ["*.db", "*.log", ".pyserv .pid"]:
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


# Register fixture plugins
pytest_plugins = [
    "tests.fixtures.database",
    "tests.fixtures.http",
]





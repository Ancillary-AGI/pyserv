"""
Database-related test fixtures
"""
from typing import AsyncGenerator

import pytest

from pydance.database.database import DatabaseConnection
from pydance.database.config import DatabaseConfig
from pydance.models.base import BaseModel


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

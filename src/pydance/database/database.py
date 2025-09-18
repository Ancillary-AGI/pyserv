from contextlib import asynccontextmanager
from typing import AsyncGenerator, Any, Dict
from .config import DatabaseConfig
from .backends import get_backend, DatabaseBackend

class DatabaseConnection:
    """Database connection manager with support for multiple database types"""

    _instances = {}

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.backend: DatabaseBackend = get_backend(config)

    @classmethod
    def get_instance(cls, config: DatabaseConfig) -> 'DatabaseConnection':
        """Get or create a database connection instance"""
        key = config.database_url
        if key not in cls._instances:
            cls._instances[key] = cls(config)
        return cls._instances[key]

    async def connect(self):
        """Establish database connection"""
        await self.backend.connect()

    async def disconnect(self):
        """Close database connections"""
        await self.backend.disconnect()

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[Any, None]:
        """Get a database connection"""
        async with self.backend.get_connection() as conn:
            yield conn

    async def execute(self, query: str, params: tuple = None) -> Any:
        """Execute a query using the backend"""
        return await self.backend.execute(query, params)

    async def create_table(self, model_class: Any) -> None:
        """Create a table for the given model"""
        await self.backend.create_table(model_class)

    def get_param_placeholder(self, index: int) -> str:
        """Get parameter placeholder for this database type"""
        return self.backend.get_param_placeholder(index)

    def get_sql_type(self, field: Any) -> str:
        """Get SQL type for a field"""
        return self.backend.get_sql_type(field)

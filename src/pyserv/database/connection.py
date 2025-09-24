"""
Database connection module for Pyserv  Framework.

This module provides the base DatabaseConnection class that handles
database connections with support for multiple backends.
"""

import asyncio
import logging
from typing import Any, Optional, Dict, AsyncGenerator
from contextlib import asynccontextmanager
from abc import ABC, abstractmethod

from pyserv.database.config import DatabaseConfig


class DatabaseConnection(ABC):
    """
    Abstract base class for database connections.

    This class provides the interface for database connections and
    implements common functionality like connection pooling and
    singleton pattern.
    """

    _instances: Dict[str, 'DatabaseConnection'] = {}

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._connection = None
        self._connected = False
        self.logger = logging.getLogger(f"{self.__class__.__name__}")

    @classmethod
    def get_instance(cls, config: DatabaseConfig) -> 'DatabaseConnection':
        """Get or create a singleton instance for the given config."""
        key = str(config.database_url)
        if key not in cls._instances:
            # Determine which backend to use
            if 'sqlite' in config.database_url.lower():
                cls._instances[key] = SQLiteConnection(config)
            elif 'postgresql' in config.database_url.lower():
                cls._instances[key] = PostgreSQLConnection(config)
            elif 'mysql' in config.database_url.lower():
                cls._instances[key] = MySQLConnection(config)
            elif 'mongodb' in config.database_url.lower():
                cls._instances[key] = MongoDBConnection(config)
            else:
                raise ValueError(f"Unsupported database URL: {config.database_url}")
        return cls._instances[key]

    @abstractmethod
    async def connect(self) -> None:
        """Establish database connection."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close database connection."""
        pass

    @abstractmethod
    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[Any, None]:
        """Get a database connection context manager."""
        pass

    @abstractmethod
    async def execute(self, query: str, params: tuple = None) -> Any:
        """Execute a query."""
        pass

    @property
    def is_connected(self) -> bool:
        """Check if connection is established."""
        return self._connected


class SQLiteConnection(DatabaseConnection):
    """SQLite database connection."""

    async def connect(self) -> None:
        """Connect to SQLite database."""
        try:
            import aiosqlite
            self._connection = await aiosqlite.connect(self.config.database_url.replace('sqlite://', ''))
            self._connected = True
            self.logger.info("Connected to SQLite database")
        except ImportError:
            raise ImportError("aiosqlite is required for SQLite support")

    async def disconnect(self) -> None:
        """Disconnect from SQLite database."""
        if self._connection:
            await self._connection.close()
            self._connection = None
            self._connected = False
            self.logger.info("Disconnected from SQLite database")

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[Any, None]:
        """Get SQLite connection."""
        if not self._connected:
            await self.connect()
        yield self._connection

    async def execute(self, query: str, params: tuple = None) -> Any:
        """Execute SQLite query."""
        async with self.get_connection() as conn:
            cursor = await conn.execute(query, params or ())
            await conn.commit()
            if query.strip().upper().startswith('SELECT'):
                return await cursor.fetchall()
            return cursor.rowcount


class PostgreSQLConnection(DatabaseConnection):
    """PostgreSQL database connection."""

    async def connect(self) -> None:
        """Connect to PostgreSQL database."""
        try:
            import asyncpg
            self._connection = await asyncpg.connect(self.config.database_url)
            self._connected = True
            self.logger.info("Connected to PostgreSQL database")
        except ImportError:
            raise ImportError("asyncpg is required for PostgreSQL support")

    async def disconnect(self) -> None:
        """Disconnect from PostgreSQL database."""
        if self._connection:
            await self._connection.close()
            self._connection = None
            self._connected = False
            self.logger.info("Disconnected from PostgreSQL database")

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[Any, None]:
        """Get PostgreSQL connection."""
        if not self._connected:
            await self.connect()
        yield self._connection

    async def execute(self, query: str, params: tuple = None) -> Any:
        """Execute PostgreSQL query."""
        async with self.get_connection() as conn:
            if params:
                result = await conn.fetch(query, *params)
            else:
                result = await conn.fetch(query)
            return result


class MySQLConnection(DatabaseConnection):
    """MySQL database connection."""

    async def connect(self) -> None:
        """Connect to MySQL database."""
        try:
            import aiomysql
            # Parse URL: mysql://user:pass@host:port/db
            url = self.config.database_url.replace('mysql://', '')
            if '@' in url:
                auth, rest = url.split('@', 1)
                user, password = auth.split(':', 1)
                if ':' in rest:
                    host_port, db = rest.split('/', 1)
                    host, port = host_port.split(':', 1)
                    port = int(port)
                else:
                    host = rest.split('/')[0]
                    port = 3306
                    db = rest.split('/')[1] if '/' in rest else ''
            else:
                raise ValueError("Invalid MySQL URL format")

            self._connection = await aiomysql.connect(
                host=host, port=port, user=user, password=password, db=db
            )
            self._connected = True
            self.logger.info("Connected to MySQL database")
        except ImportError:
            raise ImportError("aiomysql is required for MySQL support")

    async def disconnect(self) -> None:
        """Disconnect from MySQL database."""
        if self._connection:
            self._connection.close()
            self._connection = None
            self._connected = False
            self.logger.info("Disconnected from MySQL database")

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[Any, None]:
        """Get MySQL connection."""
        if not self._connected:
            await self.connect()
        yield self._connection

    async def execute(self, query: str, params: tuple = None) -> Any:
        """Execute MySQL query."""
        async with self.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(query, params or ())
                await conn.commit()
                if query.strip().upper().startswith('SELECT'):
                    return await cursor.fetchall()
                return cursor.rowcount


class MongoDBConnection(DatabaseConnection):
    """MongoDB database connection."""

    async def connect(self) -> None:
        """Connect to MongoDB database."""
        try:
            from motor.motor_asyncio import AsyncIOMotorClient
            self._connection = AsyncIOMotorClient(self.config.database_url)
            # Test connection
            await self._connection.admin.command('ping')
            self._connected = True
            self.logger.info("Connected to MongoDB database")
        except ImportError:
            raise ImportError("motor is required for MongoDB support")

    async def disconnect(self) -> None:
        """Disconnect from MongoDB database."""
        if self._connection:
            self._connection.close()
            self._connection = None
            self._connected = False
            self.logger.info("Disconnected from MongoDB database")

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[Any, None]:
        """Get MongoDB connection."""
        if not self._connected:
            await self.connect()
        yield self._connection

    async def execute(self, query: str, params: tuple = None) -> Any:
        """Execute MongoDB command."""
        async with self.get_connection() as conn:
            # For MongoDB, query is treated as a command
            db = conn.get_default_database()
            if params and isinstance(params, dict):
                return await db.command(query, **params)
            else:
                return await db.command(query)

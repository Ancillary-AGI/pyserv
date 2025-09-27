"""
Database connections module for Pyserv Framework.

This module provides the base DatabaseConnection class that handles
database connections with support for multiple database types and pooling.
"""

import asyncio
import logging
import time
from typing import Any, Dict, AsyncGenerator, Optional, List
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

from pyserv.database.config import DatabaseConfig


@dataclass
class PoolConfig:
    """Configuration for database connection pool"""
    min_size: int = 5
    max_size: int = 20
    max_idle_time: int = 300  # seconds
    max_lifetime: int = 3600  # seconds
    acquire_timeout: int = 30  # seconds
    retry_attempts: int = 3
    retry_delay: float = 0.1  # seconds
    health_check_interval: int = 60  # seconds
    prepared_statement_cache_size: int = 100


@dataclass
class ConnectionStats:
    """Connection pool statistics"""
    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    pending_acquires: int = 0
    total_acquires: int = 0
    total_releases: int = 0
    total_timeouts: int = 0
    total_errors: int = 0
    created_at: float = field(default_factory=time.time)


class PoolConnection:
    """Wrapper for pooled database connections"""

    def __init__(self, connection: Any, pool: 'DatabaseConnection', created_at: float):
        self.connection = connection
        self.pool = pool
        self.created_at = created_at
        self.last_used = created_at
        self.in_use = False
        self.prepared_statements: Dict[str, Any] = {}

    async def execute(self, query: str, params: tuple = None) -> Any:
        """Execute query with connection"""
        self.last_used = time.time()
        try:
            if hasattr(self.connection, 'execute'):
                return await self.connection.execute(query, params or ())
            else:
                # MongoDB style
                return await self.connection.command(query, params or {})
        except Exception as e:
            self.pool._stats.total_errors += 1
            raise e

    async def execute_raw(self, query: str, params: tuple = None) -> Any:
        """Execute raw query with cursor access"""
        self.last_used = time.time()
        try:
            if hasattr(self.connection, 'execute_raw'):
                return await self.connection.execute_raw(query, params or ())
            else:
                # Fallback to regular execute for backends without raw support
                return await self.execute(query, params)
        except Exception as e:
            self.pool._stats.total_errors += 1
            raise e

    async def get_cursor(self) -> Any:
        """Get raw database cursor (Django-style API)"""
        self.last_used = time.time()
        try:
            if hasattr(self.connection, 'cursor'):
                return self.connection.cursor()
            else:
                # For backends without direct cursor access
                raise NotImplementedError("Direct cursor access not available for this backend")
        except Exception as e:
            self.pool._stats.total_errors += 1
            raise e

    async def begin_transaction(self) -> Any:
        """Begin transaction with connection"""
        self.last_used = time.time()
        try:
            if hasattr(self.connection, 'begin_transaction'):
                return await self.connection.begin_transaction()
            else:
                raise NotImplementedError("Transaction support not available for this backend")
        except Exception as e:
            self.pool._stats.total_errors += 1
            raise e

    async def commit_transaction(self, transaction: Any) -> None:
        """Commit transaction"""
        try:
            if hasattr(self.connection, 'commit_transaction'):
                await self.connection.commit_transaction(transaction)
            else:
                raise NotImplementedError("Transaction support not available for this backend")
        except Exception as e:
            self.pool._stats.total_errors += 1
            raise e

    async def rollback_transaction(self, transaction: Any) -> None:
        """Rollback transaction"""
        try:
            if hasattr(self.connection, 'rollback_transaction'):
                await self.connection.rollback_transaction(transaction)
            else:
                raise NotImplementedError("Transaction support not available for this backend")
        except Exception as e:
            self.pool._stats.total_errors += 1
            raise e

    async def execute_in_transaction(self, query: str, params: tuple = None) -> Any:
        """Execute query within transaction context"""
        self.last_used = time.time()
        try:
            if hasattr(self.connection, 'execute_in_transaction'):
                return await self.connection.execute_in_transaction(query, params or ())
            else:
                # Fallback to manual transaction handling
                transaction = await self.begin_transaction()
                try:
                    result = await self.execute(query, params)
                    await self.commit_transaction(transaction)
                    return result
                except Exception:
                    await self.rollback_transaction(transaction)
                    raise
        except Exception as e:
            self.pool._stats.total_errors += 1
            raise e

    async def close(self):
        """Close the connection"""
        if hasattr(self.connection, 'close'):
            await self.connection.close()

    def is_expired(self, max_lifetime: int) -> bool:
        """Check if connection has expired"""
        return (time.time() - self.created_at) > max_lifetime

    def is_idle_timeout(self, max_idle_time: int) -> bool:
        """Check if connection has been idle too long"""
        return (time.time() - self.last_used) > max_idle_time


class DatabaseConnection(ABC):
    """
    Abstract base class for database connections with pooling support.

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

        # Pooling attributes
        self.pool_config = PoolConfig()
        self._pool: List[PoolConnection] = []
        self._available: List[PoolConnection] = []
        self._waiting: List[asyncio.Future] = []
        self._stats = ConnectionStats()
        self._lock = asyncio.Lock()
        self._health_check_task: Optional[asyncio.Task] = None

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

    @abstractmethod
    async def execute_raw(self, query: str, params: tuple = None) -> Any:
        """Execute a raw query and return cursor/results for advanced usage."""
        pass

    @abstractmethod
    async def begin_transaction(self) -> Any:
        """Begin a database transaction."""
        pass

    @abstractmethod
    async def commit_transaction(self, transaction: Any) -> None:
        """Commit a database transaction."""
        pass

    @abstractmethod
    async def rollback_transaction(self, transaction: Any) -> None:
        """Rollback a database transaction."""
        pass

    @abstractmethod
    async def execute_in_transaction(self, query: str, params: tuple = None) -> Any:
        """Execute a query within a transaction context."""
        pass

    # DatabaseBackend Protocol methods - all must be implemented
    @abstractmethod
    async def create_table(self, model_class: Any) -> None:
        """Create a table for the given model"""
        pass

    @abstractmethod
    async def get_param_placeholder(self, index: int) -> str:
        """Get parameter placeholder for this database type"""
        pass

    @abstractmethod
    def get_sql_type(self, field: Any) -> str:
        """Get SQL type for a field"""
        pass

    @abstractmethod
    async def insert_one(self, model_class: Any, data: Dict[str, Any]) -> Any:
        """Insert a single record"""
        pass

    @abstractmethod
    async def update_one(self, model_class: Any, filters: Dict[str, Any], data: Dict[str, Any]) -> bool:
        """Update a single record"""
        pass

    @abstractmethod
    async def delete_one(self, model_class: Any, filters: Dict[str, Any]) -> bool:
        """Delete a single record"""
        pass

    @abstractmethod
    async def find_one(self, model_class: Any, filters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find a single record"""
        pass

    @abstractmethod
    async def find_many(self, model_class: Any, filters: Dict[str, Any], limit: Optional[int] = None,
                       offset: Optional[int] = None, sort: Optional[List[tuple]] = None) -> List[Dict[str, Any]]:
        """Find multiple records"""
        pass

    @abstractmethod
    async def count(self, model_class: Any, filters: Dict[str, Any]) -> int:
        """Count records matching filters"""
        pass

    @abstractmethod
    async def aggregate(self, model_class: Any, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Perform aggregation operations"""
        pass

    @abstractmethod
    async def execute_query_builder(self, model_class: Any, query_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute a complex query built by QueryBuilder"""
        pass

    @abstractmethod
    async def create_migrations_table(self) -> None:
        """Create the migrations tracking table/collection"""
        pass

    @abstractmethod
    async def insert_migration_record(self, model_name: str, version: int, schema_definition: dict, operations: dict) -> None:
        """Insert a migration record"""
        pass

    @abstractmethod
    async def get_applied_migrations(self) -> Dict[str, int]:
        """Get all applied migrations"""
        pass

    @abstractmethod
    async def delete_migration_record(self, model_name: str, version: int) -> None:
        """Delete a migration record"""
        pass

    @abstractmethod
    async def drop_table(self, table_name: str) -> None:
        """Drop a table/collection"""
        pass

    @abstractmethod
    async def add_column(self, table_name: str, column_name: str, column_definition: str) -> None:
        """Add a column to a table"""
        pass

    @abstractmethod
    async def drop_column(self, table_name: str, column_name: str) -> None:
        """Drop a column from a table"""
        pass

    @abstractmethod
    async def modify_column(self, table_name: str, column_name: str, column_definition: str) -> None:
        """Modify a column in a table"""
        pass

    @abstractmethod
    async def create_index(self, table_name: str, index_name: str, columns: List[str]) -> None:
        """Create an index on a table"""
        pass

    @abstractmethod
    async def drop_index(self, table_name: str, index_name: str) -> None:
        """Drop an index from a table"""
        pass

    @abstractmethod
    async def add_field(self, model_name: str, field_name: str, field: Any) -> None:
        """Add a field to an existing model/table"""
        pass

    @abstractmethod
    async def remove_field(self, model_name: str, field_name: str) -> None:
        """Remove a field from an existing model/table"""
        pass

    @abstractmethod
    async def alter_field(self, model_name: str, field_name: str, field: Any) -> None:
        """Alter an existing field in a model/table"""
        pass

    @abstractmethod
    def get_type_mappings(self) -> Dict[Any, str]:
        """Get database-specific type mappings for fields"""
        pass

    @abstractmethod
    def format_default_value(self, value: Any) -> str:
        """Format default value for this database"""
        pass

    @abstractmethod
    def format_foreign_key(self, foreign_key: str) -> str:
        """Format foreign key constraint for this database"""
        pass

    @abstractmethod
    async def _create_connection(self) -> Any:
        """Create a new database connection for pooling"""
        pass

    # Pooling methods
    async def acquire(self) -> PoolConnection:
        """Acquire a connection from the pool"""
        async with self._lock:
            self._stats.pending_acquires += 1

            # Try to get available connection
            if self._available:
                conn = self._available.pop()
                conn.in_use = True
                self._stats.active_connections += 1
                self._stats.pending_acquires -= 1
                self._stats.total_acquires += 1
                return conn

            # Check if we can create new connection
            if len(self._pool) < self.pool_config.max_size:
                try:
                    raw_conn = await self._create_connection()
                    conn = PoolConnection(raw_conn, self, time.time())
                    conn.in_use = True
                    self._pool.append(conn)
                    self._stats.total_connections += 1
                    self._stats.active_connections += 1
                    self._stats.pending_acquires -= 1
                    self._stats.total_acquires += 1
                    return conn
                except Exception as e:
                    self.logger.error(f"Failed to create connection: {e}")
                    self._stats.total_errors += 1
                    self._stats.pending_acquires -= 1
                    raise e

            # Wait for available connection
            future = asyncio.Future()
            self._waiting.append(future)

        try:
            conn = await asyncio.wait_for(
                future, timeout=self.pool_config.acquire_timeout
            )
            return conn
        except asyncio.TimeoutError:
            async with self._lock:
                self._stats.pending_acquires -= 1
                self._stats.total_timeouts += 1
            raise asyncio.TimeoutError("Connection acquire timeout")

    async def release(self, connection: PoolConnection):
        """Release a connection back to the pool"""
        async with self._lock:
            connection.in_use = False
            self._stats.active_connections -= 1
            self._stats.total_releases += 1

            # Check if connection is still valid
            if (connection.is_expired(self.pool_config.max_lifetime) or
                connection.is_idle_timeout(self.pool_config.max_idle_time)):
                # Remove expired connection
                await connection.close()
                self._pool.remove(connection)
                self._stats.total_connections -= 1
                return

            # Return to available pool
            self._available.append(connection)
            self._stats.idle_connections += 1

            # Wake up waiting acquirers
            if self._waiting:
                future = self._waiting.pop(0)
                if not future.done():
                    conn = self._available.pop()
                    conn.in_use = True
                    self._stats.active_connections += 1
                    self._stats.idle_connections -= 1
                    future.set_result(conn)

    @asynccontextmanager
    async def get_pooled_connection(self) -> AsyncGenerator[PoolConnection, None]:
        """Context manager for getting pooled connections"""
        conn = await self.acquire()
        try:
            yield conn
        finally:
            await self.release(conn)

    async def start_health_checks(self):
        """Start periodic health checks"""
        if self._health_check_task:
            return

        self._health_check_task = asyncio.create_task(self._health_check_loop())

    async def stop_health_checks(self):
        """Stop periodic health checks"""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None

    async def _health_check_loop(self):
        """Periodic health check loop"""
        while True:
            try:
                await asyncio.sleep(self.pool_config.health_check_interval)
                await self._perform_health_checks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Health check error: {e}")

    async def _perform_health_checks(self):
        """Perform health checks on connections"""
        async with self._lock:
            expired = []
            for conn in self._pool:
                if conn.is_expired(self.pool_config.max_lifetime):
                    expired.append(conn)

            # Remove expired connections
            for conn in expired:
                if not conn.in_use:
                    await conn.close()
                    self._pool.remove(conn)
                    self._stats.total_connections -= 1
                    if conn in self._available:
                        self._available.remove(conn)
                        self._stats.idle_connections -= 1

    async def close_pool(self):
        """Close all connections in the pool"""
        await self.stop_health_checks()

        async with self._lock:
            for conn in self._pool:
                await conn.close()
            self._pool.clear()
            self._available.clear()
            self._stats = ConnectionStats()

    def get_pool_stats(self) -> ConnectionStats:
        """Get pool statistics"""
        return self._stats

    @property
    def is_connected(self) -> bool:
        """Check if connection is established."""
        return self._connected


# Import concrete implementations
from .sqlite_connection import SQLiteConnection
from .postgres_connection import PostgreSQLConnection
from .mysql_connection import MySQLConnection
from .mongodb_connection import MongoDBConnection


__all__ = [
    'DatabaseConnection',
    'SQLiteConnection',
    'PostgreSQLConnection',
    'MySQLConnection',
    'MongoDBConnection'
]

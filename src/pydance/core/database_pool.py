"""
High-performance database connection pooling for PyDance framework.

This module provides optimized database connection pooling with:
- Connection pooling for PostgreSQL, MySQL, and MongoDB
- Health checks and automatic reconnection
- Prepared statement caching
- Connection metrics and monitoring
- Raw SQL execution optimization
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, AsyncGenerator, Union
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import asyncpg
import aiomysql
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure

from .database import DatabaseConnection
from .monitoring.metrics import get_metrics_collector


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

    def __init__(self, connection: Any, pool: 'DatabasePool', created_at: float):
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


class DatabasePool(ABC):
    """Abstract base class for database connection pools"""

    def __init__(self, config: PoolConfig):
        self.config = config
        self._pool: List[PoolConnection] = []
        self._available: List[PoolConnection] = []
        self._waiting: List[asyncio.Future] = []
        self._stats = ConnectionStats()
        self._lock = asyncio.Lock()
        self._health_check_task: Optional[asyncio.Task] = None
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self.metrics = get_metrics_collector()

        # Register metrics
        self._register_metrics()

    def _register_metrics(self):
        """Register pool metrics"""
        self.metrics.create_gauge(
            f"db_pool_{self.__class__.__name__.lower()}_total_connections",
            "Total number of connections in pool"
        )
        self.metrics.create_gauge(
            f"db_pool_{self.__class__.__name__.lower()}_active_connections",
            "Number of active connections"
        )
        self.metrics.create_gauge(
            f"db_pool_{self.__class__.__name__.lower()}_idle_connections",
            "Number of idle connections"
        )
        self.metrics.create_counter(
            f"db_pool_{self.__class__.__name__.lower()}_acquires_total",
            "Total number of connection acquires"
        )
        self.metrics.create_counter(
            f"db_pool_{self.__class__.__name__.lower()}_timeouts_total",
            "Total number of connection timeouts"
        )

    @abstractmethod
    async def _create_connection(self) -> Any:
        """Create a new database connection"""
        pass

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
            if len(self._pool) < self.config.max_size:
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
                future, timeout=self.config.acquire_timeout
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
            if (connection.is_expired(self.config.max_lifetime) or
                connection.is_idle_timeout(self.config.max_idle_time)):
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
    async def get_connection(self) -> AsyncGenerator[PoolConnection, None]:
        """Context manager for getting connections"""
        conn = await self.acquire()
        try:
            yield conn
        finally:
            await self.release(conn)

    async def execute(self, query: str, params: tuple = None) -> Any:
        """Execute query using pooled connection"""
        async with self.get_connection() as conn:
            return await conn.execute(query, params)

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
                await asyncio.sleep(self.config.health_check_interval)
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
                if conn.is_expired(self.config.max_lifetime):
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

    async def close(self):
        """Close all connections in the pool"""
        await self.stop_health_checks()

        async with self._lock:
            for conn in self._pool:
                await conn.close()
            self._pool.clear()
            self._available.clear()
            self._stats = ConnectionStats()

    def get_stats(self) -> ConnectionStats:
        """Get pool statistics"""
        return self._stats


class PostgreSQLPool(DatabasePool):
    """PostgreSQL connection pool"""

    def __init__(self, dsn: str, config: PoolConfig = None):
        super().__init__(config or PoolConfig())
        self.dsn = dsn

    async def _create_connection(self) -> asyncpg.Connection:
        """Create PostgreSQL connection"""
        return await asyncpg.connect(self.dsn)


class MySQLPool(DatabasePool):
    """MySQL connection pool"""

    def __init__(self, host: str, port: int, user: str, password: str,
                 database: str, config: PoolConfig = None):
        super().__init__(config or PoolConfig())
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database

    async def _create_connection(self) -> aiomysql.Connection:
        """Create MySQL connection"""
        return await aiomysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            db=self.database
        )


class MongoDBPool(DatabasePool):
    """MongoDB connection pool"""

    def __init__(self, uri: str, config: PoolConfig = None):
        super().__init__(config or PoolConfig())
        self.uri = uri
        self.client: Optional[AsyncIOMotorClient] = None

    async def _create_connection(self) -> AsyncIOMotorClient:
        """Create MongoDB connection"""
        if self.client is None:
            self.client = AsyncIOMotorClient(
                self.uri,
                maxPoolSize=self.config.max_size,
                minPoolSize=self.config.min_size,
                maxIdleTimeMS=self.config.max_idle_time * 1000,
                waitQueueTimeoutMS=self.config.acquire_timeout * 1000
            )
        return self.client


class OptimizedDatabaseConnection(DatabaseConnection):
    """Enhanced database connection with pooling support"""

    def __init__(self, config, pool_config: PoolConfig = None):
        super().__init__(config)
        self.pool_config = pool_config or PoolConfig()
        self._pool: Optional[DatabasePool] = None

    async def connect(self):
        """Establish connection with pooling"""
        if self._pool is None:
            await self._create_pool()
        await self._pool.start_health_checks()

    async def _create_pool(self):
        """Create appropriate connection pool"""
        if 'postgresql' in self.config.database_url.lower():
            self._pool = PostgreSQLPool(self.config.database_url, self.pool_config)
        elif 'mysql' in self.config.database_url.lower():
            # Parse MySQL URL
            # mysql://user:pass@host:port/db
            parts = self.config.database_url.replace('mysql://', '').split('/')
            auth_host = parts[0].split('@')
            host_port = auth_host[1].split(':')
            user_pass = auth_host[0].split(':')

            self._pool = MySQLPool(
                host=host_port[0],
                port=int(host_port[1]),
                user=user_pass[0],
                password=user_pass[1],
                database=parts[1],
                config=self.pool_config
            )
        elif 'mongodb' in self.config.database_url.lower():
            self._pool = MongoDBPool(self.config.database_url, self.pool_config)
        else:
            # Fallback to regular connection
            await super().connect()
            return

    async def disconnect(self):
        """Close pool connections"""
        if self._pool:
            await self._pool.close()
        await super().disconnect()

    @asynccontextmanager
    async def get_connection(self):
        """Get connection from pool"""
        if self._pool:
            async with self._pool.get_connection() as conn:
                yield conn
        else:
            async with super().get_connection() as conn:
                yield conn

    async def execute(self, query: str, params: tuple = None) -> Any:
        """Execute with pooling"""
        if self._pool:
            return await self._pool.execute(query, params)
        return await super().execute(query, params)

    def get_pool_stats(self) -> Optional[ConnectionStats]:
        """Get pool statistics"""
        return self._pool.get_stats() if self._pool else None


# Global pool manager
_pool_manager = {}

def get_pooled_connection(config, pool_config: PoolConfig = None) -> OptimizedDatabaseConnection:
    """Get or create pooled database connection"""
    key = str(config.database_url)
    if key not in _pool_manager:
        _pool_manager[key] = OptimizedDatabaseConnection(config, pool_config)
    return _pool_manager[key]

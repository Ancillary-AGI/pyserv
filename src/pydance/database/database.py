import sqlite3
import asyncpg
import aiomysql
from motor.motor_asyncio import AsyncIOMotorClient
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Any, Dict
from .config import DatabaseConfig

class DatabaseConnection:
    """Database connection manager with support for multiple database types"""
    
    _instances = {}
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.pool = None
        self.client = None
    
    @classmethod
    def get_instance(cls, config: DatabaseConfig) -> 'DatabaseConnection':
        """Get or create a database connection instance"""
        key = config.database_url
        if key not in cls._instances:
            cls._instances[key] = cls(config)
        return cls._instances[key]
    
    async def connect(self):
        """Establish database connection"""
        if self.config.is_sqlite:
            # SQLite doesn't need connection pooling
            return
        elif self.config.is_postgres:
            params = self.config.get_connection_params()
            self.pool = await asyncpg.create_pool(**params)
        elif self.config.is_mysql:
            params = self.config.get_connection_params()
            self.pool = await aiomysql.create_pool(
                host=params['host'],
                port=params['port'],
                user=params['user'],
                password=params['password'],
                db=params['database'],
                autocommit=True
            )
        elif self.config.is_mongodb:
            params = self.config.get_connection_params()
            self.client = AsyncIOMotorClient(
                host=params['host'],
                port=params['port'],
                username=params['username'],
                password=params['password'],
                authSource=params['authSource']
            )
    
    async def disconnect(self):
        """Close database connections"""
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
        if self.client:
            self.client.close()
    
    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[Any, None]:
        """Get a database connection"""
        if self.config.is_sqlite:
            conn = sqlite3.connect(self.config.database)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            try:
                yield conn
            finally:
                conn.close()
        elif self.config.is_postgres:
            async with self.pool.acquire() as conn:
                yield conn
        elif self.config.is_mysql:
            async with self.pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    yield cursor
        elif self.config.is_mongodb:
            yield self.client[self.config.database]
        else:
            raise ValueError(f"Unsupported database type: {self.config.db_type}")
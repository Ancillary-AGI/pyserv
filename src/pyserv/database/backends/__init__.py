# server_framework/orm/backends/__init__.py
from typing import Protocol, Any, Dict, List, Optional, AsyncGenerator, Type
from abc import ABC, abstractmethod
from pyserv.database.config import DatabaseConfig


class DatabaseBackend(Protocol):
    """Abstract interface for database backends"""

    @abstractmethod
    async def connect(self) -> None:
        """Establish database connection"""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close database connection"""
        pass

    @abstractmethod
    async def execute_query(self, query: str, params: tuple = None) -> Any:
        """Execute a raw query and return results"""
        pass

    @abstractmethod
    async def create_table(self, model_class: Any) -> None:
        """Create a table for the given model"""
        pass

    @abstractmethod
    async def get_connection(self) -> AsyncGenerator[Any, None]:
        """Get a database connection context manager"""
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
                       offset: Optional[int] = None, sort: Optional[List[Tuple[str, int]]] = None) -> List[Dict[str, Any]]:
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


# Import concrete implementations
from .sqlite import SQLiteBackend
from .postgres import PostgresBackend
from .mysql import MySQLBackend
from .mongdb import MongoDBBackend


def get_backend(config: DatabaseConfig) -> DatabaseBackend:
    """Factory function to get the appropriate database backend"""
    if config.is_sqlite:
        return SQLiteBackend(config)
    elif config.is_postgres:
        return PostgresBackend(config)
    elif config.is_mysql:
        return MySQLBackend(config)
    elif config.is_mongodb:
        return MongoDBBackend(config)
    else:
        raise ValueError(f"Unsupported database type: {config.db_type}")


__all__ = ['DatabaseBackend', 'SQLiteBackend', 'PostgresBackend', 'MySQLBackend', 'MongoDBBackend', 'get_backend']





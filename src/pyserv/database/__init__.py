"""
Database module for Pyserv  Framework.
Contains database connection, configuration, and related utilities.
"""

from pyserv.database.config import DatabaseConfig
from pyserv.database.database_pool import PoolConfig, ConnectionStats, DatabaseConnection

# Import DatabaseConnection from the new module
from pyserv.database.connection import AbstractDatabaseConnection

__all__ = ['AbstractDatabaseConnection', 'DatabaseConfig', 'PoolConfig', 'ConnectionStats']

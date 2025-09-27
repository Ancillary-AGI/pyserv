# Consolidated database configuration for Pyserv framework
# This merges the best features from both implementations

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import os
from urllib.parse import urlparse


@dataclass
class DatabaseConfig:
    """Comprehensive database configuration with flexible initialization options"""

    def __init__(
        self,
        database_url: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
        db_type: Optional[str] = None,
        pool_size: int = 10,
        max_overflow: int = 20,
        pool_timeout: int = 30,
        echo: bool = False
    ):
        # If database_url is provided, use itn
        if database_url:
            self.database_url = database_url
            self._parse_url()
        # Otherwise, construct from individual parameters
        elif any([host, port, username, password, database, db_type]):
            self._construct_from_params(host, port, username, password, database, db_type)
        else:
            # Fallback to environment variable or default
            self.database_url = os.getenv('DATABASE_URL', 'sqlite:///:memory:')
            self._parse_url()

        # Set pooling and other advanced options
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.echo = echo

    def _construct_from_params(self, host, port, username, password, database, db_type):
        """Construct database URL from individual parameters"""
        db_type = db_type or os.getenv('DB_TYPE', 'sqlite')

        if db_type == 'sqlite':
            if database and database != ':memory:':
                self.database_url = f'sqlite:///{database}'
            else:
                self.database_url = 'sqlite:///:memory:'
        elif db_type in ['postgresql', 'postgres']:
            self.database_url = f'postgresql://{username}:{password}@{host}:{port}/{database}'
        elif db_type == 'mysql':
            self.database_url = f'mysql://{username}:{password}@{host}:{port}/{database}'
        elif db_type == 'mongodb':
            if username and password:
                self.database_url = f'mongodb://{username}:{password}@{host}:{port}/{database}'
            else:
                self.database_url = f'mongodb://{host}:{port}/{database}'
        else:
            raise ValueError(f"Unsupported database type: {db_type}")

        self._parse_url()

    @classmethod
    def from_env(cls, prefix: str = "DB_") -> Optional['DatabaseConfig']:
        """Create DatabaseConfig from environment variables"""
        database_url = os.getenv('DATABASE_URL')
        if database_url:
            return cls(database_url=database_url)

        # Try individual parameters
        host = os.getenv(f"{prefix}HOST")
        port = os.getenv(f"{prefix}PORT")
        username = os.getenv(f"{prefix}USERNAME") or os.getenv(f"{prefix}USER")
        password = os.getenv(f"{prefix}PASSWORD")
        database = os.getenv(f"{prefix}NAME") or os.getenv(f"{prefix}DATABASE")
        db_type = os.getenv(f"{prefix}TYPE") or os.getenv(f"{prefix}DRIVER", "sqlite")

        if any([host, port, username, password, database, db_type]):
            return cls(
                host=host,
                port=int(port) if port else None,
                username=username,
                password=password,
                database=database,
                db_type=db_type
            )

        return None

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'DatabaseConfig':
        """Create DatabaseConfig from dictionary"""
        return cls(
            database_url=config_dict.get('database_url'),
            host=config_dict.get('host'),
            port=config_dict.get('port'),
            username=config_dict.get('username'),
            password=config_dict.get('password'),
            database=config_dict.get('database'),
            db_type=config_dict.get('db_type'),
            pool_size=config_dict.get('pool_size', 10),
            max_overflow=config_dict.get('max_overflow', 20),
            pool_timeout=config_dict.get('pool_timeout', 30),
            echo=config_dict.get('echo', False)
        )

    def _parse_url(self):
        """Parse database URL to extract connection parameters"""
        parsed = urlparse(self.database_url)

        self.db_type = parsed.scheme
        self.is_sqlite = self.db_type == 'sqlite'
        self.is_postgres = self.db_type == 'postgresql'
        self.is_mysql = self.db_type == 'mysql'
        self.is_mongodb = self.db_type == 'mongodb'

        if self.is_sqlite:
            self.database = parsed.path.lstrip('/') or ':memory:'
            self.host = None
            self.port = None
            self.username = None
            self.password = None
        else:
            self.username = parsed.username
            self.password = parsed.password
            self.host = parsed.hostname
            self.port = parsed.port
            self.database = parsed.path.lstrip('/')

    def get_connection_params(self) -> Dict[str, Any]:
        """Get connection parameters for the database"""
        if self.is_sqlite:
            return {'database': self.database}
        elif self.is_postgres:
            return {
                'user': self.username,
                'password': self.password,
                'host': self.host,
                'port': self.port,
                'database': self.database,
                'min_size': 1,
                'max_size': self.pool_size,
                'command_timeout': 60,
                'server_settings': {
                    'jit': 'off'
                }
            }
        elif self.is_mysql:
            return {
                'user': self.username,
                'password': self.password,
                'host': self.host,
                'port': self.port,
                'database': self.database,
                'min_size': 1,
                'max_size': self.pool_size,
            }
        elif self.is_mongodb:
            return {
                'host': self.host,
                'port': self.port,
                'username': self.username,
                'password': self.password,
                'authSource': self.database,
                'maxPoolSize': self.pool_size,
            }
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")

    def __post_init__(self):
        """Set default ports if not specified"""
        if self.port is None:
            if self.db_type == "postgresql":
                self.port = 5432
            elif self.db_type == "mysql":
                self.port = 3306
            elif self.db_type == "mongodb":
                self.port = 27017


@dataclass
class AppConfig:
    """Application configuration with comprehensive settings"""

    # Application settings
    debug: bool = False
    secret_key: str = "your-secret-key-here"
    template_dir: str = "templates"
    static_dir: str = "static"
    database_url: Optional[str] = None
    allowed_hosts: Optional[List[str]] = None
    cors_origins: Optional[List[str]] = None
    trusted_hosts: Optional[List[str]] = None

    # Server settings
    host: str = "127.0.0.1"
    port: int = 8000
    workers: int = 1
    backlog: int = 2048
    keep_alive_timeout: int = 5
    max_connections: int = 1000
    ssl_certfile: Optional[str] = None
    ssl_keyfile: Optional[str] = None
    reload: bool = False
    access_log: bool = True

    # Database settings
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    echo: bool = False

    def __post_init__(self):
        """Set default values"""
        if self.allowed_hosts is None:
            self.allowed_hosts = ["localhost", "127.0.0.1"]
        if self.cors_origins is None:
            self.cors_origins = ["*"]
        if self.trusted_hosts is None:
            self.trusted_hosts = ["localhost", "127.0.0.1"]

    @classmethod
    def from_env(cls) -> 'AppConfig':
        """Create AppConfig from environment variables"""
        return cls(
            debug=os.getenv('DEBUG', 'false').lower() == 'true',
            secret_key=os.getenv('SECRET_KEY', 'your-secret-key-here'),
            host=os.getenv('HOST', '127.0.0.1'),
            port=int(os.getenv('PORT', '8000')),
            workers=int(os.getenv('WORKERS', '1')),
            database_url=os.getenv('DATABASE_URL'),
            allowed_hosts=os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(','),
            cors_origins=os.getenv('CORS_ORIGINS', '*').split(','),
            ssl_certfile=os.getenv('SSL_CERTFILE'),
            ssl_keyfile=os.getenv('SSL_KEYFILE'),
            reload=os.getenv('RELOAD', 'false').lower() == 'true',
            access_log=os.getenv('ACCESS_LOG', 'true').lower() == 'true',
            pool_size=int(os.getenv('DB_POOL_SIZE', '10')),
            max_overflow=int(os.getenv('DB_MAX_OVERFLOW', '20')),
            pool_timeout=int(os.getenv('DB_POOL_TIMEOUT', '30')),
            echo=os.getenv('DB_ECHO', 'false').lower() == 'true'
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            'debug': self.debug,
            'secret_key': self.secret_key,
            'template_dir': self.template_dir,
            'static_dir': self.static_dir,
            'database_url': self.database_url,
            'allowed_hosts': self.allowed_hosts,
            'cors_origins': self.cors_origins,
            'trusted_hosts': self.trusted_hosts,
            'host': self.host,
            'port': self.port,
            'workers': self.workers,
            'backlog': self.backlog,
            'keep_alive_timeout': self.keep_alive_timeout,
            'max_connections': self.max_connections,
            'ssl_certfile': self.ssl_certfile,
            'ssl_keyfile': self.ssl_keyfile,
            'reload': self.reload,
            'access_log': self.access_log,
            'pool_size': self.pool_size,
            'max_overflow': self.max_overflow,
            'pool_timeout': self.pool_timeout,
            'echo': self.echo
        }


# Global instances
db_config = DatabaseConfig.from_env() or DatabaseConfig()
app_config = AppConfig.from_env()

# Export all configuration classes
__all__ = ['DatabaseConfig', 'AppConfig', 'db_config', 'app_config']

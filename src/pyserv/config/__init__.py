"""
Pyserv Configuration System

This module provides comprehensive configuration management for the Pyserv framework,
including support for multiple providers and environment-based settings.
"""

import os
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum


class EmailProvider(str, Enum):
    SMTP = "smtp"
    GMAIL = "gmail"
    SENDGRID = "sendgrid"
    MAILGUN = "mailgun"

class StorageProvider(str, Enum):
    LOCAL = "local"
    S3 = "s3"
    GCS = "gcs"
    AZURE = "azure"

class CacheBackend(str, Enum):
    MEMORY = "memory"
    REDIS = "redis"
    FILE = "file"
    DATABASE = "database"


@dataclass
class DatabaseConfig:
    """Database configuration"""
    url: str = os.getenv('DATABASE_URL', 'sqlite:///app.db')
    pool_size: int = int(os.getenv('DB_POOL_SIZE', '10'))
    max_overflow: int = int(os.getenv('DB_MAX_OVERFLOW', '20'))
    pool_timeout: int = int(os.getenv('DB_POOL_TIMEOUT', '30'))
    echo: bool = os.getenv('DB_ECHO', 'False').lower() == 'true'


@dataclass
class EmailConfig:
    """Email configuration with support for multiple providers"""
    provider: EmailProvider = field(default_factory=lambda: EmailProvider(os.getenv('EMAIL_PROVIDER', 'smtp')))
    host: str = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
    port: int = int(os.getenv('EMAIL_PORT', '587'))
    username: str = os.getenv('EMAIL_USER', '')
    password: str = os.getenv('EMAIL_PASSWORD', '')
    use_tls: bool = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
    use_ssl: bool = os.getenv('EMAIL_USE_SSL', 'False').lower() == 'true'
    from_address: str = os.getenv('EMAIL_FROM', 'noreply@example.com')
    from_name: str = os.getenv('EMAIL_FROM_NAME', 'App')

    # Provider-specific settings
    aws_region: str = os.getenv('AWS_SES_REGION', 'us-east-1')
    sendgrid_api_key: str = os.getenv('SENDGRID_API_KEY', '')
    mailgun_api_key: str = os.getenv('MAILGUN_API_KEY', '')
    mailgun_domain: str = os.getenv('MAILGUN_DOMAIN', '')


@dataclass
class StorageConfig:
    """Storage configuration with support for multiple providers"""
    provider: StorageProvider = field(default_factory=lambda: StorageProvider(os.getenv('STORAGE_PROVIDER', 'local')))
    local_directory: str = os.getenv('STORAGE_LOCAL_DIR', 'uploads')
    max_file_size: int = int(os.getenv('STORAGE_MAX_FILE_SIZE', '10485760'))  # 10MB
    allowed_extensions: List[str] = field(default_factory=lambda: os.getenv('STORAGE_ALLOWED_EXTENSIONS', 'jpg,jpeg,png,gif,pdf,doc,docx,txt').split(','))

    # Cloud storage settings
    aws_access_key: str = os.getenv('AWS_ACCESS_KEY_ID', '')
    aws_secret_key: str = os.getenv('AWS_SECRET_ACCESS_KEY', '')
    aws_region: str = os.getenv('AWS_REGION', 'us-east-1')
    aws_bucket: str = os.getenv('AWS_S3_BUCKET', '')

    gcp_project: str = os.getenv('GCP_PROJECT', '')
    gcp_bucket: str = os.getenv('GCP_STORAGE_BUCKET', '')
    gcp_credentials: str = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', '')

    azure_account_name: str = os.getenv('AZURE_ACCOUNT_NAME', '')
    azure_account_key: str = os.getenv('AZURE_ACCOUNT_KEY', '')
    azure_container: str = os.getenv('AZURE_CONTAINER', '')


@dataclass
class CacheConfig:
    """Cache configuration with multiple backend support"""
    backend: CacheBackend = field(default_factory=lambda: CacheBackend(os.getenv('CACHE_BACKEND', 'memory')))
    host: str = os.getenv('CACHE_HOST', 'localhost')
    port: int = int(os.getenv('CACHE_PORT', '6379'))
    password: str = os.getenv('CACHE_PASSWORD', '')
    database: int = int(os.getenv('CACHE_DATABASE', '0'))
    default_timeout: int = int(os.getenv('CACHE_DEFAULT_TIMEOUT', '300'))
    key_prefix: str = os.getenv('CACHE_KEY_PREFIX', 'app:')

    # Redis-specific
    redis_ssl: bool = os.getenv('REDIS_SSL', 'False').lower() == 'true'
    redis_cluster: bool = os.getenv('REDIS_CLUSTER', 'False').lower() == 'true'


@dataclass
class CDNConfig:
    """CDN configuration"""
    enabled: bool = os.getenv('CDN_ENABLED', 'False').lower() == 'true'
    url: str = os.getenv('CDN_URL', '')
    key: str = os.getenv('CDN_KEY', '')
    secret: str = os.getenv('CDN_SECRET', '')
    provider: str = os.getenv('CDN_PROVIDER', 'cloudflare')  # cloudflare, aws_cloudfront, etc.


@dataclass
class SecurityConfig:
    """Security configuration"""
    secret_key: str = os.getenv('SECRET_KEY', 'your-secret-key-here')
    jwt_secret: str = os.getenv('JWT_SECRET', '')
    jwt_algorithm: str = os.getenv('JWT_ALGORITHM', 'HS256')
    jwt_expire_minutes: int = int(os.getenv('JWT_EXPIRE_MINUTES', '1440'))  # 24 hours
    password_hash_rounds: int = int(os.getenv('PASSWORD_HASH_ROUNDS', '12'))
    cors_origins: List[str] = field(default_factory=lambda: os.getenv('CORS_ORIGINS', '*').split(','))
    allowed_hosts: List[str] = field(default_factory=lambda: os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(','))
    trusted_hosts: List[str] = field(default_factory=lambda: os.getenv('TRUSTED_HOSTS', 'localhost,127.0.0.1').split(','))


@dataclass
class ServerConfig:
    """Server configuration"""
    host: str = os.getenv('HOST', '127.0.0.1')
    port: int = int(os.getenv('PORT', '8000'))
    workers: int = int(os.getenv('WORKERS', '1'))
    backlog: int = int(os.getenv('BACKLOG', '2048'))
    keep_alive_timeout: int = int(os.getenv('KEEP_ALIVE_TIMEOUT', '5'))
    max_connections: int = int(os.getenv('MAX_CONNECTIONS', '1000'))
    ssl_certfile: Optional[str] = os.getenv('SSL_CERTFILE')
    ssl_keyfile: Optional[str] = os.getenv('SSL_KEYFILE')
    reload: bool = os.getenv('RELOAD', 'False').lower() == 'true'
    access_log: bool = os.getenv('ACCESS_LOG', 'True').lower() == 'true'
    debug: bool = os.getenv('DEBUG', 'False').lower() == 'true'


@dataclass
class I18nConfig:
    """Internationalization configuration"""
    default_locale: str = os.getenv('DEFAULT_LOCALE', 'en')
    default_timezone: str = os.getenv('DEFAULT_TIMEZONE', 'UTC')
    supported_locales: List[str] = field(default_factory=lambda: os.getenv('SUPPORTED_LOCALES', 'en,es,fr,de,zh,ja').split(','))
    translations_dir: str = os.getenv('TRANSLATIONS_DIR', 'translations')
    rtl_languages: List[str] = field(default_factory=lambda: os.getenv('RTL_LANGUAGES', 'ar,he,fa,ur').split(','))


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = os.getenv('LOG_LEVEL', 'INFO')
    file: Optional[str] = os.getenv('LOG_FILE')
    json_format: bool = os.getenv('LOG_JSON_FORMAT', 'False').lower() == 'true'
    log_requests: bool = os.getenv('LOG_REQUESTS', 'True').lower() == 'true'


@dataclass
class TestingConfig:
    """Testing configuration"""
    testing: bool = os.getenv('TESTING', 'False').lower() == 'true'
    test_database_url: str = os.getenv('TEST_DATABASE_URL', 'sqlite://:memory:')


@dataclass
class StaticFilesConfig:
    """Static files configuration (Django-style)"""
    # STATICFILES_DIRS - directories to search for static files
    dirs: List[str] = field(default_factory=lambda: os.getenv('STATICFILES_DIRS', 'static').split(','))

    # STATIC_ROOT - directory where collectstatic will copy files
    root: str = os.getenv('STATIC_ROOT', 'staticfiles')

    # STATIC_URL - URL prefix for static files
    url: str = os.getenv('STATIC_URL', '/static/')

    # File patterns to include/exclude
    include_patterns: List[str] = field(default_factory=lambda: ['**/*'])
    exclude_patterns: List[str] = field(default_factory=lambda: [])

    # CDN settings
    use_cdn: bool = os.getenv('STATIC_USE_CDN', 'False').lower() == 'true'
    cdn_url: str = os.getenv('STATIC_CDN_URL', '')


@dataclass
class AppConfig:
    """Main application configuration"""
    # Core settings
    debug: bool = os.getenv('DEBUG', 'False').lower() == 'true'
    secret_key: str = os.getenv('SECRET_KEY', 'your-secret-key-here')
    allowed_hosts: List[str] = field(default_factory=lambda: os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(','))

    # Database
    database: DatabaseConfig = field(default_factory=DatabaseConfig)

    # Email
    email: EmailConfig = field(default_factory=EmailConfig)

    # Storage
    storage: StorageConfig = field(default_factory=StorageConfig)

    # Cache
    cache: CacheConfig = field(default_factory=CacheConfig)

    # CDN
    cdn: CDNConfig = field(default_factory=CDNConfig)

    # Security
    security: SecurityConfig = field(default_factory=SecurityConfig)

    # Server
    server: ServerConfig = field(default_factory=ServerConfig)

    # Internationalization
    i18n: I18nConfig = field(default_factory=I18nConfig)

    # Logging
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    # Testing
    testing: TestingConfig = field(default_factory=TestingConfig)

    # Static Files
    staticfiles: StaticFilesConfig = field(default_factory=StaticFilesConfig)

    def __post_init__(self):
        """Validate configuration after initialization"""
        # Ensure secret key is set in production
        if not self.debug and self.secret_key == 'your-secret-key-here':
            raise ValueError("SECRET_KEY must be set in production environment")

    @property
    def database_url(self) -> str:
        """Backward compatibility property"""
        return self.database.url

    @property
    def host(self) -> str:
        """Backward compatibility property"""
        return self.server.host

    @property
    def port(self) -> int:
        """Backward compatibility property"""
        return self.server.port

    @property
    def cors_origins(self) -> List[str]:
        """Backward compatibility property"""
        return self.security.cors_origins

    @property
    def trusted_hosts(self) -> List[str]:
        """Backward compatibility property"""
        return self.security.trusted_hosts


# Configuration presets for different environments
class ConfigPresets:
    """Configuration presets for different environments"""

    @staticmethod
    def development() -> AppConfig:
        """Development configuration"""
        return AppConfig(
            debug=True,
            secret_key='dev-secret-key-change-in-production',
            allowed_hosts=['*'],
            server=ServerConfig(
                host='127.0.0.1',
                port=8000,
                debug=True,
                reload=True
            ),
            logging=LoggingConfig(level='DEBUG'),
            database=DatabaseConfig(url='sqlite:///dev.db', echo=True)
        )

    @staticmethod
    def production() -> AppConfig:
        """Production configuration"""
        return AppConfig(
            debug=False,
            allowed_hosts=[],  # Must be explicitly set
            server=ServerConfig(
                host='0.0.0.0',
                port=8000,
                workers=4,
                debug=False,
                reload=False
            ),
            logging=LoggingConfig(level='WARNING'),
            database=DatabaseConfig()  # Uses environment variables
        )

    @staticmethod
    def testing() -> AppConfig:
        """Testing configuration"""
        return AppConfig(
            debug=True,
            secret_key='test-secret-key',
            allowed_hosts=['*'],
            server=ServerConfig(
                host='127.0.0.1',
                port=0,  # Random port
                debug=True,
                reload=False
            ),
            logging=LoggingConfig(level='ERROR'),
            database=DatabaseConfig(url='sqlite://:memory:'),
            testing=TestingConfig(testing=True)
        )


def get_config_from_environment() -> AppConfig:
    """Get configuration based on environment"""
    env = os.getenv('PYSERV_ENV', 'development').lower()

    if env == 'production':
        return ConfigPresets.production()
    elif env == 'testing':
        return ConfigPresets.testing()
    else:
        return ConfigPresets.development()


# Default configuration
default_config = ConfigPresets.production()

__all__ = [
    'AppConfig', 'DatabaseConfig', 'EmailConfig', 'StorageConfig',
    'CacheConfig', 'CDNConfig', 'SecurityConfig', 'ServerConfig',
    'I18nConfig', 'LoggingConfig', 'TestingConfig', 'StaticFilesConfig',
    'ConfigPresets', 'get_config_from_environment', 'default_config',
    'EmailProvider', 'StorageProvider', 'CacheBackend'
]

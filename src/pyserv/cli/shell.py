"""
Interactive shell and database shell for Pyserv framework.
Provides Django/Laravel-style shell commands for development and debugging.
"""

import asyncio
import code
import sys
import os
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from contextlib import asynccontextmanager

from pyserv.database.connection import AbstractDatabaseConnection
from pyserv.database.database_pool import DatabaseConnection
from pyserv.models.base import BaseModel
from pyserv.caching.cache_manager import CacheManager
from pyserv.exceptions import ValidationError, DatabaseError
from pyserv.utils.types import Field, Relationship

class PyservShell:
    """
    Interactive Python shell with Pyserv context pre-loaded.
    Similar to Django's shell command.
    """

    def __init__(self):
        self.logger = logging.getLogger("pyserv.shell")
        self.db_connection = None
        self.cache_manager = None

    def start_shell(self):
        """Start the interactive shell."""
        print("Pyserv Interactive Shell")
        print("=" * 50)
        print("Available objects:")
        print("- app: Pyserv application instance")
        print("- db: Database connection")
        print("- cache: Cache manager")
        print("- User, Post, etc.: Your models")
        print("- exit() or quit() to exit")
        print("=" * 50)

        # Create shell context
        context = self._get_shell_context()

        # Start interactive shell
        try:
            code.interact(local=context, banner="")
        except KeyboardInterrupt:
            print("\nShell interrupted. Goodbye!")
        except Exception as e:
            print(f"Shell error: {e}")

    def _get_shell_context(self) -> Dict[str, Any]:
        """Get context variables for the shell."""
        context = {
            'os': os,
            'sys': sys,
            'json': json,
            'datetime': datetime,
            'logging': logging,
        }

        # Add database connection
        try:
            self.db_connection = AbstractDatabaseConnection.get_instance()
            context['db'] = self.db_connection
        except Exception as e:
            self.logger.warning(f"Could not initialize database connection: {e}")

        # Add cache manager
        try:
            self.cache_manager = CacheManager.get_instance()
            context['cache'] = self.cache_manager
        except Exception as e:
            self.logger.warning(f"Could not initialize cache manager: {e}")

        # Add all models
        try:
            from pyserv.models import BaseModel
            # Import all model classes dynamically
            models_dir = os.path.join(os.path.dirname(__file__), '..', 'models')
            if os.path.exists(models_dir):
                for filename in os.listdir(models_dir):
                    if filename.endswith('.py') and not filename.startswith('__'):
                        module_name = filename[:-3]  # Remove .py
                        try:
                            module = __import__(f'pyserv.models.{module_name}', fromlist=[module_name])
                            for attr_name in dir(module):
                                attr = getattr(module, attr_name)
                                if (isinstance(attr, type) and
                                    issubclass(attr, BaseModel) and
                                    attr != BaseModel):
                                    context[attr_name] = attr
                        except Exception as e:
                            self.logger.debug(f"Could not import models from {module_name}: {e}")
        except Exception as e:
            self.logger.warning(f"Could not load models: {e}")

        return context

class DatabaseShell:
    """
    Interactive database shell for querying and managing database.
    Similar to Django's dbshell command.
    """

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv('DATABASE_URL')
        self.logger = logging.getLogger("pyserv.dbshell")
        self.connection = None

    async def start_dbshell(self):
        """Start the database shell."""
        print("Pyserv Database Shell")
        print("=" * 50)
        print("Available commands:")
        print("- \\dt: List all tables")
        print("- \\d <table>: Describe table")
        print("- \\q: Quit")
        print("- SQL queries: Execute SQL directly")
        print("=" * 50)

        try:
            await self._initialize_connection()

            while True:
                try:
                    query = input("dbshell> ").strip()

                    if not query:
                        continue

                    if query.lower() in ['\\q', 'quit', 'exit']:
                        break

                    if query.lower() == '\\dt':
                        await self._list_tables()
                    elif query.lower().startswith('\\d'):
                        table_name = query[2:].strip()
                        if table_name:
                            await self._describe_table(table_name)
                        else:
                            print("Usage: \\d <table_name>")
                    else:
                        await self._execute_query(query)

                except KeyboardInterrupt:
                    print("\nUse \\q to quit")
                except Exception as e:
                    print(f"Error: {e}")

        except Exception as e:
            print(f"Database shell error: {e}")
        finally:
            await self._close_connection()

    async def _initialize_connection(self):
        """Initialize database connection."""
        try:
            if not self.database_url:
                raise ValueError("DATABASE_URL environment variable not set")

            self.connection = await AbstractDatabaseConnection.create_connection(self.database_url)
            print(f"Connected to database: {self.database_url.split('@')[1] if '@' in self.database_url else 'database'}")
        except Exception as e:
            self.logger.error(f"Failed to connect to database: {e}")
            raise

    async def _close_connection(self):
        """Close database connection."""
        if self.connection:
            try:
                await self.connection.close()
            except Exception as e:
                self.logger.warning(f"Error closing connection: {e}")

    async def _list_tables(self):
        """List all tables in the database."""
        try:
            if hasattr(self.connection, 'get_tables'):
                tables = await self.connection.get_tables()
                if tables:
                    print("Tables:")
                    for table in tables:
                        print(f"  {table}")
                else:
                    print("No tables found")
            else:
                print("Table listing not supported for this database type")
        except Exception as e:
            print(f"Error listing tables: {e}")

    async def _describe_table(self, table_name: str):
        """Describe a table structure."""
        try:
            if hasattr(self.connection, 'describe_table'):
                description = await self.connection.describe_table(table_name)
                if description:
                    print(f"Table: {table_name}")
                    print("Columns:")
                    for column in description:
                        print(f"  {column['name']}: {column['type']} {'NOT NULL' if column['not_null'] else 'NULL'}")
                else:
                    print(f"Table {table_name} not found")
            else:
                print("Table description not supported for this database type")
        except Exception as e:
            print(f"Error describing table: {e}")

    async def _execute_query(self, query: str):
        """Execute a SQL query."""
        try:
            if hasattr(self.connection, 'execute_query'):
                result = await self.connection.execute_query(query)
                if result:
                    print("Query executed successfully")
                    if isinstance(result, list) and len(result) > 0:
                        print(f"Returned {len(result)} rows")
                else:
                    print("Query executed successfully")
            else:
                print("Query execution not supported for this database type")
        except Exception as e:
            print(f"Query error: {e}")

class ShellCommand:
    """
    Command-line interface for shell commands.
    """

    def __init__(self):
        self.logger = logging.getLogger("pyserv.shell_command")

    def shell(self):
        """Start the Python shell."""
        shell = PyservShell()
        shell.start_shell()

    async def dbshell(self, database_url: Optional[str] = None):
        """Start the database shell."""
        db_shell = DatabaseShell(database_url)
        await db_shell.start_dbshell()

    def show_urls(self):
        """Show all registered URL patterns."""
        try:
            from pyserv.routing.router import router
            print("Registered URL patterns:")
            print("=" * 50)

            for route in router.routes:
                print(f"{route.method} {route.path} -> {route.handler.__name__ if hasattr(route.handler, '__name__') else route.handler}")

        except ImportError:
            print("Router not available")
        except Exception as e:
            print(f"Error showing URLs: {e}")

    def show_models(self):
        """Show all registered models."""
        try:
            print("Registered models:")
            print("=" * 50)

            # Import all models dynamically
            models_dir = os.path.join(os.path.dirname(__file__), '..', 'models')
            if os.path.exists(models_dir):
                for filename in os.listdir(models_dir):
                    if filename.endswith('.py') and not filename.startswith('__'):
                        module_name = filename[:-3]
                        try:
                            module = __import__(f'pyserv.models.{module_name}', fromlist=[module_name])
                            for attr_name in dir(module):
                                attr = getattr(module, attr_name)
                                if (isinstance(attr, type) and
                                    issubclass(attr, BaseModel) and
                                    attr != BaseModel):
                                    print(f"- {attr_name}")
                        except Exception as e:
                            self.logger.debug(f"Could not import models from {module_name}: {e}")
            else:
                print("No models directory found")

        except Exception as e:
            print(f"Error showing models: {e}")

    def show_settings(self):
        """Show current settings."""
        print("Current settings:")
        print("=" * 50)

        # Database settings
        db_url = os.getenv('DATABASE_URL', 'Not set')
        print(f"DATABASE_URL: {db_url[:50]}..." if len(db_url) > 50 else f"DATABASE_URL: {db_url}")

        # Cache settings
        cache_url = os.getenv('CACHE_URL', 'Not set')
        print(f"CACHE_URL: {cache_url}")

        # Debug mode
        debug_mode = os.getenv('DEBUG', 'False')
        print(f"DEBUG: {debug_mode}")

        # Other settings
        settings_to_show = [
            'SECRET_KEY', 'ALLOWED_HOSTS', 'CORS_ORIGINS',
            'API_VERSION', 'TIMEZONE', 'LANGUAGE_CODE'
        ]

        for setting in settings_to_show:
            value = os.getenv(setting, 'Not set')
            if len(value) > 50:
                print(f"{setting}: {value[:50]}...")
            else:
                print(f"{setting}: {value}")

    def create_superuser(self, username: str, email: str, password: str):
        """Create a superuser."""
        try:
            from pyserv.models.user import BaseUser
            from pyserv.models.user import UserRole

            async def _create_superuser():
                # Check if user already exists
                existing_user = await BaseUser.query().filter(
                    BaseUser.email == email
                ).first()

                if existing_user:
                    print(f"User with email {email} already exists")
                    return

                # Create superuser
                user = await BaseUser.create(
                    username=username,
                    email=email,
                    password_hash=BaseUser.hash_password(password),
                    role=UserRole.ADMIN,
                    is_superuser=True,
                    is_staff=True,
                    is_active=True,
                    is_verified=True
                )

                print(f"Superuser {username} created successfully")

            asyncio.run(_create_superuser())

        except Exception as e:
            print(f"Error creating superuser: {e}")

    def migrate(self, app_name: Optional[str] = None):
        """Run database migrations."""
        try:
            from pyserv.migrations.migrator import MigrationRunner

            async def _run_migrations():
                runner = MigrationRunner()
                if app_name:
                    await runner.migrate_app(app_name)
                else:
                    await runner.migrate_all()

            asyncio.run(_run_migrations())
            print("Migrations completed successfully")

        except Exception as e:
            print(f"Migration error: {e}")

    def makemigrations(self, app_name: str, message: Optional[str] = None):
        """Create new migrations."""
        try:
            from pyserv.migrations.migrator import MigrationRunner

            async def _make_migrations():
                runner = MigrationRunner()
                await runner.make_migrations(app_name, message)

            asyncio.run(_make_migrations())
            print(f"Migration created for {app_name}")

        except Exception as e:
            print(f"Migration creation error: {e}")

# Global shell command instance
shell_command = ShellCommand()

def shell():
    """Start the Python shell."""
    shell_command.shell()

async def dbshell(database_url: Optional[str] = None):
    """Start the database shell."""
    await shell_command.dbshell(database_url)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Pyserv Shell Commands")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Shell command
    shell_parser = subparsers.add_parser('shell', help='Start Python shell')
    shell_parser.set_defaults(func=lambda: shell())

    # Database shell command
    dbshell_parser = subparsers.add_parser('dbshell', help='Start database shell')
    dbshell_parser.add_argument('--database-url', help='Database URL')
    dbshell_parser.set_defaults(func=lambda args: asyncio.run(dbshell(args.database_url)))

    # Show URLs command
    subparsers.add_parser('show_urls', help='Show registered URL patterns').set_defaults(
        func=lambda args: shell_command.show_urls()
    )

    # Show models command
    subparsers.add_parser('show_models', help='Show registered models').set_defaults(
        func=lambda args: shell_command.show_models()
    )

    # Show settings command
    subparsers.add_parser('show_settings', help='Show current settings').set_defaults(
        func=lambda args: shell_command.show_settings()
    )

    # Create superuser command
    superuser_parser = subparsers.add_parser('createsuperuser', help='Create superuser')
    superuser_parser.add_argument('username', help='Username')
    superuser_parser.add_argument('email', help='Email')
    superuser_parser.add_argument('password', help='Password')
    superuser_parser.set_defaults(func=lambda args: shell_command.create_superuser(args.username, args.email, args.password))

    # Migrate command
    migrate_parser = subparsers.add_parser('migrate', help='Run migrations')
    migrate_parser.add_argument('--app', help='Specific app to migrate')
    migrate_parser.set_defaults(func=lambda args: shell_command.migrate(args.app))

    # Makemigrations command
    makemigrations_parser = subparsers.add_parser('makemigrations', help='Create migrations')
    makemigrations_parser.add_argument('app', help='App name')
    makemigrations_parser.add_argument('--message', help='Migration message')
    makemigrations_parser.set_defaults(func=lambda args: shell_command.makemigrations(args.app, args.message))

    args = parser.parse_args()
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()

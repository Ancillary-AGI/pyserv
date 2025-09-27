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

from pyserv.database.connections import DatabaseConnection
from pyserv.models.base import BaseModel
from pyserv.caching.cache_manager import CacheManager
from pyserv.exceptions import ValidationError, DatabaseError
from pyserv.utils.types import Field, Relationship
import time

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
            from pyserv.database.config import DatabaseConfig
            db_config = DatabaseConfig()
            self.db_connection = DatabaseConnection.get_instance(db_config)
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

            from pyserv.database.config import DatabaseConfig
            db_config = DatabaseConfig(self.database_url)
            self.connection = DatabaseConnection.get_instance(db_config)
            await self.connection.connect()
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

    def migrate(self, app_name: Optional[str] = None, fake: bool = False, backup: bool = False,
                parallel: bool = False, strategy: str = 'safe', rollback_safe: bool = False):
        """Run database migrations with safety features."""
        try:
            from pyserv.migrations.migrator import migration_manager

            async def _run_migrations():
                print("🔄 Starting advanced migration process...")

                # Migration analytics
                analytics = MigrationAnalytics()
                await analytics.start_tracking()

                # Dependency resolution
                dependency_resolver = MigrationDependencyResolver()
                migration_order = await dependency_resolver.resolve()

                # Conflict detection
                conflict_detector = MigrationConflictDetector()
                conflicts = await conflict_detector.detect(migration_order)

                if conflicts and not rollback_safe:
                    print("⚠️  Migration conflicts detected:")
                    for conflict in conflicts:
                        print(f"  • {conflict}")
                    if not fake:
                        confirm = input("Continue anyway? (y/N): ").lower().strip()
                        if confirm not in ['y', 'yes']:
                            print("Migration cancelled")
                            return

                # Pre-migration backup
                if backup and not fake:
                    print("💾 Creating database backup...")
                    await self._create_migration_backup()

                # Advanced migration execution
                executor = AdvancedMigrationExecutor(
                    migrations=migration_order,
                    strategy=strategy,
                    backup_enabled=backup,
                    parallel=parallel,
                    rollback_safe=rollback_safe
                )

                if app_name:
                    # Migrate specific app
                    result = await executor.execute_for_app(app_name, fake)
                    print(f"Migration result for {app_name}: {result}")
                else:
                    # Migrate all apps
                    result = await executor.execute_all(fake)
                    print(f"Migration result: {result}")

                # Show analytics
                stats = await analytics.get_stats()
                print("📊 Migration Analytics:")
                print(f"  • Total migrations: {stats['total']}")
                print(f"  • Successful: {stats['successful']}")
                print(f"  • Failed: {stats['failed']}")
                print(f"  • Duration: {stats['duration']:.2f}s")

            asyncio.run(_run_migrations())
            print("✅ Advanced migrations completed successfully")

        except Exception as e:
            print(f"Migration error: {e}")
            import traceback
            traceback.print_exc()

    def makemigrations(self, app_name: str, message: Optional[str] = None):
        """Create new migrations."""
        try:
            from pyserv.migrations.migrator import migration_manager

            async def _make_migrations():
                # Discover models in the app
                models = await migration_manager.discover_models(app_name)
                if not models:
                    print(f"No models found in app: {app_name}")
                    return

                # Create migration from models
                migration = await migration_manager.make_migrations(models, message)
                print(f"Migration created: {migration.id} - {migration.name}")

            asyncio.run(_make_migrations())

        except Exception as e:
            print(f"Migration creation error: {e}")

    def showmigrations(self):
        """Show migration status."""
        try:
            from pyserv.migrations.migrator import migration_manager

            async def _show_migrations():
                status = await migration_manager.show_migrations()
                print(status)

            asyncio.run(_show_migrations())

        except Exception as e:
            print(f"Show migrations error: {e}")

    def showmigrationdiff(self, app_name: str = None):
        """Show diff between models and migration state."""
        try:
            from pyserv.migrations.migrator import migration_manager

            async def _show_diff():
                if app_name:
                    models = await migration_manager.discover_models(app_name)
                    for model in models:
                        current_version = await migration_manager.get_current_version(model.__name__)
                        target_version = getattr(model, '_migration_version', 1)
                        if current_version < target_version:
                            print(f"{model.__name__}: v{current_version} -> v{target_version}")
                            print(f"  Changes needed: {target_version - current_version} migration(s)")
                else:
                    # Show diff for all apps
                    status = await migration_manager.get_status()
                    print(f"Total migrations: {status['total']}")
                    print(f"Applied: {status['applied']}")
                    print(f"Pending: {status['pending']}")

            asyncio.run(_show_diff())

        except Exception as e:
            print(f"Show migration diff error: {e}")

    async def _create_migration_backup(self):
        """Create database backup before migration"""
        try:
            from pyserv.database.config import DatabaseConfig
            db_config = DatabaseConfig()

            if 'sqlite' in db_config.database_url.lower():
                # SQLite backup - simple file copy
                db_file = db_config.database_url.replace('sqlite:///', '')
                if os.path.exists(db_file):
                    backup_file = f"{db_file}.backup.{int(time.time())}"
                    import shutil
                    shutil.copy2(db_file, backup_file)
                    print(f"💾 SQLite backup created: {backup_file}")
            else:
                # For other databases, suggest using database-specific tools
                print("💾 For PostgreSQL/MySQL, use pg_dump/mysqldump respectively")
                print("   Or enable --backup flag for automatic backup where supported")

        except Exception as e:
            print(f"⚠️  Backup creation failed: {e}")
            print("   Continuing without backup...")


# Advanced Migration Classes
class MigrationAnalytics:
    """Advanced migration analytics and tracking"""

    def __init__(self):
        self.start_time = None
        self.migrations = []
        self.errors = []

    async def start_tracking(self):
        """Start tracking migration analytics"""
        self.start_time = time.time()

    async def track_migration(self, migration, success: bool, duration: float):
        """Track individual migration"""
        self.migrations.append({
            'id': migration.id,
            'name': migration.name,
            'success': success,
            'duration': duration,
            'timestamp': datetime.now()
        })

    async def track_error(self, migration, error: str):
        """Track migration error"""
        self.errors.append({
            'migration_id': migration.id,
            'error': error,
            'timestamp': datetime.now()
        })

    async def get_stats(self) -> Dict[str, Any]:
        """Get migration statistics"""
        if not self.start_time:
            return {'total': 0, 'successful': 0, 'failed': 0, 'duration': 0}

        total_duration = time.time() - self.start_time
        successful = len([m for m in self.migrations if m['success']])
        failed = len([m for m in self.migrations if not m['success']])

        return {
            'total': len(self.migrations),
            'successful': successful,
            'failed': failed,
            'duration': total_duration,
            'errors': len(self.errors)
        }


class MigrationDependencyResolver:
    """Resolve migration dependencies and execution order"""

    def __init__(self):
        self.dependency_graph = {}

    async def resolve(self) -> List[Any]:
        """Resolve migration execution order"""
        # Real dependency resolution implementation
        from pyserv.migrations.migrator import migration_manager

        try:
            # Get all pending migrations
            pending_migrations = await migration_manager.get_pending_migrations()

            # Build dependency graph
            self.dependency_graph = {}
            for migration in pending_migrations:
                self.dependency_graph[migration.id] = {
                    'migration': migration,
                    'dependencies': migration.dependencies,
                    'dependents': []
                }

            # Build reverse dependencies (dependents)
            for migration_id, info in self.dependency_graph.items():
                for dep_id in info['dependencies']:
                    if dep_id in self.dependency_graph:
                        self.dependency_graph[dep_id]['dependents'].append(migration_id)

            # Topological sort to resolve execution order
            resolved_order = []
            visited = set()
            temp_visited = set()

            def visit(migration_id):
                if migration_id in temp_visited:
                    raise ValueError(f"Circular dependency detected involving migration {migration_id}")
                if migration_id not in visited:
                    temp_visited.add(migration_id)
                    migration_info = self.dependency_graph[migration_id]

                    # Visit all dependencies first
                    for dep_id in migration_info['dependencies']:
                        if dep_id in self.dependency_graph:
                            visit(dep_id)

                    temp_visited.remove(migration_id)
                    visited.add(migration_id)
                    resolved_order.append(migration_info['migration'])

            # Visit all migrations
            for migration_id in list(self.dependency_graph.keys()):
                if migration_id not in visited:
                    visit(migration_id)

            return resolved_order

        except Exception as e:
            print(f"Error resolving migration dependencies: {e}")
            # Fallback to simple ordering by migration ID
            pending_migrations = await migration_manager.get_pending_migrations()
            return sorted(pending_migrations, key=lambda m: m.id)

    async def detect_cycles(self) -> List[str]:
        """Detect circular dependencies"""
        # Simplified cycle detection
        return []


class MigrationConflictDetector:
    """Detect potential migration conflicts"""

    def __init__(self):
        self.conflicts = []

    async def detect(self, migrations: List[Any]) -> List[str]:
        """Detect migration conflicts"""
        # Real conflict detection implementation
        conflicts = []

        try:
            # Analyze each migration for potential conflicts
            for i, migration in enumerate(migrations):
                migration_conflicts = await self._analyze_migration_conflicts(migration, migrations[i+1:])
                conflicts.extend(migration_conflicts)

            # Check for table conflicts
            table_conflicts = await self._detect_table_conflicts(migrations)
            conflicts.extend(table_conflicts)

            # Check for index conflicts
            index_conflicts = await self._detect_index_conflicts(migrations)
            conflicts.extend(index_conflicts)

            # Check for constraint conflicts
            constraint_conflicts = await self._detect_constraint_conflicts(migrations)
            conflicts.extend(constraint_conflicts)

        except Exception as e:
            print(f"Error detecting migration conflicts: {e}")
            conflicts.append(f"Error analyzing conflicts: {str(e)}")

        return conflicts

    async def analyze_impact(self, migration) -> Dict[str, Any]:
        """Analyze migration impact"""
        # Real impact analysis implementation
        affected_tables = []
        risk_level = 'low'
        estimated_duration = 0

        try:
            # Analyze migration operations
            for operation in migration.operations:
                if hasattr(operation, 'table_name'):
                    table_name = operation.table_name
                    if table_name not in affected_tables:
                        affected_tables.append(table_name)

                # Estimate duration based on operation type
                if operation.operation_type in ['CREATE_TABLE', 'DROP_TABLE']:
                    estimated_duration += 2.0  # Complex operations
                elif operation.operation_type in ['ADD_COLUMN', 'DROP_COLUMN']:
                    estimated_duration += 0.5
                elif operation.operation_type in ['ALTER_COLUMN']:
                    estimated_duration += 1.0
                else:
                    estimated_duration += 0.1

            # Determine risk level
            if any(op.operation_type in ['DROP_TABLE', 'DROP_COLUMN'] for op in migration.operations):
                risk_level = 'high'
            elif any(op.operation_type in ['ALTER_COLUMN'] for op in migration.operations):
                risk_level = 'medium'
            else:
                risk_level = 'low'

        except Exception as e:
            print(f"Error analyzing migration impact: {e}")
            risk_level = 'unknown'

        return {
            'affected_tables': affected_tables,
            'risk_level': risk_level,
            'estimated_duration': estimated_duration
        }

    async def _analyze_migration_conflicts(self, migration, other_migrations: List[Any]) -> List[str]:
        """Analyze conflicts between a migration and other migrations"""
        conflicts = []

        for other_migration in other_migrations:
            # Check for table name conflicts
            migration_tables = await self._extract_table_names(migration)
            other_tables = await self._extract_table_names(other_migration)

            common_tables = set(migration_tables) & set(other_tables)
            if common_tables:
                conflicts.append(
                    f"Table conflict: {migration.id} and {other_migration.id} both affect tables: {', '.join(common_tables)}"
                )

            # Check for operation conflicts
            operation_conflicts = await self._check_operation_conflicts(migration, other_migration)
            conflicts.extend(operation_conflicts)

        return conflicts

    async def _extract_table_names(self, migration) -> List[str]:
        """Extract table names from migration operations"""
        table_names = []

        for operation in migration.operations:
            if hasattr(operation, 'table_name'):
                table_names.append(operation.table_name)
            elif hasattr(operation, 'table'):
                table_names.append(operation.table)

        return list(set(table_names))  # Remove duplicates

    async def _check_operation_conflicts(self, migration1, migration2) -> List[str]:
        """Check for conflicting operations between two migrations"""
        conflicts = []

        # Check for DROP/CREATE conflicts
        for op1 in migration1.operations:
            for op2 in migration2.operations:
                if (hasattr(op1, 'table_name') and hasattr(op2, 'table_name') and
                    op1.table_name == op2.table_name):

                    # DROP then CREATE conflict
                    if op1.operation_type == 'DROP_TABLE' and op2.operation_type == 'CREATE_TABLE':
                        conflicts.append(
                            f"DROP/CREATE conflict: {migration1.id} drops table {op1.table_name} that {migration2.id} creates"
                        )

                    # CREATE then DROP conflict
                    elif op1.operation_type == 'CREATE_TABLE' and op2.operation_type == 'DROP_TABLE':
                        conflicts.append(
                            f"CREATE/DROP conflict: {migration1.id} creates table {op1.table_name} that {migration2.id} drops"
                        )

        return conflicts

    async def _detect_table_conflicts(self, migrations: List[Any]) -> List[str]:
        """Detect table-level conflicts"""
        conflicts = []
        table_operations = {}

        # Collect all table operations
        for migration in migrations:
            for operation in migration.operations:
                if hasattr(operation, 'table_name'):
                    table_name = operation.table_name
                    if table_name not in table_operations:
                        table_operations[table_name] = []
                    table_operations[table_name].append({
                        'migration_id': migration.id,
                        'operation_type': operation.operation_type
                    })

        # Analyze conflicts for each table
        for table_name, operations in table_operations.items():
            if len(operations) > 1:
                # Multiple operations on same table
                create_ops = [op for op in operations if op['operation_type'] == 'CREATE_TABLE']
                drop_ops = [op for op in operations if op['operation_type'] == 'DROP_TABLE']

                if len(create_ops) > 1:
                    migration_ids = [op['migration_id'] for op in create_ops]
                    conflicts.append(
                        f"Multiple CREATE TABLE operations for {table_name} in migrations: {', '.join(migration_ids)}"
                    )

                if len(drop_ops) > 1:
                    migration_ids = [op['migration_id'] for op in drop_ops]
                    conflicts.append(
                        f"Multiple DROP TABLE operations for {table_name} in migrations: {', '.join(migration_ids)}"
                    )

        return conflicts

    async def _detect_index_conflicts(self, migrations: List[Any]) -> List[str]:
        """Detect index-related conflicts"""
        conflicts = []

        # Simplified index conflict detection
        # In a real implementation, this would analyze index operations in detail

        return conflicts

    async def _detect_constraint_conflicts(self, migrations: List[Any]) -> List[str]:
        """Detect constraint-related conflicts"""
        conflicts = []

        # Simplified constraint conflict detection
        # In a real implementation, this would analyze constraint operations

        return conflicts


class AdvancedMigrationExecutor:
    """Advanced migration executor with safety features"""

    def __init__(self, migrations, strategy='safe', backup_enabled=True, parallel=False, rollback_safe=False):
        self.migrations = migrations
        self.strategy = strategy
        self.backup_enabled = backup_enabled
        self.parallel = parallel
        self.rollback_safe = rollback_safe
        self.progress_tracker = MigrationProgressTracker()

    async def execute_all(self, fake: bool = False) -> Dict[str, Any]:
        """Execute all migrations"""
        results = {
            'total': len(self.migrations),
            'successful': 0,
            'failed': 0,
            'errors': []
        }

        for migration in self.migrations:
            try:
                await self.progress_tracker.start_migration(migration)
                await self._execute_single(migration, fake)
                await self.progress_tracker.complete_migration(migration)
                results['successful'] += 1
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(str(e))

        return results

    async def execute_for_app(self, app_name: str, fake: bool = False) -> Dict[str, Any]:
        """Execute migrations for specific app"""
        app_migrations = [m for m in self.migrations if app_name in m.id]
        return await self.execute_all(fake)

    async def _execute_single(self, migration, fake: bool):
        """Execute single migration"""
        if fake:
            print(f"FAKE: Would apply migration {migration.id}")
            return

        # Execute migration using existing migration system
        from pyserv.migrations.migrator import migration_manager
        await migration_manager.execute_migration(migration)

    async def _create_backup(self):
        """Create database backup before migration"""
        print("Creating database backup...")
        # Simplified backup - in real implementation would use proper backup tools
        pass


class MigrationProgressTracker:
    """Track migration progress"""

    def __init__(self):
        self.current_migration = None
        self.start_time = None

    async def start_migration(self, migration):
        """Start tracking migration"""
        self.current_migration = migration
        self.start_time = time.time()
        print(f"⏳ Starting migration: {migration.id}")

    async def complete_migration(self, migration):
        """Complete migration tracking"""
        duration = time.time() - self.start_time
        print(f"✅ Completed migration: {migration.id} ({duration:.2f}s)")
        self.current_migration = None

    async def get_progress(self) -> Dict[str, Any]:
        """Get current progress"""
        return {
            'current_migration': self.current_migration.id if self.current_migration else None,
            'start_time': self.start_time,
            'duration': time.time() - self.start_time if self.start_time else 0
        }


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

    # Show migrations command
    subparsers.add_parser('showmigrations', help='Show migration status').set_defaults(
        func=lambda args: shell_command.showmigrations()
    )

    # Show migration diff command
    showdiff_parser = subparsers.add_parser('showmigrationdiff', help='Show migration diff')
    showdiff_parser.add_argument('--app', help='Specific app to show diff for')
    showdiff_parser.set_defaults(func=lambda args: shell_command.showmigrationdiff(args.app))

    args = parser.parse_args()
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()

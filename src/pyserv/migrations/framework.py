"""
Migration framework integration for Pyserv.
Provides high-level migration functions and model introspection.
"""

import asyncio
import logging
import inspect
from typing import Dict, List, Any, Optional, Type
from datetime import datetime
from pathlib import Path

from pyserv.database.database_pool import DatabaseConnection
from pyserv.database.config import DatabaseConfig
from pyserv.models.base import BaseModel
from .migrator import MigrationRunner, MigrationManager, Migrator
from .migration import Migration, MigrationOperation, MigrationOperationType


class MigrationFramework:
    """High-level migration framework for Pyserv applications"""

    def __init__(self, db_config: DatabaseConfig = None):
        self.db_config = db_config
        self.migration_manager = MigrationManager(db_config)
        self.logger = logging.getLogger("migration_framework")

    async def initialize(self):
        """Initialize the migration framework"""
        await self.migration_manager.initialize()

    async def discover_models(self, package_name: str) -> List[Type[BaseModel]]:
        """Discover all BaseModel subclasses in a package"""
        models = []

        try:
            import importlib
            package = importlib.import_module(package_name)

            # Get all members of the package
            for name, obj in inspect.getmembers(package):
                if (inspect.isclass(obj) and
                    issubclass(obj, BaseModel) and
                    obj != BaseModel):
                    models.append(obj)

            # Also check submodules
            package_path = Path(package.__file__).parent
            for py_file in package_path.glob("*.py"):
                if py_file.name.startswith("__"):
                    continue

                module_name = f"{package_name}.{py_file.stem}"
                try:
                    module = importlib.import_module(module_name)
                    for name, obj in inspect.getmembers(module):
                        if (inspect.isclass(obj) and
                            issubclass(obj, BaseModel) and
                            obj != BaseModel):
                            if obj not in models:
                                models.append(obj)
                except ImportError:
                    continue

        except ImportError as e:
            self.logger.warning(f"Could not import package {package_name}: {e}")

        return models

    async def analyze_model_changes(self, models: List[Type[BaseModel]]) -> Dict[str, Any]:
        """Analyze models for changes that need migrations"""
        changes = {
            'models': {},
            'fields': {},
            'relationships': {}
        }

        # This would compare models with database schema
        # For now, return basic structure
        for model in models:
            model_name = model.__name__
            changes['models'][model_name] = {
                'create': True,  # Assume new model needs creation
                'fields': {},
                'relationships': {}
            }

            # Analyze fields
            if hasattr(model, '_fields'):
                for field_name, field in model._fields.items():
                    changes['models'][model_name]['fields'][field_name] = {
                        'type': str(field.__class__.__name__),
                        'options': getattr(field, 'options', {})
                    }

        return changes

    async def create_migration_from_models(self, models: List[Type[BaseModel]], name: str = None) -> Migration:
        """Create a migration from model analysis"""
        changes = await self.analyze_model_changes(models)

        # Create migration operations
        operations = []

        for model_name, model_changes in changes['models'].items():
            if model_changes.get('create'):
                operations.append(MigrationOperation(
                    operation_type=MigrationOperationType.CREATE_MODEL,
                    model_name=model_name
                ))

            for field_name, field_info in model_changes.get('fields', {}).items():
                operations.append(MigrationOperation(
                    operation_type=MigrationOperationType.ADD_FIELD,
                    model_name=model_name,
                    field_name=field_name,
                    field_type=field_info['type'],
                    field_options=field_info['options']
                ))

        # Generate migration ID
        timestamp = int(datetime.now().timestamp())
        migration_id = f"{timestamp:010d}"

        if not name:
            name = f"auto_{migration_id}"

        migration = Migration(
            id=migration_id,
            name=name,
            description=f"Auto-generated migration from model analysis: {name}",
            version=1,
            operations=operations
        )

        return migration

    async def migrate_app(self, app_package: str, dry_run: bool = False) -> Dict[str, Any]:
        """Migrate an entire application"""
        await self.initialize()

        # Discover models
        models = await self.discover_models(app_package)

        if not models:
            return {
                'success': True,
                'message': f'No models found in {app_package}',
                'models_processed': 0,
                'migrations_applied': 0,
                'migrations': []
            }

        # Create migration from models
        migration = await self.create_migration_from_models(models)

        if not migration.operations:
            return {
                'success': True,
                'message': 'No changes detected',
                'models_processed': len(models),
                'migrations_applied': 0,
                'migrations': []
            }

        # Save migration to file
        from .migration import MigrationGenerator
        generator = MigrationGenerator()
        migration_file = generator.save_migration_file(migration)

        if dry_run:
            return {
                'success': True,
                'message': 'Dry run completed',
                'models_processed': len(models),
                'migrations_applied': 0,
                'migrations': [{
                    'id': migration.id,
                    'name': migration.name,
                    'operations': len(migration.operations),
                    'file': str(migration_file)
                }]
            }

        # Apply migration
        runner = MigrationRunner(self.db_config)
        await runner.initialize()

        try:
            success = await runner.apply_migration(migration)

            if success:
                return {
                    'success': True,
                    'message': f'Successfully applied migration {migration.id}',
                    'models_processed': len(models),
                    'migrations_applied': 1,
                    'migrations': [{
                        'id': migration.id,
                        'name': migration.name,
                        'operations': len(migration.operations),
                        'file': str(migration_file)
                    }]
                }
            else:
                return {
                    'success': False,
                    'message': f'Failed to apply migration {migration.id}',
                    'models_processed': len(models),
                    'migrations_applied': 0,
                    'migrations': []
                }

        except Exception as e:
            return {
                'success': False,
                'message': f'Migration failed: {e}',
                'models_processed': len(models),
                'migrations_applied': 0,
                'migrations': []
            }

    async def check_migration_status(self, app_package: str) -> Dict[str, Any]:
        """Check migration status for an application"""
        await self.initialize()

        # Discover models
        models = await self.discover_models(app_package)

        # Get migration status
        runner = MigrationRunner(self.db_config)
        await runner.initialize()
        migration_statuses = await runner.get_migration_status()

        # Analyze each model
        model_statuses = []
        up_to_date = 0
        needs_update = 0

        for model in models:
            model_name = model.__name__

            # Check if model has corresponding migration
            model_migrations = [ms for ms in migration_statuses if model_name.lower() in ms.name.lower()]

            if model_migrations:
                latest_migration = max(model_migrations, key=lambda x: x.migration_id)
                if latest_migration.applied:
                    up_to_date += 1
                    model_statuses.append({
                        'name': model_name,
                        'up_to_date': True,
                        'current_version': 1,
                        'target_version': 1,
                        'last_migration': latest_migration.migration_id
                    })
                else:
                    needs_update += 1
                    model_statuses.append({
                        'name': model_name,
                        'up_to_date': False,
                        'current_version': 0,
                        'target_version': 1,
                        'last_migration': latest_migration.migration_id
                    })
            else:
                needs_update += 1
                model_statuses.append({
                    'name': model_name,
                    'up_to_date': False,
                    'current_version': 0,
                    'target_version': 1,
                    'last_migration': None
                })

        return {
            'total_models': len(models),
            'up_to_date': up_to_date,
            'needs_update': needs_update,
            'models': model_statuses
        }


# Global framework instance
migration_framework = MigrationFramework()

async def migrate_app(db_config: DatabaseConfig = None, app_package: str = 'app.models', dry_run: bool = False) -> Dict[str, Any]:
    """Migrate an entire application"""
    framework = MigrationFramework(db_config)
    return await framework.migrate_app(app_package, dry_run)

async def check_migration_status(db_config: DatabaseConfig = None, app_package: str = 'app.models') -> Dict[str, Any]:
    """Check migration status for an application"""
    framework = MigrationFramework(db_config)
    return await framework.check_migration_status(app_package)

async def discover_models(package_name: str) -> List[Type[BaseModel]]:
    """Discover all BaseModel subclasses in a package"""
    framework = MigrationFramework()
    return await framework.discover_models(package_name)

async def analyze_model_changes(models: List[Type[BaseModel]]) -> Dict[str, Any]:
    """Analyze models for changes that need migrations"""
    framework = MigrationFramework()
    return await framework.analyze_model_changes(models)

__all__ = [
    'MigrationFramework', 'migration_framework', 'migrate_app',
    'check_migration_status', 'discover_models', 'analyze_model_changes'
]

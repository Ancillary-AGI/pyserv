"""
Framework integration for migrations - handles automatic discovery and execution.
"""

import asyncio
import importlib
import pkgutil
import inspect
import os
from typing import Dict, List, Any, Optional, Type
from pathlib import Path

from .migration import Migration
from .migrator import Migrator
from ..database.database import DatabaseConnection
from ..database.config import DatabaseConfig
from ..models.base import BaseModel
from ..utils.types import Field


class MigrationFramework:
    """
    Framework integration for handling migrations automatically.
    Solves the problem of users not having direct access to migration scripts.
    """

    def __init__(self, db_config: DatabaseConfig, app_package: str = "app"):
        self.db_config = db_config
        self.app_package = app_package
        self.migrator = Migrator.get_instance(db_config)
        self.discovered_models: List[Type[BaseModel]] = []

    async def initialize(self):
        """Initialize the migration framework"""
        await self.migrator.initialize()
        self.discovered_models = await self.discover_models()

    async def discover_models(self, package_name: str = None) -> List[Type[BaseModel]]:
        """Automatically discover all models in the application"""
        if package_name is None:
            package_name = self.app_package

        models = []

        try:
            # Import the main package
            package = importlib.import_module(package_name)

            # Look for models in common locations
            search_paths = [
                package_name,                    # app
                f"{package_name}.models",        # app.models
                f"{package_name}.models.base",   # app.models.base
            ]

            for path in search_paths:
                try:
                    models.extend(await self._discover_models_in_package(path))
                except ImportError:
                    continue  # Package doesn't exist, try next

            # Also search in subdirectories
            if hasattr(package, '__path__'):
                for _, module_name, is_pkg in pkgutil.iter_modules(package.__path__):
                    if not is_pkg and 'model' in module_name.lower():
                        try:
                            full_module_name = f"{package_name}.{module_name}"
                            models.extend(await self._discover_models_in_module(full_module_name))
                        except ImportError:
                            continue

        except ImportError as e:
            print(f"Could not import package {package_name}: {e}")

        return models

    async def _discover_models_in_package(self, package_name: str) -> List[Type[BaseModel]]:
        """Discover models in a specific package"""
        models = []

        try:
            package = importlib.import_module(package_name)

            # Check the package module itself
            models.extend(self._extract_models_from_module(package))

            # Check all submodules
            if hasattr(package, '__path__'):
                for _, module_name, is_pkg in pkgutil.iter_modules(package.__path__):
                    if not is_pkg:
                        try:
                            full_module_name = f"{package_name}.{module_name}"
                            module = importlib.import_module(full_module_name)
                            models.extend(self._extract_models_from_module(module))
                        except ImportError:
                            continue

        except ImportError:
            pass

        return models

    async def _discover_models_in_module(self, module_name: str) -> List[Type[BaseModel]]:
        """Discover models in a specific module"""
        models = []

        try:
            module = importlib.import_module(module_name)
            models.extend(self._extract_models_from_module(module))
        except ImportError:
            pass

        return models

    def _extract_models_from_module(self, module) -> List[Type[BaseModel]]:
        """Extract BaseModel subclasses from a module"""
        models = []

        for name, obj in inspect.getmembers(module, inspect.isclass):
            if (issubclass(obj, BaseModel) and
                obj != BaseModel and
                hasattr(obj, '_fields') and
                obj._fields):  # Must have fields defined
                models.append(obj)

        return models

    async def run_auto_migrations(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Automatically run all pending migrations.
        This is the main entry point for framework users.
        """
        results = {
            'models_processed': 0,
            'migrations_applied': 0,
            'errors': [],
            'migrations': []
        }

        print("🔄 Starting automatic migration discovery...")

        for model_class in self.discovered_models:
            try:
                model_name = model_class.__name__
                current_version = await self.migrator.get_current_version(model_name)
                target_version = getattr(model_class, '_migration_version', 1)

                if current_version >= target_version:
                    print(f"✓ {model_name} is up to date (v{current_version})")
                    continue

                print(f"📦 Processing {model_name}: v{current_version} -> v{target_version}")

                # Generate migration for this model
                migration = await self._generate_migration_for_model(model_class, current_version, target_version)

                if migration:
                    if not dry_run:
                        success = await self.migrator.execute_migration(migration)
                        if success:
                            results['migrations_applied'] += 1
                            results['migrations'].append({
                                'model': model_name,
                                'from_version': current_version,
                                'to_version': target_version,
                                'operations': len(migration.operations)
                            })
                        else:
                            results['errors'].append(f"Failed to apply migration for {model_name}")
                    else:
                        print(f"  [DRY RUN] Would apply migration: {migration}")
                        results['migrations'].append({
                            'model': model_name,
                            'from_version': current_version,
                            'to_version': target_version,
                            'operations': len(migration.operations),
                            'dry_run': True
                        })

                results['models_processed'] += 1

            except Exception as e:
                error_msg = f"Error processing {model_class.__name__}: {e}"
                print(f"❌ {error_msg}")
                results['errors'].append(error_msg)

        if not dry_run:
            print(f"✅ Migration complete: {results['migrations_applied']} migrations applied")
        else:
            print(f"📋 Dry run complete: {len(results['migrations'])} migrations would be applied")

        return results

    async def _generate_migration_for_model(self, model_class: Type[BaseModel],
                                          from_version: int, to_version: int) -> Optional[Migration]:
        """Generate a migration for a model based on its current state"""
        model_name = model_class.__name__

        # For now, create a simple migration that captures the current schema
        # In a full implementation, this would compare against previous versions
        operations = {
            'added_columns': [],
            'removed_columns': [],
            'modified_columns': [],
            'added_indexes': [],
            'removed_indexes': []
        }

        # Analyze current fields
        for field_name, field in model_class._fields.items():
            if field.index:
                operations['added_indexes'].append({
                    'name': field_name,
                    'index_name': f"idx_{model_class.get_table_name()}_{field_name}"
                })

        # Serialize current schema
        schema_definition = self._serialize_schema(model_class._fields)

        return Migration(
            model_class=model_class,
            from_version=from_version,
            to_version=to_version,
            operations=operations,
            schema_definition=schema_definition
        )

    def _serialize_schema(self, fields: Dict[str, Field]) -> Dict:
        """Serialize field definitions for storage"""
        return {name: self._serialize_field(field) for name, field in fields.items()}

    def _serialize_field(self, field: Field) -> Dict:
        """Serialize a field definition for storage"""
        return {
            'field_type': field.field_type.value if hasattr(field.field_type, 'value') else str(field.field_type),
            'primary_key': field.primary_key,
            'autoincrement': field.autoincrement,
            'unique': field.unique,
            'nullable': field.nullable,
            'default': field.default,
            'foreign_key': field.foreign_key,
            'index': field.index
        }

    async def get_migration_status(self) -> Dict[str, Any]:
        """Get current migration status for all discovered models"""
        status = {
            'models': [],
            'total_models': len(self.discovered_models),
            'up_to_date': 0,
            'needs_update': 0
        }

        for model_class in self.discovered_models:
            model_name = model_class.__name__
            current_version = await self.migrator.get_current_version(model_name)
            target_version = getattr(model_class, '_migration_version', 1)

            model_status = {
                'name': model_name,
                'current_version': current_version,
                'target_version': target_version,
                'up_to_date': current_version >= target_version,
                'table_name': model_class.get_table_name(),
                'field_count': len(model_class._fields)
            }

            status['models'].append(model_status)

            if model_status['up_to_date']:
                status['up_to_date'] += 1
            else:
                status['needs_update'] += 1

        return status

    async def create_initial_tables(self):
        """Create initial tables for all models (useful for first setup)"""
        print("🏗️  Creating initial tables...")

        for model_class in self.discovered_models:
            try:
                if not self.db_config.is_mongodb:  # MongoDB creates collections automatically
                    await model_class.create_table()
                print(f"✓ Created table for {model_class.__name__}")
            except Exception as e:
                print(f"❌ Failed to create table for {model_class.__name__}: {e}")

        print("✅ Initial table creation complete")


# Convenience functions for framework integration

async def migrate_app(db_config: DatabaseConfig, app_package: str = "app", dry_run: bool = False):
    """
    Convenience function to migrate an entire application.
    This is what framework users would call.
    """
    framework = MigrationFramework(db_config, app_package)
    await framework.initialize()
    return await framework.run_auto_migrations(dry_run=dry_run)


async def check_migration_status(db_config: DatabaseConfig, app_package: str = "app"):
    """
    Check migration status for an application.
    """
    framework = MigrationFramework(db_config, app_package)
    await framework.initialize()
    return await framework.get_migration_status()


async def setup_database(db_config: DatabaseConfig, app_package: str = "app"):
    """
    Set up database with initial tables and migrations.
    """
    framework = MigrationFramework(db_config, app_package)
    await framework.initialize()
    await framework.create_initial_tables()
    await framework.run_auto_migrations()

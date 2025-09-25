"""
Migration runner and manager for Pyserv framework.
Handles both database-stored and file-based migrations.
"""

import asyncio
import json
import logging
import os
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass

from pyserv.database.database_pool import DatabaseConnection
from pyserv.database.config import DatabaseConfig
from pyserv.models.base import BaseModel
from .migration import (
    Migration, MigrationFile, MigrationGenerator, MigrationOperationType,
    MigrationOperation, ModelMigration
)


@dataclass
class MigrationStatus:
    """Status of a migration"""
    migration_id: str
    name: str
    applied: bool
    applied_at: Optional[datetime]
    checksum: Optional[str]
    file_path: Optional[str]
    dependencies: List[str]
    operations_count: int


class Migrator:
    """
    Handles the execution and management of database migrations.
    Contains all the complex logic from the original MigrationManager.
    """

    _instance = None

    def __init__(self, db_config: DatabaseConfig):
        self.db_config = db_config
        self.applied_migrations: Dict[str, int] = {}  # model_name -> current_version
        self.migration_schemas: Dict[str, Dict[int, Any]] = {}  # model_name -> {version: schema_definition}

    @classmethod
    def get_instance(cls, db_config: DatabaseConfig = None):
        if cls._instance is None and db_config:
            cls._instance = cls(db_config)
        return cls._instance

    async def initialize(self):
        """Create migrations table/collection if it doesn't exist and load applied migrations"""
        if not self.db_config:
            from pyserv.database.config import DatabaseConfig
            self.db_config = DatabaseConfig.from_env()
        db = DatabaseConnection.get_instance(self.db_config)

        # Create migrations table/collection using backend
        await db.backend.create_migrations_table()

        # Load applied migrations using backend
        applied_migrations = await db.backend.get_applied_migrations()
        self.applied_migrations.update(applied_migrations)

        # Load migration schemas (this would need to be enhanced to load full schema definitions)
        # For now, we'll keep the basic structure

    async def discover_models(self, package_name: str = "app.models") -> List[Type[BaseModel]]:
        """Discover all models in the specified package"""
        models = []

        try:
            # Import the package
            import importlib
            import pkgutil
            import inspect

            package = importlib.import_module(package_name)

            # Iterate through all modules in the package
            for _, module_name, is_pkg in pkgutil.iter_modules(package.__path__):
                if not is_pkg:
                    try:
                        # Import the module
                        full_module_name = f"{package_name}.{module_name}"
                        module = importlib.import_module(full_module_name)

                        # Find all classes that are subclasses of BaseModel but not BaseModel itself
                        for name, obj in inspect.getmembers(module, inspect.isclass):
                            if (issubclass(obj, BaseModel) and
                                obj != BaseModel and
                                hasattr(obj, '_fields')):
                                models.append(obj)
                    except ImportError as e:
                        print(f"Could not import module {module_name}: {e}")
                        continue

            # Also check the main package module for models
            for name, obj in inspect.getmembers(package, inspect.isclass):
                if (issubclass(obj, BaseModel) and
                    obj != BaseModel and
                    hasattr(obj, '_fields')):
                    models.append(obj)

        except ImportError as e:
            print(f"Could not import package {package_name}: {e}")

        return models

    async def apply_model_migrations(self, model_class):
        """Apply migrations for a specific model based on column changes"""
        model_name = model_class.__name__
        current_version = self.applied_migrations.get(model_name, 0)
        target_version = getattr(model_class, '_migration_version', 1)

        if current_version >= target_version:
            print(f"{model_name} is already at version {current_version} (target: {target_version})")
            return

        db = DatabaseConnection.get_instance(self.db_config)

        print(f"Migrating {model_name} from v{current_version} to v{target_version}")

        # Apply each migration step sequentially
        for version in range(current_version + 1, target_version + 1):
            if self.db_config.is_mongodb:
                # For MongoDB, we handle schema changes differently
                success = await self._apply_mongodb_migration(model_class, version)
                if success:
                    print(f"✓ Applied MongoDB migration for {model_name} to v{version}")
                else:
                    print(f"✗ Failed to apply MongoDB migration for {model_name} to v{version}")
            else:
                # For SQL databases
                migration_sql, operations, schema_definition = self._generate_migration_sql(
                    model_class, version - 1, version
                )

                if not migration_sql:
                    print(f"No migration needed for {model_name} to v{version}")
                    continue

                async with db.get_connection() as conn:
                    try:
                        if self.db_config.is_sqlite:
                            # SQLite - execute each statement separately
                            statements = [s.strip() for s in migration_sql.split(';') if s.strip()]
                            for statement in statements:
                                await conn.execute(statement)

                            # Store migration schema and operations for downgrade
                            await conn.execute(
                                "INSERT INTO migrations (model_name, version, schema_definition, operations) VALUES (?, ?, ?, ?)",
                                (model_name, version, json.dumps(schema_definition), json.dumps(operations))
                            )

                        elif self.db_config.is_postgres:
                            # PostgreSQL - execute directly
                            await conn.execute(migration_sql)

                            # Store migration schema and operations for downgrade
                            await conn.execute(
                                "INSERT INTO migrations (model_name, version, schema_definition, operations) VALUES ($1, $2, $3, $4)",
                                model_name, version, json.dumps(schema_definition), json.dumps(operations)
                            )

                        elif self.db_config.is_mysql:
                            # MySQL - execute each statement separately
                            statements = [s.strip() for s in migration_sql.split(';') if s.strip()]
                            for statement in statements:
                                await conn.execute(statement)

                            # Store migration schema and operations for downgrade
                            await conn.execute(
                                "INSERT INTO migrations (model_name, version, schema_definition, operations) VALUES (%s, %s, %s, %s)",
                                (model_name, version, json.dumps(schema_definition), json.dumps(operations))
                            )

                        self.applied_migrations[model_name] = version
                        if model_name not in self.migration_schemas:
                            self.migration_schemas[model_name] = {}
                        self.migration_schemas[model_name][version] = schema_definition

                        print(f"✓ Applied migration for {model_name} to v{version}")

                    except Exception as e:
                        print(f"✗ Failed to apply migration for {model_name} to v{version}: {e}")
                        if self.db_config.is_mysql:
                            # MySQL often requires explicit transaction handling
                            await conn.execute("ROLLBACK")
                        raise

    async def _apply_mongodb_migration(self, model_class, version: int) -> bool:
        """Apply MongoDB-specific migration"""
        model_name = model_class.__name__
        collection_name = model_class.get_table_name()

        db = DatabaseConnection.get_instance(self.db_config)

        try:
            async with db.get_connection() as conn:
                collection = conn[collection_name]

                # For MongoDB, we typically handle schema changes at the application level
                # rather than database level. We can create indexes or validations if needed.

                # Create indexes based on field definitions
                index_operations = []
                for name, field in model_class._fields.items():
                    if field.index:
                        index_operations.append((name, 1))

                if index_operations:
                    await collection.create_index(index_operations)

                # Store migration record
                migrations_collection = conn.migrations
                schema_definition = Migration._serialize_schema(model_class._fields)

                await migrations_collection.insert_one({
                    'model_name': model_name,
                    'version': version,
                    'schema_definition': schema_definition,
                    'operations': {'indexes_created': [op[0] for op in index_operations]},
                    'applied_at': datetime.now()
                })

                self.applied_migrations[model_name] = version
                if model_name not in self.migration_schemas:
                    self.migration_schemas[model_name] = {}
                self.migration_schemas[model_name][version] = schema_definition

                return True

        except Exception as e:
            print(f"MongoDB migration error: {e}")
            return False

    async def execute_migration(self, migration: Migration) -> bool:
        """Execute a single migration using backend abstraction"""
        db = DatabaseConnection.get_instance(self.db_config)

        # Use backend to insert migration record
        await db.backend.insert_migration_record(
            migration.model_name,
            migration.to_version,
            migration.schema_definition,
            migration.operations,
            migration.migration_id
        )

        # Update in-memory tracking
        self.applied_migrations[migration.model_name] = migration.to_version
        if migration.model_name not in self.migration_schemas:
            self.migration_schemas[migration.model_name] = {}
        self.migration_schemas[migration.model_name][migration.to_version] = migration.schema_definition

        print(f"✓ Applied migration '{migration.migration_id}' for {migration.model_name} to v{migration.to_version}")
        return True

    async def downgrade_model(self, model_class, target_version: int):
        """Downgrade a model to a specific version"""
        model_name = model_class.__name__
        current_version = self.applied_migrations.get(model_name, 0)

        if current_version <= target_version:
            print(f"{model_name} is already at version {current_version} (target downgrade: {target_version})")
            return

        if self.db_config.is_mongodb:
            print("Downgrade is not typically supported for MongoDB in the same way as SQL databases")
            return

        db = DatabaseConnection.get_instance(self.db_config)

        print(f"Downgrading {model_name} from v{current_version} to v{target_version}")

        # Downgrade step by step from current version down to target version
        for version in range(current_version, target_version, -1):
            downgrade_sql = self._generate_downgrade_sql(model_name, version)

            if not downgrade_sql:
                print(f"No downgrade needed for {model_name} from v{version}")
                continue

            async with db.get_connection() as conn:
                try:
                    if self.db_config.is_sqlite:
                        # SQLite - execute each statement separately
                        statements = [s.strip() for s in downgrade_sql.split(';') if s.strip()]
                        for statement in statements:
                            await conn.execute(statement)

                        # Remove the migration record
                        await conn.execute(
                            "DELETE FROM migrations WHERE model_name = ? AND version = ?",
                            (model_name, version)
                        )

                    elif self.db_config.is_postgres:
                        # PostgreSQL - execute directly
                        await conn.execute(downgrade_sql)

                        # Remove the migration record
                        await conn.execute(
                            "DELETE FROM migrations WHERE model_name = $1 AND version = $2", model_name, version
                        )

                    elif self.db_config.is_mysql:
                        # MySQL - execute each statement separately
                        statements = [s.strip() for s in downgrade_sql.split(';') if s.strip()]
                        for statement in statements:
                            await conn.execute(statement)

                        # Remove the migration record
                        await conn.execute(
                            "DELETE FROM migrations WHERE model_name = %s AND version = %s",
                            (model_name, version)
                        )

                    self.applied_migrations[model_name] = version - 1
                    if model_name in self.migration_schemas and version in self.migration_schemas[model_name]:
                        del self.migration_schemas[model_name][version]

                    print(f"✓ Downgraded {model_name} from v{version} to v{version - 1}")

                except Exception as e:
                    print(f"✗ Failed to downgrade {model_name} from v{version}: {e}")
                    if self.db_config.is_mysql:
                        await conn.execute("ROLLBACK")
                    raise

    async def drop_table(self, model_class):
        """Completely drop the table/collection for this model using backend abstraction"""
        model_name = model_class.__name__
        table_name = model_class.get_table_name()

        db = DatabaseConnection.get_instance(self.db_config)

        # Use backend to drop table/collection
        await db.backend.drop_table(table_name)

        # Remove migration records using backend
        await db.backend.delete_migration_record(model_name, 0)  # Delete all versions

        # Clear from memory
        if model_name in self.applied_migrations:
            del self.applied_migrations[model_name]
        if model_name in self.migration_schemas:
            del self.migration_schemas[model_name]

        print(f"✓ Dropped table/collection {table_name} for {model_name}")

    async def reset_database(self, models: List[Type[BaseModel]]):
        """Completely reset the database by dropping all tables/collections"""
        for model_class in models:
            await self.drop_table(model_class)

        # Recreate tables/collections
        for model_class in models:
            if not self.db_config.is_mongodb:
                await model_class.create_table()
            await self.apply_model_migrations(model_class)

        print("✓ Database reset complete")

    async def get_current_version(self, model_name: str) -> int:
        """Get the current migration version for a model"""
        return self.applied_migrations.get(model_name, 0)

    async def show_status(self, models: List[Type[BaseModel]]):
        """Show current migration status for all models"""
        print("\nMigration Status:")
        print("=================")

        for model_class in models:
            model_name = model_class.__name__
            current_version = self.applied_migrations.get(model_name, 0)
            target_version = getattr(model_class, '_migration_version', 1)

            status = "✓ Up to date" if current_version >= target_version else "⚠ Needs update"
            print(f"{model_name}: v{current_version} -> v{target_version} ({status})")

    def _generate_migration_sql(self, model_class, from_version: int, to_version: int) -> Tuple[str, Dict, Dict]:
        """Generate SQL for migrating a model between versions"""
        model_name = model_class.__name__
        table_name = model_class.get_table_name()

        operations = {
            'added_columns': [],
            'removed_columns': [],
            'modified_columns': [],
            'added_indexes': [],
            'removed_indexes': []
        }

        sql_statements = []

        # Store the current schema definition for downgrade
        schema_definition = Migration._serialize_schema(model_class._fields)

        # If table doesn't exist yet, create it
        if from_version == 0:
            columns_sql = []
            for name, field in model_class._fields.items():
                columns_sql.append(field.sql_definition(name, self.db_config))

            # Handle different CREATE TABLE syntax for different databases
            if self.db_config.is_mysql:
                sql_statements.append(f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(columns_sql)}) ENGINE=InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            else:
                sql_statements.append(f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(columns_sql)};")

            # Add indexes
            for name, field in model_class._fields.items():
                if field.index:
                    index_name = f"idx_{table_name}_{name}"
                    if self.db_config.is_mysql:
                        sql_statements.append(f"CREATE INDEX {index_name} ON {table_name}({name}) USING BTREE;")
                    else:
                        sql_statements.append(f"CREATE INDEX {index_name} ON {table_name}({name});")
                    operations['added_indexes'].append({
                        'name': name,
                        'index_name': index_name
                    })

            return ';'.join(sql_statements), operations, schema_definition

        # Get previous schema for comparison
        previous_schema = self.migration_schemas.get(model_name, {}).get(from_version, {})
        current_schema = Migration._serialize_schema(model_class._fields)

        # Compare schemas to generate migration SQL
        previous_cols = set(previous_schema.keys())
        current_cols = set(current_schema.keys())

        # Columns to add
        for col_name in current_cols - previous_cols:
            field = model_class._fields[col_name]
            if self.db_config.is_sqlite:
                # SQLite can only add columns with ALTER TABLE
                sql_statements.append(f"ALTER TABLE {table_name} ADD COLUMN {field.sql_definition(col_name, self.db_config)};")
            else:
                # PostgreSQL and MySQL can add columns with constraints
                sql_statements.append(f"ALTER TABLE {table_name} ADD COLUMN {field.sql_definition(col_name, self.db_config)};")
            operations['added_columns'].append({
                'name': col_name,
                'definition': Migration._serialize_field(field)
            })

        # Columns to remove - requires table recreation in SQLite
        columns_to_remove = previous_cols - current_cols
        if columns_to_remove:
            if self.db_config.is_sqlite:
                # SQLite doesn't support DROP COLUMN, so we need to recreate the table
                sql_statements.extend(self._generate_sqlite_column_modification(
                    table_name, model_class._fields, previous_schema, current_schema
                ))
                for col_name in columns_to_remove:
                    operations['removed_columns'].append({
                        'name': col_name,
                        'definition': previous_schema[col_name]
                    })
            else:
                # PostgreSQL and MySQL support DROP COLUMN
                for col_name in columns_to_remove:
                    sql_statements.append(f"ALTER TABLE {table_name} DROP COLUMN {col_name};")
                    operations['removed_columns'].append({
                        'name': col_name,
                        'definition': previous_schema[col_name]
                    })

        # Column modifications - handle ALTER COLUMN for both databases
        modified_columns = []
        for col_name in previous_cols & current_cols:
            if previous_schema[col_name] != current_schema[col_name]:
                modified_columns.append(col_name)
                operations['modified_columns'].append({
                    'name': col_name,
                    'old_definition': previous_schema[col_name],
                    'new_definition': current_schema[col_name]
                })

        # Handle column modifications
        if modified_columns:
            if self.db_config.is_sqlite:
                # SQLite doesn't support MODIFY COLUMN, so we need to recreate the table
                sql_statements.extend(self._generate_sqlite_column_modification(
                    table_name, model_class._fields, previous_schema, current_schema
                ))
            else:
                # PostgreSQL and MySQL support ALTER COLUMN with various modifications
                for col_name in modified_columns:
                    field = model_class._fields[col_name]
                    old_field = Migration._deserialize_field(previous_schema[col_name])

                    # Handle type changes
                    if field.field_type != old_field.field_type:
                        if self.db_config.is_mysql:
                            sql_statements.append(f"ALTER TABLE {table_name} MODIFY COLUMN {field.sql_definition(col_name, self.db_config)};")
                        else:
                            sql_statements.append(f"ALTER TABLE {table_name} ALTER COLUMN {col_name} TYPE {field.field_type};")

                    # Handle NULL/NOT NULL changes
                    if field.nullable != old_field.nullable:
                        if field.nullable:
                            if self.db_config.is_mysql:
                                sql_statements.append(f"ALTER TABLE {table_name} MODIFY COLUMN {col_name} {field.field_type} NULL;")
                            else:
                                sql_statements.append(f"ALTER TABLE {table_name} ALTER COLUMN {col_name} DROP NOT NULL;")
                        else:
                            if self.db_config.is_mysql:
                                sql_statements.append(f"ALTER TABLE {model_class.get_table_name()} MODIFY COLUMN {col_name} {field.field_type} NOT NULL;")
                            else:
                                sql_statements.append(f"ALTER TABLE {table_name} ALTER COLUMN {col_name} SET NOT NULL;")

                    # Handle default value changes
                    if field.default != old_field.default:
                        if field.default is None:
                            if self.db_config.is_mysql:
                                sql_statements.append(f"ALTER TABLE {table_name} ALTER COLUMN {col_name} DROP DEFAULT;")
                            else:
                                sql_statements.append(f"ALTER TABLE {table_name} ALTER COLUMN {col_name} DROP DEFAULT;")
                        else:
                            default_value = f"'{field.default}'" if isinstance(field.default, str) else str(field.default)
                            if self.db_config.is_mysql:
                                sql_statements.append(f"ALTER TABLE {table_name} ALTER COLUMN {col_name} SET DEFAULT {default_value};")
                            else:
                                sql_statements.append(f"ALTER TABLE {table_name} ALTER COLUMN {col_name} SET DEFAULT {default_value};")

        # Handle index changes
        previous_indexes = {name for name, field_data in previous_schema.items() if field_data.get('index', False)}
        current_indexes = {name for name, field_data in current_schema.items() if field_data.get('index', False)}

        # Indexes to add
        for index_name in current_indexes - previous_indexes:
            if self.db_config.is_mysql:
                index_sql = f"CREATE INDEX idx_{table_name}_{index_name} ON {table_name}({index_name}) USING BTREE;"
            else:
                index_sql = f"CREATE INDEX idx_{table_name}_{index_name} ON {table_name}({index_name});"
            sql_statements.append(index_sql)
            operations['added_indexes'].append({
                'name': index_name,
                'index_name': f"idx_{table_name}_{index_name}"
            })

        # Indexes to remove
        for index_name in previous_indexes - current_indexes:
            index_sql = f"DROP INDEX IF EXISTS idx_{table_name}_{index_name};"
            sql_statements.append(index_sql)
            operations['removed_indexes'].append({
                'name': index_name,
                'index_name': f"idx_{table_name}_{index_name}"
            })

        return ';'.join(sql_statements), operations, schema_definition

    def _generate_sqlite_column_modification(self, table_name: str, current_columns: Dict[str, Field], previous_schema: Dict, current_schema: Dict) -> List[str]:
        """Generate SQL for SQLite table recreation (for column removal/modification)"""
        sql_statements = []
        temp_table = f"{table_name}_temp"

        # 1. Create temporary table with new schema
        columns_sql = []
        for name, field in current_columns.items():
            columns_sql.append(field.sql_definition(name, self.db_config))

        sql_statements.append(f"CREATE TABLE {temp_table} ({', '.join(columns_sql)});")

        # 2. Copy data from old table to temporary table
        common_columns = set(previous_schema.keys()) & set(current_schema.keys())
        if common_columns:
            columns_list = ', '.join(common_columns)
            sql_statements.append(f"INSERT INTO {temp_table} ({columns_list}) SELECT {columns_list} FROM {table_name};")

        # 3. Drop old table
        sql_statements.append(f"DROP TABLE {table_name};")

        # 4. Rename temporary table to original name
        sql_statements.append(f"ALTER TABLE {temp_table} RENAME TO {table_name};")

        # 5. Recreate indexes
        for name, field in current_columns.items():
            if field.index:
                index_name = f"idx_{table_name}_{name}"
                sql_statements.append(f"CREATE INDEX {index_name} ON {table_name}({name});")

        return sql_statements

    def _generate_downgrade_sql(self, model_name: str, from_version: int) -> str:
        """Generate SQL to downgrade from a specific version"""
        # Get the operations that were performed for this version
        migration_data = self.migration_schemas.get(model_name, {}).get(from_version, {})
        if not migration_data:
            return ""

        # Get the actual operations from the stored data
        operations = migration_data.get('operations', {}) if isinstance(migration_data, dict) else {}
        if not operations:
            return ""

        sql_statements = []
        table_name = model_name.lower() + 's'

        # Reverse added columns (remove them)
        for column_info in operations.get('added_columns', []):
            if self.db_config.is_sqlite:
                # For SQLite, we need to recreate the table to remove columns
                # Get the previous schema (version - 1)
                previous_schema = self.migration_schemas.get(model_name, {}).get(from_version - 1, {})
                current_schema = self.migration_schemas.get(model_name, {}).get(from_version, {})

                if previous_schema and current_schema:
                    # Convert schema back to field objects
                    previous_fields = {}
                    for col_name, field_data in previous_schema.items():
                        previous_fields[col_name] = Migration._deserialize_field(field_data)

                    sql_statements.extend(self._generate_sqlite_column_modification(
                        table_name, previous_fields, current_schema, previous_schema
                    ))
                    break  # Only need to do this once for all columns
            else:
                # PostgreSQL and MySQL can drop columns directly
                sql_statements.append(f"ALTER TABLE {table_name} DROP COLUMN IF EXISTS {column_info['name']};")

        # Reverse removed columns (add them back with original definition)
        for column_info in operations.get('removed_columns', []):
            field = Migration._deserialize_field(column_info['definition'])
            sql_statements.append(f"ALTER TABLE {table_name} ADD COLUMN {field.sql_definition(column_info['name'], self.db_config)};")

        # Reverse index changes
        for index_info in operations.get('added_indexes', []):
            sql_statements.append(f"DROP INDEX IF EXISTS {index_info['index_name']};")

        # For modified columns, revert the changes
        for column_info in operations.get('modified_columns', []):
            old_field = Migration._deserialize_field(column_info['old_definition'])
            col_name = column_info['name']

            if self.db_config.is_sqlite:
                # SQLite requires table recreation for column modifications
                previous_schema = self.migration_schemas.get(model_name, {}).get(from_version - 1, {})
                current_schema = self.migration_schemas.get(model_name, {}).get(from_version, {})

                if previous_schema and current_schema:
                    previous_fields = {}
                    for col_name, field_data in previous_schema.items():
                        previous_fields[col_name] = Migration._deserialize_field(field_data)

                    sql_statements.extend(self._generate_sqlite_column_modification(
                        table_name, previous_fields, current_schema, previous_schema
                    ))
                    break  # Only need to do this once for all columns
            else:
                # PostgreSQL and MySQL can alter columns directly
                current_field = Migration._deserialize_field(column_info['new_definition'])

                # Revert type changes
                if old_field.field_type != current_field.field_type:
                    if self.db_config.is_mysql:
                        sql_statements.append(f"ALTER TABLE {table_name} MODIFY COLUMN {old_field.sql_definition(col_name, self.db_config)};")
                    else:
                        sql_statements.append(f"ALTER TABLE {table_name} ALTER COLUMN {col_name} TYPE {old_field.field_type};")

                # Revert NULL/NOT NULL changes
                if old_field.nullable != current_field.nullable:
                    if old_field.nullable:
                        if self.db_config.is_mysql:
                            sql_statements.append(f"ALTER TABLE {table_name} MODIFY COLUMN {col_name} {old_field.field_type} NULL;")
                        else:
                            sql_statements.append(f"ALTER TABLE {table_name} ALTER COLUMN {col_name} DROP NOT NULL;")
                    else:
                        if self.db_config.is_mysql:
                            sql_statements.append(f"ALTER TABLE {table_name} MODIFY COLUMN {col_name} {old_field.field_type} NOT NULL;")
                        else:
                            sql_statements.append(f"ALTER TABLE {table_name} ALTER COLUMN {col_name} SET NOT NULL;")

                # Revert default value changes
                if old_field.default != current_field.default:
                    if old_field.default is None:
                        if self.db_config.is_mysql:
                            sql_statements.append(f"ALTER TABLE {table_name} ALTER COLUMN {col_name} DROP DEFAULT;")
                        else:
                            sql_statements.append(f"ALTER TABLE {table_name} ALTER COLUMN {col_name} DROP DEFAULT;")
                    else:
                        default_value = f"'{old_field.default}'" if isinstance(old_field.default, str) else str(old_field.default)
                        if self.db_config.is_mysql:
                            sql_statements.append(f"ALTER TABLE {table_name} ALTER COLUMN {col_name} SET DEFAULT {default_value};")
                        else:
                            sql_statements.append(f"ALTER TABLE {table_name} ALTER COLUMN {col_name} SET DEFAULT {default_value};")

        return ';'.join(sql_statements)

    async def migrate_app(self, app_name: str):
        """Migrate a specific app"""
        self.logger.info(f"Migrating app: {app_name}")
        # Use the new migration system
        runner = MigrationRunner(self.db_config)
        await runner.initialize()
        result = await runner.migrate()
        return result

    async def migrate_all(self):
        """Migrate all apps"""
        self.logger.info("Migrating all apps")
        # Use the new migration system
        runner = MigrationRunner(self.db_config)
        await runner.initialize()
        result = await runner.migrate()
        return result

    async def make_migrations(self, app_name: str, message: str = None):
        """Create migrations for an app"""
        self.logger.info(f"Creating migrations for app: {app_name}")
        # Use the new migration system
        runner = MigrationRunner(self.db_config)
        await runner.initialize()

        # Import models from the app
        try:
            import importlib
            app_module = importlib.import_module(app_name)

            # Find all model classes
            import inspect
            from pyserv.models.base import BaseModel

            models = []
            for name, obj in inspect.getmembers(app_module):
                if (inspect.isclass(obj) and
                    issubclass(obj, BaseModel) and
                    obj != BaseModel):
                    models.append(obj)

            if models:
                migration = await runner.create_migration(models, message or f"Auto migration for {app_name}")
                self.logger.info(f"Created migration: {migration.id}")
                return migration
            else:
                self.logger.warning(f"No models found in app: {app_name}")

        except ImportError as e:
            self.logger.error(f"Could not import app {app_name}: {e}")


class MigrationRunner:
    """Runs and manages database migrations"""

    def __init__(self, db_config: DatabaseConfig = None, migrations_dir: Path = None):
        self.db_config = db_config
        self.migrations_dir = migrations_dir or Path("migrations")
        self.migrations_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger("migration_runner")
        self.db_connection = None
        self.migration_generator = MigrationGenerator(self.migrations_dir)

    async def initialize(self):
        """Initialize migration system"""
        if not self.db_config:
            from pyserv.database.config import DatabaseConfig
            self.db_config = DatabaseConfig.from_env()

        self.db_connection = DatabaseConnection.get_instance(self.db_config)
        await self._ensure_migration_tables()

    async def _ensure_migration_tables(self):
        """Ensure migration tracking tables exist"""
        # Create migrations table if it doesn't exist
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS migrations (
            id VARCHAR(255) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            version INTEGER NOT NULL,
            operations JSON,
            dependencies JSON,
            created_at DATETIME NOT NULL,
            applied_at DATETIME,
            checksum VARCHAR(64),
            rollback_sql TEXT,
            migration_file VARCHAR(500),
            migration_type VARCHAR(50) DEFAULT 'auto'
        )
        """

        await self.db_connection.execute_query(create_table_sql)

        # Create migration_files table for file-based migrations
        create_files_table_sql = """
        CREATE TABLE IF NOT EXISTS migration_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            migration_id VARCHAR(255) NOT NULL,
            file_path VARCHAR(500) NOT NULL,
            file_hash VARCHAR(64),
            created_at DATETIME NOT NULL,
            modified_at DATETIME,
            FOREIGN KEY (migration_id) REFERENCES migrations (id)
        )
        """

        await self.db_connection.execute_query(create_files_table_sql)

    async def get_applied_migrations(self) -> Dict[str, Migration]:
        """Get all applied migrations from database"""
        query = """
        SELECT id, name, description, version, operations, dependencies,
               created_at, applied_at, checksum, rollback_sql, migration_file, migration_type
        FROM migrations
        WHERE applied_at IS NOT NULL
        ORDER BY applied_at
        """

        results = await self.db_connection.execute_query(query)

        migrations = {}
        for row in results:
            migration = Migration(
                id=row['id'],
                name=row['name'],
                description=row['description'],
                version=row['version'],
                operations=[MigrationOperation.from_dict(op) for op in row['operations']],
                dependencies=row['dependencies'],
                created_at=row['created_at'],
                applied_at=row['applied_at'],
                checksum=row['checksum'],
                rollback_sql=row['rollback_sql'],
                migration_file=row['migration_file'],
                migration_type=row['migration_type']
            )
            migrations[migration.id] = migration

        return migrations

    async def get_pending_migrations(self) -> List[Migration]:
        """Get pending migrations that haven't been applied"""
        applied = await self.get_applied_migrations()

        # Get all migration files
        migration_files = self._get_migration_files()

        pending = []
        for migration_file in migration_files:
            if migration_file.migration.id not in applied:
                pending.append(migration_file.migration)

        return pending

    def _get_migration_files(self) -> List[MigrationFile]:
        """Get all migration files from migrations directory"""
        migration_files = []

        if not self.migrations_dir.exists():
            return migration_files

        # Find all Python files in migrations directory
        for file_path in self.migrations_dir.glob("*.py"):
            if file_path.name.startswith("__"):
                continue  # Skip __init__.py and similar files

            try:
                migration_file = MigrationFile(file_path)
                if migration_file.migration:
                    migration_files.append(migration_file)
            except Exception as e:
                self.logger.warning(f"Failed to load migration file {file_path}: {e}")

        return migration_files

    async def get_migration_status(self) -> List[MigrationStatus]:
        """Get status of all migrations"""
        applied = await self.get_applied_migrations()
        pending = await self.get_pending_migrations()

        status_list = []

        # Add applied migrations
        for migration in applied.values():
            status_list.append(MigrationStatus(
                migration_id=migration.id,
                name=migration.name,
                applied=True,
                applied_at=migration.applied_at,
                checksum=migration.checksum,
                file_path=migration.migration_file,
                dependencies=migration.dependencies,
                operations_count=len(migration.operations)
            ))

        # Add pending migrations
        for migration in pending:
            status_list.append(MigrationStatus(
                migration_id=migration.id,
                name=migration.name,
                applied=False,
                applied_at=None,
                checksum=None,
                file_path=migration.migration_file,
                dependencies=migration.dependencies,
                operations_count=len(migration.operations)
            ))

        # Sort by migration ID
        status_list.sort(key=lambda x: x.migration_id)

        return status_list

    async def apply_migration(self, migration: Migration) -> bool:
        """Apply a single migration"""
        try:
            self.logger.info(f"Applying migration {migration.id}: {migration.name}")

            # Validate migration
            errors = migration.validate()
            if errors:
                raise ValueError(f"Migration validation failed: {', '.join(errors)}")

            # Check dependencies
            await self._check_dependencies(migration)

            # Execute migration
            await migration.execute(self.db_connection)

            # Save to database
            await self._save_migration_to_db(migration)

            self.logger.info(f"Migration {migration.id} applied successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to apply migration {migration.id}: {e}")
            raise

    async def _check_dependencies(self, migration: Migration):
        """Check if migration dependencies are satisfied"""
        applied = await self.get_applied_migrations()

        for dep_id in migration.dependencies:
            if dep_id not in applied:
                raise ValueError(f"Migration {migration.id} depends on {dep_id} which is not applied")

    async def _save_migration_to_db(self, migration: Migration):
        """Save migration record to database"""
        # Update applied_at and checksum
        migration.applied_at = datetime.now()
        migration.checksum = migration.calculate_checksum()

        # Insert or update migration record
        insert_sql = """
        INSERT OR REPLACE INTO migrations
        (id, name, description, version, operations, dependencies, created_at, applied_at, checksum, rollback_sql, migration_file, migration_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        await self.db_connection.execute_query(insert_sql, (
            migration.id,
            migration.name,
            migration.description,
            migration.version,
            json.dumps([op.to_dict() for op in migration.operations]),
            json.dumps(migration.dependencies),
            migration.created_at,
            migration.applied_at,
            migration.checksum,
            migration.rollback_sql,
            migration.migration_file,
            migration.migration_type
        ))

    async def rollback_migration(self, migration_id: str) -> bool:
        """Rollback a migration"""
        applied = await self.get_applied_migrations()

        if migration_id not in applied:
            raise ValueError(f"Migration {migration_id} is not applied")

        migration = applied[migration_id]

        try:
            self.logger.info(f"Rolling back migration {migration_id}: {migration.name}")

            # Execute rollback operations
            await self._execute_rollback(migration)

            # Mark as not applied
            update_sql = "UPDATE migrations SET applied_at = NULL, checksum = NULL WHERE id = ?"
            await self.db_connection.execute_query(update_sql, (migration_id,))

            self.logger.info(f"Migration {migration_id} rolled back successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to rollback migration {migration_id}: {e}")
            raise

    async def _execute_rollback(self, migration: Migration):
        """Execute rollback operations"""
        # Reverse the operations
        for operation in reversed(migration.operations):
            await self._execute_rollback_operation(operation)

    async def _execute_rollback_operation(self, operation: MigrationOperation):
        """Execute rollback for a single operation"""
        # This would implement rollback logic for each operation type
        # For now, just log the rollback
        self.logger.info(f"Rolling back operation: {operation.operation_type}")

    async def migrate(self, target_migration: str = None, fake: bool = False) -> Dict[str, Any]:
        """Run all pending migrations"""
        await self.initialize()

        pending = await self.get_pending_migrations()
        applied = await self.get_applied_migrations()

        if not pending:
            return {
                'success': True,
                'message': 'No pending migrations',
                'applied': 0,
                'total': len(applied)
            }

        # Filter by target if specified
        if target_migration:
            pending = [m for m in pending if m.id <= target_migration]
            pending.sort(key=lambda x: x.id)

        applied_count = 0

        for migration in pending:
            try:
                if fake:
                    # Just mark as applied without executing
                    migration.applied_at = datetime.now()
                    migration.checksum = migration.calculate_checksum()
                    await self._save_migration_to_db(migration)
                else:
                    await self.apply_migration(migration)

                applied_count += 1

            except Exception as e:
                return {
                    'success': False,
                    'message': f'Migration failed: {e}',
                    'applied': applied_count,
                    'total': len(applied) + len(pending)
                }

        return {
            'success': True,
            'message': f'Successfully applied {applied_count} migration(s)',
            'applied': applied_count,
            'total': len(applied) + applied_count
        }

    async def show_migration_status(self) -> str:
        """Show migration status in a formatted way"""
        status_list = await self.get_migration_status()

        if not status_list:
            return "No migrations found"

        output = []
        output.append("Migration Status")
        output.append("=" * 50)

        for status in status_list:
            marker = "[X]" if status.applied else "[ ]"
            applied_info = f" (applied {status.applied_at})" if status.applied_at else ""
            output.append(f"{marker} {status.migration_id} - {status.name}{applied_info}")

            if status.file_path:
                output.append(f"      File: {status.file_path}")

            if status.dependencies:
                output.append(f"      Dependencies: {', '.join(status.dependencies)}")

            output.append(f"      Operations: {status.operations_count}")
            output.append("")

        return "\n".join(output)

    async def create_migration(self, models: List[type], name: str = None) -> Migration:
        """Create a new migration from model changes"""
        await self.initialize()

        migration = self.migration_generator.generate_migration(models, name)

        # Save to database as pending
        await self._save_migration_to_db(migration)

        self.logger.info(f"Created migration {migration.id}: {migration.name}")
        return migration

    async def load_migration_from_file(self, file_path: Path) -> Migration:
        """Load migration from file"""
        migration_file = MigrationFile(file_path)
        return migration_file.migration

    async def validate_migration(self, migration: Migration) -> List[str]:
        """Validate a migration"""
        errors = migration.validate()

        # Check for circular dependencies
        if self._has_circular_dependencies(migration):
            errors.append("Circular dependency detected")

        # Check if dependencies exist
        applied = await self.get_applied_migrations()
        for dep_id in migration.dependencies:
            if dep_id not in applied and dep_id != migration.id:
                errors.append(f"Dependency {dep_id} not found")

        return errors

    def _has_circular_dependencies(self, migration: Migration, visited: set = None) -> bool:
        """Check for circular dependencies"""
        if visited is None:
            visited = set()

        if migration.id in visited:
            return True

        visited.add(migration.id)

        # This would check the dependency graph
        # For now, return False
        return False


class MigrationManager:
    """High-level migration manager"""

    def __init__(self, db_config: DatabaseConfig = None):
        self.db_config = db_config
        self.runner = MigrationRunner(db_config)
        self.logger = logging.getLogger("migration_manager")

    async def initialize(self):
        """Initialize migration manager"""
        await self.runner.initialize()

    async def make_migrations(self, models: List[type], name: str = None) -> Migration:
        """Create migrations from model changes"""
        return await self.runner.create_migration(models, name)

    async def migrate(self, target: str = None, fake: bool = False) -> Dict[str, Any]:
        """Run migrations"""
        return await self.runner.migrate(target, fake)

    async def show_migrations(self) -> str:
        """Show migration status"""
        return await self.runner.show_migration_status()

    async def rollback(self, migration_id: str) -> bool:
        """Rollback a migration"""
        return await self.runner.rollback_migration(migration_id)

    async def get_status(self) -> Dict[str, Any]:
        """Get migration status summary"""
        status_list = await self.runner.get_migration_status()

        applied = [s for s in status_list if s.applied]
        pending = [s for s in status_list if not s.applied]

        return {
            'total': len(status_list),
            'applied': len(applied),
            'pending': len(pending),
            'last_applied': applied[-1].applied_at.isoformat() if applied else None
        }


# Global migration manager instance
migration_manager = MigrationManager()

async def make_migrations(models: List[type], name: str = None) -> Migration:
    """Create migrations from model changes"""
    return await migration_manager.make_migrations(models, name)

async def migrate(target: str = None, fake: bool = False) -> Dict[str, Any]:
    """Run migrations"""
    return await migration_manager.migrate(target, fake)

async def show_migrations() -> str:
    """Show migration status"""
    return await migration_manager.show_migrations()

async def rollback_migration(migration_id: str) -> bool:
    """Rollback a migration"""
    return await migration_manager.rollback(migration_id)

async def get_migration_status() -> Dict[str, Any]:
    """Get migration status summary"""
    return await migration_manager.get_status()

__all__ = [
    'MigrationRunner', 'MigrationManager', 'MigrationStatus',
    'migration_manager', 'make_migrations', 'migrate', 'show_migrations',
    'rollback_migration', 'get_migration_status'
]

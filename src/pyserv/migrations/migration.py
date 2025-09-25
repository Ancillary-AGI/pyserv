"""
Migration classes and operations for Pyserv framework.
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Callable, Union, Type
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from pyserv.database.database_pool import DatabaseConnection
from pyserv.database.config import DatabaseConfig
from pyserv.models.base import BaseModel
from pyserv.utils.types import Field


class MigrationOperationType(str, Enum):
    """Types of migration operations"""
    CREATE_MODEL = "create_model"
    DELETE_MODEL = "delete_model"
    RENAME_MODEL = "rename_model"
    ADD_FIELD = "add_field"
    REMOVE_FIELD = "remove_field"
    ALTER_FIELD = "alter_field"
    RENAME_FIELD = "rename_field"
    CREATE_INDEX = "create_index"
    DELETE_INDEX = "delete_index"
    CREATE_RELATIONSHIP = "create_relationship"
    DELETE_RELATIONSHIP = "delete_relationship"
    RUN_SQL = "run_sql"
    RUN_PYTHON = "run_python"


@dataclass
class MigrationOperation:
    """Represents a single migration operation"""
    operation_type: MigrationOperationType
    model_name: Optional[str] = None
    field_name: Optional[str] = None
    old_name: Optional[str] = None
    new_name: Optional[str] = None
    field_type: Optional[str] = None
    field_options: Dict[str, Any] = field(default_factory=dict)
    index_name: Optional[str] = None
    index_fields: List[str] = field(default_factory=list)
    index_options: Dict[str, Any] = field(default_factory=dict)
    relationship_type: Optional[str] = None
    related_model: Optional[str] = None
    sql: Optional[str] = None
    python_code: Optional[str] = None
    reverse_code: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    atomic: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert operation to dictionary"""
        return {
            'operation_type': self.operation_type.value,
            'model_name': self.model_name,
            'field_name': self.field_name,
            'old_name': self.old_name,
            'new_name': self.new_name,
            'field_type': self.field_type,
            'field_options': self.field_options,
            'index_name': self.index_name,
            'index_fields': self.index_fields,
            'index_options': self.index_options,
            'relationship_type': self.relationship_type,
            'related_model': self.related_model,
            'sql': self.sql,
            'python_code': self.python_code,
            'reverse_code': self.reverse_code,
            'dependencies': self.dependencies,
            'atomic': self.atomic
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MigrationOperation':
        """Create operation from dictionary"""
        return cls(
            operation_type=MigrationOperationType(data['operation_type']),
            model_name=data.get('model_name'),
            field_name=data.get('field_name'),
            old_name=data.get('old_name'),
            new_name=data.get('new_name'),
            field_type=data.get('field_type'),
            field_options=data.get('field_options', {}),
            index_name=data.get('index_name'),
            index_fields=data.get('index_fields', []),
            index_options=data.get('index_options', {}),
            relationship_type=data.get('relationship_type'),
            related_model=data.get('related_model'),
            sql=data.get('sql'),
            python_code=data.get('python_code'),
            reverse_code=data.get('reverse_code'),
            dependencies=data.get('dependencies', []),
            atomic=data.get('atomic', True)
        )


@dataclass
class Migration:
    """Represents a database migration"""
    id: str
    name: str
    description: str
    version: int
    operations: List[MigrationOperation] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    applied_at: Optional[datetime] = None
    checksum: Optional[str] = None
    rollback_sql: Optional[str] = None
    migration_file: Optional[str] = None
    migration_type: str = "auto"  # auto, manual, data

    def to_dict(self) -> Dict[str, Any]:
        """Convert migration to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'version': self.version,
            'operations': [op.to_dict() for op in self.operations],
            'dependencies': self.dependencies,
            'created_at': self.created_at.isoformat(),
            'applied_at': self.applied_at.isoformat() if self.applied_at else None,
            'checksum': self.checksum,
            'rollback_sql': self.rollback_sql,
            'migration_file': self.migration_file,
            'migration_type': self.migration_type
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Migration':
        """Create migration from dictionary"""
        return cls(
            id=data['id'],
            name=data['name'],
            description=data['description'],
            version=data['version'],
            operations=[MigrationOperation.from_dict(op) for op in data.get('operations', [])],
            dependencies=data.get('dependencies', []),
            created_at=datetime.fromisoformat(data['created_at']),
            applied_at=datetime.fromisoformat(data['applied_at']) if data.get('applied_at') else None,
            checksum=data.get('checksum'),
            rollback_sql=data.get('rollback_sql'),
            migration_file=data.get('migration_file'),
            migration_type=data.get('migration_type', 'auto')
        )

    def calculate_checksum(self) -> str:
        """Calculate checksum for migration integrity"""
        import hashlib

        content = json.dumps(self.to_dict(), sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()

    def validate(self) -> List[str]:
        """Validate migration for potential issues"""
        errors = []

        if not self.operations:
            errors.append("Migration has no operations")

        for i, op in enumerate(self.operations):
            if op.operation_type == MigrationOperationType.CREATE_MODEL and not op.model_name:
                errors.append(f"Operation {i}: CREATE_MODEL requires model_name")

            if op.operation_type == MigrationOperationType.ADD_FIELD and not op.field_name:
                errors.append(f"Operation {i}: ADD_FIELD requires field_name")

            if op.operation_type == MigrationOperationType.REMOVE_FIELD and not op.field_name:
                errors.append(f"Operation {i}: REMOVE_FIELD requires field_name")

        return errors

    async def execute(self, db_connection: DatabaseConnection) -> bool:
        """Execute migration operations"""
        logger = logging.getLogger("migration_executor")

        try:
            logger.info(f"Executing migration {self.id}: {self.name}")

            for operation in self.operations:
                await self._execute_operation(operation, db_connection)

            # Mark as applied
            self.applied_at = datetime.now()
            self.checksum = self.calculate_checksum()

            logger.info(f"Migration {self.id} executed successfully")
            return True

        except Exception as e:
            logger.error(f"Migration {self.id} failed: {e}")
            raise

    async def _execute_operation(self, operation: MigrationOperation, db_connection: DatabaseConnection):
        """Execute a single migration operation"""
        if operation.operation_type == MigrationOperationType.CREATE_MODEL:
            await self._create_model(operation, db_connection)
        elif operation.operation_type == MigrationOperationType.ADD_FIELD:
            await self._add_field(operation, db_connection)
        elif operation.operation_type == MigrationOperationType.REMOVE_FIELD:
            await self._remove_field(operation, db_connection)
        elif operation.operation_type == MigrationOperationType.ALTER_FIELD:
            await self._alter_field(operation, db_connection)
        elif operation.operation_type == MigrationOperationType.CREATE_INDEX:
            await self._create_index(operation, db_connection)
        elif operation.operation_type == MigrationOperationType.RUN_SQL:
            await self._run_sql(operation, db_connection)
        elif operation.operation_type == MigrationOperationType.RUN_PYTHON:
            await self._run_python(operation, db_connection)
        else:
            raise ValueError(f"Unsupported operation type: {operation.operation_type}")

    async def _create_model(self, operation: MigrationOperation, db_connection: DatabaseConnection):
        """Create a new model/table"""
        from pyserv.models.base import BaseModel
        from pyserv.utils.types import Field

        # Find the model class
        model_class = None
        for cls in BaseModel.__subclasses__():
            if cls.__name__ == operation.model_name:
                model_class = cls
                break

        if not model_class:
            raise ValueError(f"Model class {operation.model_name} not found")

        # Create table using the database backend
        await db_connection.backend.create_table(model_class)

    async def _add_field(self, operation: MigrationOperation, db_connection: DatabaseConnection):
        """Add a field to an existing model"""
        from pyserv.utils.types import Field

        # Create field object from operation data
        field = Field(
            field_type=operation.field_type,
            primary_key=operation.field_options.get('primary_key', False),
            nullable=operation.field_options.get('nullable', True),
            default=operation.field_options.get('default', None),
            max_length=operation.field_options.get('max_length', None),
            autoincrement=operation.field_options.get('autoincrement', False)
        )

        # Add field using database backend
        await db_connection.backend.add_field(
            operation.model_name,
            operation.field_name,
            field
        )

    async def _remove_field(self, operation: MigrationOperation, db_connection: DatabaseConnection):
        """Remove a field from an existing model"""
        # Remove field using database backend
        await db_connection.backend.remove_field(
            operation.model_name,
            operation.field_name
        )

    async def _alter_field(self, operation: MigrationOperation, db_connection: DatabaseConnection):
        """Alter an existing field"""
        from pyserv.utils.types import Field

        # Create field object from operation data
        field = Field(
            field_type=operation.field_type,
            primary_key=operation.field_options.get('primary_key', False),
            nullable=operation.field_options.get('nullable', True),
            default=operation.field_options.get('default', None),
            max_length=operation.field_options.get('max_length', None),
            autoincrement=operation.field_options.get('autoincrement', False)
        )

        # Alter field using database backend
        await db_connection.backend.alter_field(
            operation.model_name,
            operation.field_name,
            field
        )

    async def _create_index(self, operation: MigrationOperation, db_connection: DatabaseConnection):
        """Create an index"""
        # Create index using database backend
        await db_connection.backend.create_index(
            operation.model_name,
            operation.index_name,
            operation.index_fields,
            operation.index_options
        )

    async def _run_sql(self, operation: MigrationOperation, db_connection: DatabaseConnection):
        """Run raw SQL"""
        if operation.sql:
            await db_connection.execute_query(operation.sql)

    async def _run_python(self, operation: MigrationOperation, db_connection: DatabaseConnection):
        """Run Python code"""
        if operation.python_code:
            # Execute Python code in a safe context
            exec_globals = {'db': db_connection, 'datetime': datetime}
            exec(operation.python_code, exec_globals)


class MigrationFile:
    """Represents a migration file on disk"""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.migration = None
        self._load_migration()

    def _load_migration(self):
        """Load migration from file"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse migration file
            # This would parse the migration file format
            # For now, create a basic migration
            self.migration = Migration(
                id=self.file_path.stem,
                name=self.file_path.stem,
                description=f"Migration from {self.file_path.name}",
                version=1
            )

        except Exception as e:
            logging.error(f"Failed to load migration file {self.file_path}: {e}")

    def save(self):
        """Save migration to file"""
        if not self.migration:
            return

        try:
            # Generate migration file content
            content = self._generate_file_content()

            with open(self.file_path, 'w', encoding='utf-8') as f:
                f.write(content)

        except Exception as e:
            logging.error(f"Failed to save migration file {self.file_path}: {e}")

    def _generate_file_content(self) -> str:
        """Generate file content for migration"""
        if not self.migration:
            return ""

        # Generate Python migration file
        content = f'''"""
Migration: {self.migration.name}
Generated: {datetime.now().isoformat()}
"""

import asyncio
from pyserv.migrations.migration import Migration, MigrationOperation, MigrationOperationType
from pyserv.database.database_pool import DatabaseConnection

# Migration operations
operations = [
'''

        for op in self.migration.operations:
            content += f'''    MigrationOperation(
        operation_type=MigrationOperationType.{op.operation_type.value.upper()},
        model_name="{op.model_name}",
        field_name="{op.field_name}",
        field_type="{op.field_type}",
        field_options={op.field_options}
    ),
'''

        content += f''']

# Create migration
migration = Migration(
    id="{self.migration.id}",
    name="{self.migration.name}",
    description="{self.migration.description}",
    version={self.migration.version},
    operations=operations
)

async def upgrade(db_connection: DatabaseConnection):
    """Run migration upgrade"""
    await migration.execute(db_connection)

async def downgrade(db_connection: DatabaseConnection):
    """Run migration downgrade"""
    # Reverse operations would go here
    pass

if __name__ == "__main__":
    # Run migration directly
    async def main():
        db = DatabaseConnection.get_instance()
        await upgrade(db)

    asyncio.run(main())
'''

        return content


class MigrationGenerator:
    """Generates migrations from model changes"""

    def __init__(self, migrations_dir: Path = None):
        self.migrations_dir = migrations_dir or Path("migrations")
        self.migrations_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger("migration_generator")

    def generate_migration_id(self) -> str:
        """Generate unique migration ID"""
        timestamp = int(datetime.now().timestamp())
        return f"{timestamp:010d}"

    def generate_migration_name(self, changes: Dict[str, Any]) -> str:
        """Generate migration name from changes"""
        if not changes:
            return "auto_migration"

        # Analyze changes to create descriptive name
        model_changes = changes.get('models', {})

        if len(model_changes) == 1:
            model_name = list(model_changes.keys())[0]
            operations = list(model_changes[model_name].keys())
            if 'create' in operations:
                return f"create_{model_name}_model"
            elif 'fields' in operations:
                return f"alter_{model_name}_fields"
            else:
                return f"modify_{model_name}"

        return "auto_migration"

    def detect_model_changes(self, models: List[type]) -> Dict[str, Any]:
        """Detect changes in models compared to current database schema"""
        # This would compare models with database schema
        # For now, return empty changes
        return {}

    def create_migration_from_changes(self, changes: Dict[str, Any], name: str = None) -> Migration:
        """Create migration from detected changes"""
        migration_id = self.generate_migration_id()
        migration_name = name or self.generate_migration_name(changes)

        operations = []

        # Convert changes to operations
        for model_name, model_changes in changes.get('models', {}).items():
            if 'create' in model_changes:
                operations.append(MigrationOperation(
                    operation_type=MigrationOperationType.CREATE_MODEL,
                    model_name=model_name
                ))

            if 'fields' in model_changes:
                for field_name, field_changes in model_changes['fields'].items():
                    if field_changes.get('added'):
                        operations.append(MigrationOperation(
                            operation_type=MigrationOperationType.ADD_FIELD,
                            model_name=model_name,
                            field_name=field_name
                        ))

        migration = Migration(
            id=migration_id,
            name=migration_name,
            description=f"Auto-generated migration: {migration_name}",
            version=1,
            operations=operations
        )

        return migration

    def save_migration_file(self, migration: Migration):
        """Save migration to file"""
        filename = f"{migration.id}_{migration.name}.py"
        file_path = self.migrations_dir / filename

        migration_file = MigrationFile(file_path)
        migration_file.migration = migration
        migration_file.save()

        migration.migration_file = str(file_path)
        return file_path

    def generate_migration(self, models: List[type], name: str = None) -> Migration:
        """Generate migration from models"""
        changes = self.detect_model_changes(models)
        migration = self.create_migration_from_changes(changes, name)
        self.save_migration_file(migration)
        return migration











# Model-based Migration class for framework integration
class ModelMigration:
    """
    Represents a single database migration with its operations and metadata.
    """

    def __init__(self, model_class: Type[BaseModel], from_version: int, to_version: int,
                 operations: Dict[str, List], schema_definition: Dict, migration_id: Optional[str] = None):
        self.model_class = model_class
        self.model_name = model_class.__name__
        self.from_version = from_version
        self.to_version = to_version
        self.operations = operations
        self.schema_definition = schema_definition
        self.migration_id = migration_id or self._generate_migration_id()
        self.created_at = datetime.now()

    @property
    def table_name(self) -> str:
        """Get the table name for this migration's model"""
        return self.model_class.get_table_name()

    def is_upgrade(self) -> bool:
        """Check if this is an upgrade migration"""
        return self.to_version > self.from_version

    def is_downgrade(self) -> bool:
        """Check if this is a downgrade migration"""
        return self.to_version < self.from_version

    def is_initial(self) -> bool:
        """Check if this is the initial table creation"""
        return self.from_version == 0

    def get_added_columns(self) -> List[Dict]:
        """Get list of columns being added"""
        return self.operations.get('added_columns', [])

    def get_removed_columns(self) -> List[Dict]:
        """Get list of columns being removed"""
        return self.operations.get('removed_columns', [])

    def get_modified_columns(self) -> List[Dict]:
        """Get list of columns being modified"""
        return self.operations.get('modified_columns', [])

    def get_added_indexes(self) -> List[Dict]:
        """Get list of indexes being added"""
        return self.operations.get('added_indexes', [])

    def get_removed_indexes(self) -> List[Dict]:
        """Get list of indexes being removed"""
        return self.operations.get('removed_indexes', [])

    def to_dict(self) -> Dict[str, Any]:
        """Convert migration to dictionary representation"""
        return {
            'model_name': self.model_name,
            'from_version': self.from_version,
            'to_version': self.to_version,
            'operations': self.operations,
            'schema_definition': self.schema_definition,
            'created_at': self.created_at.isoformat(),
            'is_upgrade': self.is_upgrade(),
            'is_downgrade': self.is_downgrade(),
            'is_initial': self.is_initial()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], model_class: Type[BaseModel]) -> 'ModelMigration':
        """Create migration from dictionary representation"""
        migration = cls(
            model_class=model_class,
            from_version=data['from_version'],
            to_version=data['to_version'],
            operations=data['operations'],
            schema_definition=data['schema_definition']
        )
        migration.created_at = datetime.fromisoformat(data['created_at'])
        return migration

    def _generate_migration_id(self) -> str:
        """Generate a unique migration ID"""
        timestamp = self.created_at.strftime("%Y%m%d_%H%M%S")
        direction = "upgrade" if self.is_upgrade() else "downgrade" if self.is_downgrade() else "initial"
        return f"{timestamp}_{self.model_name.lower()}_{direction}_v{self.from_version}_to_v{self.to_version}"

    def __repr__(self) -> str:
        direction = "UPGRADE" if self.is_upgrade() else "DOWNGRADE" if self.is_downgrade() else "INITIAL"
        return f"<Migration {self.migration_id}: {self.model_name} v{self.from_version} -> v{self.to_version} ({direction})>"

    # Schema serialization/deserialization methods
    @staticmethod
    def _serialize_schema(columns: Dict[str, Field]) -> Dict:
        """Serialize column definitions for storage"""
        return {name: ModelMigration._serialize_field(field) for name, field in columns.items()}

    @staticmethod
    def _serialize_field(field: Field) -> Dict:
        """Serialize a field definition for storage"""
        return {
            'field_type': field.field_type.value if hasattr(field.field_type, 'value') else field.field_type,
            'primary_key': field.primary_key,
            'autoincrement': field.autoincrement,
            'unique': field.unique,
            'nullable': field.nullable,
            'default': field.default,
            'foreign_key': field.foreign_key,
            'index': field.index
        }

    @staticmethod
    def _deserialize_field(field_data: Dict) -> Field:
        """Deserialize a field definition from storage"""
        return Field(
            field_type=field_data['field_type'],
            primary_key=field_data['primary_key'],
            autoincrement=field_data['autoincrement'],
            unique=field_data['unique'],
            nullable=field_data['nullable'],
            default=field_data['default'],
            foreign_key=field_data['foreign_key'],
            index=field_data['index']
        )


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
            import importlib
            import pkgutil
            import inspect

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
            import importlib
            import pkgutil
            import inspect

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
            import importlib
            import inspect

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
                                'migration_id': migration.migration_id,
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
                            'migration_id': migration.migration_id,
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
                                          from_version: int, to_version: int) -> Optional[ModelMigration]:
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
        schema_definition = ModelMigration._serialize_schema(model_class._fields)

        return ModelMigration(
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


# Global migration generator instance
migration_generator = MigrationGenerator()

__all__ = [
    'Migration', 'MigrationOperation', 'MigrationOperationType',
    'MigrationFile', 'MigrationGenerator', 'migration_generator',
    'ModelMigration', 'MigrationFramework'
]

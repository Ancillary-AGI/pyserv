"""
Migration class for representing database schema changes.
"""

from typing import Dict, List, Any, Optional, Type, Tuple
from datetime import datetime
from pyserv.models.base import BaseModel
from pyserv.utils.types import Field


class Migration:
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
    def from_dict(cls, data: Dict[str, Any], model_class: Type[BaseModel]) -> 'Migration':
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

    # Schema serialization/deserialization methods (moved from MigrationManager)
    @staticmethod
    def _serialize_schema(columns: Dict[str, Field]) -> Dict:
        """Serialize column definitions for storage"""
        return {name: Migration._serialize_field(field) for name, field in columns.items()}

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





"""
Base model class for database operations.
"""

from typing import Dict, Optional, Any, Union, ClassVar
from datetime import datetime

from pyserv.database.connections import DatabaseConnection
from pyserv.database.config import DatabaseConfig
from pyserv.utils.types import Field, Relationship
from pyserv.models.query import QueryBuilder
from pyserv.exceptions import NotFound


class ModelMeta(type):
    """
    Metaclass that collects fields and prevents field names from overwriting class attributes.

    Field precedence (highest to lowest):
    1. Methods - Always preserved, never removed
    2. Non-method class attributes - Removed if they conflict with field names
    3. Field names - Define the actual field access

    This prevents field names from shadowing class methods/attributes while allowing
    proper field access through the data dictionary pattern.
    """

    def __new__(cls, name, bases, attrs):
        # Collect fields from class attributes (like the provided ORM)
        fields = {}
        for key, value in attrs.items():
            if isinstance(value, Field):
                fields[key] = value
                value.name = key

        # Remove fields from class attributes to avoid shadowing
        for key in fields:
            attrs.pop(key)

        # Create the class
        new_class = super().__new__(cls, name, bases, attrs)

        # Store fields in _fields class variable (like the provided ORM)
        new_class._fields = fields

        # Maintain backward compatibility with _columns
        new_class._columns = fields

        # Set table name if not specified
        if not hasattr(new_class, '_table_name') or not new_class._table_name:
            new_class._table_name = f"{name.lower()}s"

        # Create Django-style DoesNotExist exception for the model
        class DoesNotExist(NotFound):
            """Exception raised when the model instance does not exist"""
            def __init__(self, message: Optional[str] = None, **kwargs):
                if message is None:
                    message = f"{name} does not exist"
                super().__init__(message, error_code=f"{name.lower()}_does_not_exist", **kwargs)

        # Attach the exception to the model class
        new_class.DoesNotExist = DoesNotExist

        return new_class


class BaseModel(metaclass=ModelMeta):
    """
    Base model class for database operations.
    """

    # Class attributes with ClassVar typing
    _fields: ClassVar[Dict[str, Field]] = {}
    _table_name: ClassVar[Optional[str]] = None
    _verbose_name: ClassVar[Optional[str]] = None
    _verbose_name_plural: ClassVar[Optional[str]] = None
    _db_config: Optional[DatabaseConfig] = None
    _relationships: ClassVar[Dict[str, Relationship]] = {}

    def __init__(self, **kwargs):
        """Initialize model instance with field values"""
        self._data = {}  # Initialize data dictionary (from provided ORM)

        # Initialize all fields from _fields with their defaults
        for col_name, field in self._fields.items():
            value = kwargs.get(col_name, field.default)
            setattr(self, col_name, value)

        # Set any additional kwargs that aren't in _fields
        for key, value in kwargs.items():
            if key not in self._fields:
                setattr(self, key, value)

        # Initialize relationship tracking
        self._loaded_relations: Dict[str, Any] = {}

    def __getattribute__(self, name):
        """Custom getattr to handle field access (improved from provided ORM)"""
        # Use object.__getattribute__ to avoid recursion (from provided ORM)
        fields = object.__getattribute__(self, '_fields')
        if name in fields:
            data = object.__getattribute__(self, '_data')
            return data.get(name)
        return object.__getattribute__(self, name)

    def __setattr__(self, name, value):
        """Custom setattr to handle field assignment (improved from provided ORM)"""
        # Use object.__getattribute__ to avoid recursion (from provided ORM)
        fields = object.__getattribute__(self, '_fields')
        if name in fields:
            data = object.__getattribute__(self, '_data')
            data[name] = value
        else:
            object.__setattr__(self, name, value)

    @classmethod
    def set_db_config(cls, config: DatabaseConfig):
        """Set database configuration for this model"""
        cls._db_config = config

    @classmethod
    def get_table_name(cls) -> str:
        """Get table name for this model"""
        if cls._table_name:
            return cls._table_name
        return cls.__name__.lower() + 's'

    @classmethod
    def get_verbose_name(cls) -> str:
        """Get verbose name for this model (for internationalization)"""
        if cls._verbose_name:
            return cls._verbose_name
        # Convert CamelCase to Title Case
        name = cls.__name__
        return ''.join([' ' + c if c.isupper() else c for c in name]).strip()

    @classmethod
    def get_verbose_name_plural(cls) -> str:
        """Get verbose name plural for this model (for internationalization)"""
        if cls._verbose_name_plural:
            return cls._verbose_name_plural
        # Simple pluralization (can be enhanced with proper i18n library)
        verbose_name = cls.get_verbose_name()
        if verbose_name.endswith(('s', 'sh', 'ch', 'x', 'z')):
            return verbose_name + 'es'
        elif verbose_name.endswith('y') and not verbose_name.endswith(('ay', 'ey', 'iy', 'oy', 'uy')):
            return verbose_name[:-1] + 'ies'
        else:
            return verbose_name + 's'

    @classmethod
    def get_primary_key(cls) -> Optional[str]:
        """Get primary key field name"""
        for name, field in cls._fields.items():
            if field.primary_key:
                return name
        return None

    @classmethod
    def query(cls) -> QueryBuilder:
        """Return a new QueryBuilder instance"""
        return QueryBuilder(cls)

    @classmethod
    async def create_table(cls):
        """Create database table for this model"""
        db = DatabaseConnection.get_instance(cls._db_config)
        await db.create_table(cls)

    async def save(self):
        """Save the instance to the database using backend abstraction"""
        db = DatabaseConnection.get_instance(self._db_config)

        # Convert instance to dict for backend
        data = self.to_dict()

        # Get primary key field name
        primary_key = self.get_primary_key()
        primary_key_value = getattr(self, primary_key, None) if primary_key else None

        if primary_key_value is not None:
            # Update existing record
            filters = {primary_key: primary_key_value}
            success = await db.backend.update_one(self.__class__, filters, data)
            if not success:
                raise ValueError("Record not found or not modified")
        else:
            # Insert new record
            result = await db.backend.insert_one(self.__class__, data)
            if primary_key and result:
                setattr(self, primary_key, result)

    @classmethod
    async def get(cls, id: Union[int, str]) -> Optional['BaseModel']:
        """Get a single record by primary key"""
        primary_key = cls.get_primary_key()
        if not primary_key:
            raise ValueError("Model does not have a primary key")

        instance = await cls.query().filter(**{primary_key: id}).first()
        if instance is None:
            raise cls.DoesNotExist()
        return instance

    @classmethod
    async def create(cls, **kwargs) -> 'BaseModel':
        """Create a new instance and save it"""
        instance = cls(**kwargs)
        await instance.save()
        return instance

    async def delete(self):
        """Delete the instance from the database using backend abstraction"""
        primary_key = self.get_primary_key()
        if not primary_key or not hasattr(self, primary_key):
            raise ValueError("Cannot delete object without primary key")

        db = DatabaseConnection.get_instance(self._db_config)

        # Use backend delete method
        filters = {primary_key: getattr(self, primary_key)}
        success = await db.backend.delete_one(self.__class__, filters)
        if not success:
            raise ValueError("Record not found")

    def to_dict(self, include_relations: bool = False) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {}
        # Use _data dictionary for field values (improved from provided ORM)
        for col_name in self._fields.keys():
            value = self._data.get(col_name)
            if isinstance(value, datetime):
                result[col_name] = value.isoformat()
            else:
                result[col_name] = value

        if include_relations:
            for rel_name, rel_value in self._loaded_relations.items():
                if isinstance(rel_value, list):
                    result[rel_name] = [item.to_dict() for item in rel_value]
                elif hasattr(rel_value, 'to_dict'):
                    result[rel_name] = rel_value.to_dict()
                else:
                    result[rel_name] = rel_value

        return result

    @classmethod
    def objects(cls) -> QueryBuilder:
        """Get a queryset for this model (Django-like API from provided ORM)"""
        return cls.query()

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.to_dict()}>"

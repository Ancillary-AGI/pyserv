"""
Base model class for database operations.
"""

from typing import Dict, List, Optional, Any, Union, Type, ClassVar
from datetime import datetime

# Motor for async MongoDB operations (async version of PyMongo)
from motor.motor_asyncio import AsyncIOMotorClient
from motor.core import AgnosticCollection
from bson import ObjectId

from ..database.database import DatabaseConnection
from ..database.config import DatabaseConfig
from ..utils.types import Field, Relationship
from .query import QueryBuilder


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

        if cls._db_config.is_mongodb:
            # MongoDB doesn't need table creation, but we can create indexes
            async with db.get_connection() as conn:
                collection = conn[cls.get_table_name()]

                # Create indexes for fields marked with index=True
                for name, field in cls._fields.items():
                    if field.index:
                        await collection.create_index([(name, ASCENDING)])

                # Create unique indexes for fields marked with unique=True
                for name, field in cls._fields.items():
                    if field.unique:
                        await collection.create_index([(name, ASCENDING)], unique=True)
        else:
            # SQL table creation
            columns = []
            for name, field in cls._fields.items():
                columns.append(field.sql_definition(name, cls._db_config.is_sqlite))

            # Add indexes
            indexes = []
            for name, field in cls._fields.items():
                if field.index:
                    index_name = f"idx_{cls.get_table_name()}_{name}"
                    indexes.append(f"CREATE INDEX IF NOT EXISTS {index_name} ON {cls.get_table_name()}({name});")

            sql = f"CREATE TABLE IF NOT EXISTS {cls.get_table_name()} ({', '.join(columns)});"

            async with db.get_connection() as conn:
                if hasattr(conn, 'execute'):
                    # SQLite
                    conn.execute("PRAGMA foreign_keys = ON")
                    conn.execute(sql)
                    for index_sql in indexes:
                        conn.execute(index_sql)
                    conn.commit()
                elif hasattr(conn, 'fetch'):
                    # PostgreSQL
                    await conn.execute(sql)
                    for index_sql in indexes:
                        await conn.execute(index_sql)
                else:
                    # MySQL
                    await conn.execute(sql)
                    for index_sql in indexes:
                        await conn.execute(index_sql)

    async def save(self):
        """Save the instance to the database"""
        db = DatabaseConnection.get_instance(self._db_config)

        if self._db_config.is_mongodb:
            # MongoDB save operation
            data = self.to_dict()

            # Remove ID if it's None for new documents
            if 'id' in data and data['id'] is None:
                del data['id']

            async with db.get_connection() as conn:
                collection = conn[self.get_table_name()]

                if hasattr(self, 'id') and self.id:
                    # Update existing document
                    result = await collection.replace_one({'_id': ObjectId(self.id)}, data)
                    if result.modified_count == 0:
                        raise ValueError("Document not found or not modified")
                else:
                    # Insert new document
                    result = await collection.insert_one(data)
                    self.id = str(result.inserted_id)
        else:
            # SQL save operation
            fields = []
            values = []
            primary_key = self.get_primary_key()
            primary_key_value = getattr(self, primary_key, None) if primary_key else None

            for name, field in self._fields.items():
                if name == primary_key and primary_key_value is None and field.autoincrement:
                    continue

                value = getattr(self, name, None)
                if value is not None or field.nullable:
                    fields.append(name)
                    values.append(value)

            if primary_key_value is not None:
                # Update existing record
                set_clause = ', '.join([f"{f} = {self._get_param_placeholder(i+1)}" for i, f in enumerate(fields)])
                sql = f"UPDATE {self.get_table_name()} SET {set_clause} WHERE {primary_key} = {self._get_param_placeholder(len(fields) + 1)}"
                values.append(primary_key_value)
            else:
                # Insert new record
                placeholders = ', '.join([self._get_param_placeholder(i+1) for i in range(len(fields))])
                sql = f"INSERT INTO {self.get_table_name()} ({', '.join(fields)}) VALUES ({placeholders})"
                if not self._db_config.is_sqlite and primary_key:
                    sql += f" RETURNING {primary_key}"

            async with db.get_connection() as conn:
                if hasattr(conn, 'execute'):
                    # SQLite
                    cursor = conn.execute(sql, values)
                    conn.commit()
                    if primary_key and cursor.lastrowid:
                        setattr(self, primary_key, cursor.lastrowid)
                elif hasattr(conn, 'fetchrow'):
                    # PostgreSQL
                    if primary_key_value is None and primary_key:
                        result = await conn.fetchrow(sql, *values)
                        if result and primary_key in result:
                            setattr(self, primary_key, result[primary_key])
                    else:
                        await conn.execute(sql, *values)
                else:
                    # MySQL
                    await conn.execute(sql, values)
                    if primary_key_value is None and primary_key:
                        result = await conn.fetchone()
                        if result and primary_key in result:
                            setattr(self, primary_key, result[primary_key])

    @classmethod
    async def get(cls, id: Union[int, str]) -> Optional['BaseModel']:
        """Get a single record by primary key"""
        primary_key = cls.get_primary_key()
        if not primary_key:
            raise ValueError("Model does not have a primary key")

        return await cls.query().filter(**{primary_key: id}).first()

    @classmethod
    async def create(cls, **kwargs) -> 'BaseModel':
        """Create a new instance and save it"""
        instance = cls(**kwargs)
        await instance.save()
        return instance

    async def delete(self):
        """Delete the instance from the database"""
        primary_key = self.get_primary_key()
        if not primary_key or not hasattr(self, primary_key):
            raise ValueError("Cannot delete object without primary key")

        db = DatabaseConnection.get_instance(self._db_config)

        if self._db_config.is_mongodb:
            # MongoDB delete operation
            async with db.get_connection() as conn:
                collection = conn[self.get_table_name()]
                result = await collection.delete_one({'_id': ObjectId(getattr(self, primary_key))})
                if result.deleted_count == 0:
                    raise ValueError("Document not found")
        else:
            # SQL delete operation
            sql = f"DELETE FROM {self.get_table_name()} WHERE {primary_key} = {self._get_param_placeholder(1)}"

            async with db.get_connection() as conn:
                if hasattr(conn, 'execute'):
                    conn.execute(sql, [getattr(self, primary_key)])
                    conn.commit()
                elif hasattr(conn, 'fetch'):
                    await conn.execute(sql, getattr(self, primary_key))
                else:
                    await conn.execute(sql, getattr(self, primary_key))

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

    @classmethod
    def _get_param_placeholder(cls, index: int) -> str:
        """Get parameter placeholder based on database type"""
        if cls._db_config.is_sqlite:
            return '?'
        elif cls._db_config.is_mysql:
            return '%s'
        else:
            return f"${index}"

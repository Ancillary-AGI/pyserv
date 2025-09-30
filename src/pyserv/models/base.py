# Consolidated comprehensive type system for Pyserv framework

from typing import Any, Callable, Optional, Union, Dict, List, Type, ClassVar
from enum import Enum
from datetime import datetime, date, time, timezone
import uuid
import re
import json
from decimal import Decimal
from dataclasses import dataclass, field
from pyserv.database.connections import DatabaseConnection

class FieldType(str, Enum):
    """Field types for database schema"""
    # Basic types
    STRING = "STRING"
    INTEGER = "INTEGER"
    BIGINT = "BIGINT"
    SMALLINT = "SMALLINT"
    BOOLEAN = "BOOLEAN"
    DATETIME = "DATETIME"
    DATE = "DATE"
    TIME = "TIME"
    FLOAT = "FLOAT"
    DOUBLE = "DOUBLE"
    DECIMAL = "DECIMAL"
    NUMERIC = "NUMERIC"
    UUID = "UUID"
    JSON = "JSON"
    JSONB = "JSONB"
    TEXT = "TEXT"
    VARCHAR = "VARCHAR"
    CHAR = "CHAR"
    BLOB = "BLOB"
    BYTEA = "BYTEA"
    TIMESTAMP = "TIMESTAMP"
    TIMESTAMPTZ = "TIMESTAMPTZ"

    # Specialized types
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    URL = "URL"
    IP_ADDRESS = "IP_ADDRESS"
    MAC_ADDRESS = "MAC_ADDRESS"
    ENUM = "ENUM"
    ARRAY = "ARRAY"
    RANGE = "RANGE"
    GEOMETRY = "GEOMETRY"
    GEOGRAPHY = "GEOGRAPHY"
    HSTORE = "HSTORE"
    INET = "INET"
    MONEY = "MONEY"

class RelationshipType(str, Enum):
    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_ONE = "many_to_one"
    MANY_TO_MANY = "many_to_many"

class OrderDirection(str, Enum):
    ASC = "ASC"
    DESC = "DESC"

@dataclass
class PaginatedResponse:
    """Response for paginated queries"""
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int

@dataclass
class AggregationResult:
    """Result of aggregation operations"""
    count: int = 0
    sum: float = 0
    avg: float = 0
    min: Any = None
    max: Any = None
    group_by: Dict[Any, Any] = field(default_factory=dict)

class LazyLoad:
    """Descriptor for lazy loading of relationships"""

    def __init__(self, relationship_name: str):
        self.relationship_name = relationship_name
        self._cached_value = None
        self._loaded = False

    def __get__(self, instance, owner):
        if instance is None:
            return self

        if not self._loaded:
            return instance.__getattr__(self.relationship_name)

        return self._cached_value

    def __set__(self, instance, value):
        self._cached_value = value
        self._loaded = True
        instance._loaded_relations[self.relationship_name] = value

@dataclass
class Field:
    """Base field class with comprehensive functionality"""

    field_type: FieldType
    primary_key: bool = False
    nullable: bool = True
    default: Any = None
    autoincrement: bool = False
    unique: bool = False
    index: bool = False
    after: Optional[str] = None
    validators: List[Callable] = field(default_factory=list)
    help_text: str = ""
    verbose_name: str = ""
    foreign_key: Optional[str] = None
    max_length: Optional[int] = None
    min_length: Optional[int] = None
    choices: Optional[List[str]] = None
    pattern: Optional[str] = None
    min_value: Optional[Union[int, float, Decimal]] = None
    max_value: Optional[Union[int, float, Decimal]] = None

    def __post_init__(self):
        if self.primary_key:
            self.nullable = False

        if self.autoincrement and self.field_type not in [FieldType.INTEGER, FieldType.BIGINT, FieldType.SMALLINT]:
            raise ValueError("Autoincrement can only be set on integer fields")

        # Set up validators based on field properties
        if self.choices:
            self.validators.append(self._validate_choices)
        if self.pattern:
            self.validators.append(self._validate_regex)
        if self.min_length or self.max_length:
            self.validators.append(self._validate_length)
        if self.min_value is not None or self.max_value is not None:
            self.validators.append(self._validate_range)
        
        # Don't validate callable defaults here

    def validate(self, value: Any) -> Any:
        """Validate field value"""
        if value is None and not self.nullable:
            raise ValueError(f"{self.verbose_name or 'Field'} cannot be null")

        for validator in self.validators:
            value = validator(value)

        return value

    def _validate_choices(self, value: str) -> str:
        if self.choices and value not in self.choices:
            raise ValueError(f"Value must be one of {self.choices}")
        return value

    def _validate_regex(self, value: str) -> str:
        if not re.match(self.pattern, value):
            raise ValueError(f"Value does not match required pattern")
        return value

    def _validate_length(self, value: str) -> str:
        if self.min_length and len(value) < self.min_length:
            raise ValueError(f"Minimum length is {self.min_length}")
        if self.max_length and len(value) > self.max_length:
            raise ValueError(f"Maximum length is {self.max_length}")
        return value

    def _validate_range(self, value: Union[int, float, Decimal]) -> Union[int, float, Decimal]:
        if self.min_value is not None and value < self.min_value:
            raise ValueError(f"Minimum value is {self.min_value}")
        if self.max_value is not None and value > self.max_value:
            raise ValueError(f"Maximum value is {self.max_value}")
        return value

    def to_dict(self) -> Dict[str, Any]:
        """Convert field to dictionary"""
        return {
            "field_type": self.field_type.value,
            "primary_key": self.primary_key,
            "nullable": self.nullable,
            "default": self.default,
            "autoincrement": self.autoincrement,
            "unique": self.unique,
            "index": self.index,
            "after": self.after,
            "help_text": self.help_text,
            "verbose_name": self.verbose_name,
            "max_length": self.max_length,
            "min_length": self.min_length,
            "choices": self.choices,
            "pattern": self.pattern,
            "min_value": self.min_value,
            "max_value": self.max_value
        }

    def sql_definition(self, name: str, db_config) -> Optional[str]:
        """Generate SQL column definition - skips MongoDB"""
        if hasattr(db_config, 'is_mongodb') and db_config.is_mongodb:
            # MongoDB migrations are handled separately in migrator
            return None
            
        # For SQL databases, generate SQL definition
        connection = DatabaseConnection.get_instance(db_config)
        sql_type = connection.get_sql_type(self)
        parts = [name, sql_type]

        if self.primary_key:
            parts.append("PRIMARY KEY")
            if self.autoincrement:
                if hasattr(db_config, 'is_sqlite') and db_config.is_sqlite:
                    parts.append("AUTOINCREMENT")
                elif hasattr(db_config, 'is_mysql') and db_config.is_mysql:
                    parts.append("AUTO_INCREMENT")
                elif hasattr(db_config, 'is_postgres') and db_config.is_postgres:
                    parts.append("GENERATED ALWAYS AS IDENTITY")

        if not self.nullable:
            parts.append("NOT NULL")

        if self.unique:
            parts.append("UNIQUE")

        if self.default is not None:
            default_str = connection.format_default_value(self.default)
            parts.append(f"DEFAULT {default_str}")

        if self.foreign_key:
            fk_str = connection.format_foreign_key(self.foreign_key)
            parts.append(fk_str)

        if self.after and hasattr(db_config, 'is_mysql') and db_config.is_mysql:
            parts.append(f"AFTER {self.after}")

        return " ".join(parts)

    def get_type_mapping(self, db_config) -> Dict[FieldType, str]:
        """Get database-specific type mappings using connection"""
        connection = DatabaseConnection.get_instance(db_config)
        return connection.get_type_mappings()

# Specialized field classes
class StringField(Field):
    """String field with length validation"""

    def __init__(self, max_length: Optional[int] = None, min_length: Optional[int] = None,
                 pattern: Optional[str] = None, **kwargs):
        field_type = FieldType.VARCHAR if max_length else FieldType.TEXT
        super().__init__(field_type, **kwargs)
        self.max_length = max_length
        self.min_length = min_length
        self.pattern = pattern
        if max_length and field_type == FieldType.VARCHAR:
            self.field_type = f"VARCHAR({max_length})"

class IntegerField(Field):
    """Integer field with range validation"""

    def __init__(self, min_value: Optional[int] = None, max_value: Optional[int] = None, **kwargs):
        super().__init__(FieldType.INTEGER, **kwargs)
        self.min_value = min_value
        self.max_value = max_value

class BigIntegerField(Field):
    """Big integer field for large numbers"""

    def __init__(self, **kwargs):
        super().__init__(FieldType.BIGINT, **kwargs)

class BooleanField(Field):
    """Boolean field"""

    def __init__(self, **kwargs):
        super().__init__(FieldType.BOOLEAN, **kwargs)

class DateTimeField(Field):
    """DateTime field with timezone support"""

    def __init__(self, auto_now: bool = False, auto_now_add: bool = False, **kwargs):
        super().__init__(FieldType.TIMESTAMPTZ, **kwargs)
        self.auto_now = auto_now
        self.auto_now_add = auto_now_add

        if auto_now_add and self.default is None:
            self.default = 'CURRENT_TIMESTAMP'

    def validate(self, value: Any) -> Any:
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except ValueError:
                raise ValueError("Invalid datetime format")
        return super().validate(value)

class DateField(Field):
    """Date field (without time)"""

    def __init__(self, **kwargs):
        super().__init__(FieldType.DATE, **kwargs)

    def validate(self, value: Any) -> Any:
        if isinstance(value, str):
            try:
                value = date.fromisoformat(value)
            except ValueError:
                raise ValueError("Invalid date format")
        return super().validate(value)

class TimeField(Field):
    """Time field"""

    def __init__(self, **kwargs):
        super().__init__(FieldType.TIME, **kwargs)

    def validate(self, value: Any) -> Any:
        if isinstance(value, str):
            try:
                value = time.fromisoformat(value)
            except ValueError:
                raise ValueError("Invalid time format")
        return super().validate(value)

class FloatField(Field):
    """Float field with precision validation"""

    def __init__(self, min_value: Optional[float] = None, max_value: Optional[float] = None,
                 precision: Optional[int] = None, **kwargs):
        super().__init__(FieldType.FLOAT, **kwargs)
        self.min_value = min_value
        self.max_value = max_value
        self.precision = precision

class DecimalField(Field):
    """Decimal field with fixed precision"""

    def __init__(self, max_digits: int = 10, decimal_places: int = 2, **kwargs):
        super().__init__(FieldType.DECIMAL, **kwargs)
        self.max_digits = max_digits
        self.decimal_places = decimal_places

    def sql_definition(self, name: str, db_config) -> Optional[str]:
        if hasattr(db_config, 'is_mongodb') and db_config.is_mongodb:
            return None
        if hasattr(db_config, 'is_postgresql') and db_config.is_postgresql:
            self.field_type = f"NUMERIC({self.max_digits}, {self.decimal_places})"
        elif hasattr(db_config, 'is_mysql') and db_config.is_mysql:
            self.field_type = f"DECIMAL({self.max_digits}, {self.decimal_places})"
        return super().sql_definition(name, db_config)

class UUIDField(Field):
    """UUID field with automatic generation"""

    def __init__(self, **kwargs):
        if 'default' not in kwargs:
            kwargs['default'] = str(uuid.uuid4())
        super().__init__(FieldType.UUID, **kwargs)

    def validate(self, value: Any) -> Any:
        if isinstance(value, str):
            try:
                value = uuid.UUID(value)
            except ValueError:
                raise ValueError("Invalid UUID format")
        return super().validate(value)

class JSONField(Field):
    """JSON field with schema validation"""

    def __init__(self, schema: Optional[Dict] = None, **kwargs):
        super().__init__(FieldType.JSON, **kwargs)
        self.schema = schema

    def validate(self, value: Any) -> Any:
        """Validate JSON against schema if provided"""
        if self.schema and value is not None:
            try:
                # Simple schema validation - in production, use jsonschema library
                if isinstance(self.schema, type) and not isinstance(value, self.schema):
                    raise ValueError("Value does not match schema type")
            except Exception:
                raise ValueError("Schema validation failed")
            
        if value is not None:
            try:
                if isinstance(value, str):
                    json.loads(value)
                else:
                    json.dumps(value)
            except (json.JSONDecodeError, TypeError):
                raise ValueError("Invalid JSON data")
        return super().validate(value)

class TextField(Field):
    """Text field (large text)"""

    def __init__(self, **kwargs):
        super().__init__(FieldType.TEXT, **kwargs)

class BlobField(Field):
    """Binary large object field"""

    def __init__(self, **kwargs):
        super().__init__(FieldType.BLOB, **kwargs)

class ByteaField(Field):
    """PostgreSQL bytea field"""

    def __init__(self, **kwargs):
        super().__init__(FieldType.BYTEA, **kwargs)

class TimestampTZField(Field):
    """Timestamp with timezone field"""

    def __init__(self, **kwargs):
        super().__init__(FieldType.TIMESTAMPTZ, **kwargs)

# Advanced field types with specialized validation
class EmailField(StringField):
    """Email field with validation"""

    def __init__(self, **kwargs):
        kwargs.setdefault('max_length', 255)
        super().__init__(**kwargs)
        self.pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

class PhoneField(StringField):
    """Phone number field with international validation using phonenumbers"""

    def __init__(self, region: str = "US", **kwargs):
        kwargs.setdefault('max_length', 20)
        super().__init__(**kwargs)
        self.region = region

    def validate(self, value: str) -> str:
        """Validate phone number using phonenumbers library"""
        if not value:
            return super().validate(value)
            
        try:
            import phonenumbers
            from phonenumbers import NumberParseException
            
            # Parse the phone number
            parsed_number = phonenumbers.parse(value, self.region)
            
            # Validate the number
            if not phonenumbers.is_valid_number(parsed_number):
                raise ValueError(f"Invalid phone number for region {self.region}")
            
            # Format to international format
            formatted = phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
            return super().validate(formatted)
            
        except ImportError:
            # Fallback to basic validation if phonenumbers not installed
            pattern = r'^\+?[\d\s\-\(\)]{10,}$'
            if not re.match(pattern, value):
                raise ValueError(
                    "Invalid phone number format. Install 'phonenumbers' package for better validation: "
                    "pip install phonenumbers"
                )
            return super().validate(value)
            
        except NumberParseException as e:
            raise ValueError(f"Invalid phone number: {e}")
        except Exception as e:
            raise ValueError(f"Phone validation error: {e}")

class URLField(StringField):
    """URL field with validation"""

    def __init__(self, **kwargs):
        kwargs.setdefault('max_length', 2083)  # Maximum URL length in browsers
        super().__init__(**kwargs)
        self.pattern = r'^(https?|ftp)://[^\s/$.?#].[^\s]*$'

class IPAddressField(StringField):
    """IP address field (IPv4/IPv6)"""

    def __init__(self, **kwargs):
        kwargs.setdefault('max_length', 45)  # IPv6 maximum length
        super().__init__(**kwargs)

    def validate(self, value: str) -> str:
        """Validate IP address format"""
        if not value:
            return super().validate(value)
        # Simple IPv4 validation
        ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        # Simple IPv6 validation
        ipv6_pattern = r'^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$'

        if not (re.match(ipv4_pattern, value) or re.match(ipv6_pattern, value)):
            raise ValueError("Invalid IP address")

        return super().validate(value)

class PasswordField(StringField):
    """Password field with strength validation"""

    def __init__(self, min_length: int = 8, require_special: bool = True, **kwargs):
        kwargs.setdefault('min_length', min_length)
        super().__init__(**kwargs)
        self.require_special = require_special

    def validate(self, value: str) -> str:
        """Validate password strength"""
        if value is None:
            return super().validate(value)

        if len(value) < (self.min_length or 8):
            raise ValueError(f"Password must be at least {self.min_length or 8} characters long")

        if self.require_special:
            # Check for at least one special character
            if not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
                raise ValueError("Password must contain at least one special character")

        # Check for at least one number and one letter
        if not (re.search(r'\d', value) and re.search(r'[a-zA-Z]', value)):
            raise ValueError("Password must contain at least one number and letter")

        return super().validate(value)

    def hash_password(self, password: str) -> str:
        """Hash password (implement proper hashing in production)"""
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest()

class ArrayField(Field):
    """Array field for storing lists"""

    def __init__(self, item_type: FieldType, dimensions: int = 1, **kwargs):
        super().__init__(FieldType.ARRAY, **kwargs)
        self.item_type = item_type
        self.dimensions = dimensions

    def sql_definition(self, name: str, db_config) -> Optional[str]:
        if hasattr(db_config, 'is_mongodb') and db_config.is_mongodb:
            return None
        if hasattr(db_config, 'is_postgresql') and db_config.is_postgresql:
            array_type = f"{self.item_type.value}[]{'[]' * (self.dimensions - 1)}"
            return f"{name} {array_type}"
        else:
            # For databases that don't support arrays natively, use JSON
            return super().sql_definition(name, db_config)

class EnumField(Field):
    """Enum field with predefined choices"""

    def __init__(self, enum_class: Type[Enum], **kwargs):
        super().__init__(FieldType.ENUM, **kwargs)
        self.enum_class = enum_class
        self.choices = [e.value for e in enum_class]

    def validate(self, value: Any) -> Any:
        """Validate value is in enum choices"""
        if value is None:
            return super().validate(value)
        if value not in self.choices:
            raise ValueError(f"Value must be one of {self.choices}")
        return super().validate(value)

class ForeignKeyField(Field):
    """Foreign key field with relationship support"""

    def __init__(self, to: Union[str, Type['BaseModel']], on_delete: str = "CASCADE", **kwargs):
        super().__init__(FieldType.INTEGER, **kwargs)
        self.to = to
        self.on_delete = on_delete.upper()

    def sql_definition(self, name: str, db_config) -> Optional[str]:
        if hasattr(db_config, 'is_mongodb') and db_config.is_mongodb:
            return None
        # Resolve the target table name
        if isinstance(self.to, str):
            table_name = self.to
        else:
            table_name = self.to.__tablename__

        self.foreign_key = f"{table_name}.id"
        sql = super().sql_definition(name, db_config)

        # Add ON DELETE clause
        if self.on_delete != "CASCADE":
            sql = sql.replace("REFERENCES", f"REFERENCES ON DELETE {self.on_delete}")

        return sql

class FileField(Field):
    """File upload field"""

    def __init__(self, allowed_extensions: Optional[List[str]] = None, max_size: int = 5242880, **kwargs):
        super().__init__(FieldType.TEXT, **kwargs)  # Store file path or metadata
        self.allowed_extensions = allowed_extensions or []
        self.max_size = max_size  # 5MB default

class ImageField(FileField):
    """Image upload field with dimension validation"""

    def __init__(self, max_width: Optional[int] = None, max_height: Optional[int] = None, **kwargs):
        super().__init__(**kwargs)
        self.max_width = max_width
        self.max_height = max_height

@dataclass
class Relationship:
    """Relationship definition between models"""

    model_class: Type['BaseModel']
    relationship_type: RelationshipType
    foreign_key: Optional[str] = None
    local_key: Optional[str] = None
    through_table: Optional[str] = None
    through_local_key: Optional[str] = None
    through_foreign_key: Optional[str] = None
    backref: Optional[str] = None
    lazy: bool = True

class ModelMeta(type):
    """Metaclass that collects fields and prevents field names from overwriting class attributes"""

    def __new__(cls, name, bases, attrs):
        # Collect fields from class attributes
        fields = {}

        for base in bases:
            if hasattr(base, '_fields'):
                fields.update(base._fields)

        for key, value in attrs.items():
            if isinstance(value, Field):
                fields[key] = value
                # Set verbose name if not set
                if not value.verbose_name:
                    value.verbose_name = key.replace('_', ' ').title()

        # Remove fields from class attributes to avoid shadowing
        for key in fields:
            attrs.pop(key, None)

        # Create the class
        new_class = super().__new__(cls, name, bases, attrs)

        # Store fields in _fields class variable
        new_class._fields = fields

        # Set table name if not specified
        if not hasattr(new_class, '_table_name') or not new_class._table_name:
            new_class._table_name = f"{name.lower()}s"

        # Create DoesNotExist exception for the model
        class DoesNotExist(Exception):
            """Exception raised when the model instance does not exist"""
            def __init__(self, message: Optional[str] = None, **kwargs):
                if message is None:
                    message = f"{name} does not exist"
                super().__init__(message)

        new_class.DoesNotExist = DoesNotExist

        return new_class

class BaseModel(metaclass=ModelMeta):
    """Base model class for database operations"""

    # Class attributes with ClassVar typing
    _fields: ClassVar[Dict[str, Field]] = {}
    _table_name: ClassVar[Optional[str]] = None
    _verbose_name: ClassVar[Optional[str]] = None
    _verbose_name_plural: ClassVar[Optional[str]] = None
    _db_config = None
    _relationships: ClassVar[Dict[str, Relationship]] = {}

    def __init__(self, **kwargs):
        """Initialize model instance with field values"""
        self._data = {}  # Initialize data dictionary

        # Initialize all fields from _fields with their defaults
        for col_name, field in self._fields.items():
            value = kwargs.get(col_name)
            if value is None:
                # Handle default values - call functions for each instance
                if callable(field.default):
                    value = field.default()
                elif field.default is not None:
                    value = field.default
                elif field.primary_key and field.field_type in [FieldType.UUID, FieldType.TEXT]:
                    value = str(uuid.uuid4())
            
            if value is not None:
                validated_value = field.validate(value)
                setattr(self, col_name, validated_value)

        # Set any additional kwargs that aren't in _fields
        for key, value in kwargs.items():
            if key not in self._fields:
                setattr(self, key, value)

        # Initialize relationship tracking
        self._loaded_relations: Dict[str, Any] = {}

    def __getattribute__(self, name):
        """Custom getattr to handle field access"""
        try:
            fields = object.__getattribute__(self, '_fields')
            if name in fields:
                data = object.__getattribute__(self, '_data')
                return data.get(name)
        except AttributeError:
            pass
        return object.__getattribute__(self, name)

    def __setattr__(self, name, value):
        """Custom setattr to handle field assignment"""
        try:
            fields = object.__getattribute__(self, '_fields')
            if name in fields:
                data = object.__getattribute__(self, '_data')
                data[name] = value
                return
        except AttributeError:
            pass
        object.__setattr__(self, name, value)

    def to_dict(self, include_relations: bool = False) -> Dict[str, Any]:
        """Convert model to dictionary"""
        result = {}
        for key, field in self._fields.items():
            value = getattr(self, key, None)
            if value is not None:
                if isinstance(field, (DateTimeField, DateField, TimeField)):
                    if isinstance(value, (datetime, date, time)):
                        result[key] = value.isoformat()
                    else:
                        result[key] = value
                elif isinstance(field, (DecimalField, FloatField)):
                    if isinstance(value, Decimal):
                        result[key] = float(value)
                    else:
                        result[key] = value
                elif isinstance(field, UUIDField):
                    if isinstance(value, uuid.UUID):
                        result[key] = str(value)
                    else:
                        result[key] = value
                elif isinstance(field, JSONField):
                    if isinstance(value, str):
                        result[key] = value
                    else:
                        result[key] = json.dumps(value)
                else:
                    result[key] = value

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
    def set_db_config(cls, config):
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
        """Get verbose name for this model"""
        if cls._verbose_name:
            return cls._verbose_name
        # Convert CamelCase to Title Case
        name = cls.__name__
        return ''.join([' ' + c if c.isupper() else c for c in name]).strip()

    @classmethod
    def get_verbose_name_plural(cls) -> str:
        """Get verbose name plural for this model"""
        if cls._verbose_name_plural:
            return cls._verbose_name_plural
        # Simple pluralization
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
    def query(cls):
        """Return a new QueryBuilder instance"""
        from pyserv.models.query import QueryBuilder
        return QueryBuilder(cls)

    @classmethod
    def objects(cls):
        """Get a queryset for this model (Django-like API)"""
        return cls.query()

    async def save(self, update_fields: Optional[List[str]] = None):
        """Save the instance to the database"""
        db = DatabaseConnection.get_instance(self._db_config)

        # Update timestamps
        now = datetime.now(timezone.utc)
        if hasattr(self, 'updated_at'):
            self.updated_at = now
        if not hasattr(self, 'created_at') or not getattr(self, 'created_at'):
            if hasattr(self, 'created_at'):
                self.created_at = now

        # Convert instance to dict for backend
        if update_fields:
            # Only include specified fields plus updated_at
            data = {}
            for field in update_fields:
                if hasattr(self, field):
                    value = getattr(self, field)
                    if isinstance(value, (datetime, date, time)):
                        data[field] = value.isoformat()
                    else:
                        data[field] = value
        else:
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
    async def get(cls, id: Union[int, str]):
        """Get a single record by primary key"""
        primary_key = cls.get_primary_key()
        if not primary_key:
            raise ValueError("Model does not have a primary key")

        instance = await cls.query().filter(**{primary_key: id}).first()
        if instance is None:
            raise cls.DoesNotExist()
        return instance

    @classmethod
    async def create(cls, **kwargs):
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

        # Use backend delete method
        filters = {primary_key: getattr(self, primary_key)}
        success = await db.backend.delete_one(self.__class__, filters)
        if not success:
            raise ValueError("Record not found")

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.to_dict()}>"

# Validators
def validate_email(value: str) -> str:
    """Email validator"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, value):
        raise ValueError("Invalid email format")
    return value

def validate_url(value: str) -> str:
    """URL validator"""
    pattern = r'^https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:\w)*)?)?$'
    if not re.match(pattern, value):
        raise ValueError("Invalid URL format")
    return value

def validate_phone(value: str) -> str:
    """Phone number validator"""
    pattern = r'^\+?[\d\s\-\(\)]{10,}$'
    if not re.match(pattern, value):
        raise ValueError("Invalid phone number format")
    return value

def validate_ip(value: str) -> str:
    """IP address validator"""
    import ipaddress
    try:
        ipaddress.ip_address(value)
    except ValueError:
        raise ValueError("Invalid IP address")
    return value

# Utility function to get appropriate field type from Python type
def get_field_from_type(python_type: Type) -> Field:
    """Get appropriate Field subclass from Python type"""
    from typing import get_origin
    
    type_map = {
        int: IntegerField,
        str: StringField,
        bool: BooleanField,
        float: FloatField,
        datetime: DateTimeField,
        date: DateField,
        time: TimeField,
        uuid.UUID: UUIDField,
        Decimal: DecimalField,
        dict: JSONField,
        list: JSONField,
    }

    origin = get_origin(python_type) or python_type
    field_class = type_map.get(origin, Field)
    return field_class() if callable(field_class) else Field()

# Export all field types
__all__ = [
    'FieldType', 'Field', 'StringField', 'IntegerField', 'BigIntegerField', 'BooleanField',
    'DateTimeField', 'DateField', 'TimeField', 'FloatField', 'DecimalField',
    'UUIDField', 'JSONField', 'TextField', 'BlobField', 'ByteaField',
    'TimestampTZField', 'EmailField', 'PhoneField', 'URLField', 'IPAddressField',
    'PasswordField', 'ArrayField', 'EnumField', 'ForeignKeyField', 'FileField', 'ImageField',
    'BaseModel', 'Relationship', 'RelationshipType', 'PaginatedResponse', 'AggregationResult',
    'OrderDirection', 'LazyLoad', 'ModelMeta', 'validate_email', 'validate_url', 
    'validate_phone', 'validate_ip', 'get_field_from_type'
]
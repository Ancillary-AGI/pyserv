"""
Type system for Pyserv framework with comprehensive field definitions.
"""

from typing import Any, Dict, List, Optional, Type, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid
from datetime import datetime, date, time
from decimal import Decimal


class FieldType(Enum):
    """Field types for database schema"""
    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    DATE = "date"
    TIME = "time"
    FLOAT = "float"
    DECIMAL = "decimal"
    UUID = "uuid"
    JSON = "json"
    TEXT = "text"
    BLOB = "blob"
    BYTEA = "bytea"
    TIMESTAMPTZ = "timestamptz"


@dataclass
class Field:
    """Base field class"""

    field_type: FieldType
    primary_key: bool = False
    nullable: bool = True
    default: Any = None
    autoincrement: bool = False
    unique: bool = False
    index: bool = False
    validators: List[Callable] = field(default_factory=list)
    help_text: str = ""
    verbose_name: str = ""

    def __post_init__(self):
        if self.primary_key:
            self.nullable = False

    def validate(self, value: Any) -> Any:
        """Validate field value"""
        if value is None and not self.nullable:
            raise ValueError(f"{self.verbose_name or 'Field'} cannot be null")

        for validator in self.validators:
            value = validator(value)

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
            "help_text": self.help_text,
            "verbose_name": self.verbose_name
        }


@dataclass
class StringField(Field):
    """String field"""

    max_length: Optional[int] = None
    min_length: Optional[int] = None
    choices: Optional[List[str]] = None
    regex: Optional[str] = None

    def __post_init__(self):
        super().__post_init__()
        self.field_type = FieldType.STRING

        if self.choices:
            self.validators.append(self._validate_choices)

        if self.regex:
            self.validators.append(self._validate_regex)

        if self.min_length or self.max_length:
            self.validators.append(self._validate_length)

    def _validate_choices(self, value: str) -> str:
        if self.choices and value not in self.choices:
            raise ValueError(f"Value must be one of {self.choices}")
        return value

    def _validate_regex(self, value: str) -> str:
        import re
        if not re.match(self.regex, value):
            raise ValueError(f"Value does not match required pattern")
        return value

    def _validate_length(self, value: str) -> str:
        if self.min_length and len(value) < self.min_length:
            raise ValueError(f"Minimum length is {self.min_length}")
        if self.max_length and len(value) > self.max_length:
            raise ValueError(f"Maximum length is {self.max_length}")
        return value


@dataclass
class IntegerField(Field):
    """Integer field"""

    min_value: Optional[int] = None
    max_value: Optional[int] = None

    def __post_init__(self):
        super().__post_init__()
        self.field_type = FieldType.INTEGER

        if self.min_value is not None or self.max_value is not None:
            self.validators.append(self._validate_range)

    def _validate_range(self, value: int) -> int:
        if self.min_value is not None and value < self.min_value:
            raise ValueError(f"Minimum value is {self.min_value}")
        if self.max_value is not None and value > self.max_value:
            raise ValueError(f"Maximum value is {self.max_value}")
        return value


@dataclass
class BooleanField(Field):
    """Boolean field"""

    def __post_init__(self):
        super().__post_init__()
        self.field_type = FieldType.BOOLEAN


@dataclass
class DateTimeField(Field):
    """DateTime field"""

    auto_now: bool = False
    auto_now_add: bool = False

    def __post_init__(self):
        super().__post_init__()
        self.field_type = FieldType.DATETIME

        if self.auto_now or self.auto_now_add:
            self.default = datetime.now

    def validate(self, value: Any) -> Any:
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except ValueError:
                raise ValueError("Invalid datetime format")
        return super().validate(value)


@dataclass
class DateField(Field):
    """Date field"""

    def __post_init__(self):
        super().__post_init__()
        self.field_type = FieldType.DATE

    def validate(self, value: Any) -> Any:
        if isinstance(value, str):
            try:
                value = date.fromisoformat(value)
            except ValueError:
                raise ValueError("Invalid date format")
        return super().validate(value)


@dataclass
class TimeField(Field):
    """Time field"""

    def __post_init__(self):
        super().__post_init__()
        self.field_type = FieldType.TIME

    def validate(self, value: Any) -> Any:
        if isinstance(value, str):
            try:
                value = time.fromisoformat(value)
            except ValueError:
                raise ValueError("Invalid time format")
        return super().validate(value)


@dataclass
class FloatField(Field):
    """Float field"""

    min_value: Optional[float] = None
    max_value: Optional[float] = None
    decimal_places: Optional[int] = None

    def __post_init__(self):
        super().__post_init__()
        self.field_type = FieldType.FLOAT

        if self.min_value is not None or self.max_value is not None:
            self.validators.append(self._validate_range)

    def _validate_range(self, value: float) -> float:
        if self.min_value is not None and value < self.min_value:
            raise ValueError(f"Minimum value is {self.min_value}")
        if self.max_value is not None and value > self.max_value:
            raise ValueError(f"Maximum value is {self.max_value}")
        return value


@dataclass
class DecimalField(Field):
    """Decimal field"""

    max_digits: Optional[int] = None
    decimal_places: Optional[int] = None
    min_value: Optional[Decimal] = None
    max_value: Optional[Decimal] = None

    def __post_init__(self):
        super().__post_init__()
        self.field_type = FieldType.DECIMAL

        if self.min_value is not None or self.max_value is not None:
            self.validators.append(self._validate_range)

    def _validate_range(self, value: Decimal) -> Decimal:
        if self.min_value is not None and value < self.min_value:
            raise ValueError(f"Minimum value is {self.min_value}")
        if self.max_value is not None and value > self.max_value:
            raise ValueError(f"Maximum value is {self.max_value}")
        return value


@dataclass
class UUIDField(Field):
    """UUID field"""

    auto_generate: bool = False

    def __post_init__(self):
        super().__post_init__()
        self.field_type = FieldType.UUID

        if self.auto_generate:
            self.default = lambda: str(uuid.uuid4())

    def validate(self, value: Any) -> Any:
        if isinstance(value, str):
            try:
                value = uuid.UUID(value)
            except ValueError:
                raise ValueError("Invalid UUID format")
        return super().validate(value)


@dataclass
class JSONField(Field):
    """JSON field"""

    def __post_init__(self):
        super().__post_init__()
        self.field_type = FieldType.JSON

    def validate(self, value: Any) -> Any:
        if value is not None:
            try:
                if isinstance(value, str):
                    json.loads(value)
                else:
                    json.dumps(value)
            except (json.JSONDecodeError, TypeError):
                raise ValueError("Invalid JSON data")
        return super().validate(value)


@dataclass
class TextField(Field):
    """Text field (large text)"""

    def __post_init__(self):
        super().__post_init__()
        self.field_type = FieldType.TEXT


@dataclass
class BlobField(Field):
    """Binary large object field"""

    def __post_init__(self):
        super().__post_init__()
        self.field_type = FieldType.BLOB


@dataclass
class ByteaField(Field):
    """PostgreSQL bytea field"""

    def __post_init__(self):
        super().__post_init__()
        self.field_type = FieldType.BYTEA


@dataclass
class TimestampTZField(Field):
    """Timestamp with timezone field"""

    def __post_init__(self):
        super().__post_init__()
        self.field_type = FieldType.TIMESTAMPTZ


# Validators
def validate_email(value: str) -> str:
    """Email validator"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, value):
        raise ValueError("Invalid email format")
    return value


def validate_url(value: str) -> str:
    """URL validator"""
    import re
    pattern = r'^https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:\w)*)?)?$'
    if not re.match(pattern, value):
        raise ValueError("Invalid URL format")
    return value


def validate_phone(value: str) -> str:
    """Phone number validator"""
    import re
    # Simple international phone validation
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


# Model metaclass
class ModelMetaclass(type):
    """Metaclass for models"""

    def __new__(cls, name, bases, namespace, **kwargs):
        # Collect fields
        fields = {}

        for base in bases:
            if hasattr(base, '_fields'):
                fields.update(base._fields)

        for key, value in namespace.items():
            if isinstance(value, Field):
                fields[key] = value
                # Set verbose name if not set
                if not value.verbose_name:
                    value.verbose_name = key.replace('_', ' ').title()

        namespace['_fields'] = fields

        # Create the class
        new_class = super().__new__(cls, name, bases, namespace, **kwargs)

        return new_class


# Base model class
class BaseModel(metaclass=ModelMetaclass):
    """Base model class"""

    _fields: Dict[str, Field] = {}

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if key in self._fields:
                field = self._fields[key]
                validated_value = field.validate(value)
                setattr(self, key, validated_value)
            else:
                setattr(self, key, value)

    def to_dict(self) -> Dict[str, Any]:
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
        return result

    @classmethod
    def get_table_name(cls) -> str:
        """Get table name for model"""
        return cls.__name__.lower() + 's'

    @classmethod
    def get_primary_key(cls) -> Optional[str]:
        """Get primary key field name"""
        for name, field in cls._fields.items():
            if field.primary_key:
                return name
        return None

    def save(self):
        """Save model instance"""
        # This would be implemented by the ORM
        pass

    def delete(self):
        """Delete model instance"""
        # This would be implemented by the ORM
        pass

    @classmethod
    def create(cls, **kwargs):
        """Create new model instance"""
        # This would be implemented by the ORM
        return cls(**kwargs)

    @classmethod
    def query(cls):
        """Get query builder for model"""
        # This would be implemented by the ORM
        return QueryBuilder(cls)


class QueryBuilder:
    """Query builder for models"""

    def __init__(self, model_class: Type[BaseModel]):
        self.model_class = model_class
        self._filters = {}
        self._order_by = []
        self._limit = None
        self._offset = None
        self._select_fields = None

    def filter(self, **kwargs) -> 'QueryBuilder':
        """Add filters"""
        self._filters.update(kwargs)
        return self

    def exclude(self, **kwargs) -> 'QueryBuilder':
        """Add exclusion filters"""
        for key, value in kwargs.items():
            self._filters[key] = {'$ne': value}
        return self

    def order_by(self, field: str, direction: str = 'asc') -> 'QueryBuilder':
        """Add ordering"""
        direction_int = 1 if direction.lower() == 'asc' else -1
        self._order_by.append((field, direction_int))
        return self

    def limit(self, count: int) -> 'QueryBuilder':
        """Set limit"""
        self._limit = count
        return self

    def offset(self, count: int) -> 'QueryBuilder':
        """Set offset"""
        self._offset = count
        return self

    def select(self, *fields) -> 'QueryBuilder':
        """Select specific fields"""
        self._select_fields = fields
        return self

    def first(self):
        """Get first result"""
        # This would be implemented by the ORM
        pass

    def all(self):
        """Get all results"""
        # This would be implemented by the ORM
        pass

    def count(self) -> int:
        """Get count of results"""
        # This would be implemented by the ORM
        return 0

    def exists(self) -> bool:
        """Check if results exist"""
        return self.count() > 0


# Export all field types
__all__ = [
    'FieldType', 'Field', 'StringField', 'IntegerField', 'BooleanField',
    'DateTimeField', 'DateField', 'TimeField', 'FloatField', 'DecimalField',
    'UUIDField', 'JSONField', 'TextField', 'BlobField', 'ByteaField',
    'TimestampTZField', 'BaseModel', 'QueryBuilder',
    'validate_email', 'validate_url', 'validate_phone', 'validate_ip'
]


"""
Advanced type system for Pyserv framework with comprehensive field definitions.
"""

from typing import Any, Callable, Optional, Union, Dict, List, Type, get_origin, Awaitable
from enum import Enum
from pyserv.database.config import DatabaseConfig
from pyserv.database.connections import DatabaseConnection
from pydantic import BaseModel, Field as PydanticField
from datetime import datetime, date, time
import uuid
import re
from decimal import Decimal
from email_validator import validate_email, EmailNotValidError
from phonenumbers import parse as parse_phone, is_valid_number, format_number, PhoneNumberFormat, NumberParseException


class FieldType(str, Enum):
    # Basic types
    INTEGER = "INTEGER"
    BIGINT = "BIGINT"
    SMALLINT = "SMALLINT"
    TEXT = "TEXT"
    VARCHAR = "VARCHAR"
    CHAR = "CHAR"
    BOOLEAN = "BOOLEAN"
    TIMESTAMP = "TIMESTAMP"
    TIMESTAMPTZ = "TIMESTAMPTZ"
    FLOAT = "FLOAT"
    DOUBLE = "DOUBLE"
    DECIMAL = "DECIMAL"
    NUMERIC = "NUMERIC"
    JSON = "JSON"
    JSONB = "JSONB"
    DATE = "DATE"
    TIME = "TIME"
    UUID = "UUID"
    BLOB = "BLOB"
    BYTEA = "BYTEA"

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
            # This will be handled by the __getattr__ in BaseModel
            return instance.__getattr__(self.relationship_name)

        return self._cached_value

    def __set__(self, instance, value):
        self._cached_value = value
        self._loaded = True
        instance._loaded_relations[self.relationship_name] = value

# Base Field class remains the same
class Field:
    """Field definition for database columns"""

    def __init__(
        self,
        field_type: Union[FieldType, str],
        primary_key: bool = False,
        autoincrement: bool = False,
        unique: bool = False,
        nullable: bool = True,
        default: Any = None,
        foreign_key: Optional[str] = None,
        index: bool = False,
        after: Optional[str] = None
    ):
        self.field_type = FieldType(field_type) if isinstance(field_type, str) else field_type
        self.primary_key = primary_key
        self.autoincrement = autoincrement
        self.unique = unique
        self.nullable = nullable
        self.default = default() if callable(default) else default
        self.foreign_key = foreign_key
        self.index = index
        self.after = after

        # Set default for primary key if not specified
        if primary_key and default is None and field_type in ['UUID', 'TEXT']:
            self.default = str(uuid.uuid4())

    def sql_definition(self, name: str, db_config: DatabaseConfig) -> str:
        """Generate SQL column definition using connection abstraction"""
        connection = DatabaseConnection.get_instance(db_config)

        # Use connection to get SQL type
        sql_type = connection.get_sql_type(self)
        parts = [name, sql_type]

        if self.primary_key:
            parts.append("PRIMARY KEY")
            if self.autoincrement:
                # Use connection-specific autoincrement syntax
                if db_config.is_sqlite:
                    parts.append("AUTOINCREMENT")
                elif db_config.is_mysql:
                    parts.append("AUTO_INCREMENT")
                elif db_config.is_postgres:
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

        if self.after and db_config.is_mysql:
            parts.append(f"AFTER {self.after}")

        return " ".join(parts)

    def get_type_mapping(self, db_config: DatabaseConfig) -> Dict[FieldType, str]:
        """Get database-specific type mappings using connection"""
        connection = DatabaseConnection.get_instance(db_config)
        # This method delegates to connection for type mappings
        return connection.get_type_mappings()



# Predefined specialized field types
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

class DateField(Field):
    """Date field (without time)"""

    def __init__(self, **kwargs):
        super().__init__(FieldType.DATE, **kwargs)

class TimeField(Field):
    """Time field"""

    def __init__(self, **kwargs):
        super().__init__(FieldType.TIME, **kwargs)

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

    def sql_definition(self, name: str, db_config: DatabaseConfig) -> str:
        if db_config.is_postgresql:
            self.field_type = f"NUMERIC({self.max_digits}, {self.decimal_places})"
        elif db_config.is_mysql:
            self.field_type = f"DECIMAL({self.max_digits}, {self.decimal_places})"
        return super().sql_definition(name, db_config)

class UUIDField(Field):
    """UUID field with automatic generation"""

    def __init__(self, **kwargs):
        if 'default' not in kwargs:
            kwargs['default'] = str(uuid.uuid4())
        super().__init__(FieldType.UUID, **kwargs)

class EmailField(StringField):
    """Email field with validation"""

    def __init__(self, **kwargs):
        kwargs.setdefault('max_length', 255)
        super().__init__(**kwargs)
        self.pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    def validate(self, value: str) -> bool:
        """Validate email format"""
        if not value:
            return True
        try:
            validate_email(value)
            return True
        except EmailNotValidError:
            return False

class PhoneField(StringField):
    """Phone number field with validation"""

    def __init__(self, region: str = "US", **kwargs):
        kwargs.setdefault('max_length', 20)
        super().__init__(**kwargs)
        self.region = region

    def validate(self, value: str) -> bool:
        """Validate phone number format"""
        if not value:
            return True
        try:
            phone_number = parse_phone(value, self.region)
            return is_valid_number(phone_number)
        except NumberParseException:
            return False

    def format(self, value: str, format: PhoneNumberFormat = PhoneNumberFormat.INTERNATIONAL) -> str:
        """Format phone number"""
        if not value:
            return value
        try:
            phone_number = parse_phone(value, self.region)
            return format_number(phone_number, format)
        except NumberParseException:
            return value

class URLField(StringField):
    """URL field with validation"""

    def __init__(self, **kwargs):
        kwargs.setdefault('max_length', 2083)  # Maximum URL length in browsers
        super().__init__(**kwargs)
        self.pattern = r'^(https?|ftp)://[^\s/$.?#].[^\s]*$'

    def validate(self, value: str) -> bool:
        """Validate URL format"""
        if not value:
            return True
        return re.match(self.pattern, value) is not None

class IPAddressField(StringField):
    """IP address field (IPv4/IPv6)"""

    def __init__(self, **kwargs):
        kwargs.setdefault('max_length', 45)  # IPv6 maximum length
        super().__init__(**kwargs)

    def validate(self, value: str) -> bool:
        """Validate IP address format"""
        if not value:
            return True
        # Simple IPv4 validation
        ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        # Simple IPv6 validation
        ipv6_pattern = r'^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$'

        return (re.match(ipv4_pattern, value) is not None or
                re.match(ipv6_pattern, value) is not None)

class JSONField(Field):
    """JSON field with schema validation"""

    def __init__(self, schema: Optional[Dict] = None, **kwargs):
        super().__init__(FieldType.JSON, **kwargs)
        self.schema = schema

    def validate(self, value: Any) -> bool:
        """Validate JSON against schema if provided"""
        if not self.schema or value is None:
            return True

        try:
            # Simple schema validation - in production, use jsonschema library
            if isinstance(self.schema, type) and not isinstance(value, self.schema):
                return False
            return True
        except:
            return False

class ArrayField(Field):
    """Array field for storing lists"""

    def __init__(self, item_type: FieldType, dimensions: int = 1, **kwargs):
        super().__init__(FieldType.ARRAY, **kwargs)
        self.item_type = item_type
        self.dimensions = dimensions

    def sql_definition(self, name: str, db_config: DatabaseConfig) -> str:
        if db_config.is_postgresql:
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

    def validate(self, value: Any) -> bool:
        """Validate value is in enum choices"""
        if value is None:
            return True
        return value in self.choices

class ForeignKeyField(Field):
    """Foreign key field with relationship support"""

    def __init__(self, to: Union[str, Type['BaseModel']], on_delete: str = "CASCADE", **kwargs):
        super().__init__(FieldType.INTEGER, **kwargs)
        self.to = to
        self.on_delete = on_delete.upper()

    def sql_definition(self, name: str, db_config: DatabaseConfig) -> str:
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

class PasswordField(StringField):
    """Password field with hashing"""

    def __init__(self, min_length: int = 8, require_special: bool = True, **kwargs):
        kwargs.setdefault('min_length', min_length)
        super().__init__(**kwargs)
        self.require_special = require_special

    def validate(self, value: str) -> bool:
        """Validate password strength"""
        if not value or len(value) < self.min_length:
            return False

        if self.require_special:
            # Check for at least one special character
            if not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
                return False

        # Check for at least one number and one letter
        if not (re.search(r'\d', value) and re.search(r'[a-zA-Z]', value)):
            return False

        return True

    def hash_password(self, password: str) -> str:
        """Hash password (implement proper hashing in production)"""
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest()




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

# Relationship class remains the same
class Relationship:
    """Relationship definition between models"""

    def __init__(
        self,
        model_class: 'BaseModel',
        relationship_type: RelationshipType,
        foreign_key: Optional[str] = None,
        local_key: Optional[str] = None,
        through_table: Optional[str] = None,
        through_local_key: Optional[str] = None,
        through_foreign_key: Optional[str] = None,
        backref: Optional[str] = None,
        lazy: bool = True
    ):
        self.model_class = model_class
        self.relationship_type = relationship_type
        self.foreign_key = foreign_key
        self.local_key = local_key or 'id'
        self.through_table = through_table
        self.through_local_key = through_local_key
        self.through_foreign_key = through_foreign_key
        self.backref = backref
        self.lazy = lazy

class PaginatedResponse(BaseModel):
    """Paginated response DTO"""
    items: List[Any] = PydanticField(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 0

class AggregationResult(BaseModel):
    """Aggregation result DTO"""
    count: int = 0
    sum: float = 0
    avg: float = 0
    min: Optional[Any] = None
    max: Optional[Any] = None
    group_by: Dict[Any, Any] = PydanticField(default_factory=dict)

# Utility function to get appropriate field type from Python type
def get_field_from_type(python_type: Type) -> Field:
    """Get appropriate Field subclass from Python type"""
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
    return type_map.get(origin, Field)()

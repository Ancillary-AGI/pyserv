# Consolidated comprehensive type system for Pyserv framework
# This merges the best features from both implementations

from typing import Any, Callable, Optional, Union, Dict, List, Type, get_origin, Awaitable
from enum import Enum
from datetime import datetime, date, time
import uuid
import re
import json
from decimal import Decimal
from dataclasses import dataclass, field

# Basic FieldType enum combining both implementations
class FieldType(Enum):
    """Field types for database schema"""
    # Basic types
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

    # Advanced database types
    BIGINT = "bigint"
    SMALLINT = "smallint"
    VARCHAR = "varchar"
    CHAR = "char"
    TIMESTAMP = "timestamp"
    DOUBLE = "double"
    NUMERIC = "numeric"
    JSONB = "jsonb"

    # Specialized types
    EMAIL = "email"
    PHONE = "phone"
    URL = "url"
    IP_ADDRESS = "ip_address"
    MAC_ADDRESS = "mac_address"
    ENUM = "enum"
    ARRAY = "array"
    RANGE = "range"
    GEOMETRY = "geometry"
    GEOGRAPHY = "geography"
    HSTORE = "hstore"
    INET = "inet"
    MONEY = "money"

# Relationship types
class RelationshipType(str, Enum):
    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_ONE = "many_to_one"
    MANY_TO_MANY = "many_to_many"

# Order directions
class OrderDirection(str, Enum):
    ASC = "ASC"
    DESC = "DESC"

# Lazy loading descriptor
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

# Base Field class with comprehensive functionality
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
    validators: List[Callable] = field(default_factory=list)
    help_text: str = ""
    verbose_name: str = ""
    foreign_key: Optional[str] = None
    max_length: Optional[int] = None
    min_length: Optional[int] = None
    choices: Optional[List[str]] = None
    regex: Optional[str] = None
    min_value: Optional[Union[int, float, Decimal]] = None
    max_value: Optional[Union[int, float, Decimal]] = None

    def __post_init__(self):
        if self.primary_key:
            self.nullable = False

        # Set up validators based on field properties
        if self.choices:
            self.validators.append(self._validate_choices)
        if self.regex:
            self.validators.append(self._validate_regex)
        if self.min_length or self.max_length:
            self.validators.append(self._validate_length)
        if self.min_value is not None or self.max_value is not None:
            self.validators.append(self._validate_range)

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
        if not re.match(self.regex, value):
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
            "help_text": self.help_text,
            "verbose_name": self.verbose_name,
            "max_length": self.max_length,
            "min_length": self.min_length,
            "choices": self.choices,
            "regex": self.regex,
            "min_value": self.min_value,
            "max_value": self.max_value
        }

# Specialized field classes
@dataclass
class StringField(Field):
    """String field with comprehensive validation"""

    def __post_init__(self):
        super().__post_init__()
        self.field_type = FieldType.STRING

@dataclass
class IntegerField(Field):
    """Integer field with range validation"""

    def __post_init__(self):
        super().__post_init__()
        self.field_type = FieldType.INTEGER

@dataclass
class BooleanField(Field):
    """Boolean field"""

    def __post_init__(self):
        super().__post_init__()
        self.field_type = FieldType.BOOLEAN

@dataclass
class DateTimeField(Field):
    """DateTime field with auto timestamps"""

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
    """Float field with precision validation"""

    def __post_init__(self):
        super().__post_init__()
        self.field_type = FieldType.FLOAT

@dataclass
class DecimalField(Field):
    """Decimal field with fixed precision"""

    max_digits: Optional[int] = None
    decimal_places: Optional[int] = None

    def __post_init__(self):
        super().__post_init__()
        self.field_type = FieldType.DECIMAL

@dataclass
class UUIDField(Field):
    """UUID field with automatic generation"""

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
    """JSON field with validation"""

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

# Advanced field types with specialized validation
@dataclass
class EmailField(StringField):
    """Email field with validation"""

    def __post_init__(self):
        super().__post_init__()
        self.regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not self.max_length:
            self.max_length = 255

    def validate(self, value: str) -> str:
        """Validate email format and strength"""
        if value is None:
            return super().validate(value)

        # Basic regex validation
        if not re.match(self.regex, value):
            raise ValueError("Invalid email format")

        return value

@dataclass
class PhoneField(StringField):
    """Phone number field with validation"""

    region: str = "US"

    def __post_init__(self):
        super().__post_init__()
        if not self.max_length:
            self.max_length = 20

    def validate(self, value: str) -> str:
        """Validate phone number format"""
        if value is None:
            return super().validate(value)

        # Basic international phone validation
        pattern = r'^\+?[\d\s\-\(\)]{10,}$'
        if not re.match(pattern, value):
            raise ValueError("Invalid phone number format")

        return value

    def format(self, value: str, format_style: str = "INTERNATIONAL") -> str:
        """Format phone number"""
        if not value:
            return value
        # Simple formatting - in production, use phonenumbers library
        return value

@dataclass
class URLField(StringField):
    """URL field with validation"""

    def __post_init__(self):
        super().__post_init__()
        self.regex = r'^(https?|ftp)://[^\s/$.?#].[^\s]*$'
        if not self.max_length:
            self.max_length = 2083  # Maximum URL length in browsers

    def validate(self, value: str) -> str:
        """Validate URL format"""
        if value is None:
            return super().validate(value)

        if not re.match(self.regex, value):
            raise ValueError("Invalid URL format")

        return value

@dataclass
class IPAddressField(StringField):
    """IP address field (IPv4/IPv6)"""

    def __post_init__(self):
        super().__post_init__()
        if not self.max_length:
            self.max_length = 45  # IPv6 maximum length

    def validate(self, value: str) -> str:
        """Validate IP address format"""
        if value is None:
            return super().validate(value)

        # Simple IPv4 validation
        ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        # Simple IPv6 validation
        ipv6_pattern = r'^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$'

        if not (re.match(ipv4_pattern, value) or re.match(ipv6_pattern, value)):
            raise ValueError("Invalid IP address")

        return value

@dataclass
class PasswordField(StringField):
    """Password field with strength validation"""

    min_length: int = 8
    require_special: bool = True
    require_numbers: bool = True
    require_uppercase: bool = True

    def __post_init__(self):
        super().__post_init__()
        if not self.max_length:
            self.max_length = 128

    def validate(self, value: str) -> str:
        """Validate password strength"""
        if value is None:
            return super().validate(value)

        if len(value) < self.min_length:
            raise ValueError(f"Password must be at least {self.min_length} characters long")

        if self.require_special:
            # Check for at least one special character
            if not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
                raise ValueError("Password must contain at least one special character")

        if self.require_numbers:
            # Check for at least one number
            if not re.search(r'\d', value):
                raise ValueError("Password must contain at least one number")

        if self.require_uppercase:
            # Check for at least one uppercase letter
            if not re.search(r'[A-Z]', value):
                raise ValueError("Password must contain at least one uppercase letter")

        return value

    def hash_password(self, password: str) -> str:
        """Hash password (implement proper hashing in production)"""
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest()

# Relationship class
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
    """Base model class with comprehensive functionality"""

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

# Query builder
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

# Export all field types
__all__ = [
    'FieldType', 'Field', 'StringField', 'IntegerField', 'BooleanField',
    'DateTimeField', 'DateField', 'TimeField', 'FloatField', 'DecimalField',
    'UUIDField', 'JSONField', 'TextField', 'BlobField', 'ByteaField',
    'TimestampTZField', 'EmailField', 'PhoneField', 'URLField', 'IPAddressField',
    'PasswordField', 'BaseModel', 'QueryBuilder', 'Relationship', 'RelationshipType',
    'OrderDirection', 'LazyLoad', 'validate_email', 'validate_url', 'validate_phone', 'validate_ip'
]

from typing import Any, Callable, Optional, Union, Dict, List, Type, get_origin, get_args, Awaitable
from enum import Enum
from core.config import DatabaseConfig
from pydantic import BaseModel, Field as PydanticField, validator
from datetime import datetime, date, time
import inspect
import uuid
import re
import json
from decimal import Decimal
from email_validator import validate_email, EmailNotValidError
from phonenumbers import parse as parse_phone, is_valid_number, format_number, PhoneNumberFormat
from phonenumbers import NumberParseException


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
        """Generate SQL column definition"""
        parts = [name]
        
        # Handle field type differences between databases
        type_mapping = self._get_type_mapping(db_config)
        db_type = type_mapping.get(self.field_type, self.field_type.value)
        parts.append(db_type)
        
        if self.primary_key:
            parts.append("PRIMARY KEY")
            if self.autoincrement:
                if db_config.is_sqlite:
                    parts.append("AUTOINCREMENT")
                elif db_config.is_mysql:
                    parts.append("AUTO_INCREMENT")
        
        if not self.nullable:
            parts.append("NOT NULL")
            
        if self.unique:
            parts.append("UNIQUE")
            
        if self.default is not None:
            default_str = self._format_default(db_config)
            parts.append(f"DEFAULT {default_str}")
        
        if self.foreign_key:
            parts.append(self._format_foreign_key(db_config))
        
        if self.after and db_config.is_mysql:
            parts.append(f"AFTER {self.after}")
                
        return " ".join(parts)
    
    def _get_type_mapping(self, db_config: DatabaseConfig) -> Dict[FieldType, str]:
        """Get database-specific type mappings"""
        if db_config.is_mysql:
            return {
                FieldType.BOOLEAN: "TINYINT(1)",
                FieldType.UUID: "CHAR(36)",
                FieldType.JSON: "JSON",
                FieldType.TIMESTAMPTZ: "TIMESTAMP",
            }
        elif db_config.is_postgresql:
            return {
                FieldType.BOOLEAN: "BOOLEAN",
                FieldType.UUID: "UUID",
                FieldType.JSON: "JSONB",
                FieldType.TIMESTAMPTZ: "TIMESTAMPTZ",
            }
        elif db_config.is_sqlite:
            return {
                FieldType.BOOLEAN: "INTEGER",
                FieldType.UUID: "TEXT",
                FieldType.JSON: "TEXT",
                FieldType.TIMESTAMPTZ: "TEXT",
            }
        return {}
    
    def _format_default(self, db_config: DatabaseConfig) -> str:
        """Format default value for SQL"""
        if isinstance(self.default, str):
            if self.default.upper() in ['CURRENT_TIMESTAMP', 'CURRENT_DATE']:
                return self.default
            return f"'{self.default}'"
        elif isinstance(self.default, (int, float, Decimal)):
            return str(self.default)
        elif isinstance(self.default, bool):
            return '1' if self.default else '0' if db_config.is_mysql else 'TRUE' if self.default else 'FALSE'
        elif self.default is None:
            return 'NULL'
        return f"'{str(self.default)}'"
    
    def _format_foreign_key(self, db_config: DatabaseConfig) -> str:
        """Format foreign key constraint"""
        ref_table, ref_column = self.foreign_key.split('.')
        if db_config.is_mysql:
            return f"FOREIGN KEY REFERENCES {ref_table}({ref_column})"
        else:
            return f"REFERENCES {ref_table}({ref_column})"

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
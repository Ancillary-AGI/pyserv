"""
Form validation and data handling for Pyserv  framework.
Provides comprehensive validation, sanitization, and CSRF protection.
"""

import re
import hashlib
import hmac
import secrets
from typing import Dict, List, Any, Optional, Union, Callable, Type, Pattern
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from functools import wraps
from urllib.parse import unquote

from pyserv.utils.types import ValidationError, FieldValidationError, PasswordField


class Validator:
    """Base validator class"""

    def __init__(self, message: str = None):
        self.message = message

    def validate(self, value: Any, field_name: str = None) -> Any:
        """Validate and return the value, or raise ValidationError"""
        raise NotImplementedError

    def __call__(self, value: Any, field_name: str = None) -> Any:
        return self.validate(value, field_name)


class RequiredValidator(Validator):
    """Validator for required fields"""

    def __init__(self, message: str = "This field is required"):
        super().__init__(message)

    def validate(self, value: Any, field_name: str = None) -> Any:
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ValidationError(self.message, field_name)
        return value


class LengthValidator(Validator):
    """Validator for string length"""

    def __init__(self, min_length: int = None, max_length: int = None,
                 message: str = None):
        super().__init__(message)
        self.min_length = min_length
        self.max_length = max_length

    def validate(self, value: Any, field_name: str = None) -> Any:
        if not isinstance(value, str):
            value = str(value)

        length = len(value)

        if self.min_length is not None and length < self.min_length:
            message = self.message or f"Minimum length is {self.min_length}"
            raise ValidationError(message, field_name)

        if self.max_length is not None and length > self.max_length:
            message = self.message or f"Maximum length is {self.max_length}"
            raise ValidationError(message, field_name)

        return value


class RegexValidator(Validator):
    """Validator using regular expressions"""

    def __init__(self, pattern: Union[str, Pattern], message: str = None):
        super().__init__(message)
        self.pattern = re.compile(pattern) if isinstance(pattern, str) else pattern

    def validate(self, value: Any, field_name: str = None) -> Any:
        if not isinstance(value, str):
            value = str(value)

        if not self.pattern.match(value):
            message = self.message or "Invalid format"
            raise ValidationError(message, field_name)

        return value


class EmailValidator(RegexValidator):
    """Validator for email addresses"""

    EMAIL_PATTERN = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )

    def __init__(self, message: str = "Invalid email address"):
        super().__init__(self.EMAIL_PATTERN, message)


class URLValidator(RegexValidator):
    """Validator for URLs"""

    URL_PATTERN = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )

    def __init__(self, message: str = "Invalid URL"):
        super().__init__(self.URL_PATTERN, message)


class RangeValidator(Validator):
    """Validator for numeric ranges"""

    def __init__(self, min_value: Union[int, float] = None,
                 max_value: Union[int, float] = None, message: str = None):
        super().__init__(message)
        self.min_value = min_value
        self.max_value = max_value

    def validate(self, value: Any, field_name: str = None) -> Any:
        try:
            num_value = float(value)
        except (ValueError, TypeError):
            raise ValidationError("Value must be numeric", field_name)

        if self.min_value is not None and num_value < self.min_value:
            message = self.message or f"Value must be at least {self.min_value}"
            raise ValidationError(message, field_name)

        if self.max_value is not None and num_value > self.max_value:
            message = self.message or f"Value must be at most {self.max_value}"
            raise ValidationError(message, field_name)

        return num_value


class ChoiceValidator(Validator):
    """Validator for choice fields"""

    def __init__(self, choices: List[Any], message: str = None):
        super().__init__(message)
        self.choices = choices

    def validate(self, value: Any, field_name: str = None) -> Any:
        if value not in self.choices:
            message = self.message or f"Value must be one of: {self.choices}"
            raise ValidationError(message, field_name)
        return value


class DateValidator(Validator):
    """Validator for date/datetime fields"""

    def __init__(self, date_format: str = "%Y-%m-%d",
                 message: str = "Invalid date format"):
        super().__init__(message)
        self.date_format = date_format

    def validate(self, value: Any, field_name: str = None) -> Any:
        if isinstance(value, (date, datetime)):
            return value

        if not isinstance(value, str):
            value = str(value)

        try:
            return datetime.strptime(value, self.date_format).date()
        except ValueError:
            raise ValidationError(self.message, field_name)


class FileValidator(Validator):
    """Validator for file uploads"""

    def __init__(self, allowed_extensions: List[str] = None,
                 max_size: int = None, message: str = None):
        super().__init__(message)
        self.allowed_extensions = allowed_extensions or []
        self.max_size = max_size

    def validate(self, value: Any, field_name: str = None) -> Any:
        if hasattr(value, 'filename') and hasattr(value, 'read'):
            # File-like object
            filename = getattr(value, 'filename', '')

            # Check file extension
            if self.allowed_extensions:
                ext = filename.split('.')[-1].lower() if '.' in filename else ''
                if ext not in self.allowed_extensions:
                    message = self.message or f"File type not allowed. Allowed: {self.allowed_extensions}"
                    raise ValidationError(message, field_name)

            # Check file size
            if self.max_size:
                content = value.read()
                value.seek(0)  # Reset file pointer
                if len(content) > self.max_size:
                    message = self.message or f"File too large. Max size: {self.max_size} bytes"
                    raise ValidationError(message, field_name)

        return value


class Field:
    """Form field with validation"""

    def __init__(self, validators: List[Validator] = None,
                 required: bool = False, default: Any = None,
                 label: str = None, help_text: str = None):
        self.validators = validators or []
        self.required = required
        self.default = default
        self.label = label
        self.help_text = help_text

        if required:
            self.validators.insert(0, RequiredValidator())

    def validate(self, value: Any, field_name: str = None) -> Any:
        """Validate the field value"""
        if value is None or (isinstance(value, str) and not value.strip()):
            if self.required:
                raise ValidationError("This field is required", field_name)
            return self.default

        for validator in self.validators:
            value = validator.validate(value, field_name)

        return value


class Form:
    """Base form class with validation"""

    def __init__(self, data: Dict[str, Any] = None):
        self.data = data or {}
        self.errors: Dict[str, List[str]] = {}
        self.cleaned_data: Dict[str, Any] = {}
        self.fields: Dict[str, Field] = {}

        # Initialize fields from class attributes
        for attr_name in dir(self):
            attr_value = getattr(self, attr_name)
            if isinstance(attr_value, Field):
                self.fields[attr_name] = attr_value

    def is_valid(self) -> bool:
        """Validate the form and return True if valid"""
        self.errors = {}
        self.cleaned_data = {}

        for field_name, field in self.fields.items():
            try:
                value = self.data.get(field_name)
                cleaned_value = field.validate(value, field_name)
                self.cleaned_data[field_name] = cleaned_value
            except ValidationError as e:
                self.errors[field_name] = [str(e)]
            except Exception as e:
                self.errors[field_name] = [f"Validation error: {str(e)}"]

        return len(self.errors) == 0

    def add_error(self, field: str, message: str):
        """Add an error to a specific field"""
        if field not in self.errors:
            self.errors[field] = []
        self.errors[field].append(message)

    def full_clean(self):
        """Perform full form cleaning and validation"""
        self.is_valid()

    def __getitem__(self, key: str) -> Any:
        """Get cleaned data by key"""
        return self.cleaned_data.get(key)

    def __setitem__(self, key: str, value: Any):
        """Set data by key"""
        self.data[key] = value


class ModelForm(Form):
    """Form that works with models"""

    def __init__(self, instance=None, data: Dict[str, Any] = None):
        super().__init__(data)
        self.instance = instance

        if instance and not data:
            # Populate form with instance data
            self.data = {}
            for field_name in self.fields.keys():
                if hasattr(instance, field_name):
                    self.data[field_name] = getattr(instance, field_name)

    def save(self, commit: bool = True):
        """Save the form data to the model instance"""
        if not self.is_valid():
            raise ValidationError("Form is not valid")

        if self.instance:
            # Update existing instance
            for field_name, value in self.cleaned_data.items():
                setattr(self.instance, field_name, value)
            if commit:
                self.instance.save()
            return self.instance
        else:
            # Create new instance
            model_class = self.Meta.model
            instance = model_class(**self.cleaned_data)
            if commit:
                instance.save()
            return instance

    class Meta:
        model = None


class CSRFToken:
    """CSRF token management"""

    def __init__(self, secret_key: str):
        self.secret_key = secret_key

    def generate_token(self, session_id: str = None) -> str:
        """Generate a CSRF token"""
        if not session_id:
            session_id = secrets.token_hex(16)

        # Create token with timestamp for expiration
        timestamp = str(int(datetime.now().timestamp()))
        message = f"{session_id}:{timestamp}"

        # Create HMAC signature
        signature = hmac.new(
            self.secret_key.encode(),
            message.encode(),
            hashlib.sha3_256
        ).hexdigest()

        return f"{message}:{signature}"

    def validate_token(self, token: str, session_id: str = None) -> bool:
        """Validate a CSRF token"""
        try:
            parts = token.split(':')
            if len(parts) != 3:
                return False

            token_session_id, timestamp, signature = parts

            # Check if token is for correct session
            if session_id and token_session_id != session_id:
                return False

            # Check if token is expired (24 hours)
            token_time = int(timestamp)
            current_time = int(datetime.now().timestamp())
            if current_time - token_time > 86400:  # 24 hours
                return False

            # Verify signature
            message = f"{token_session_id}:{timestamp}"
            expected_signature = hmac.new(
                self.secret_key.encode(),
                message.encode(),
                hashlib.sha3_256
            ).hexdigest()

            return hmac.compare_digest(signature, expected_signature)

        except (ValueError, IndexError):
            return False


class Sanitizer:
    """Data sanitization utilities"""

    @staticmethod
    def sanitize_html(text: str) -> str:
        """Basic HTML sanitization"""
        # Remove script tags and their contents
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
        # Remove javascript: URLs
        text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
        # Remove event handlers
        text = re.sub(r'on\w+="[^"]*"', '', text, flags=re.IGNORECASE)
        return text

    @staticmethod
    def sanitize_sql(text: str) -> str:
        """Basic SQL injection prevention"""
        # This is a very basic implementation
        # In production, use parameterized queries
        dangerous_chars = ["'", '"', ';', '--', '/*', '*/']
        for char in dangerous_chars:
            text = text.replace(char, '')
        return text

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename for security"""
        # Remove path separators and dangerous characters
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        # Remove control characters
        filename = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', filename)
        return filename

    @staticmethod
    def escape_html(text: str) -> str:
        """HTML escape text"""
        return (text.replace('&', '&')
                .replace('<', '<')
                .replace('>', '>')
                .replace('"', '"')
                .replace("'", '&#x27;'))


# Common field types
class CharField(Field):
    def __init__(self, max_length: int = None, min_length: int = None, **kwargs):
        validators = []
        if max_length or min_length:
            validators.append(LengthValidator(min_length, max_length))
        super().__init__(validators=validators, **kwargs)


class EmailField(CharField):
    def __init__(self, **kwargs):
        super().__init__(validators=[EmailValidator()], **kwargs)


class URLField(CharField):
    def __init__(self, **kwargs):
        super().__init__(validators=[URLValidator()], **kwargs)


class IntegerField(Field):
    def __init__(self, min_value: int = None, max_value: int = None, **kwargs):
        validators = []
        if min_value is not None or max_value is not None:
            validators.append(RangeValidator(min_value, max_value))
        super().__init__(validators=validators, **kwargs)

    def validate(self, value: Any, field_name: str = None) -> Any:
        if value is not None:
            try:
                value = int(value)
            except (ValueError, TypeError):
                raise ValidationError("Value must be an integer", field_name)
        return super().validate(value, field_name)


class FloatField(Field):
    def __init__(self, min_value: float = None, max_value: float = None, **kwargs):
        validators = []
        if min_value is not None or max_value is not None:
            validators.append(RangeValidator(min_value, max_value))
        super().__init__(validators=validators, **kwargs)

    def validate(self, value: Any, field_name: str = None) -> Any:
        if value is not None:
            try:
                value = float(value)
            except (ValueError, TypeError):
                raise ValidationError("Value must be a number", field_name)
        return super().validate(value, field_name)


class DateField(Field):
    def __init__(self, date_format: str = "%Y-%m-%d", **kwargs):
        super().__init__(validators=[DateValidator(date_format)], **kwargs)


class ChoiceField(Field):
    def __init__(self, choices: List[Any], **kwargs):
        super().__init__(validators=[ChoiceValidator(choices)], **kwargs)


class FileField(Field):
    def __init__(self, allowed_extensions: List[str] = None,
                 max_size: int = None, **kwargs):
        super().__init__(validators=[FileValidator(allowed_extensions, max_size)], **kwargs)





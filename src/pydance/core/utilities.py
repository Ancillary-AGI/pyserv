"""
Comprehensive utility functions for PyDance framework.

This module provides efficient utilities for:
- Number operations and formatting
- String manipulation and validation
- Date/time handling with UTC and locale support
- High-performance collections (space and time efficient)
- Data sanitization and validation
- CSRF protection utilities
"""

import re
import math
import hashlib
import hmac
import secrets
import threading
from typing import Dict, List, Optional, Any, Union, TypeVar, Generic, Iterator, Callable
from datetime import datetime, date, time, timedelta
from decimal import Decimal, ROUND_HALF_UP
from functools import lru_cache, wraps
from collections import defaultdict, deque
import unicodedata
import locale
import pytz
from email_validator import validate_email, EmailNotValidError
from urllib.parse import quote, unquote
import html
import json
import base64
import zlib
import gzip
from io import BytesIO
import weakref

# Type variables for generic collections
T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')


# ============================================================================
# NUMBER UTILITIES
# ============================================================================

class NumberUtils:
    """High-performance number utilities"""

    @staticmethod
    @lru_cache(maxsize=1024)
    def format_number(value: Union[int, float, Decimal],
                     locale_str: str = 'en_US',
                     precision: int = 2,
                     use_grouping: bool = True) -> str:
        """Format number with locale-specific formatting"""
        try:
            # Save current locale
            current_locale = locale.getlocale()

            # Set desired locale
            locale.setlocale(locale.LC_NUMERIC, locale_str)

            if isinstance(value, Decimal):
                # Round decimal to specified precision
                value = value.quantize(Decimal(f'0.{"0" * precision}'), rounding=ROUND_HALF_UP)

            # Format with grouping
            if use_grouping:
                formatted = locale.format_string(f"%.{precision}f", float(value), grouping=True)
            else:
                formatted = locale.format_string(f"%.{precision}f", float(value), grouping=False)

            # Restore original locale
            if current_locale[0]:
                locale.setlocale(locale.LC_NUMERIC, current_locale)

            return formatted

        except (locale.Error, ValueError):
            # Fallback to basic formatting
            return f"{float(value):.{precision}f}"

    @staticmethod
    def format_currency(amount: Union[int, float, Decimal],
                       currency_code: str = 'USD',
                       locale_str: str = 'en_US') -> str:
        """Format currency amount"""
        try:
            # Use locale for currency formatting
            locale.setlocale(locale.LC_MONETARY, locale_str)
            formatted = locale.currency(float(amount), symbol=True, grouping=True)
            return formatted
        except (locale.Error, ValueError):
            # Fallback formatting
            return f"${float(amount):.2f}"

    @staticmethod
    def format_percentage(value: Union[int, float, Decimal],
                         precision: int = 1) -> str:
        """Format percentage"""
        return f"{float(value) * 100:.{precision}f}%"

    @staticmethod
    def format_file_size(bytes_size: int, binary: bool = True) -> str:
        """Format file size in human readable format"""
        if binary:
            # Binary (1024-based)
            for unit in ['B', 'KiB', 'MiB', 'GiB', 'TiB']:
                if bytes_size < 1024.0:
                    return f"{bytes_size:.1f} {unit}"
                bytes_size /= 1024.0
        else:
            # Decimal (1000-based)
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if bytes_size < 1000.0:
                    return f"{bytes_size:.1f} {unit}"
                bytes_size /= 1000.0

        return f"{bytes_size:.1f} PB"

    @staticmethod
    def clamp(value: Union[int, float], min_val: Union[int, float],
              max_val: Union[int, float]) -> Union[int, float]:
        """Clamp value between min and max"""
        return max(min_val, min(max_val, value))

    @staticmethod
    def is_numeric(value: Any) -> bool:
        """Check if value is numeric"""
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False

    @staticmethod
    def safe_divide(numerator: Union[int, float],
                   denominator: Union[int, float],
                   default: Union[int, float] = 0) -> Union[int, float]:
        """Safe division that handles division by zero"""
        try:
            return numerator / denominator
        except ZeroDivisionError:
            return default


# ============================================================================
# STRING UTILITIES
# ============================================================================

class StringUtils:
    """High-performance string manipulation utilities"""

    @staticmethod
    @lru_cache(maxsize=512)
    def slugify(text: str, separator: str = '-') -> str:
        """Convert text to URL-friendly slug"""
        # Normalize unicode
        text = unicodedata.normalize('NFKD', text)

        # Remove non-word characters and convert to lowercase
        text = re.sub(r'[^\w\s-]', '', text).strip().lower()

        # Replace spaces and multiple separators with single separator
        text = re.sub(rf'[{re.escape(separator)}\s]+', separator, text)

        # Remove leading/trailing separators
        text = text.strip(separator)

        return text

    @staticmethod
    def truncate(text: str, length: int, suffix: str = '...') -> str:
        """Truncate string to specified length with suffix"""
        if len(text) <= length:
            return text

        # Find last space within length to avoid cutting words
        if length > len(suffix):
            truncated = text[:length - len(suffix)]
            last_space = truncated.rfind(' ')
            if last_space > length // 2:  # Only if space is reasonably positioned
                truncated = truncated[:last_space]

        return truncated + suffix

    @staticmethod
    def extract_numbers(text: str) -> List[Union[int, float]]:
        """Extract all numbers from text"""
        # Find all number patterns
        number_pattern = re.compile(r'-?\d+\.?\d*')
        matches = number_pattern.findall(text)

        numbers = []
        for match in matches:
            try:
                # Try int first, then float
                if '.' in match:
                    numbers.append(float(match))
                else:
                    numbers.append(int(match))
            except ValueError:
                continue

        return numbers

    @staticmethod
    def remove_accents(text: str) -> str:
        """Remove accents from text"""
        return unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('ascii')

    @staticmethod
    def camel_to_snake(text: str) -> str:
        """Convert camelCase to snake_case"""
        # Insert underscore before uppercase letters
        text = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', text)
        return text.lower()

    @staticmethod
    def snake_to_camel(text: str) -> str:
        """Convert snake_case to camelCase"""
        components = text.split('_')
        return components[0] + ''.join(word.capitalize() for word in components[1:])

    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Validate email address"""
        try:
            validate_email(email)
            return True
        except EmailNotValidError:
            return False

    @staticmethod
    def mask_sensitive_data(text: str, mask_char: str = '*',
                          visible_start: int = 2, visible_end: int = 2) -> str:
        """Mask sensitive data (e.g., credit cards, SSNs)"""
        if len(text) <= visible_start + visible_end:
            return text

        return (text[:visible_start] +
                mask_char * (len(text) - visible_start - visible_end) +
                text[-visible_end:])

    @staticmethod
    def generate_random_string(length: int = 32,
                             charset: str = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') -> str:
        """Generate cryptographically secure random string"""
        return ''.join(secrets.choice(charset) for _ in range(length))


# ============================================================================
# DATE/TIME UTILITIES
# ============================================================================

class DateTimeUtils:
    """Comprehensive date/time utilities with UTC and locale support"""

    # Common timezone mappings
    TIMEZONE_ALIASES = {
        'EST': 'US/Eastern',
        'CST': 'US/Central',
        'MST': 'US/Mountain',
        'PST': 'US/Pacific',
        'GMT': 'GMT',
        'UTC': 'UTC',
    }

    @staticmethod
    def now(tz: str = 'UTC') -> datetime:
        """Get current datetime in specified timezone"""
        timezone = pytz.timezone(DateTimeUtils._resolve_timezone(tz))
        return datetime.now(timezone)

    @staticmethod
    def utc_now() -> datetime:
        """Get current UTC datetime"""
        return datetime.now(pytz.UTC)

    @staticmethod
    def to_timezone(dt: datetime, tz: str) -> datetime:
        """Convert datetime to specified timezone"""
        if dt.tzinfo is None:
            dt = pytz.UTC.localize(dt)

        target_tz = pytz.timezone(DateTimeUtils._resolve_timezone(tz))
        return dt.astimezone(target_tz)

    @staticmethod
    def to_utc(dt: datetime) -> datetime:
        """Convert datetime to UTC"""
        if dt.tzinfo is None:
            # Assume local timezone if none specified
            dt = pytz.timezone(DateTimeUtils._get_local_timezone()).localize(dt)
        return dt.astimezone(pytz.UTC)

    @staticmethod
    def format_datetime(dt: datetime, format_str: str = '%Y-%m-%d %H:%M:%S',
                       tz: Optional[str] = None, locale_str: str = 'en_US') -> str:
        """Format datetime with timezone and locale support"""
        if tz:
            dt = DateTimeUtils.to_timezone(dt, tz)

        try:
            # Set locale for formatting
            current_locale = locale.getlocale()
            locale.setlocale(locale.LC_TIME, locale_str)

            formatted = dt.strftime(format_str)

            # Restore locale
            if current_locale[0]:
                locale.setlocale(locale.LC_TIME, current_locale)

            return formatted

        except (locale.Error, ValueError):
            # Fallback to basic formatting
            return dt.strftime(format_str)

    @staticmethod
    def parse_datetime(date_str: str, format_str: str = '%Y-%m-%d %H:%M:%S',
                      tz: str = 'UTC') -> datetime:
        """Parse datetime string with timezone support"""
        try:
            dt = datetime.strptime(date_str, format_str)

            # Add timezone info
            timezone = pytz.timezone(DateTimeUtils._resolve_timezone(tz))
            dt = timezone.localize(dt)

            return dt

        except (ValueError, pytz.exceptions.UnknownTimeZoneError):
            # Try parsing as ISO format
            try:
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                if dt.tzinfo is None:
                    dt = pytz.UTC.localize(dt)
                return dt
            except ValueError:
                raise ValueError(f"Unable to parse datetime: {date_str}")

    @staticmethod
    def format_relative_time(dt: datetime, now: Optional[datetime] = None) -> str:
        """Format datetime as relative time (e.g., '2 hours ago')"""
        if now is None:
            now = DateTimeUtils.utc_now()

        # Ensure both datetimes are timezone-aware
        if dt.tzinfo is None:
            dt = pytz.UTC.localize(dt)
        if now.tzinfo is None:
            now = pytz.UTC.localize(now)

        diff = now - dt
        seconds = abs(diff.total_seconds())

        if seconds < 60:
            return "just now"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif seconds < 86400:
            hours = int(seconds // 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif seconds < 604800:
            days = int(seconds // 86400)
            return f"{days} day{'s' if days != 1 else ''} ago"
        else:
            weeks = int(seconds // 604800)
            return f"{weeks} week{'s' if weeks != 1 else ''} ago"

    @staticmethod
    def get_business_days(start_date: date, end_date: date) -> int:
        """Calculate number of business days between two dates"""
        if start_date > end_date:
            start_date, end_date = end_date, start_date

        business_days = 0
        current_date = start_date

        while current_date <= end_date:
            # Monday = 0, Sunday = 6
            if current_date.weekday() < 5:  # Monday to Friday
                business_days += 1
            current_date += timedelta(days=1)

        return business_days

    @staticmethod
    def add_business_days(start_date: date, days: int) -> date:
        """Add business days to a date"""
        current_date = start_date
        remaining_days = abs(days)
        direction = 1 if days >= 0 else -1

        while remaining_days > 0:
            current_date += timedelta(days=direction)
            if current_date.weekday() < 5:  # Monday to Friday
                remaining_days -= 1

        return current_date

    @staticmethod
    def _resolve_timezone(tz: str) -> str:
        """Resolve timezone alias to full timezone name"""
        return DateTimeUtils.TIMEZONE_ALIASES.get(tz.upper(), tz)

    @staticmethod
    def _get_local_timezone() -> str:
        """Get local system timezone"""
        try:
            return str(datetime.now().astimezone().tzinfo)
        except:
            return 'UTC'


# ============================================================================
# HIGH-PERFORMANCE COLLECTIONS
# ============================================================================

class FastList(Generic[T]):
    """High-performance list with optimized operations"""

    def __init__(self, items: Optional[List[T]] = None):
        self._items = list(items) if items else []
        self._size = len(self._items)

    def append(self, item: T) -> None:
        """Fast append operation"""
        self._items.append(item)
        self._size += 1

    def extend(self, items: List[T]) -> None:
        """Fast extend operation"""
        self._items.extend(items)
        self._size = len(self._items)

    def pop(self, index: int = -1) -> T:
        """Fast pop operation"""
        item = self._items.pop(index)
        self._size -= 1
        return item

    def __getitem__(self, index: Union[int, slice]) -> Union[T, List[T]]:
        return self._items[index]

    def __setitem__(self, index: Union[int, slice], value: Union[T, List[T]]) -> None:
        self._items[index] = value

    def __len__(self) -> int:
        return self._size

    def __iter__(self) -> Iterator[T]:
        return iter(self._items)

    def clear(self) -> None:
        """Fast clear operation"""
        self._items.clear()
        self._size = 0


class FastDict(Generic[K, V]):
    """High-performance dictionary with optimized operations"""

    def __init__(self, items: Optional[Dict[K, V]] = None):
        self._dict = dict(items) if items else {}
        self._size = len(self._dict)

    def __getitem__(self, key: K) -> V:
        return self._dict[key]

    def __setitem__(self, key: K, value: V) -> None:
        old_size = self._size
        self._dict[key] = value
        self._size = len(self._dict)

    def __delitem__(self, key: K) -> None:
        del self._dict[key]
        self._size = len(self._dict)

    def __contains__(self, key: K) -> bool:
        return key in self._dict

    def get(self, key: K, default: Optional[V] = None) -> Optional[V]:
        return self._dict.get(key, default)

    def keys(self):
        return self._dict.keys()

    def values(self):
        return self._dict.values()

    def items(self):
        return self._dict.items()

    def __len__(self) -> int:
        return self._size

    def clear(self) -> None:
        """Fast clear operation"""
        self._dict.clear()
        self._size = 0


class CircularBuffer(Generic[T]):
    """Space-efficient circular buffer"""

    def __init__(self, capacity: int):
        self.capacity = capacity
        self.buffer: List[Optional[T]] = [None] * capacity
        self.size = 0
        self.head = 0
        self.tail = 0

    def append(self, item: T) -> None:
        """Add item to buffer"""
        self.buffer[self.tail] = item
        self.tail = (self.tail + 1) % self.capacity

        if self.size < self.capacity:
            self.size += 1
        else:
            # Overwrite oldest item
            self.head = (self.head + 1) % self.capacity

    def popleft(self) -> Optional[T]:
        """Remove and return oldest item"""
        if self.size == 0:
            return None

        item = self.buffer[self.head]
        self.buffer[self.head] = None
        self.head = (self.head + 1) % self.capacity
        self.size -= 1

        return item

    def __getitem__(self, index: int) -> Optional[T]:
        if index < 0 or index >= self.size:
            raise IndexError("Index out of range")

        actual_index = (self.head + index) % self.capacity
        return self.buffer[actual_index]

    def __len__(self) -> int:
        return self.size

    def clear(self) -> None:
        """Clear all items"""
        self.buffer = [None] * self.capacity
        self.size = 0
        self.head = 0
        self.tail = 0


class BloomFilter:
    """Space-efficient probabilistic data structure"""

    def __init__(self, capacity: int, error_rate: float = 0.001):
        self.capacity = capacity
        self.error_rate = error_rate

        # Calculate optimal parameters
        self.size = self._optimal_size(capacity, error_rate)
        self.hash_count = self._optimal_hash_count(self.size, capacity)

        # Initialize bit array
        self.bit_array = [False] * self.size

    def add(self, item: str) -> None:
        """Add item to bloom filter"""
        for seed in range(self.hash_count):
            index = self._hash(item, seed) % self.size
            self.bit_array[index] = True

    def contains(self, item: str) -> bool:
        """Check if item might be in the filter"""
        for seed in range(self.hash_count):
            index = self._hash(item, seed) % self.size
            if not self.bit_array[index]:
                return False
        return True

    def _hash(self, item: str, seed: int) -> int:
        """Simple hash function"""
        hash_value = hash(item + str(seed))
        return abs(hash_value)

    def _optimal_size(self, capacity: int, error_rate: float) -> int:
        """Calculate optimal bit array size"""
        return int(-capacity * math.log(error_rate) / (math.log(2) ** 2))

    def _optimal_hash_count(self, size: int, capacity: int) -> int:
        """Calculate optimal number of hash functions"""
        return int((size / capacity) * math.log(2))


# ============================================================================
# DATA SANITIZATION UTILITIES
# ============================================================================

class Sanitizer:
    """Comprehensive data sanitization utilities"""

    # SQL injection patterns
    SQL_PATTERNS = [
        r';\s*DROP\s+TABLE',
        r';\s*DELETE\s+FROM',
        r';\s*UPDATE\s+.*SET',
        r';\s*INSERT\s+INTO',
        r'UNION\s+SELECT',
        r'--\s*$',  # SQL comments
        r'/\*.*\*/',  # Block comments
    ]

    # XSS patterns
    XSS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'vbscript:',
        r'on\w+\s*=',
        r'<iframe[^>]*>.*?</iframe>',
        r'<object[^>]*>.*?</object>',
        r'<embed[^>]*>.*?</embed>',
    ]

    @staticmethod
    def sanitize_sql_input(value: str) -> str:
        """Sanitize input to prevent SQL injection"""
        if not isinstance(value, str):
            return str(value)

        # Remove dangerous SQL keywords and patterns
        for pattern in Sanitizer.SQL_PATTERNS:
            value = re.sub(pattern, '', value, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL)

        # Escape single quotes
        value = value.replace("'", "''")

        # Remove null bytes
        value = value.replace('\x00', '')

        return value

    @staticmethod
    def sanitize_html(value: str) -> str:
        """Sanitize HTML to prevent XSS attacks"""
        if not isinstance(value, str):
            return html.escape(str(value))

        # Remove dangerous tags and attributes
        for pattern in Sanitizer.XSS_PATTERNS:
            value = re.sub(pattern, '', value, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL)

        # HTML escape remaining content
        return html.escape(value)

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename for security"""
        if not isinstance(filename, str):
            filename = str(filename)

        # Remove path traversal attempts
        filename = filename.replace('../', '').replace('..\\', '')

        # Remove dangerous characters
        dangerous_chars = ['<', '>', ':', '"', '|', '?', '*']
        for char in dangerous_chars:
            filename = filename.replace(char, '')

        # Remove control characters
        filename = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', filename)

        # Ensure filename is not empty and doesn't start with dot
        filename = filename.strip()
        if not filename or filename.startswith('.'):
            filename = 'file_' + str(hash(filename) % 10000)

        return filename

    @staticmethod
    def sanitize_url(url: str) -> str:
        """Sanitize URL to prevent SSRF and other attacks"""
        if not isinstance(url, str):
            return ''

        # Parse URL and validate
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)

            # Only allow http and https
            if parsed.scheme not in ['http', 'https']:
                return ''

            # Validate host
            if not parsed.hostname:
                return ''

            # Prevent localhost/private IP access (SSRF protection)
            private_ips = [
                '127.0.0.1', 'localhost', '0.0.0.0',
                '10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16'
            ]

            for private_ip in private_ips:
                if private_ip in parsed.hostname:
                    return ''

            return url

        except Exception:
            return ''

    @staticmethod
    def sanitize_json_input(data: Any) -> Any:
        """Sanitize JSON data recursively"""
        if isinstance(data, dict):
            return {key: Sanitizer.sanitize_json_input(value)
                   for key, value in data.items()}
        elif isinstance(data, list):
            return [Sanitizer.sanitize_json_input(item) for item in data]
        elif isinstance(data, str):
            return Sanitizer.sanitize_html(data)
        else:
            return data


# ============================================================================
# CSRF PROTECTION UTILITIES
# ============================================================================

class CSRFUtils:
    """CSRF protection utilities with selective disabling"""

    _disabled_forms: Set[str] = set()
    _disabled_endpoints: Set[str] = set()

    @staticmethod
    def generate_token(session_id: str = None) -> str:
        """Generate CSRF token"""
        if not session_id:
            session_id = secrets.token_hex(16)

        timestamp = str(int(datetime.now().timestamp()))
        message = f"{session_id}:{timestamp}"

        signature = hmac.new(
            secrets.token_bytes(32),
            message.encode(),
            hashlib.sha3_256
        ).hexdigest()

        return f"{message}:{signature}"

    @staticmethod
    def validate_token(token: str, session_id: str = None) -> bool:
        """Validate CSRF token"""
        try:
            parts = token.split(':')
            if len(parts) != 3:
                return False

            token_session_id, timestamp, signature = parts

            if session_id and token_session_id != session_id:
                return False

            # Check expiration (24 hours)
            token_time = int(timestamp)
            current_time = int(datetime.now().timestamp())
            if current_time - token_time > 86400:
                return False

            message = f"{token_session_id}:{timestamp}"
            expected_signature = hmac.new(
                secrets.token_bytes(32),
                message.encode(),
                hashlib.sha3_256
            ).hexdigest()

            return hmac.compare_digest(signature, expected_signature)

        except (ValueError, IndexError):
            return False

    @classmethod
    def disable_for_form(cls, form_class: type) -> None:
        """Disable CSRF protection for specific form class"""
        cls._disabled_forms.add(form_class.__name__)

    @classmethod
    def disable_for_endpoint(cls, endpoint: str) -> None:
        """Disable CSRF protection for specific endpoint"""
        cls._disabled_endpoints.add(endpoint)

    @classmethod
    def is_disabled_for_form(cls, form_class: type) -> bool:
        """Check if CSRF is disabled for form"""
        return form_class.__name__ in cls._disabled_forms

    @classmethod
    def is_disabled_for_endpoint(cls, endpoint: str) -> bool:
        """Check if CSRF is disabled for endpoint"""
        return endpoint in cls._disabled_endpoints

    @classmethod
    def enable_for_form(cls, form_class: type) -> None:
        """Re-enable CSRF protection for form"""
        cls._disabled_forms.discard(form_class.__name__)

    @classmethod
    def enable_for_endpoint(cls, endpoint: str) -> None:
        """Re-enable CSRF protection for endpoint"""
        cls._disabled_endpoints.discard(endpoint)


# ============================================================================
# DECORATORS FOR EASY CSRF CONTROL
# ============================================================================

def csrf_exempt(form_class: type):
    """Decorator to disable CSRF for specific form"""
    CSRFUtils.disable_for_form(form_class)
    return form_class


def csrf_exempt_endpoint(endpoint: str):
    """Decorator to disable CSRF for specific endpoint"""
    def decorator(func):
        CSRFUtils.disable_for_endpoint(endpoint)
        return func
    return decorator


def enable_csrf_for_form(form_class: type):
    """Decorator to enable CSRF for specific form"""
    CSRFUtils.enable_for_form(form_class)
    return form_class


def enable_csrf_for_endpoint(endpoint: str):
    """Decorator to enable CSRF for specific endpoint"""
    def decorator(func):
        CSRFUtils.enable_for_endpoint(endpoint)
        return func
    return decorator


# ============================================================================
# COMPRESSION UTILITIES
# ============================================================================

class CompressionUtils:
    """High-performance compression utilities"""

    @staticmethod
    def compress_gzip(data: bytes, level: int = 6) -> bytes:
        """Compress data using gzip"""
        buffer = BytesIO()
        with gzip.GzipFile(fileobj=buffer, mode='wb', compresslevel=level) as f:
            f.write(data)
        return buffer.getvalue()

    @staticmethod
    def decompress_gzip(data: bytes) -> bytes:
        """Decompress gzip data"""
        buffer = BytesIO(data)
        with gzip.GzipFile(fileobj=buffer, mode='rb') as f:
            return f.read()

    @staticmethod
    def compress_zlib(data: bytes, level: int = 6) -> bytes:
        """Compress data using zlib"""
        return zlib.compress(data, level=level)

    @staticmethod
    def decompress_zlib(data: bytes) -> bytes:
        """Decompress zlib data"""
        return zlib.decompress(data)


# ============================================================================
# ENCODING UTILITIES
# ============================================================================

class EncodingUtils:
    """Safe encoding/decoding utilities"""

    @staticmethod
    def safe_base64_encode(data: bytes) -> str:
        """Safe base64 encoding"""
        return base64.urlsafe_b64encode(data).decode('ascii')

    @staticmethod
    def safe_base64_decode(data: str) -> bytes:
        """Safe base64 decoding"""
        try:
            return base64.urlsafe_b64decode(data.encode('ascii'))
        except Exception:
            return b''

    @staticmethod
    def safe_json_encode(data: Any) -> str:
        """Safe JSON encoding with error handling"""
        try:
            return json.dumps(data, default=str, separators=(',', ':'))
        except Exception:
            return '{}'

    @staticmethod
    def safe_json_decode(data: str) -> Any:
        """Safe JSON decoding with error handling"""
        try:
            return json.loads(data)
        except Exception:
            return {}


# ============================================================================
# EXPORT ALL UTILITIES
# ============================================================================

__all__ = [
    # Number utilities
    'NumberUtils',

    # String utilities
    'StringUtils',

    # Date/Time utilities
    'DateTimeUtils',

    # High-performance collections
    'FastList',
    'FastDict',
    'CircularBuffer',
    'BloomFilter',

    # Data sanitization
    'Sanitizer',

    # CSRF utilities
    'CSRFUtils',
    'csrf_exempt',
    'csrf_exempt_endpoint',
    'enable_csrf_for_form',
    'enable_csrf_for_endpoint',

    # Compression utilities
    'CompressionUtils',

    # Encoding utilities
    'EncodingUtils',
]

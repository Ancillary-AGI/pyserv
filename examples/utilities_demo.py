"""
PyDance Utilities Comprehensive Demo

This example demonstrates all the utility functions available in PyDance:
- Number formatting and operations
- String manipulation and validation
- Date/time handling with UTC and locale support
- High-performance collections (space and time efficient)
- Data sanitization for security
- Selective CSRF protection control
- Compression and encoding utilities

Run with: python examples/utilities_demo.py
"""

import asyncio
from datetime import datetime, date
from decimal import Decimal
from pydance import (
    # Number utilities
    NumberUtils,

    # String utilities
    StringUtils,

    # Date/Time utilities
    DateTimeUtils,

    # High-performance collections
    FastList, FastDict, CircularBuffer, BloomFilter,

    # Data sanitization
    Sanitizer,

    # CSRF utilities
    CSRFUtils, csrf_exempt, csrf_exempt_endpoint,

    # Compression utilities
    CompressionUtils,

    # Encoding utilities
    EncodingUtils,

    # Form validation
    Form, CharField, EmailField, IntegerField, CSRFToken
)


class ContactForm(Form):
    """Example form with CSRF protection"""
    name = CharField(max_length=100, required=True)
    email = EmailField(required=True)
    age = IntegerField(min_value=18, max_value=120)
    message = CharField(max_length=1000)


@csrf_exempt
class PublicContactForm(Form):
    """Form with CSRF protection disabled"""
    subject = CharField(max_length=200, required=True)
    message = CharField(max_length=2000, required=True)


async def demonstrate_number_utilities():
    """Demonstrate number formatting and operations"""
    print("🔢 NUMBER UTILITIES DEMO")
    print("=" * 50)

    # Number formatting
    amount = Decimal('1234567.89')
    print(f"US Format: {NumberUtils.format_number(amount, 'en_US', precision=2)}")
    print(f"German Format: {NumberUtils.format_number(amount, 'de_DE', precision=2)}")
    print(f"Japanese Format: {NumberUtils.format_number(amount, 'ja_JP', precision=0)}")

    # Currency formatting
    print(f"USD: {NumberUtils.format_currency(1234.56, 'USD', 'en_US')}")
    print(f"EUR: {NumberUtils.format_currency(1234.56, 'EUR', 'de_DE')}")
    print(f"JPY: {NumberUtils.format_currency(1234.56, 'JPY', 'ja_JP')}")

    # File size formatting
    print(f"File size: {NumberUtils.format_file_size(2147483648)}")  # 2GB
    print(f"Small file: {NumberUtils.format_file_size(1536, binary=False)}")  # 1.5KB

    # Safe operations
    print(f"Safe divide: {NumberUtils.safe_divide(10, 0, default=999)}")
    print(f"Clamp: {NumberUtils.clamp(15, 10, 20)}")
    print()


def demonstrate_string_utilities():
    """Demonstrate string manipulation and validation"""
    print("🔤 STRING UTILITIES DEMO")
    print("=" * 50)

    # Slug generation
    title = "Hello World! This is a Test Title"
    print(f"Slug: {StringUtils.slugify(title)}")

    # Text truncation
    long_text = "This is a very long text that needs to be truncated for display purposes."
    print(f"Truncated: {StringUtils.truncate(long_text, 30)}")

    # Number extraction
    text_with_numbers = "The price is $123.45 and the quantity is 42 items."
    numbers = StringUtils.extract_numbers(text_with_numbers)
    print(f"Extracted numbers: {numbers}")

    # Case conversion
    camel_case = "userNameField"
    snake_case = "user_name_field"
    print(f"Camel to snake: {StringUtils.camel_to_snake(camel_case)}")
    print(f"Snake to camel: {StringUtils.snake_to_camel(snake_case)}")

    # Email validation
    emails = ["user@example.com", "invalid-email", "test@domain.co.uk"]
    for email in emails:
        print(f"'{email}' is valid: {StringUtils.is_valid_email(email)}")

    # Sensitive data masking
    credit_card = "4111111111111111"
    ssn = "123-45-6789"
    print(f"Masked CC: {StringUtils.mask_sensitive_data(credit_card)}")
    print(f"Masked SSN: {StringUtils.mask_sensitive_data(ssn)}")

    # Random string generation
    print(f"Random string: {StringUtils.generate_random_string(16)}")
    print()


def demonstrate_datetime_utilities():
    """Demonstrate date/time handling with UTC and locale support"""
    print("📅 DATE/TIME UTILITIES DEMO")
    print("=" * 50)

    # Current time in different timezones
    print(f"UTC now: {DateTimeUtils.utc_now()}")
    print(f"EST now: {DateTimeUtils.now('US/Eastern')}")
    print(f"PST now: {DateTimeUtils.now('US/Pacific')}")

    # Timezone conversion
    dt_utc = DateTimeUtils.utc_now()
    dt_est = DateTimeUtils.to_timezone(dt_utc, 'US/Eastern')
    print(f"UTC to EST: {dt_est}")

    # Formatting with locale
    dt = DateTimeUtils.utc_now()
    print(f"US format: {DateTimeUtils.format_datetime(dt, locale_str='en_US')}")
    print(f"German format: {DateTimeUtils.format_datetime(dt, locale_str='de_DE')}")
    print(f"Japanese format: {DateTimeUtils.format_datetime(dt, locale_str='ja_JP')}")

    # Parsing
    date_str = "2023-12-25 15:30:00"
    parsed = DateTimeUtils.parse_datetime(date_str, tz='UTC')
    print(f"Parsed: {parsed}")

    # Relative time
    past_time = DateTimeUtils.utc_now().replace(hour=10)
    print(f"Relative: {DateTimeUtils.format_relative_time(past_time)}")

    # Business days
    start = date.today()
    end = start.replace(day=start.day + 10)
    business_days = DateTimeUtils.get_business_days(start, end)
    print(f"Business days in next 10 days: {business_days}")

    # Add business days
    future_date = DateTimeUtils.add_business_days(start, 5)
    print(f"5 business days from today: {future_date}")
    print()


def demonstrate_collections():
    """Demonstrate high-performance collections"""
    print("📦 HIGH-PERFORMANCE COLLECTIONS DEMO")
    print("=" * 50)

    # FastList
    fast_list = FastList([1, 2, 3, 4, 5])
    fast_list.append(6)
    fast_list.extend([7, 8, 9])
    print(f"FastList: {list(fast_list)}")

    # FastDict
    fast_dict = FastDict({'a': 1, 'b': 2, 'c': 3})
    fast_dict['d'] = 4
    print(f"FastDict: {dict(fast_dict.items())}")

    # CircularBuffer
    buffer = CircularBuffer(5)
    for i in range(8):
        buffer.append(f"item_{i}")
    print(f"CircularBuffer: {[buffer[i] for i in range(len(buffer))]}")

    # BloomFilter
    bloom = BloomFilter(1000, 0.001)
    test_items = ["apple", "banana", "cherry", "date", "elderberry"]

    for item in test_items:
        bloom.add(item)

    # Test lookups
    for item in test_items + ["grape", "fig"]:
        print(f"Bloom filter '{item}' might exist: {bloom.contains(item)}")

    print()


def demonstrate_data_sanitization():
    """Demonstrate data sanitization for security"""
    print("🛡️ DATA SANITIZATION DEMO")
    print("=" * 50)

    # SQL injection prevention
    malicious_sql = "'; DROP TABLE users; --"
    safe_sql = Sanitizer.sanitize_sql_input(malicious_sql)
    print(f"Original: {malicious_sql}")
    print(f"Sanitized: {safe_sql}")

    # XSS prevention
    malicious_html = '<script>alert("XSS")</script><p>Hello</p>'
    safe_html = Sanitizer.sanitize_html(malicious_html)
    print(f"Original HTML: {malicious_html}")
    print(f"Sanitized HTML: {safe_html}")

    # Filename sanitization
    dangerous_filename = "../../../etc/passwd"
    safe_filename = Sanitizer.sanitize_filename(dangerous_filename)
    print(f"Original filename: {dangerous_filename}")
    print(f"Sanitized filename: {safe_filename}")

    # URL sanitization
    malicious_url = "javascript:alert('XSS')"
    safe_url = Sanitizer.sanitize_url(malicious_url)
    print(f"Original URL: {malicious_url}")
    print(f"Sanitized URL: {safe_url}")

    # JSON sanitization
    malicious_json = {
        "name": "<script>alert('XSS')</script>",
        "query": "'; DROP TABLE users; --",
        "nested": {
            "data": "<iframe src='evil.com'></iframe>"
        }
    }
    safe_json = Sanitizer.sanitize_json_input(malicious_json)
    print(f"Original JSON: {malicious_json}")
    print(f"Sanitized JSON: {safe_json}")

    print()


def demonstrate_csrf_control():
    """Demonstrate selective CSRF protection control"""
    print("🔐 CSRF PROTECTION CONTROL DEMO")
    print("=" * 50)

    # Generate CSRF token
    session_id = "user_session_123"
    token = CSRFUtils.generate_token(session_id)
    print(f"Generated CSRF token: {token}")

    # Validate token
    is_valid = CSRFUtils.validate_token(token, session_id)
    print(f"Token validation: {is_valid}")

    # Demonstrate selective disabling
    print(f"CSRF disabled for ContactForm: {CSRFUtils.is_disabled_for_form(ContactForm)}")
    print(f"CSRF disabled for PublicContactForm: {CSRFUtils.is_disabled_for_form(PublicContactForm)}")

    # Test form validation with CSRF
    form_data = {
        'name': 'John Doe',
        'email': 'john@example.com',
        'age': '25',
        'message': 'Hello world!'
    }

    # Regular form (CSRF enabled)
    regular_form = ContactForm(form_data)
    print(f"Regular form valid: {regular_form.is_valid()}")
    if not regular_form.is_valid():
        print(f"Regular form errors: {regular_form.errors}")

    # Public form (CSRF disabled)
    public_form = PublicContactForm({
        'subject': 'Public inquiry',
        'message': 'This is a public message'
    })
    print(f"Public form valid: {public_form.is_valid()}")
    if not public_form.is_valid():
        print(f"Public form errors: {public_form.errors}")

    print()


def demonstrate_compression_encoding():
    """Demonstrate compression and encoding utilities"""
    print("🗜️ COMPRESSION & ENCODING DEMO")
    print("=" * 50)

    # Test data
    test_data = b"This is a test string for compression and encoding utilities in PyDance framework."
    json_data = {"message": "Hello World", "timestamp": datetime.now().isoformat(), "data": list(range(100))}

    # Gzip compression
    compressed = CompressionUtils.compress_gzip(test_data)
    decompressed = CompressionUtils.decompress_gzip(compressed)
    print(f"Original size: {len(test_data)} bytes")
    print(f"Compressed size: {len(compressed)} bytes")
    print(f"Compression ratio: {len(compressed)/len(test_data):.2%}")
    print(f"Decompression successful: {test_data == decompressed}")

    # Safe JSON encoding/decoding
    json_str = EncodingUtils.safe_json_encode(json_data)
    decoded_data = EncodingUtils.safe_json_decode(json_str)
    print(f"JSON encoding/decoding successful: {json_data['message'] == decoded_data['message']}")

    # Base64 encoding/decoding
    encoded = EncodingUtils.safe_base64_encode(test_data)
    decoded = EncodingUtils.safe_base64_decode(encoded)
    print(f"Base64 encoding/decoding successful: {test_data == decoded}")

    print()


async def main():
    """Main demonstration function"""
    print("🚀 PyDance Utilities Comprehensive Demo")
    print("=" * 60)
    print()

    # Demonstrate all utilities
    demonstrate_number_utilities()
    demonstrate_string_utilities()
    demonstrate_datetime_utilities()
    demonstrate_collections()
    demonstrate_data_sanitization()
    demonstrate_csrf_control()
    demonstrate_compression_encoding()

    print("✅ All demonstrations completed successfully!")
    print()
    print("📚 SUMMARY:")
    print("- NumberUtils: Formatting, currency, file sizes, safe operations")
    print("- StringUtils: Slugs, truncation, validation, case conversion")
    print("- DateTimeUtils: Timezone handling, formatting, business days")
    print("- Collections: FastList, FastDict, CircularBuffer, BloomFilter")
    print("- Sanitizer: SQL injection, XSS, filename, URL protection")
    print("- CSRFUtils: Selective protection control with decorators")
    print("- CompressionUtils: Gzip, zlib compression/decompression")
    print("- EncodingUtils: Safe JSON, Base64 encoding/decoding")


if __name__ == "__main__":
    asyncio.run(main())

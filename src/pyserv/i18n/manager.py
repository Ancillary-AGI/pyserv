"""
Internationalization (i18n) support for Pyserv  framework
"""
import os
import json
from typing import Dict, Any, Optional
from pathlib import Path

# Import the new i18n system
from .translations import Translations, gettext as _gettext, ngettext as _ngettext
from .utils import get_locale as _get_locale, set_locale as _set_locale, get_timezone as _get_timezone, set_timezone as _set_timezone


class I18n:
    """Internationalization manager - backward compatibility layer"""

    _instance = None
    _translations: Dict[str, Dict[str, str]] = {}
    _current_locale = 'en'

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._load_translations()

    def _load_translations(self):
        """Load translation files"""
        # Default English translations
        self._translations['en'] = {
            # HTTP Exceptions
            'bad_request': 'Bad Request',
            'unauthorized': 'Unauthorized',
            'forbidden': 'Forbidden',
            'not_found': 'Not Found',
            'internal_server_error': 'Internal Server Error',

            # User exceptions
            'user_not_found': 'User not found',
            'user_already_exists': 'User already exists',
            'invalid_credentials': 'Invalid credentials',
            'password_too_weak': 'Password does not meet strength requirements',
            'email_already_exists': 'Email address already registered',
            'username_already_exists': 'Username already taken',
            'invalid_email_format': 'Invalid email format',
            'invalid_username_format': 'Invalid username format',
            'account_locked': 'Account is locked',
            'account_not_verified': 'Account not verified',
            'account_suspended': 'Account is suspended',
            'account_inactive': 'Account is inactive',

            # Validation
            'validation_error': 'Validation error',
            'invalid_json': 'Invalid JSON',

            # Database
            'database_error': 'Database operation error',
            'record_not_found': 'Record not found',

            # Authentication
            'token_expired': 'Token has expired',
            'token_invalid': 'Invalid token',
            'permission_denied': 'Permission denied',

            # File operations
            'file_too_large': 'File too large. Maximum size: {max_size} bytes, actual size: {actual_size} bytes',
            'invalid_file_type': 'Invalid file type \'{actual_type}\'. Allowed types: {allowed_types}',

            # Rate limiting
            'rate_limit_exceeded': 'Rate limit exceeded',

            # Configuration
            'missing_configuration': 'Required configuration \'{key}\' is missing',
            'unsupported_hash_algorithm': 'Unsupported hash algorithm: {algorithm}',
            'current_password_incorrect': 'Current password is incorrect',
        }

        # Load additional translation files if they exist
        translations_dir = Path(__file__).parent.parent / 'translations'
        if translations_dir.exists():
            for file_path in translations_dir.glob('*.json'):
                locale = file_path.stem
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        self._translations[locale] = json.load(f)
                except Exception as e:
                    print(f"Error loading translation file {file_path}: {e}")

    def set_locale(self, locale: str):
        """Set current locale"""
        if locale in self._translations:
            self._current_locale = locale
        else:
            # Fallback to English if locale not found
            self._current_locale = 'en'
        # Also set in the new system
        _set_locale(locale)

    def get_locale(self) -> str:
        """Get current locale"""
        return _get_locale()

    def translate(self, key: str, **kwargs) -> str:
        """Translate a message key"""
        # Try the new system first
        try:
            return _gettext(key, **kwargs)
        except:
            # Fall back to old system
            translations = self._translations.get(self._current_locale, self._translations.get('en', {}))
            message = translations.get(key, key)  # Fallback to key if translation not found

            # Format message with kwargs
            if kwargs:
                try:
                    message = message.format(**kwargs)
                except (KeyError, ValueError):
                    pass  # Keep original message if formatting fails

            return message

    def add_translation(self, locale: str, key: str, message: str):
        """Add a translation for a specific locale"""
        if locale not in self._translations:
            self._translations[locale] = {}

        self._translations[locale][key] = message

    def get_available_locales(self) -> list:
        """Get list of available locales"""
        return list(self._translations.keys())


# Global instance
i18n = I18n()


def _(key: str, **kwargs) -> str:
    """Translation shortcut function"""
    return i18n.translate(key, **kwargs)


def set_locale(locale: str):
    """Set current locale"""
    i18n.set_locale(locale)


def get_locale() -> str:
    """Get current locale"""
    return i18n.get_locale()


def set_timezone(timezone: str):
    """Set current timezone"""
    _set_timezone(timezone)


def get_timezone() -> str:
    """Get current timezone"""
    return _get_timezone()


# Context manager for temporary locale changes
class LocaleContext:
    """Context manager for temporary locale changes"""

    def __init__(self, locale: str):
        self.locale = locale
        self.original_locale = None

    def __enter__(self):
        self.original_locale = get_locale()
        set_locale(self.locale)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.original_locale:
            set_locale(self.original_locale)

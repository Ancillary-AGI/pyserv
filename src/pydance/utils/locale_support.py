"""
Locale support utilities for PyDance
Comprehensive internationalization and localization features
"""

import locale as locale_module
import gettext
import os
import json
from typing import Dict, List, Optional, Any, Union, Callable
from pathlib import Path
from datetime import datetime, date, time
from decimal import Decimal
import babel
from babel import Locale, dates, numbers, support
import pytz
from functools import lru_cache


class LocaleManager:
    """Advanced locale management system"""

    def __init__(self, default_locale: str = 'en_US', domain: str = 'pydance'):
        self.default_locale = default_locale
        self.current_locale = default_locale
        self.domain = domain
        self._locales: Dict[str, Locale] = {}
        self._translations: Dict[str, gettext.GNUTranslations] = {}
        self._formatters: Dict[str, Any] = {}
        self._timezone = pytz.UTC

        # Initialize default locale
        self._load_locale(default_locale)

    def _load_locale(self, locale_code: str) -> None:
        """Load a locale and its translations"""
        try:
            # Create Babel locale object
            babel_locale = Locale.parse(locale_code)
            self._locales[locale_code] = babel_locale

            # Load translations
            self._load_translations(locale_code)

            # Create formatters
            self._create_formatters(locale_code)

        except (babel.UnknownLocaleError, ValueError) as e:
            print(f"Warning: Could not load locale {locale_code}: {e}")

    def _load_translations(self, locale_code: str) -> None:
        """Load translation files for a locale"""
        try:
            # Try to find translation files
            locale_dir = Path(__file__).parent.parent / 'locale'
            mo_file = locale_dir / locale_code / 'LC_MESSAGES' / f'{self.domain}.mo'

            if mo_file.exists():
                with open(mo_file, 'rb') as f:
                    translation = gettext.GNUTranslations(f)
                    translation.install()
                    self._translations[locale_code] = translation
            else:
                # Create empty translation object
                self._translations[locale_code] = gettext.NullTranslations()

        except Exception as e:
            print(f"Warning: Could not load translations for {locale_code}: {e}")
            self._translations[locale_code] = gettext.NullTranslations()

    def _create_formatters(self, locale_code: str) -> None:
        """Create formatters for a locale"""
        babel_locale = self._locales.get(locale_code)
        if babel_locale:
            self._formatters[locale_code] = {
                'date': lambda dt, fmt=None: dates.format_date(dt, fmt, babel_locale),
                'time': lambda t, fmt=None: dates.format_time(t, fmt, babel_locale),
                'datetime': lambda dt, fmt=None: dates.format_datetime(dt, fmt, babel_locale),
                'number': lambda n: numbers.format_number(n, babel_locale),
                'currency': lambda n, c='USD': numbers.format_currency(n, c, babel_locale),
                'percent': lambda n: numbers.format_percent(n, babel_locale),
                'decimal': lambda n: numbers.format_decimal(n, babel_locale),
            }

    def set_locale(self, locale_code: str) -> bool:
        """Set the current locale"""
        if locale_code not in self._locales:
            self._load_locale(locale_code)

        if locale_code in self._locales:
            self.current_locale = locale_code
            # Install translations
            translation = self._translations.get(locale_code)
            if translation:
                translation.install()
            return True
        return False

    def get_locale(self) -> str:
        """Get the current locale"""
        return self.current_locale

    def get_available_locales(self) -> List[str]:
        """Get list of available locales"""
        return list(self._locales.keys())

    def set_timezone(self, timezone: str) -> bool:
        """Set the current timezone"""
        try:
            self._timezone = pytz.timezone(timezone)
            return True
        except pytz.exceptions.UnknownTimeZoneError:
            return False

    def get_timezone(self) -> str:
        """Get the current timezone"""
        return str(self._timezone)

    def format_date(self, date_obj: Union[date, datetime], format_str: Optional[str] = None) -> str:
        """Format a date according to current locale"""
        formatter = self._formatters.get(self.current_locale, {}).get('date')
        if formatter:
            return formatter(date_obj, format_str)
        return str(date_obj)

    def format_time(self, time_obj: Union[time, datetime], format_str: Optional[str] = None) -> str:
        """Format a time according to current locale"""
        formatter = self._formatters.get(self.current_locale, {}).get('time')
        if formatter:
            return formatter(time_obj, format_str)
        return str(time_obj)

    def format_datetime(self, datetime_obj: datetime, format_str: Optional[str] = None) -> str:
        """Format a datetime according to current locale"""
        formatter = self._formatters.get(self.current_locale, {}).get('datetime')
        if formatter:
            return formatter(datetime_obj, format_str)
        return str(datetime_obj)

    def format_number(self, number: Union[int, float, Decimal]) -> str:
        """Format a number according to current locale"""
        formatter = self._formatters.get(self.current_locale, {}).get('number')
        if formatter:
            return formatter(number)
        return str(number)

    def format_currency(self, amount: Union[int, float, Decimal], currency: str = 'USD') -> str:
        """Format currency according to current locale"""
        formatter = self._formatters.get(self.current_locale, {}).get('currency')
        if formatter:
            return formatter(amount, currency)
        return f"{currency} {amount}"

    def format_percent(self, percentage: Union[int, float, Decimal]) -> str:
        """Format percentage according to current locale"""
        formatter = self._formatters.get(self.current_locale, {}).get('percent')
        if formatter:
            return formatter(percentage)
        return f"{percentage}%"

    def translate(self, message: str, **kwargs) -> str:
        """Translate a message"""
        translation = self._translations.get(self.current_locale)
        if translation:
            translated = translation.gettext(message)
            if kwargs:
                return translated.format(**kwargs)
            return translated
        return message.format(**kwargs) if kwargs else message

    def pluralize(self, singular: str, plural: str, count: int) -> str:
        """Get the correct plural form based on count"""
        translation = self._translations.get(self.current_locale)
        if translation and hasattr(translation, 'ngettext'):
            return translation.ngettext(singular, plural, count)
        return singular if count == 1 else plural

    def get_locale_info(self, locale_code: Optional[str] = None) -> Dict[str, Any]:
        """Get detailed information about a locale"""
        code = locale_code or self.current_locale
        babel_locale = self._locales.get(code)

        if not babel_locale:
            return {}

        return {
            'code': code,
            'language': babel_locale.language,
            'territory': babel_locale.territory,
            'script': babel_locale.script,
            'display_name': babel_locale.display_name,
            'english_name': babel_locale.english_name,
            'currency': babel_locale.currency,
            'number_symbols': babel_locale.number_symbols,
            'date_formats': {
                'short': babel_locale.date_formats['short'].pattern,
                'medium': babel_locale.date_formats['medium'].pattern,
                'long': babel_locale.date_formats['long'].pattern,
                'full': babel_locale.date_formats['full'].pattern,
            },
            'time_formats': {
                'short': babel_locale.time_formats['short'].pattern,
                'medium': babel_locale.time_formats['medium'].pattern,
                'long': babel_locale.time_formats['long'].pattern,
                'full': babel_locale.time_formats['full'].pattern,
            },
        }


class TranslationManager:
    """Translation file management"""

    def __init__(self, locale_dir: str = None):
        self.locale_dir = Path(locale_dir) if locale_dir else Path(__file__).parent.parent / 'locale'
        self.locale_dir.mkdir(parents=True, exist_ok=True)

    def extract_messages(self, source_dir: str, output_file: str = 'messages.pot') -> None:
        """Extract translatable messages from source files"""
        import polib

        pot_file = self.locale_dir / output_file
        pot = polib.POFile()

        # Scan Python files for translatable strings
        for py_file in Path(source_dir).rglob('*.py'):
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract strings using simple regex (in production, use proper extraction tools)
            import re
            gettext_pattern = r'_\(["\']([^"\']+)["\']'
            matches = re.findall(gettext_pattern, content)

            for msg in matches:
                entry = polib.POEntry(msgid=msg)
                pot.append(entry)

        pot.save(str(pot_file))
        print(f"Extracted {len(pot)} messages to {pot_file}")

    def compile_translations(self, locale_code: str, domain: str = 'pydance') -> None:
        """Compile .po files to .mo files"""
        import subprocess

        po_file = self.locale_dir / locale_code / 'LC_MESSAGES' / f'{domain}.po'
        mo_file = self.locale_dir / locale_code / 'LC_MESSAGES' / f'{domain}.mo'

        if po_file.exists():
            # Use msgfmt to compile
            try:
                subprocess.run(['msgfmt', str(po_file), '-o', str(mo_file)], check=True)
                print(f"Compiled {po_file} to {mo_file}")
            except subprocess.CalledProcessError:
                print(f"Failed to compile {po_file}")
        else:
            print(f"Translation file not found: {po_file}")

    def update_translations(self, locale_code: str, pot_file: str = 'messages.pot',
                           domain: str = 'pydance') -> None:
        """Update existing .po files with new messages"""
        import subprocess

        pot_path = self.locale_dir / pot_file
        po_file = self.locale_dir / locale_code / 'LC_MESSAGES' / f'{domain}.po'

        if pot_path.exists():
            po_file.parent.mkdir(parents=True, exist_ok=True)

            try:
                if po_file.exists():
                    subprocess.run(['msgmerge', '--update', str(po_file), str(pot_path)], check=True)
                else:
                    subprocess.run(['msginit', '--input', str(pot_path), '--output', str(po_file),
                                  '--locale', locale_code], check=True)
                print(f"Updated translations for {locale_code}")
            except subprocess.CalledProcessError:
                print(f"Failed to update translations for {locale_code}")


class LocalizedFormatter:
    """Advanced localized formatting utilities"""

    def __init__(self, locale_manager: LocaleManager):
        self.locale_manager = locale_manager

    def format_address(self, address_data: Dict[str, str]) -> str:
        """Format address according to locale conventions"""
        locale_code = self.locale_manager.get_locale()
        babel_locale = self.locale_manager._locales.get(locale_code)

        if not babel_locale:
            # Fallback to generic format
            return self._format_generic_address(address_data)

        # Use locale-specific address formatting
        parts = []
        if 'street' in address_data:
            parts.append(address_data['street'])
        if 'city' in address_data:
            parts.append(address_data['city'])
        if 'region' in address_data:
            parts.append(address_data['region'])
        if 'postal_code' in address_data:
            parts.append(address_data['postal_code'])
        if 'country' in address_data:
            parts.append(address_data['country'])

        return ', '.join(parts)

    def _format_generic_address(self, address_data: Dict[str, str]) -> str:
        """Generic address formatting fallback"""
        parts = []
        for field in ['street', 'city', 'region', 'postal_code', 'country']:
            if field in address_data and address_data[field]:
                parts.append(address_data[field])
        return ', '.join(parts)

    def format_phone_number(self, phone: str) -> str:
        """Format phone number according to locale"""
        # This would integrate with phonenumbers library
        # For now, return as-is
        return phone

    def format_measurement(self, value: float, unit: str) -> str:
        """Format measurements with locale-appropriate units"""
        locale_code = self.locale_manager.get_locale()

        # Convert units based on locale (metric vs imperial)
        if locale_code.startswith(('en_US', 'en_LR', 'en_MM')):
            # US customary units
            if unit == 'kg':
                return f"{value * 2.20462:.2f} lbs"
            elif unit == 'km':
                return f"{value * 0.621371:.2f} miles"
            elif unit == 'm':
                return f"{value * 3.28084:.2f} feet"
            elif unit == 'L':
                return f"{value * 0.264172:.2f} gallons"
        else:
            # Metric system
            return f"{value:.2f} {unit}"

        return f"{value:.2f} {unit}"

    def format_list(self, items: List[str]) -> str:
        """Format list according to locale conventions"""
        if not items:
            return ""

        if len(items) == 1:
            return items[0]

        if len(items) == 2:
            # Use "and" or locale-specific conjunction
            conjunction = self.locale_manager.translate("and")
            return f"{items[0]} {conjunction} {items[1]}"

        # Multiple items
        separator = self.locale_manager.translate(", ")
        last_separator = f" {self.locale_manager.translate('and')} "

        return separator.join(items[:-1]) + last_separator + items[-1]


# Global instances
_locale_manager = LocaleManager()
_translation_manager = TranslationManager()
_localized_formatter = LocalizedFormatter(_locale_manager)


def get_locale_manager() -> LocaleManager:
    """Get the global locale manager instance"""
    return _locale_manager


def get_translation_manager() -> TranslationManager:
    """Get the global translation manager instance"""
    return _translation_manager


def get_localized_formatter() -> LocalizedFormatter:
    """Get the global localized formatter instance"""
    return _localized_formatter


# Convenience functions
def set_locale(locale_code: str) -> bool:
    """Set the current locale"""
    return _locale_manager.set_locale(locale_code)


def get_locale() -> str:
    """Get the current locale"""
    return _locale_manager.get_locale()


def _(message: str) -> str:
    """Translate a message"""
    return _locale_manager.translate(message)


def ngettext(singular: str, plural: str, count: int) -> str:
    """Get the correct plural form"""
    return _locale_manager.pluralize(singular, plural, count)


def format_date(date_obj: Union[date, datetime], format_str: Optional[str] = None) -> str:
    """Format a date according to current locale"""
    return _locale_manager.format_date(date_obj, format_str)


def format_datetime(datetime_obj: datetime, format_str: Optional[str] = None) -> str:
    """Format a datetime according to current locale"""
    return _locale_manager.format_datetime(datetime_obj, format_str)


def format_number(number: Union[int, float, Decimal]) -> str:
    """Format a number according to current locale"""
    return _locale_manager.format_number(number)


def format_currency(amount: Union[int, float, Decimal], currency: str = 'USD') -> str:
    """Format currency according to current locale"""
    return _locale_manager.format_currency(amount, currency)


def format_percent(percentage: Union[int, float, Decimal]) -> str:
    """Format percentage according to current locale"""
    return _locale_manager.format_percent(percentage)


def format_address(address_data: Dict[str, str]) -> str:
    """Format address according to locale conventions"""
    return _localized_formatter.format_address(address_data)


def format_measurement(value: float, unit: str) -> str:
    """Format measurements with locale-appropriate units"""
    return _localized_formatter.format_measurement(value, unit)


def format_list(items: List[str]) -> str:
    """Format list according to locale conventions"""
    return _localized_formatter.format_list(items)

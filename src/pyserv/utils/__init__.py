"""
Pyserv  Utilities
Consolidated utility functions for the Pyserv  framework.

All utilities are now centralized in pyserv .core.utilities for better organization
and to eliminate code duplication. This module provides convenient access to all
utility classes and functions.
"""

# Import all utilities from the consolidated core module
from pyserv.utilities import *

# Import advanced utilities
from .advanced_math import AdvancedMathUtils
from .advanced_functions import (
    FunctionUtils, AsyncUtils, DataUtils, ValidationUtils,
    PerformanceUtils, ThreadingUtils, LoggingUtils,
    function_utils, async_utils, data_utils, validation_utils,
    performance_utils, threading_utils, logging_utils
)
from .locale_support import (
    LocaleManager, TranslationManager, LocalizedFormatter,
    get_locale_manager, get_translation_manager, get_localized_formatter,
    set_locale, get_locale, _, ngettext,
    format_date, format_datetime, format_number, format_currency, format_percent,
    format_address, format_measurement, format_list
)

__all__ = [
    # Core utilities (from pyserv.core.utilities)
    'NumberUtils', 'StringUtils', 'DateTimeUtils',
    'FastList', 'FastDict', 'CircularBuffer', 'BloomFilter',
    'Sanitizer', 'CSRFUtils', 'CompressionUtils', 'EncodingUtils',
    'csrf_exempt', 'csrf_exempt_endpoint',

    # Advanced mathematical utilities
    'AdvancedMathUtils',

    # Advanced function utilities
    'FunctionUtils', 'AsyncUtils', 'DataUtils', 'ValidationUtils',
    'PerformanceUtils', 'ThreadingUtils', 'LoggingUtils',
    'function_utils', 'async_utils', 'data_utils', 'validation_utils',
    'performance_utils', 'threading_utils', 'logging_utils',

    # Locale and internationalization support
    'LocaleManager', 'TranslationManager', 'LocalizedFormatter',
    'get_locale_manager', 'get_translation_manager', 'get_localized_formatter',
    'set_locale', 'get_locale', '_', 'ngettext',
    'format_date', 'format_datetime', 'format_number', 'format_currency', 'format_percent',
    'format_address', 'format_measurement', 'format_list',
]

"""
Internationalization and localization system for Pyserv applications.

This module provides comprehensive i18n support including:
- Message translation and localization
- Pluralization support
- Date, time, and number formatting
- Currency formatting
- Language detection and switching
- Translation file management
"""

import json
import os
import gettext
import locale
import threading
from typing import Dict, List, Any, Optional, Union, Callable
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime, date, time
from decimal import Decimal
import logging


@dataclass
class TranslationConfig:
    """Configuration for translation system"""
    default_language: str = "en"
    supported_languages: List[str] = field(default_factory=lambda: ["en", "es", "fr", "de"])
    translations_dir: str = "translations"
    domain: str = "messages"
    enable_fallback: bool = True
    cache_translations: bool = True
    auto_reload: bool = False


class TranslationManager:
    """Main translation manager for Pyserv applications"""

    _instance = None
    _lock = threading.Lock()

    def __init__(self, config: TranslationConfig = None):
        self.config = config or TranslationConfig()
        self.translations: Dict[str, Dict[str, str]] = {}
        self.current_language = self.config.default_language
        self.fallback_language = self.config.default_language
        self.logger = logging.getLogger("translation_manager")

        # Load translations
        self._load_translations()

    @classmethod
    def get_instance(cls, config: TranslationConfig = None) -> 'TranslationManager':
        """Get singleton instance"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(config)
        return cls._instance

    def _load_translations(self):
        """Load translation files"""
        translations_dir = Path(self.config.translations_dir)

        if not translations_dir.exists():
            self.logger.warning(f"Translations directory {translations_dir} does not exist")
            return

        for lang_file in translations_dir.glob("*.json"):
            language = lang_file.stem
            try:
                with open(lang_file, 'r', encoding='utf-8') as f:
                    self.translations[language] = json.load(f)
                self.logger.info(f"Loaded translations for language: {language}")
            except Exception as e:
                self.logger.error(f"Failed to load translations for {language}: {e}")

    def set_language(self, language: str):
        """Set current language"""
        if language in self.config.supported_languages:
            self.current_language = language
            self.logger.info(f"Language set to: {language}")
        else:
            self.logger.warning(f"Unsupported language: {language}")

    def get_language(self) -> str:
        """Get current language"""
        return self.current_language

    def translate(self, message: str, language: str = None, **kwargs) -> str:
        """Translate a message"""
        lang = language or self.current_language

        # Try current language first
        if lang in self.translations and message in self.translations[lang]:
            translation = self.translations[lang][message]
        # Try fallback language
        elif (self.config.enable_fallback and
              self.fallback_language in self.translations and
              message in self.translations[self.fallback_language]):
            translation = self.translations[self.fallback_language][message]
        else:
            # Return original message if no translation found
            translation = message

        # Handle variable substitution
        if kwargs:
            try:
                translation = translation.format(**kwargs)
            except (KeyError, ValueError):
                self.logger.warning(f"Translation format error for message: {message}")

        return translation

    def translate_plural(self, singular: str, plural: str, count: int,
                        language: str = None, **kwargs) -> str:
        """Translate with pluralization support"""
        lang = language or self.current_language

        # Simple pluralization logic (can be enhanced with proper plural rules)
        if count == 1:
            message = singular
        else:
            message = plural

        return self.translate(message, lang, **kwargs)

    def get_available_languages(self) -> List[str]:
        """Get list of available languages"""
        return list(self.translations.keys())

    def add_translation(self, language: str, key: str, value: str):
        """Add a translation programmatically"""
        if language not in self.translations:
            self.translations[language] = {}
        self.translations[language][key] = value

    def reload_translations(self):
        """Reload translation files"""
        self.translations.clear()
        self._load_translations()


# Convenience functions for translation
def _(message: str, **kwargs) -> str:
    """Translate a message (gettext style)"""
    manager = TranslationManager.get_instance()
    return manager.translate(message, **kwargs)

def gettext(message: str, **kwargs) -> str:
    """Translate a message"""
    return _(message, **kwargs)

def ngettext(singular: str, plural: str, count: int, **kwargs) -> str:
    """Translate with pluralization"""
    manager = TranslationManager.get_instance()
    return manager.translate_plural(singular, plural, count, **kwargs)

def set_language(language: str):
    """Set current language"""
    manager = TranslationManager.get_instance()
    manager.set_language(language)

def get_current_language() -> str:
    """Get current language"""
    manager = TranslationManager.get_instance()
    return manager.get_current_language()

# Language detection utilities
def detect_language_from_request(request) -> str:
    """Detect language from HTTP request"""
    # Check Accept-Language header
    accept_language = request.headers.get('Accept-Language', '')
    if accept_language:
        # Simple language detection - take first language
        primary_language = accept_language.split(',')[0].split('-')[0]
        manager = TranslationManager.get_instance()
        if primary_language in manager.config.supported_languages:
            return primary_language

    # Check user preferences or session
    # This would be implemented based on your authentication system

    return TranslationManager.get_instance().config.default_language

def detect_language_from_browser() -> str:
    """Detect language from browser settings"""
    try:
        # Try to get system locale
        system_locale = locale.getlocale()[0]
        if system_locale:
            language = system_locale.split('_')[0]
            manager = TranslationManager.get_instance()
            if language in manager.config.supported_languages:
                return language
    except Exception:
        pass

    return TranslationManager.get_instance().config.default_language

# Context manager for temporary language switching
class LanguageContext:
    """Context manager for temporary language switching"""

    def __init__(self, language: str):
        self.language = language
        self.previous_language = None
        self.manager = TranslationManager.get_instance()

    def __enter__(self):
        self.previous_language = self.manager.get_language()
        self.manager.set_language(self.language)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.previous_language:
            self.manager.set_language(self.previous_language)

# Middleware for automatic language detection
class TranslationMiddleware:
    """Middleware for automatic language detection and setup"""

    def __init__(self, app, default_language: str = "en"):
        self.app = app
        self.default_language = default_language

    async def __call__(self, request, call_next):
        # Detect language from request
        language = detect_language_from_request(request)

        # Set language for this request
        with LanguageContext(language):
            response = await call_next(request)

        # Add language header to response
        response.headers['Content-Language'] = language

        return response

# Export all translation utilities
__all__ = [
    'TranslationConfig', 'TranslationManager', 'translate', 'gettext',
    '_', 'ngettext', 'set_language', 'get_current_language',
    'detect_language_from_request', 'detect_language_from_browser',
    'LanguageContext', 'TranslationMiddleware'
]

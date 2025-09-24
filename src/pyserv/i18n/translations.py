"""
Internationalization (i18n) translation system for Pyserv .

This module provides comprehensive translation support with multiple backends,
including JSON files and GNU gettext. It supports plural forms, context-aware
translations, and lazy evaluation.

Features:
- Multiple translation backends (JSON, gettext)
- Plural form support with locale-specific rules
- Context-aware translations
- Lazy translation evaluation
- Fallback language support
- UTF-8 encoding support

Example:
    >>> from pyserv.i18n import set_locale, gettext
    >>>
    >>> set_locale("es")
    >>> message = gettext("Hello, World!")
    >>> print(message)  # "¡Hola, Mundo!"
"""

import gettext as gettext_module
from pathlib import Path
from typing import Dict, Optional, Callable, Any

import json

class Translations:
    """Translation system with support for multiple domains and languages.

    This class manages translation loading and retrieval from various sources
    including JSON files and GNU gettext message catalogs.
    """

    def __init__(self, translation_dir: str = "translations",
                 default_domain: str = "messages"):
        self.translation_dir = Path(translation_dir)
        self.default_domain = default_domain
        self.translations: Dict[str, Dict[str, Any]] = {}
        self.gettext_translations: Dict[str, gettext_module.GNUTranslations] = {}

    def load_translations(self, domain: Optional[str] = None):
        """Load translations for a domain"""
        domain = domain or self.default_domain
        if domain in self.translations:
            return

        translations = {}
        domain_dir = self.translation_dir / domain

        if domain_dir.exists():
            for lang_file in domain_dir.glob("*.json"):
                lang = lang_file.stem
                with open(lang_file, 'r', encoding='utf-8') as f:
                    translations[lang] = json.load(f)

            # Also load gettext translations if available
            gettext_dir = domain_dir / "LC_MESSAGES"
            if gettext_dir.exists():
                for mo_file in gettext_dir.glob("*.mo"):
                    lang = mo_file.stem
                    with open(mo_file, 'rb') as f:
                        self.gettext_translations[f"{domain}_{lang}"] = gettext_module.GNUTranslations(f)

        self.translations[domain] = translations

    def get_translation(self, key: str, domain: Optional[str] = None,
                       locale: Optional[str] = None, **kwargs) -> str:
        """Get a translation for a key"""
        domain = domain or self.default_domain
        locale = locale or "en"

        if domain not in self.translations:
            self.load_translations(domain)

        # Try gettext first
        gettext_key = f"{domain}_{locale}"
        if gettext_key in self.gettext_translations:
            translation = self.gettext_translations[gettext_key].gettext(key)
            if translation != key:  # Translation found
                return translation.format(**kwargs) if kwargs else translation

        # Fall back to JSON translations
        domain_translations = self.translations.get(domain, {})
        locale_translations = domain_translations.get(locale, {})

        # Try exact locale match
        if key in locale_translations:
            translation = locale_translations[key]
            return translation.format(**kwargs) if kwargs else translation

        # Try language only (e.g., "es" for "es-ES")
        if "-" in locale:
            lang_only = locale.split("-")[0]
            lang_translations = domain_translations.get(lang_only, {})
            if key in lang_translations:
                translation = lang_translations[key]
                return translation.format(**kwargs) if kwargs else translation

        # Fall back to default language
        if locale != "en":
            en_translations = domain_translations.get("en", {})
            if key in en_translations:
                translation = en_translations[key]
                return translation.format(**kwargs) if kwargs else translation

        # Return the key itself as fallback
        return key.format(**kwargs) if kwargs else key

    def get_plural_translation(self, key: str, count: int, domain: Optional[str] = None,
                              locale: Optional[str] = None, **kwargs) -> str:
        """Get a plural translation"""
        domain = domain or self.default_domain
        locale = locale or "en"

        if domain not in self.translations:
            self.load_translations(domain)

        # Try gettext plural
        gettext_key = f"{domain}_{locale}"
        if gettext_key in self.gettext_translations:
            translation = self.gettext_translations[gettext_key].ngettext(key, f"{key}_plural", count)
            if translation not in [key, f"{key}_plural"]:  # Translation found
                return translation.format(count=count, **kwargs) if kwargs else translation

        # Fall back to JSON translations with plural handling
        plural_key = self._get_plural_key(key, count, locale)
        translation = self.get_translation(plural_key, domain, locale, count=count, **kwargs)

        if translation == plural_key:  # No translation found
            # Fall back to English plural rules
            if count == 1:
                return key.format(count=count, **kwargs) if kwargs else key
            else:
                plural_key = f"{key}_plural"
                translation = self.get_translation(plural_key, domain, "en", count=count, **kwargs)
                if translation == plural_key:
                    return f"{key}s".format(count=count, **kwargs) if kwargs else f"{key}s"
                return translation

        return translation

    def _get_plural_key(self, key: str, count: int, locale: str) -> str:
        """Get the appropriate plural form key based on locale rules"""
        # Simplified plural rules - in a real implementation, use proper CLDR rules
        if locale.startswith("zh"):  # Chinese
            return key  # Chinese has no plural forms
        elif locale.startswith("ja"):  # Japanese
            return key  # Japanese has no plural forms
        elif locale.startswith("ru"):  # Russian
            # Russian has complex plural rules, simplified here
            if count % 10 == 1 and count % 100 != 11:
                return f"{key}_one"
            elif 2 <= count % 10 <= 4 and not (12 <= count % 100 <= 14):
                return f"{key}_few"
            else:
                return f"{key}_many"
        else:  # English and most European languages
            if count == 1:
                return key
            else:
                return f"{key}_plural"

# Global translation instance
_translations = Translations()

def gettext(key: str, **kwargs) -> str:
    """Translate a string"""
    from .utils import get_locale
    return _translations.get_translation(key, locale=get_locale(), **kwargs)

def ngettext(key: str, count: int, **kwargs) -> str:
    """Translate a plural string"""
    from .utils import get_locale
    return _translations.get_plural_translation(key, count, locale=get_locale(), **kwargs)

def pgettext(context: str, key: str, **kwargs) -> str:
    """Translate a string with context"""
    from .utils import get_locale
    # For simplicity, ignore context in this implementation
    return _translations.get_translation(key, locale=get_locale(), **kwargs)

def lazy_gettext(key: str, **kwargs) -> Callable[[], str]:
    """Create a lazy translation that gets evaluated when used"""
    def lazy_eval():
        return gettext(key, **kwargs)
    return lazy_eval

# Short aliases
_ = gettext
_n = ngettext





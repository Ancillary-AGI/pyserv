"""
Tests for internationalization functionality.
"""

import pytest
from datetime import datetime
from pyserv import Application
from pyserv.i18n import gettext, ngettext, lazy_gettext, set_locale, get_locale
from pyserv.i18n.middleware import LocaleMiddleware
from testing import TestClient


@pytest.mark.asyncio
async def test_basic_translation():
    """Test basic translation functionality"""
    set_locale("es")
    assert gettext("Hello, World!") == "¡Hola, Mundo!"

    set_locale("fr")
    assert gettext("Hello, World!") == "Bonjour le monde!"

    set_locale("en")
    assert gettext("Hello, World!") == "Hello, World!"


@pytest.mark.asyncio
async def test_plural_translation():
    """Test plural translation"""
    set_locale("en")
    assert gettext("You have {count} message", count=1) == "You have 1 message"
    assert gettext("You have {count} message", count=2) == "You have 2 messages"

    # Test with ngettext for proper plural handling
    assert ngettext("message", 1) == "message"
    assert ngettext("message", 2) == "messages"


@pytest.mark.asyncio
async def test_locale_middleware():
    """Test locale detection middleware"""
    app = Application()
    app.setup_i18n(supported_locales=["en", "es", "fr"])

    @app.route("/test/")
    async def test_handler(request):
        from pyserv.i18n import get_locale
        return {"locale": get_locale()}

    client = TestClient(app)

    # Test default locale
    response = await client.get("/test/")
    assert "en" in response.content

    # Test query parameter
    response = await client.get("/test/", params={"lang": "es"})
    assert "es" in response.content

    # Test header-based detection
    response = await client.get("/test/", headers={"Accept-Language": "fr,en;q=0.9"})
    assert "fr" in response.content


@pytest.mark.asyncio
async def test_date_formatting():
    """Test date formatting by locale"""
    from pyserv.i18n.formatters import format_date

    test_date = datetime(2023, 12, 25)

    set_locale("en")
    en_date = format_date(test_date)

    set_locale("es")
    es_date = format_date(test_date)

    set_locale("fr")
    fr_date = format_date(test_date)

    # Dates should be formatted differently for each locale
    assert en_date != es_date
    assert en_date != fr_date
    assert es_date != fr_date


@pytest.mark.asyncio
async def test_number_formatting():
    """Test number formatting by locale"""
    from pyserv.i18n.formatters import format_number

    test_number = 1234567.89

    set_locale("en")
    en_number = format_number(test_number)

    set_locale("es")
    es_number = format_number(test_number)

    set_locale("de")
    de_number = format_number(test_number)

    # Numbers should be formatted differently for each locale
    assert en_number != es_number
    assert en_number != de_number
    assert es_number != de_number


@pytest.mark.asyncio
async def test_lazy_translation():
    """Test lazy translation functionality"""
    set_locale("es")

    # Test lazy translation
    lazy_text = lazy_gettext("Hello, World!")
    assert str(lazy_text) == "¡Hola, Mundo!"

    set_locale("fr")
    assert str(lazy_text) == "Bonjour le monde!"


@pytest.mark.asyncio
async def test_translation_context():
    """Test translation with context"""
    from pyserv.i18n import pgettext

    set_locale("en")
    assert pgettext("menu", "File") == "File"
    assert pgettext("button", "File") == "File"

    # In a real implementation, these would have different translations
    # based on context, but for this test we'll just verify the function works


@pytest.mark.asyncio
async def test_locale_fallback():
    """Test locale fallback functionality"""
    set_locale("nonexistent")
    # Should fall back to default locale
    assert get_locale() == "en"
    assert gettext("Hello, World!") == "Hello, World!"


@pytest.mark.asyncio
async def test_timezone_handling():
    """Test timezone handling in i18n"""
    from pyserv.i18n.utils import get_timezone, set_timezone

    set_timezone("UTC")
    assert get_timezone() == "UTC"

    set_timezone("America/New_York")
    assert get_timezone() == "America/New_York"


@pytest.mark.asyncio
async def test_currency_formatting():
    """Test currency formatting by locale"""
    from pyserv.i18n.formatters import format_currency

    amount = 1234.56

    set_locale("en")
    en_currency = format_currency(amount, "USD")

    set_locale("es")
    es_currency = format_currency(amount, "EUR")

    set_locale("de")
    de_currency = format_currency(amount, "EUR")

    # Currency formats should be different
    assert en_currency != es_currency
    assert en_currency != de_currency


@pytest.mark.asyncio
async def test_rtl_language_support():
    """Test right-to-left language support"""
    from pyserv.i18n.utils import is_rtl_language

    assert is_rtl_language("ar") == True
    assert is_rtl_language("he") == True
    assert is_rtl_language("fa") == True
    assert is_rtl_language("ur") == True
    assert is_rtl_language("en") == False
    assert is_rtl_language("es") == False


@pytest.mark.asyncio
async def test_locale_validation():
    """Test locale validation"""
    from pyserv.i18n.utils import validate_locale

    assert validate_locale("en") == True
    assert validate_locale("es-ES") == True
    assert validate_locale("zh_CN") == True
    assert validate_locale("invalid") == False


@pytest.mark.asyncio
async def test_translation_file_loading():
    """Test loading translation files"""
    from pyserv.i18n.translations import Translations

    manager = Translations()
    manager.load_translations("tests/fixtures/translations")

    set_locale("es")
    assert gettext("Hello") == "Hola"

    set_locale("fr")
    assert gettext("Hello") == "Bonjour"


@pytest.mark.asyncio
async def test_fallback_translations():
    """Test fallback to default locale when translation missing"""
    set_locale("es")
    # This should fall back to English if Spanish translation doesn't exist
    result = gettext("Nonexistent Key")
    assert result == "Nonexistent Key"  # Should return the key itself as fallback


@pytest.mark.asyncio
async def test_parameter_interpolation():
    """Test parameter interpolation in translations"""
    set_locale("en")
    result = gettext("Welcome, {name}!", name="John")
    assert result == "Welcome, John!"

    result = gettext("You have {count} messages", count=5)
    assert result == "You have 5 messages"





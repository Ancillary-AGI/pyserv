from typing import Callable, Optional, List
from ..core.http.request import Request
from ..core.http.response import Response
from ..core.middleware import HTTPMiddleware
import re
from .utils import set_locale, set_timezone

class LocaleMiddleware(HTTPMiddleware):
    """Middleware for locale and timezone detection"""

    def __init__(self, default_locale: str = "en", default_timezone: str = "UTC",
                 supported_locales: Optional[List[str]] = None):
        self.default_locale = default_locale
        self.default_timezone = default_timezone
        self.supported_locales = supported_locales or ["en"]
        self.locale_pattern = re.compile(r"^[a-z]{2}(?:-[A-Z]{2})?$")

    async def process_request(self, request: Request) -> Request:
        """Detect locale and timezone from request"""
        locale = self.detect_locale(request)
        timezone = self.detect_timezone(request)

        # Set locale and timezone for this request
        request.state.locale = locale
        request.state.timezone = timezone

        # Set thread-local locale and timezone
        set_locale(locale)
        set_timezone(timezone)

        return request

    def detect_locale(self, request: Request) -> str:
        """Detect locale from request headers, query params, or cookies"""
        # Check query parameter first
        locale_param = self._get_query_param(request, "lang") or self._get_query_param(request, "locale")
        if locale_param and self.is_valid_locale(locale_param):
            return locale_param

        # Check cookie
        locale_cookie = request.headers.get("Cookie", "")
        if "locale=" in locale_cookie:
            # Simple cookie parsing - in real implementation use proper cookie parser
            cookie_parts = locale_cookie.split(";")
            for part in cookie_parts:
                if "locale=" in part:
                    locale_value = part.split("=")[1].strip()
                    if self.is_valid_locale(locale_value):
                        return locale_value

        # Check Accept-Language header
        accept_language = request.headers.get("Accept-Language", "")
        if accept_language:
            locales = self.parse_accept_language(accept_language)
            for locale in locales:
                if self.is_valid_locale(locale):
                    return locale

        return self.default_locale

    def detect_timezone(self, request: Request) -> str:
        """Detect timezone from request"""
        # Check query parameter
        tz_param = self._get_query_param(request, "tz") or self._get_query_param(request, "timezone")
        if tz_param and self.is_valid_timezone(tz_param):
            return tz_param

        # Check cookie
        tz_cookie = request.headers.get("Cookie", "")
        if "timezone=" in tz_cookie:
            # Simple cookie parsing
            cookie_parts = tz_cookie.split(";")
            for part in cookie_parts:
                if "timezone=" in part:
                    tz_value = part.split("=")[1].strip()
                    if self.is_valid_timezone(tz_value):
                        return tz_value

        return self.default_timezone

    def _get_query_param(self, request: Request, key: str) -> Optional[str]:
        """Get query parameter value from request"""
        values = request.query_params.get(key)
        if values and len(values) > 0:
            return values[0]
        return None

    def is_valid_locale(self, locale: str) -> bool:
        """Check if locale is valid and supported"""
        if not self.locale_pattern.match(locale):
            return False

        # Check if locale is supported (either exact match or language match)
        for supported in self.supported_locales:
            if locale == supported or locale.startswith(supported.split("-")[0] + "-"):
                return True

        return False

    def is_valid_timezone(self, timezone: str) -> bool:
        """Basic timezone validation"""
        # In a real implementation, you would check against a list of valid timezones
        return True  # Simplified for this example

    def parse_accept_language(self, accept_language: str) -> List[str]:
        """Parse Accept-Language header"""
        locales = []
        parts = accept_language.split(",")

        for part in parts:
            locale = part.split(";")[0].strip()
            if locale:
                locales.append(locale)

        return locales

    async def process_response(self, request: Request, response: Response) -> Response:
        """Set locale and timezone cookies if needed"""
        # You could set cookies here to remember user preferences
        return response

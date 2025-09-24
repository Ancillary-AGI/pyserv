from typing import Optional, Union
from datetime import datetime, date, time
import locale as locale_module
from babel import numbers, dates
from .utils import get_locale, get_timezone

def format_date(value: Union[date, datetime], format: Optional[str] = None,
               locale: Optional[str] = None) -> str:
    """Format a date according to locale"""
    if format:
        return value.strftime(format)

    locale = locale or get_locale()
    return dates.format_date(value, locale=locale)

def format_time(value: Union[time, datetime], format: Optional[str] = None,
               locale: Optional[str] = None, timezone: Optional[str] = None) -> str:
    """Format a time according to locale"""
    if isinstance(value, datetime):
        value = value.time()

    if format:
        return value.strftime(format)

    locale = locale or get_locale()
    timezone = timezone or get_timezone()
    return dates.format_time(value, locale=locale, tzinfo=timezone)

def format_datetime(value: datetime, format: Optional[str] = None,
                   locale: Optional[str] = None, timezone: Optional[str] = None) -> str:
    """Format a datetime according to locale"""
    if format:
        return value.strftime(format)

    locale = locale or get_locale()
    timezone = timezone or get_timezone()
    return dates.format_datetime(value, locale=locale, tzinfo=timezone)

def format_number(value: Union[int, float], locale: Optional[str] = None) -> str:
    """Format a number according to locale"""
    locale = locale or get_locale()
    return numbers.format_number(value, locale=locale)

def format_currency(value: Union[int, float], currency: str,
                   locale: Optional[str] = None) -> str:
    """Format currency according to locale"""
    locale = locale or get_locale()
    return numbers.format_currency(value, currency, locale=locale)

def format_percent(value: Union[int, float], locale: Optional[str] = None) -> str:
    """Format percentage according to locale"""
    locale = locale or get_locale()
    return numbers.format_percent(value, locale=locale)

def format_scientific(value: Union[int, float], locale: Optional[str] = None) -> str:
    """Format scientific notation according to locale"""
    locale = locale or get_locale()
    return numbers.format_scientific(value, locale=locale)





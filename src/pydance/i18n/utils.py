"""
Utilities for internationalization and localization
"""
import threading
from typing import Optional
from datetime import datetime
import pytz

# Thread-local storage for locale and timezone
_thread_locals = threading.local()

def get_locale() -> str:
    """Get the current locale for this thread"""
    return getattr(_thread_locals, 'locale', 'en')

def set_locale(locale: str):
    """Set the locale for this thread"""
    _thread_locals.locale = locale

def get_timezone() -> str:
    """Get the current timezone for this thread"""
    return getattr(_thread_locals, 'timezone', 'UTC')

def set_timezone(timezone: str):
    """Set the timezone for this thread"""
    _thread_locals.timezone = timezone

def get_current_time() -> datetime:
    """Get current time in the current timezone"""
    tz = pytz.timezone(get_timezone())
    return datetime.now(tz)

def to_timezone(dt: datetime, timezone: str) -> datetime:
    """Convert datetime to specified timezone"""
    if dt.tzinfo is None:
        dt = pytz.UTC.localize(dt)
    return dt.astimezone(pytz.timezone(timezone))

def to_utc(dt: datetime) -> datetime:
    """Convert datetime to UTC"""
    if dt.tzinfo is None:
        return pytz.UTC.localize(dt)
    return dt.astimezone(pytz.UTC)

__all__ = ['get_locale', 'set_locale', 'get_timezone', 'set_timezone',
           'get_current_time', 'to_timezone', 'to_utc']

"""
Pydance - A comprehensive web framework with MVC architecture
"""

__version__ = "0.1.0"

from .core.application import Application
from .core.routing import Router, Route
from .core.middleware import HTTPMiddleware, WebSocketMiddleware
from .core.exceptions import HTTPException, BadRequest, NotFound, Forbidden
from .core.templating import TemplateEngineManager
from .core.security import Security, CryptoUtils

# Widgets system
try:
    from .widgets import (
        RichText, RichSelect, RichTitle, RichFile, RichDate,
        RichColor, RichRating, RichTags, RichSlider, RichCode
    )
    _widgets_available = True
except ImportError:
    _widgets_available = False

__all__ = [
    'Application', 'Router', 'Route', 'HTTPMiddleware', 'WebSocketMiddleware',
    'HTTPException', 'BadRequest', 'NotFound', 'Forbidden',
    'TemplateEngineManager', 'Security', 'CryptoUtils'
]

# Add widgets to __all__ if available
if _widgets_available:
    __all__.extend([
        'RichText', 'RichSelect', 'RichTitle', 'RichFile', 'RichDate',
        'RichColor', 'RichRating', 'RichTags', 'RichSlider', 'RichCode'
    ])

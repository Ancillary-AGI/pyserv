"""
PyDance Widgets System

A comprehensive widget system for building dynamic web interfaces.
Provides rich UI components with form handling, validation, and theming.
"""

from .core import (
    Widget, BaseWidget, WidgetRegistry, WidgetConfig,
    RichText, RichSelect, RichTitle, RichFile, RichDate,
    RichColor, RichRating, RichTags, RichSlider, RichCode,
    # Date and Time Widgets
    RichDateTime, RichTime,
    # File Management Widgets
    RichFileManager,
    # Commerce Widgets
    RichPrice, RichQuantity, RichProductCard, RichShoppingCart
)
from .forms import (
    FormWidget, FieldWidget, ButtonWidget, InputWidget,
    TextareaWidget, SelectWidget, CheckboxWidget, RadioWidget
)

__version__ = "1.0.0"
__all__ = [
    # Core widgets
    'Widget', 'BaseWidget', 'WidgetRegistry', 'WidgetConfig',
    'RichText', 'RichSelect', 'RichTitle', 'RichFile', 'RichDate',
    'RichColor', 'RichRating', 'RichTags', 'RichSlider', 'RichCode',

    # Date and Time Widgets
    'RichDateTime', 'RichTime',

    # File Management Widgets
    'RichFileManager',

    # Commerce Widgets
    'RichPrice', 'RichQuantity', 'RichProductCard', 'RichShoppingCart',

    # Form widgets
    'FormWidget', 'FieldWidget', 'ButtonWidget', 'InputWidget',
    'TextareaWidget', 'SelectWidget', 'CheckboxWidget', 'RadioWidget'
]

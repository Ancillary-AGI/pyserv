"""
Pydance Rich Widgets - Advanced Form Widgets System
==================================================

A comprehensive collection of secure, efficient, and feature-rich form widgets
for modern web applications.

Features:
- XSS Protection & Security
- Markdown/HTML Content Support
- Responsive Design
- Accessibility Support
- Customizable Themes
- Rich Interactions
- Form Validation
- File Upload Handling
- Internationalization Ready

Available Widgets:
- RichText: WYSIWYG editor with Markdown support
- RichSelect: Advanced dropdown with search
- RichDate: Calendar picker with time selection
- RichColor: Color picker with palette
- RichRating: Star rating system
- RichTags: Tag input with suggestions
- RichFile: Drag & drop file upload
- RichSlider: Range slider with values
- RichCode: Code editor with highlighting
- RichTitle: Dynamic title with formatting

Usage:
    from pydance.widgets import RichText, RichSelect

    editor = RichText('content', format='markdown')
    select = RichSelect('category', options=[...])

    html = editor.render()
"""

__version__ = "1.0.0"
__author__ = "Pydance Framework"

from .core import (
    BaseWidget, WidgetType, ContentFormat, WidgetAttributes,
    WidgetSecurity, MarkdownProcessor, WidgetFactory
)

from .widgets import (
    TextWidget, RichTextWidget, RichSelectWidget, RichTitleWidget
)

from .widgets_extra import (
    RichFileWidget, RichDateWidget, RichColorWidget, RichRatingWidget,
    RichTagsWidget, RichSliderWidget, RichCodeWidget
)

from .forms import WidgetForm, FormField

# Convenience imports
RichText = RichTextWidget
RichSelect = RichSelectWidget
RichTitle = RichTitleWidget
RichFile = RichFileWidget
RichDate = RichDateWidget
RichColor = RichColorWidget
RichRating = RichRatingWidget
RichTags = RichTagsWidget
RichSlider = RichSliderWidget
RichCode = RichCodeWidget

__all__ = [
    # Core classes
    'BaseWidget', 'WidgetType', 'ContentFormat', 'WidgetAttributes',
    'WidgetSecurity', 'MarkdownProcessor', 'WidgetFactory',

    # Basic widgets
    'TextWidget', 'RichTextWidget', 'RichSelectWidget', 'RichTitleWidget',

    # Advanced widgets
    'RichFileWidget', 'RichDateWidget', 'RichColorWidget', 'RichRatingWidget',
    'RichTagsWidget', 'RichSliderWidget', 'RichCodeWidget',

    # Form integration
    'WidgetForm', 'FormField',

    # Convenience aliases
    'RichText', 'RichSelect', 'RichTitle', 'RichFile', 'RichDate',
    'RichColor', 'RichRating', 'RichTags', 'RichSlider', 'RichCode'
]

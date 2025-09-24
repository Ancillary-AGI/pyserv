"""
Pyserv  Rich Widgets Core System

Advanced widget system with rich UI components, security features,
and comprehensive functionality for modern web applications.
"""

import os
import uuid
import json
import hashlib
from datetime import datetime, date, time
from typing import Any, Dict, List, Optional, Union, Callable
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum


class WidgetTheme(Enum):
    """Widget theme options"""
    LIGHT = "light"
    DARK = "dark"
    BLUE = "blue"
    GREEN = "green"
    PURPLE = "purple"
    RED = "red"
    ORANGE = "orange"
    AUTO = "auto"  # Follows current application theme


class ThemeManager:
    """Manages application-wide theme settings"""

    _current_theme: Optional[WidgetTheme] = None
    _theme_listeners: List[Callable[[WidgetTheme], None]] = []

    @classmethod
    def get_current_theme(cls) -> WidgetTheme:
        """Get the current application theme"""
        if cls._current_theme is None:
            # Try to detect theme from various sources
            cls._current_theme = cls._detect_current_theme()
        return cls._current_theme

    @classmethod
    def set_current_theme(cls, theme: WidgetTheme) -> None:
        """Set the current application theme"""
        if theme != cls._current_theme:
            old_theme = cls._current_theme
            cls._current_theme = theme
            # Notify listeners of theme change
            for listener in cls._theme_listeners:
                try:
                    listener(theme)
                except Exception:
                    pass  # Ignore listener errors

    @classmethod
    def add_theme_listener(cls, listener: Callable[[WidgetTheme], None]) -> None:
        """Add a listener for theme changes"""
        if listener not in cls._theme_listeners:
            cls._theme_listeners.append(listener)

    @classmethod
    def remove_theme_listener(cls, listener: Callable[[WidgetTheme], None]) -> None:
        """Remove a theme listener"""
        if listener in cls._theme_listeners:
            cls._theme_listeners.remove(listener)

    @classmethod
    def _detect_current_theme(cls) -> WidgetTheme:
        """Detect the current theme from various sources"""
        # Try to detect from environment variables
        env_theme = os.getenv('PYSERV _THEME', '').upper()
        if env_theme and hasattr(WidgetTheme, env_theme):
            return getattr(WidgetTheme, env_theme)

        # Try to detect from CSS custom properties (if running in browser)
        # This would be set by JavaScript, but we can check for a default

        # Try to detect from system preference (if available)
        try:
            import platform
            if platform.system() == 'Darwin':  # macOS
                # Could check macOS appearance setting
                pass
        except ImportError:
            pass

        # Default to light theme
        return WidgetTheme.LIGHT

    @classmethod
    def resolve_theme(cls, theme: Optional[WidgetTheme]) -> WidgetTheme:
        """Resolve AUTO theme to actual theme"""
        if theme == WidgetTheme.AUTO or theme is None:
            return cls.get_current_theme()
        return theme


class WidgetSize(Enum):
    """Widget size options"""
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    EXTRA_LARGE = "extra-large"


class WidgetType(Enum):
    """Widget type classifications"""
    INPUT = "input"
    DISPLAY = "display"
    CONTAINER = "container"
    FORM = "form"
    MEDIA = "media"
    COMMERCE = "commerce"


@dataclass
class WidgetConfig:
    """Configuration for widget behavior and appearance"""
    theme: WidgetTheme = WidgetTheme.LIGHT
    size: WidgetSize = WidgetSize.MEDIUM
    disabled: bool = False
    readonly: bool = False
    required: bool = False
    placeholder: str = ""
    help_text: str = ""
    classes: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    validation_rules: List[Dict[str, Any]] = field(default_factory=list)


class BaseWidget:
    """Base class for all Pyserv  widgets"""

    def __init__(self, name: str, config: Optional[WidgetConfig] = None, **kwargs):
        self.name = name
        self.config = config or WidgetConfig()
        self.id = f"widget-{uuid.uuid4().hex[:8]}"
        self.value = kwargs.get('value', None)
        self.errors: List[str] = []
        self.dependencies: List[str] = []

        # Update config with kwargs
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)

        # Resolve AUTO theme to current theme
        if self.config.theme == WidgetTheme.AUTO:
            self.config.theme = ThemeManager.get_current_theme()

        # Listen for theme changes if using AUTO theme
        if kwargs.get('theme') == WidgetTheme.AUTO:
            ThemeManager.add_theme_listener(self._on_theme_change)

    def _on_theme_change(self, new_theme: WidgetTheme) -> None:
        """Handle theme change events"""
        if self.config.theme == WidgetTheme.AUTO:
            self.config.theme = new_theme
            # Re-render the widget if it has been rendered
            # This would typically be handled by the frontend JavaScript
            pass

    def render(self) -> str:
        """Render the widget to HTML"""
        raise NotImplementedError("Subclasses must implement render()")

    def validate(self) -> bool:
        """Validate the widget's current value"""
        self.errors = []
        return len(self.errors) == 0

    def get_value(self) -> Any:
        """Get the current value of the widget"""
        return self.value

    def set_value(self, value: Any) -> None:
        """Set the value of the widget"""
        self.value = value

    def add_error(self, error: str) -> None:
        """Add an error message"""
        self.errors.append(error)

    def clear_errors(self) -> None:
        """Clear all error messages"""
        self.errors = []

    def is_valid(self) -> bool:
        """Check if the widget is in a valid state"""
        return len(self.errors) == 0

    def get_css_classes(self) -> str:
        """Get CSS classes for the widget"""
        classes = [
            f"widget-{self.widget_type.value}",
            f"widget-theme-{self.config.theme.value}",
            f"widget-size-{self.config.size.value}",
        ]

        if self.config.disabled:
            classes.append("widget-disabled")
        if self.config.readonly:
            classes.append("widget-readonly")
        if self.config.required:
            classes.append("widget-required")
        if self.errors:
            classes.append("widget-error")

        classes.extend(self.config.classes)
        return " ".join(classes)

    def get_attributes(self) -> Dict[str, Any]:
        """Get HTML attributes for the widget"""
        attrs = {
            'id': self.id,
            'name': self.name,
            'class': self.get_css_classes(),
        }

        if self.config.disabled:
            attrs['disabled'] = 'disabled'
        if self.config.readonly:
            attrs['readonly'] = 'readonly'
        if self.config.required:
            attrs['required'] = 'required'
        if self.config.placeholder:
            attrs['placeholder'] = self.config.placeholder

        attrs.update(self.config.attributes)
        return attrs

    def to_dict(self) -> Dict[str, Any]:
        """Convert widget to dictionary representation"""
        return {
            'id': self.id,
            'name': self.name,
            'type': self.widget_type.value,
            'value': self.value,
            'config': {
                'theme': self.config.theme.value,
                'size': self.config.size.value,
                'disabled': self.config.disabled,
                'readonly': self.config.readonly,
                'required': self.config.required,
                'placeholder': self.config.placeholder,
                'help_text': self.config.help_text,
                'classes': self.config.classes,
                'attributes': self.config.attributes,
            },
            'errors': self.errors,
            'dependencies': self.dependencies,
        }

    @property
    def widget_type(self) -> WidgetType:
        """Get the widget type"""
        return WidgetType.INPUT


class Widget(BaseWidget):
    """Basic widget class with common functionality"""

    def __init__(self, name: str, config: Optional[WidgetConfig] = None, **kwargs):
        super().__init__(name, config, **kwargs)
        self.label = kwargs.get('label', self._generate_label(name))

    def _generate_label(self, name: str) -> str:
        """Generate a human-readable label from the widget name"""
        return name.replace('_', ' ').title()

    def render_label(self) -> str:
        """Render the widget label"""
        if not self.label:
            return ""

        attrs = {
            'for': self.id,
            'class': 'widget-label'
        }

        if self.config.required:
            attrs['class'] += ' required'

        attr_str = ' '.join(f'{k}="{v}"' for k, v in attrs.items())
        return f'<label {attr_str}>{self.label}</label>'

    def render_help_text(self) -> str:
        """Render help text"""
        if not self.config.help_text:
            return ""
        return f'<div class="widget-help">{self.config.help_text}</div>'

    def render_errors(self) -> str:
        """Render error messages"""
        if not self.errors:
            return ""
        errors_html = '\n'.join(f'<li>{error}</li>' for error in self.errors)
        return f'<ul class="widget-errors">{errors_html}</ul>'

    def render_wrapper(self, content: str) -> str:
        """Render the widget wrapper with label, content, help, and errors"""
        wrapper_classes = ['widget-wrapper', f"widget-{self.widget_type.value}"]
        if self.errors:
            wrapper_classes.append('has-errors')

        wrapper_attrs = {
            'class': ' '.join(wrapper_classes),
            'data-widget-type': self.widget_type.value,
            'data-widget-name': self.name
        }

        wrapper_attr_str = ' '.join(f'{k}="{v}"' for k, v in wrapper_attrs.items())

        return f'''
<div {wrapper_attr_str}>
    {self.render_label()}
    {content}
    {self.render_help_text()}
    {self.render_errors()}
</div>'''


# Date and Time Widgets
class RichDateTime(Widget):
    """Advanced date and time picker widget"""

    def __init__(self, name: str, config: Optional[WidgetConfig] = None, **kwargs):
        super().__init__(name, config, **kwargs)
        self.date_format = kwargs.get('date_format', 'YYYY-MM-DD')
        self.time_format = kwargs.get('time_format', 'HH:mm:ss')
        self.show_date = kwargs.get('show_date', True)
        self.show_time = kwargs.get('show_time', True)
        self.show_seconds = kwargs.get('show_seconds', True)
        self.min_date = kwargs.get('min_date')
        self.max_date = kwargs.get('max_date')
        self.timezone = kwargs.get('timezone', 'UTC')
        self.locale = kwargs.get('locale', 'en')
        self.dependencies = ['datetime-picker.js', 'datetime-picker.css']

    @property
    def widget_type(self) -> WidgetType:
        return WidgetType.INPUT

    def render(self) -> str:
        """Render the datetime picker"""
        attrs = self.get_attributes()
        attrs.update({
            'type': 'text',
            'data-datetime-picker': 'true',
            'data-date-format': self.date_format,
            'data-time-format': self.time_format,
            'data-show-date': str(self.show_date).lower(),
            'data-show-time': str(self.show_time).lower(),
            'data-show-seconds': str(self.show_seconds).lower(),
            'data-timezone': self.timezone,
            'data-locale': self.locale,
        })

        if self.min_date:
            attrs['data-min-date'] = self.min_date
        if self.max_date:
            attrs['data-max-date'] = self.max_date
        if self.value:
            if isinstance(self.value, datetime):
                attrs['value'] = self.value.strftime(f"{self.date_format} {self.time_format}")
            elif isinstance(self.value, date):
                attrs['value'] = self.value.strftime(self.date_format)
            elif isinstance(self.value, time):
                attrs['value'] = self.value.strftime(self.time_format)
            else:
                attrs['value'] = str(self.value)

        attr_str = ' '.join(f'{k}="{v}"' for k, v in attrs.items())
        input_html = f'<input {attr_str}>'

        # Add calendar and clock icons
        icons_html = '''
        <div class="datetime-icons">
            <span class="datetime-calendar-icon" title="Select Date">📅</span>
            <span class="datetime-clock-icon" title="Select Time">🕐</span>
        </div>
        '''

        content = f'<div class="datetime-input-wrapper">{input_html}{icons_html}</div>'
        return self.render_wrapper(content)


class RichDate(Widget):
    """Advanced date picker widget"""

    def __init__(self, name: str, config: Optional[WidgetConfig] = None, **kwargs):
        super().__init__(name, config, **kwargs)
        self.date_format = kwargs.get('date_format', 'YYYY-MM-DD')
        self.min_date = kwargs.get('min_date')
        self.max_date = kwargs.get('max_date')
        self.locale = kwargs.get('locale', 'en')
        self.dependencies = ['date-picker.js', 'date-picker.css']

    @property
    def widget_type(self) -> WidgetType:
        return WidgetType.INPUT

    def render(self) -> str:
        """Render the date picker"""
        attrs = self.get_attributes()
        attrs.update({
            'type': 'date',
            'data-date-picker': 'true',
            'data-date-format': self.date_format,
            'data-locale': self.locale,
        })

        if self.min_date:
            attrs['min'] = self.min_date
        if self.max_date:
            attrs['max'] = self.max_date
        if self.value:
            if isinstance(self.value, (datetime, date)):
                attrs['value'] = self.value.strftime('%Y-%m-%d')
            else:
                attrs['value'] = str(self.value)

        attr_str = ' '.join(f'{k}="{v}"' for k, v in attrs.items())
        input_html = f'<input {attr_str}>'

        icon_html = '<span class="date-calendar-icon" title="Select Date">📅</span>'
        content = f'<div class="date-input-wrapper">{input_html}{icon_html}</div>'
        return self.render_wrapper(content)


class RichTime(Widget):
    """Advanced time picker widget"""

    def __init__(self, name: str, config: Optional[WidgetConfig] = None, **kwargs):
        super().__init__(name, config, **kwargs)
        self.time_format = kwargs.get('time_format', 'HH:mm')
        self.show_seconds = kwargs.get('show_seconds', False)
        self.step = kwargs.get('step', 60)  # Step in seconds
        self.dependencies = ['time-picker.js', 'time-picker.css']

    @property
    def widget_type(self) -> WidgetType:
        return WidgetType.INPUT

    def render(self) -> str:
        """Render the time picker"""
        attrs = self.get_attributes()
        attrs.update({
            'type': 'time',
            'data-time-picker': 'true',
            'data-time-format': self.time_format,
            'data-show-seconds': str(self.show_seconds).lower(),
            'step': str(self.step),
        })

        if self.value:
            if isinstance(self.value, (datetime, time)):
                format_str = '%H:%M:%S' if self.show_seconds else '%H:%M'
                attrs['value'] = self.value.strftime(format_str)
            else:
                attrs['value'] = str(self.value)

        attr_str = ' '.join(f'{k}="{v}"' for k, v in attrs.items())
        input_html = f'<input {attr_str}>'

        icon_html = '<span class="time-clock-icon" title="Select Time">🕐</span>'
        content = f'<div class="time-input-wrapper">{input_html}{icon_html}</div>'
        return self.render_wrapper(content)


# File Management Widgets
class RichFile(Widget):
    """Advanced file upload and management widget"""

    def __init__(self, name: str, config: Optional[WidgetConfig] = None, **kwargs):
        super().__init__(name, config, **kwargs)
        self.multiple = kwargs.get('multiple', False)
        self.accept = kwargs.get('accept', '*/*')
        self.max_size = kwargs.get('max_size', 10 * 1024 * 1024)  # 10MB default
        self.max_files = kwargs.get('max_files', 5)
        self.allowed_types = kwargs.get('allowed_types', [])
        self.show_preview = kwargs.get('show_preview', True)
        self.allow_drag_drop = kwargs.get('allow_drag_drop', True)
        self.auto_upload = kwargs.get('auto_upload', False)
        self.chunk_size = kwargs.get('chunk_size', 1024 * 1024)  # 1MB chunks
        self.upload_url = kwargs.get('upload_url', '/upload')
        self.dependencies = ['file-uploader.js', 'file-uploader.css']

    @property
    def widget_type(self) -> WidgetType:
        return WidgetType.MEDIA

    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} GB"

    def render(self) -> str:
        """Render the file uploader"""
        attrs = self.get_attributes()
        attrs.update({
            'type': 'file',
            'data-file-uploader': 'true',
            'data-max-size': str(self.max_size),
            'data-max-files': str(self.max_files),
            'data-show-preview': str(self.show_preview).lower(),
            'data-drag-drop': str(self.allow_drag_drop).lower(),
            'data-auto-upload': str(self.auto_upload).lower(),
            'data-chunk-size': str(self.chunk_size),
            'data-upload-url': self.upload_url,
        })

        if self.multiple:
            attrs['multiple'] = 'multiple'
        if self.accept != '*/*':
            attrs['accept'] = self.accept

        attr_str = ' '.join(f'{k}="{v}"' for k, v in attrs.items())
        input_html = f'<input {attr_str}>'

        # File drop zone
        drop_zone = f'''
        <div class="file-drop-zone" data-drop-zone="true">
            <div class="file-drop-content">
                <div class="file-drop-icon">📁</div>
                <div class="file-drop-text">
                    Drag & drop files here or click to browse
                </div>
                <div class="file-drop-hint">
                    Max {self.max_files} files, up to {self._format_file_size(self.max_size)} each
                </div>
            </div>
        </div>
        '''

        # File list
        file_list = '<div class="file-list" data-file-list="true"></div>'

        # Progress bar
        progress = '<div class="upload-progress" data-upload-progress="true" style="display: none;"><div class="progress-bar"></div></div>'

        content = f'''
        <div class="file-uploader-wrapper">
            {input_html}
            {drop_zone}
            {file_list}
            {progress}
        </div>
        '''

        return self.render_wrapper(content)


class RichFileManager(Widget):
    """File management widget with browse, upload, delete capabilities"""

    def __init__(self, name: str, config: Optional[WidgetConfig] = None, **kwargs):
        super().__init__(name, config, **kwargs)
        self.root_path = kwargs.get('root_path', '/')
        self.allowed_extensions = kwargs.get('allowed_extensions', [])
        self.show_hidden = kwargs.get('show_hidden', False)
        self.enable_upload = kwargs.get('enable_upload', True)
        self.enable_delete = kwargs.get('enable_delete', True)
        self.enable_rename = kwargs.get('enable_rename', True)
        self.enable_create_folder = kwargs.get('enable_create_folder', True)
        self.view_mode = kwargs.get('view_mode', 'list')  # list, grid, tree
        self.dependencies = ['file-manager.js', 'file-manager.css']

    @property
    def widget_type(self) -> WidgetType:
        return WidgetType.MEDIA

    def render(self) -> str:
        """Render the file manager"""
        attrs = self.get_attributes()
        attrs.update({
            'data-file-manager': 'true',
            'data-root-path': self.root_path,
            'data-view-mode': self.view_mode,
            'data-show-hidden': str(self.show_hidden).lower(),
            'data-enable-upload': str(self.enable_upload).lower(),
            'data-enable-delete': str(self.enable_delete).lower(),
            'data-enable-rename': str(self.enable_rename).lower(),
            'data-enable-create-folder': str(self.enable_create_folder).lower(),
        })

        if self.allowed_extensions:
            attrs['data-allowed-extensions'] = ','.join(self.allowed_extensions)

        attr_str = ' '.join(f'{k}="{v}"' for k, v in attrs.items())

        # Toolbar
        toolbar = f'''
        <div class="file-manager-toolbar">
            <button type="button" class="btn-upload" data-upload-btn="true" {'disabled' if not self.enable_upload else ''}>
                📤 Upload
            </button>
            <button type="button" class="btn-create-folder" data-create-folder-btn="true" {'disabled' if not self.enable_create_folder else ''}>
                📁 New Folder
            </button>
            <div class="view-toggle">
                <button type="button" class="btn-view-list" data-view-list="true">📋</button>
                <button type="button" class="btn-view-grid" data-view-grid="true">⊞</button>
                <button type="button" class="btn-view-tree" data-view-tree="true">🌳</button>
            </div>
        </div>
        '''

        # Breadcrumb navigation
        breadcrumb = '<div class="file-manager-breadcrumb" data-breadcrumb="true"></div>'

        # File container
        container = f'<div class="file-manager-container {self.view_mode}-view" data-file-container="true"></div>'

        # Context menu (hidden by default)
        context_menu = f'''
        <div class="file-context-menu" data-context-menu="true" style="display: none;">
            <div class="context-menu-item" data-action="download">📥 Download</div>
            <div class="context-menu-item" data-action="rename" {'style="display: none;"' if not self.enable_rename else ''}>✏️ Rename</div>
            <div class="context-menu-item" data-action="delete" {'style="display: none;"' if not self.enable_delete else ''}>🗑️ Delete</div>
            <div class="context-menu-item" data-action="properties">ℹ️ Properties</div>
        </div>
        '''

        content = f'''
        <div class="file-manager-wrapper" {attr_str}>
            {toolbar}
            {breadcrumb}
            {container}
            {context_menu}
        </div>
        '''

        return self.render_wrapper(content)


# Commerce Widgets
class RichPrice(Widget):
    """Price input widget with currency support"""

    def __init__(self, name: str, config: Optional[WidgetConfig] = None, **kwargs):
        super().__init__(name, config, **kwargs)
        self.currency = kwargs.get('currency', 'USD')
        self.currency_symbol = kwargs.get('currency_symbol', '$')
        self.currency_position = kwargs.get('currency_position', 'before')  # before, after
        self.decimals = kwargs.get('decimals', 2)
        self.min_value = kwargs.get('min_value', 0)
        self.max_value = kwargs.get('max_value')
        self.step = kwargs.get('step', 0.01)
        self.dependencies = ['price-input.js', 'price-input.css']

    @property
    def widget_type(self) -> WidgetType:
        return WidgetType.COMMERCE

    def render(self) -> str:
        """Render the price input"""
        attrs = self.get_attributes()
        attrs.update({
            'type': 'number',
            'data-price-input': 'true',
            'data-currency': self.currency,
            'data-currency-symbol': self.currency_symbol,
            'data-currency-position': self.currency_position,
            'data-decimals': str(self.decimals),
            'min': str(self.min_value),
            'step': str(self.step),
        })

        if self.max_value is not None:
            attrs['max'] = str(self.max_value)
        if self.value is not None:
            attrs['value'] = str(self.value)

        attr_str = ' '.join(f'{k}="{v}"' for k, v in attrs.items())
        input_html = f'<input {attr_str}>'

        # Currency display
        currency_display = f'<span class="price-currency">{self.currency_symbol}</span>'

        if self.currency_position == 'before':
            content = f'<div class="price-input-wrapper">{currency_display}{input_html}</div>'
        else:
            content = f'<div class="price-input-wrapper">{input_html}{currency_display}</div>'

        return self.render_wrapper(content)


class RichQuantity(Widget):
    """Quantity selector widget with increment/decrement buttons"""

    def __init__(self, name: str, config: Optional[WidgetConfig] = None, **kwargs):
        super().__init__(name, config, **kwargs)
        self.min_value = kwargs.get('min_value', 1)
        self.max_value = kwargs.get('max_value', 999)
        self.step = kwargs.get('step', 1)
        self.show_buttons = kwargs.get('show_buttons', True)
        self.button_labels = kwargs.get('button_labels', {'minus': '−', 'plus': '+'})
        self.dependencies = ['quantity-selector.js', 'quantity-selector.css']

    @property
    def widget_type(self) -> WidgetType:
        return WidgetType.COMMERCE

    def render(self) -> str:
        """Render the quantity selector"""
        attrs = self.get_attributes()
        attrs.update({
            'type': 'number',
            'data-quantity-selector': 'true',
            'min': str(self.min_value),
            'max': str(self.max_value),
            'step': str(self.step),
        })

        if self.value is not None:
            attrs['value'] = str(self.value)
        else:
            attrs['value'] = str(self.min_value)

        attr_str = ' '.join(f'{k}="{v}"' for k, v in attrs.items())
        input_html = f'<input {attr_str}>'

        if self.show_buttons:
            minus_btn = f'<button type="button" class="quantity-btn quantity-minus" data-quantity-minus="true">{self.button_labels["minus"]}</button>'
            plus_btn = f'<button type="button" class="quantity-btn quantity-plus" data-quantity-plus="true">{self.button_labels["plus"]}</button>'
            content = f'<div class="quantity-wrapper">{minus_btn}{input_html}{plus_btn}</div>'
        else:
            content = input_html

        return self.render_wrapper(content)


class RichProductCard(Widget):
    """Product card widget for e-commerce"""

    def __init__(self, name: str, config: Optional[WidgetConfig] = None, **kwargs):
        super().__init__(name, config, **kwargs)
        self.product_id = kwargs.get('product_id')
        self.title = kwargs.get('title', '')
        self.description = kwargs.get('description', '')
        self.price = kwargs.get('price', 0)
        self.original_price = kwargs.get('original_price')
        self.currency = kwargs.get('currency', 'USD')
        self.currency_symbol = kwargs.get('currency_symbol', '$')
        self.image_url = kwargs.get('image_url')
        self.images = kwargs.get('images', [])
        self.in_stock = kwargs.get('in_stock', True)
        self.stock_quantity = kwargs.get('stock_quantity')
        self.rating = kwargs.get('rating', 0)
        self.review_count = kwargs.get('review_count', 0)
        self.badges = kwargs.get('badges', [])  # ['sale', 'new', 'featured']
        self.show_add_to_cart = kwargs.get('show_add_to_cart', True)
        self.show_wishlist = kwargs.get('show_wishlist', True)
        self.show_quick_view = kwargs.get('show_quick_view', True)
        self.dependencies = ['product-card.js', 'product-card.css']

    @property
    def widget_type(self) -> WidgetType:
        return WidgetType.COMMERCE

    def render(self) -> str:
        """Render the product card"""
        attrs = self.get_attributes()
        attrs.update({
            'data-product-card': 'true',
            'data-product-id': str(self.product_id) if self.product_id else '',
        })

        attr_str = ' '.join(f'{k}="{v}"' for k, v in attrs.items())

        # Badges
        badges_html = ''
        if self.badges:
            badges_html = '<div class="product-badges">'
            for badge in self.badges:
                badge_class = f'badge-{badge.lower()}'
                badges_html += f'<span class="product-badge {badge_class}">{badge.title()}</span>'
            badges_html += '</div>'

        # Image
        image_html = ''
        if self.image_url:
            image_html = f'<img src="{self.image_url}" alt="{self.title}" class="product-image" loading="lazy">'
        elif self.images:
            image_html = f'<img src="{self.images[0]}" alt="{self.title}" class="product-image" loading="lazy">'

        # Title and description
        title_html = f'<h3 class="product-title">{self.title}</h3>'
        desc_html = f'<p class="product-description">{self.description}</p>' if self.description else ''

        # Price
        price_html = f'<div class="product-price">{self.currency_symbol}{self.price:.2f}</div>'
        if self.original_price and self.original_price > self.price:
            discount = ((self.original_price - self.price) / self.original_price) * 100
            price_html = f'''
            <div class="product-price">
                <span class="current-price">{self.currency_symbol}{self.price:.2f}</span>
                <span class="original-price">{self.currency_symbol}{self.original_price:.2f}</span>
                <span class="discount">-{discount:.0f}%</span>
            </div>
            '''

        # Rating
        rating_html = ''
        if self.rating > 0:
            stars = '⭐' * int(self.rating) + '☆' * (5 - int(self.rating))
            rating_html = f'<div class="product-rating">{stars} ({self.review_count})</div>'

        # Stock status
        stock_html = ''
        if not self.in_stock:
            stock_html = '<div class="product-stock out-of-stock">Out of Stock</div>'
        elif self.stock_quantity is not None and self.stock_quantity < 10:
            stock_html = f'<div class="product-stock low-stock">Only {self.stock_quantity} left</div>'

        # Action buttons
        buttons_html = '<div class="product-actions">'
        if self.show_add_to_cart:
            buttons_html += '<button type="button" class="btn-add-to-cart" data-add-to-cart="true">Add to Cart</button>'
        if self.show_wishlist:
            buttons_html += '<button type="button" class="btn-wishlist" data-wishlist="true">❤️</button>'
        if self.show_quick_view:
            buttons_html += '<button type="button" class="btn-quick-view" data-quick-view="true">👁️ Quick View</button>'
        buttons_html += '</div>'

        content = f'''
        <div class="product-card" {attr_str}>
            {badges_html}
            <div class="product-image-container">
                {image_html}
            </div>
            <div class="product-info">
                {title_html}
                {desc_html}
                {price_html}
                {rating_html}
                {stock_html}
                {buttons_html}
            </div>
        </div>
        '''

        return content  # Product cards don't need the standard wrapper


class RichShoppingCart(Widget):
    """Shopping cart widget"""

    def __init__(self, name: str, config: Optional[WidgetConfig] = None, **kwargs):
        super().__init__(name, config, **kwargs)
        self.items = kwargs.get('items', [])  # List of cart items
        self.currency = kwargs.get('currency', 'USD')
        self.currency_symbol = kwargs.get('currency_symbol', '$')
        self.show_subtotal = kwargs.get('show_subtotal', True)
        self.show_tax = kwargs.get('show_tax', True)
        self.show_shipping = kwargs.get('show_shipping', True)
        self.tax_rate = kwargs.get('tax_rate', 0.08)  # 8% default
        self.shipping_cost = kwargs.get('shipping_cost', 0)
        self.free_shipping_threshold = kwargs.get('free_shipping_threshold')
        self.allow_quantity_edit = kwargs.get('allow_quantity_edit', True)
        self.allow_item_removal = kwargs.get('allow_item_removal', True)
        self.checkout_url = kwargs.get('checkout_url', '/checkout')
        self.dependencies = ['shopping-cart.js', 'shopping-cart.css']

    @property
    def widget_type(self) -> WidgetType:
        return WidgetType.COMMERCE

    def get_subtotal(self) -> float:
        """Calculate subtotal"""
        return sum(item.get('price', 0) * item.get('quantity', 1) for item in self.items)

    def get_tax(self) -> float:
        """Calculate tax"""
        return self.get_subtotal() * self.tax_rate

    def get_shipping(self) -> float:
        """Calculate shipping cost"""
        if self.free_shipping_threshold and self.get_subtotal() >= self.free_shipping_threshold:
            return 0
        return self.shipping_cost

    def get_total(self) -> float:
        """Calculate total"""
        return self.get_subtotal() + self.get_tax() + self.get_shipping()

    def render(self) -> str:
        """Render the shopping cart"""
        attrs = self.get_attributes()
        attrs.update({
            'data-shopping-cart': 'true',
            'data-currency': self.currency,
            'data-currency-symbol': self.currency_symbol,
            'data-checkout-url': self.checkout_url,
        })

        attr_str = ' '.join(f'{k}="{v}"' for k, v in attrs.items())

        # Cart header
        header = f'''
        <div class="cart-header">
            <h3>Shopping Cart ({len(self.items)} items)</h3>
            <button type="button" class="btn-clear-cart" data-clear-cart="true">Clear All</button>
        </div>
        '''

        # Cart items
        items_html = '<div class="cart-items">'
        for i, item in enumerate(self.items):
            item_attrs = {
                'data-cart-item': 'true',
                'data-item-id': str(item.get('id', i)),
                'data-item-price': str(item.get('price', 0)),
            }
            item_attr_str = ' '.join(f'{k}="{v}"' for k, v in item_attrs.items())

            quantity_controls = ''
            if self.allow_quantity_edit:
                quantity_controls = f'''
                <div class="quantity-controls">
                    <button type="button" class="btn-quantity-minus" data-quantity-minus="true">−</button>
                    <input type="number" class="item-quantity" value="{item.get('quantity', 1)}" min="1" max="99">
                    <button type="button" class="btn-quantity-plus" data-quantity-plus="true">+</button>
                </div>
                '''
            else:
                quantity_controls = f'<span class="item-quantity-display">Qty: {item.get('quantity', 1)}</span>'

            remove_btn = ''
            if self.allow_item_removal:
                remove_btn = '<button type="button" class="btn-remove-item" data-remove-item="true">🗑️</button>'

            items_html += f'''
            <div class="cart-item" {item_attr_str}>
                <img src="{item.get('image', '')}" alt="{item.get('name', '')}" class="item-image">
                <div class="item-details">
                    <h4 class="item-name">{item.get('name', '')}</h4>
                    <div class="item-price">{self.currency_symbol}{item.get('price', 0):.2f}</div>
                    {quantity_controls}
                </div>
                <div class="item-total">{self.currency_symbol}{item.get('price', 0) * item.get('quantity', 1):.2f}</div>
                {remove_btn}
            </div>
            '''
        items_html += '</div>'

        # Cart summary
        summary_html = '<div class="cart-summary">'
        if self.show_subtotal:
            summary_html += f'<div class="summary-row"><span>Subtotal:</span><span>{self.currency_symbol}{self.get_subtotal():.2f}</span></div>'
        if self.show_tax:
            summary_html += f'<div class="summary-row"><span>Tax:</span><span>{self.currency_symbol}{self.get_tax():.2f}</span></div>'
        if self.show_shipping:
            shipping_text = "FREE" if self.get_shipping() == 0 else f"{self.currency_symbol}{self.get_shipping():.2f}"
            summary_html += f'<div class="summary-row"><span>Shipping:</span><span>{shipping_text}</span></div>'

        summary_html += f'<div class="summary-row total-row"><span>Total:</span><span>{self.currency_symbol}{self.get_total():.2f}</span></div>'
        summary_html += '</div>'

        # Checkout button
        checkout_btn = f'<button type="button" class="btn-checkout" data-checkout="true">Proceed to Checkout</button>'

        content = f'''
        <div class="shopping-cart" {attr_str}>
            {header}
            {items_html}
            {summary_html}
            <div class="cart-footer">
                {checkout_btn}
            </div>
        </div>
        '''

        return self.render_wrapper(content)


# Rich Text and Enhanced Widgets
class RichText(Widget):
    """Rich text editor widget"""

    def __init__(self, name: str, config: Optional[WidgetConfig] = None, **kwargs):
        super().__init__(name, config, **kwargs)
        self.format = kwargs.get('format', 'html')  # html, markdown
        self.toolbar = kwargs.get('toolbar', 'full')  # full, basic, minimal
        self.max_length = kwargs.get('max_length', 10000)
        self.min_length = kwargs.get('min_length', 0)
        self.placeholder = kwargs.get('placeholder', 'Enter your text here...')
        self.autosave = kwargs.get('autosave', False)
        self.word_count = kwargs.get('word_count', True)
        self.dependencies = ['rich-text-editor.js', 'rich-text-editor.css']

    @property
    def widget_type(self) -> WidgetType:
        return WidgetType.INPUT

    def render(self) -> str:
        """Render the rich text editor"""
        attrs = self.get_attributes()
        attrs.update({
            'data-rich-text': 'true',
            'data-format': self.format,
            'data-toolbar': self.toolbar,
            'data-max-length': str(self.max_length),
            'data-min-length': str(self.min_length),
            'data-autosave': str(self.autosave).lower(),
            'data-word-count': str(self.word_count).lower(),
            'contenteditable': 'true',
        })

        if self.value:
            content = str(self.value)
        else:
            content = f'<p>{self.placeholder}</p>' if self.placeholder else '<p><br></p>'

        attr_str = ' '.join(f'{k}="{v}"' for k, v in attrs.items())

        # Toolbar
        toolbar_html = self._render_toolbar()

        # Editor
        editor_html = f'<div {attr_str}>{content}</div>'

        # Word count
        word_count_html = '<div class="word-count" data-word-count="true">0 words</div>' if self.word_count else ''

        content = f'''
        <div class="rich-text-wrapper">
            {toolbar_html}
            {editor_html}
            {word_count_html}
        </div>
        '''

        return self.render_wrapper(content)

    def _render_toolbar(self) -> str:
        """Render the editor toolbar"""
        if self.toolbar == 'minimal':
            buttons = ['bold', 'italic', 'underline']
        elif self.toolbar == 'basic':
            buttons = ['bold', 'italic', 'underline', 'bullet-list', 'numbered-list', 'link']
        else:  # full
            buttons = [
                'bold', 'italic', 'underline', 'strikethrough',
                'bullet-list', 'numbered-list', 'blockquote',
                'link', 'image', 'code', 'heading1', 'heading2', 'heading3'
            ]

        button_html = ''
        for button in buttons:
            button_class = f'btn-{button.replace("_", "-")}'
            button_html += f'<button type="button" class="toolbar-btn {button_class}" data-cmd="{button}" title="{button.title()}">{self._get_button_icon(button)}</button>'

        return f'<div class="rich-text-toolbar">{button_html}</div>'

    def _get_button_icon(self, button: str) -> str:
        """Get icon for toolbar button"""
        icons = {
            'bold': '𝐁',
            'italic': '𝐼',
            'underline': 'U̲',
            'strikethrough': 'S̶',
            'bullet-list': '•',
            'numbered-list': '1.',
            'blockquote': '"',
            'link': '🔗',
            'image': '🖼️',
            'code': '</>',
            'heading1': 'H1',
            'heading2': 'H2',
            'heading3': 'H3',
        }
        return icons.get(button, button)


class RichSelect(Widget):
    """Enhanced select widget with search and multi-select"""

    def __init__(self, name: str, config: Optional[WidgetConfig] = None, **kwargs):
        super().__init__(name, config, **kwargs)
        self.options = kwargs.get('options', [])
        self.searchable = kwargs.get('searchable', False)
        self.allow_multiple = kwargs.get('allow_multiple', False)
        self.max_selections = kwargs.get('max_selections')
        self.allow_custom = kwargs.get('allow_custom', False)
        self.placeholder = kwargs.get('placeholder', 'Select an option...')
        self.groups = kwargs.get('groups', {})  # Option groups
        self.dependencies = ['rich-select.js', 'rich-select.css']

    @property
    def widget_type(self) -> WidgetType:
        return WidgetType.INPUT

    def add_group(self, name: str, options: List) -> None:
        """Add an option group"""
        self.groups[name] = options

    def render(self) -> str:
        """Render the rich select widget"""
        attrs = self.get_attributes()
        attrs.update({
            'data-rich-select': 'true',
            'data-searchable': str(self.searchable).lower(),
            'data-multiple': str(self.allow_multiple).lower(),
            'data-allow-custom': str(self.allow_custom).lower(),
        })

        if self.max_selections:
            attrs['data-max-selections'] = str(self.max_selections)

        attr_str = ' '.join(f'{k}="{v}"' for k, v in attrs.items())

        # Hidden select for form submission
        select_html = f'<select {attr_str} style="display: none;">'
        for option in self.options:
            if isinstance(option, tuple):
                value, label = option
            else:
                value = label = option
            selected = 'selected' if self.value and str(value) in [str(v) for v in (self.value if isinstance(self.value, list) else [self.value])] else ''
            select_html += f'<option value="{value}" {selected}>{label}</option>'
        select_html += '</select>'

        # Custom dropdown display
        display_html = f'''
        <div class="rich-select-display" data-select-display="true">
            <div class="selected-values" data-selected-values="true">
                {self.placeholder}
            </div>
            <span class="select-arrow">▼</span>
        </div>
        '''

        # Dropdown options
        options_html = '<div class="select-dropdown" data-select-dropdown="true" style="display: none;">'
        if self.searchable:
            options_html += f'<input type="text" class="select-search" placeholder="Search..." data-select-search="true">'

        for option in self.options:
            if isinstance(option, tuple):
                value, label = option
            else:
                value = label = option
            selected = 'selected' if self.value and str(value) in [str(v) for v in (self.value if isinstance(self.value, list) else [self.value])] else ''
            options_html += f'<div class="select-option {selected}" data-value="{value}" data-select-option="true">{label}</div>'

        options_html += '</div>'

        content = f'''
        <div class="rich-select-wrapper">
            {select_html}
            {display_html}
            {options_html}
        </div>
        '''

        return self.render_wrapper(content)

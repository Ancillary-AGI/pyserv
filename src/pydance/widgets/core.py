"""
Pydance Widgets Core - Enhanced Widget System
=============================================

Advanced widget architecture with enhanced security, customization, and features.
"""

import re
import hashlib
import secrets
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import json

import markdown
import bleach
from bs4 import BeautifulSoup


class WidgetType(Enum):
    """Enhanced widget type enumeration"""
    TEXT = "text"
    PASSWORD = "password"
    EMAIL = "email"
    URL = "url"
    NUMBER = "number"
    TEXTAREA = "textarea"
    SELECT = "select"
    MULTISELECT = "multiselect"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    FILE = "file"
    HIDDEN = "hidden"
    RICHTEXT = "richtext"
    RICHTITLE = "richtitle"
    RICHSELECT = "richselect"
    RICHDATE = "richdate"
    RICHCOLOR = "richcolor"
    RICHRATING = "richrating"
    RICHTAGS = "richtags"
    RICHSLIDER = "richslider"
    RICHCODE = "richcode"
    RICHTABLE = "richtable"
    RICHMULTIMEDIA = "richmultimedia"


class ContentFormat(Enum):
    """Enhanced content format for rich widgets"""
    HTML = "html"
    MARKDOWN = "markdown"
    PLAIN = "plain"
    JSON = "json"
    XML = "xml"


class WidgetTheme(Enum):
    """Widget theme options"""
    DEFAULT = "default"
    DARK = "dark"
    LIGHT = "light"
    BLUE = "blue"
    GREEN = "green"
    PURPLE = "purple"
    CUSTOM = "custom"


class WidgetSize(Enum):
    """Widget size options"""
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    EXTRA_LARGE = "extra-large"


@dataclass
class WidgetAttributes:
    """Enhanced widget HTML attributes with security"""
    id: Optional[str] = None
    name: str = ""
    value: Any = ""
    placeholder: Optional[str] = None
    required: bool = False
    disabled: bool = False
    readonly: bool = False
    maxlength: Optional[int] = None
    minlength: Optional[int] = None
    pattern: Optional[str] = None
    autocomplete: Optional[str] = None
    classes: List[str] = field(default_factory=list)
    styles: Dict[str, str] = field(default_factory=dict)
    data_attributes: Dict[str, str] = field(default_factory=dict)
    aria_label: Optional[str] = None
    aria_describedby: Optional[str] = None
    tabindex: Optional[int] = None
    role: Optional[str] = None
    # Security attributes
    nonce: Optional[str] = None
    csp_hash: Optional[str] = None


class WidgetSecurity:
    """Enhanced security utilities for widgets"""

    # Comprehensive allowed HTML tags
    ALLOWED_TAGS = [
        # Basic formatting
        'p', 'br', 'div', 'span', 'strong', 'em', 'u', 'b', 'i',
        # Headings
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        # Lists
        'ul', 'ol', 'li', 'dl', 'dt', 'dd',
        # Links and media
        'a', 'img', 'figure', 'figcaption', 'picture', 'source',
        # Tables
        'table', 'thead', 'tbody', 'tfoot', 'tr', 'th', 'td', 'caption', 'col', 'colgroup',
        # Code
        'code', 'pre', 'kbd', 'samp', 'var', 'blockquote', 'cite', 'q',
        # Semantic elements
        'article', 'section', 'aside', 'header', 'footer', 'nav', 'main',
        'mark', 'time', 'address', 'abbr', 'dfn', 'small', 'sub', 'sup',
        # Interactive elements (carefully controlled)
        'details', 'summary', 'dialog',
        # Form elements (for rich content)
        'form', 'fieldset', 'legend', 'label', 'input', 'textarea', 'select', 'option', 'optgroup',
        # Media elements
        'audio', 'video', 'track', 'canvas', 'svg',
    ]

    # Comprehensive allowed HTML attributes
    ALLOWED_ATTRIBUTES = {
        # Global attributes
        '*': [
            'class', 'id', 'title', 'lang', 'dir', 'tabindex', 'accesskey',
            'contenteditable', 'spellcheck', 'translate', 'draggable', 'hidden',
            'data-*', 'aria-*', 'role'
        ],
        # Link attributes
        'a': [
            'href', 'title', 'target', 'rel', 'download', 'hreflang', 'type',
            'ping', 'referrerpolicy'
        ],
        # Image attributes
        'img': [
            'src', 'alt', 'title', 'width', 'height', 'loading', 'decoding',
            'crossorigin', 'usemap', 'ismap', 'sizes', 'srcset'
        ],
        # Media attributes
        'audio': ['src', 'controls', 'autoplay', 'loop', 'muted', 'preload', 'volume'],
        'video': ['src', 'controls', 'autoplay', 'loop', 'muted', 'preload', 'poster', 'width', 'height'],
        'source': ['src', 'type', 'media', 'sizes', 'srcset'],
        # Table attributes
        'table': ['border', 'cellpadding', 'cellspacing', 'width', 'height', 'summary'],
        'td': ['colspan', 'rowspan', 'width', 'height', 'headers'],
        'th': ['colspan', 'rowspan', 'width', 'height', 'headers', 'scope', 'abbr'],
        'col': ['span', 'width'],
        'colgroup': ['span', 'width'],
        # Form attributes
        'input': ['type', 'name', 'value', 'placeholder', 'required', 'disabled', 'readonly', 'maxlength', 'minlength', 'pattern', 'autocomplete', 'autofocus', 'multiple', 'accept', 'capture', 'checked', 'min', 'max', 'step', 'size', 'list'],
        'textarea': ['name', 'value', 'placeholder', 'required', 'disabled', 'readonly', 'maxlength', 'minlength', 'rows', 'cols', 'wrap', 'autocomplete', 'autofocus', 'spellcheck'],
        'select': ['name', 'value', 'required', 'disabled', 'multiple', 'size', 'autocomplete', 'autofocus'],
        'option': ['value', 'selected', 'disabled', 'label'],
        'optgroup': ['label', 'disabled'],
        # Time attributes
        'time': ['datetime'],
        # Canvas/SVG (limited for security)
        'canvas': ['width', 'height'],
        'svg': ['width', 'height', 'viewbox', 'xmlns'],
    }

    # Dangerous patterns to block
    DANGEROUS_PATTERNS = [
        # JavaScript injection
        r'javascript:', r'vbscript:', r'data:', r'blob:',
        # Event handlers
        r'on\w+\s*=',
        # Script tags and includes
        r'<script[^>]*>.*?</script>',
        r'<iframe[^>]*>.*?</iframe>',
        r'<object[^>]*>.*?</object>',
        r'<embed[^>]*>.*?</embed>',
        r'<link[^>]*rel\s*=\s*["\']?import["\']?[^>]*>',
        # CSS injection
        r'expression\s*\(',
        r'url\s*\(\s*javascript:',
        # Template injection
        r'\{\{.*?\}\}',
        r'\{\%.*?\%\}',
        # PHP/ASP injection
        r'<\?php', r'<%', r'%>',
        # Base64 encoded scripts (basic detection)
        r'data:text/html;base64,',
        r'data:text/javascript;base64,',
    ]

    @staticmethod
    def sanitize_html(html_content: str, allow_scripts: bool = False) -> str:
        """Enhanced HTML sanitization with comprehensive security"""
        if not html_content:
            return ""

        # Pre-sanitization: remove dangerous patterns
        for pattern in WidgetSecurity.DANGEROUS_PATTERNS:
            html_content = re.sub(pattern, '', html_content, flags=re.IGNORECASE | re.DOTALL)

        # Use bleach for comprehensive sanitization
        sanitized = bleach.clean(
            html_content,
            tags=WidgetSecurity.ALLOWED_TAGS if allow_scripts else [tag for tag in WidgetSecurity.ALLOWED_TAGS if tag not in ['script', 'iframe', 'object', 'embed']],
            attributes=WidgetSecurity.ALLOWED_ATTRIBUTES,
            strip=True,
            strip_comments=True
        )

        # Post-sanitization: additional security checks
        return WidgetSecurity._post_sanitize(sanitized)

    @staticmethod
    def _post_sanitize(html_content: str) -> str:
        """Additional post-sanitization security checks"""
        # Remove any remaining dangerous attributes
        dangerous_attrs = [
            'onload', 'onerror', 'onclick', 'onmouseover', 'onmouseout',
            'onkeydown', 'onkeyup', 'onkeypress', 'onsubmit', 'onreset',
            'onfocus', 'onblur', 'onchange', 'onselect', 'oninput'
        ]

        for attr in dangerous_attrs:
            html_content = re.sub(rf'\s+{attr}\s*=\s*["\'][^"\']*["\']', '', html_content, flags=re.IGNORECASE)

        return html_content

    @staticmethod
    def validate_markdown(markdown_content: str) -> Tuple[bool, List[str]]:
        """Enhanced markdown validation with detailed error reporting"""
        if not markdown_content:
            return True, []

        errors = []
        warnings = []

        # Check for dangerous patterns
        for pattern in WidgetSecurity.DANGEROUS_PATTERNS:
            if re.search(pattern, markdown_content, re.IGNORECASE | re.DOTALL):
                errors.append(f"Dangerous pattern detected: {pattern}")

        # Check for excessively long lines (potential DoS)
        lines = markdown_content.split('\n')
        long_lines = [i for i, line in enumerate(lines) if len(line) > 10000]
        if long_lines:
            warnings.append(f"Very long lines detected at: {long_lines[:5]}")

        # Check for excessive nesting
        if markdown_content.count('[') > 1000 or markdown_content.count('(') > 1000:
            warnings.append("Excessive link/image nesting detected")

        # Check for potential XSS in code blocks
        code_blocks = re.findall(r'```[\s\S]*?```', markdown_content)
        for block in code_blocks:
            if re.search(r'<script|<iframe|<object', block, re.IGNORECASE):
                errors.append("Dangerous content in code block")

        return len(errors) == 0, errors + warnings

    @staticmethod
    def escape_html(text: str) -> str:
        """Enhanced HTML escaping"""
        if not text:
            return ""

        # Use bleach for consistent escaping
        return bleach.clean(text, tags=[], strip=False)

    @staticmethod
    def generate_nonce() -> str:
        """Generate cryptographically secure nonce"""
        return secrets.token_urlsafe(16)

    @staticmethod
    def generate_csp_hash(content: str) -> str:
        """Generate CSP hash for inline scripts/styles"""
        return f"sha256-{hashlib.sha256(content.encode()).hexdigest()}"

    @staticmethod
    def validate_file_upload(file_data: Dict[str, Any], allowed_types: List[str] = None,
                           max_size: int = None) -> Tuple[bool, str]:
        """Validate file upload with comprehensive checks"""
        filename = file_data.get('filename', '')
        content_type = file_data.get('content_type', '')
        size = file_data.get('size', 0)

        # Check file size
        if max_size and size > max_size:
            return False, f"File too large: {size} bytes (max: {max_size})"

        # Check file type
        if allowed_types:
            if not any(content_type.startswith(allowed) for allowed in allowed_types):
                return False, f"Invalid file type: {content_type}"

        # Check filename for dangerous patterns
        dangerous_names = ['..', '/', '\\', '<', '>', ':', '*', '?', '"', '|']
        if any(char in filename for char in dangerous_names):
            return False, "Invalid filename"

        # Check for null bytes
        if '\x00' in filename:
            return False, "Invalid filename (null bytes)"

        return True, "Valid"


class MarkdownProcessor:
    """Enhanced markdown processing with security and features"""

    def __init__(self):
        self.md = markdown.Markdown(extensions=[
            'extra',           # Extra features
            'codehilite',      # Code highlighting
            'toc',            # Table of contents
            'tables',         # Tables support
            'fenced_code',    # Fenced code blocks
            'footnotes',      # Footnotes
            'attr_list',      # Attribute lists
            'def_list',       # Definition lists
            'abbr',          # Abbreviations
            'md_in_html',    # Markdown in HTML
        ])

    def markdown_to_html(self, markdown_content: str, allow_scripts: bool = False) -> str:
        """Convert markdown to HTML with security"""
        if not markdown_content:
            return ""

        # Validate markdown first
        is_valid, messages = WidgetSecurity.validate_markdown(markdown_content)
        if not is_valid:
            raise ValueError(f"Invalid markdown content: {messages}")

        # Convert to HTML
        html = self.md.convert(markdown_content)

        # Sanitize HTML
        return WidgetSecurity.sanitize_html(html, allow_scripts)

    def html_to_markdown(self, html_content: str) -> str:
        """Convert HTML to markdown (enhanced version)"""
        if not html_content:
            return ""

        # Sanitize HTML first
        html_content = WidgetSecurity.sanitize_html(html_content)

        # Use BeautifulSoup for better conversion
        soup = BeautifulSoup(html_content, 'html.parser')

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        # Convert common elements to markdown
        conversions = {
            'strong': lambda el: f"**{el.get_text()}**",
            'em': lambda el: f"*{el.get_text()}*",
            'b': lambda el: f"**{el.get_text()}**",
            'i': lambda el: f"*{el.get_text()}*",
            'code': lambda el: f"`{el.get_text()}`",
            'pre': lambda el: f"```\n{el.get_text()}\n```",
            'blockquote': lambda el: f"> {el.get_text()}",
            'h1': lambda el: f"# {el.get_text()}",
            'h2': lambda el: f"## {el.get_text()}",
            'h3': lambda el: f"### {el.get_text()}",
            'h4': lambda el: f"#### {el.get_text()}",
            'h5': lambda el: f"##### {el.get_text()}",
            'h6': lambda el: f"###### {el.get_text()}",
            'li': lambda el: f"- {el.get_text()}",
        }

        # Process elements
        for tag, converter in conversions.items():
            for element in soup.find_all(tag):
                element.replace_with(converter(element))

        # Handle links
        for a in soup.find_all('a'):
            href = a.get('href', '')
            text = a.get_text()
            if href:
                a.replace_with(f"[{text}]({href})")

        # Handle images
        for img in soup.find_all('img'):
            src = img.get('src', '')
            alt = img.get('alt', '')
            if src:
                img.replace_with(f"![{alt}]({src})")

        return soup.get_text().strip()

    def get_table_of_contents(self, markdown_content: str) -> str:
        """Generate table of contents from markdown"""
        if not markdown_content:
            return ""

        toc_md = markdown.Markdown(extensions=['toc'])
        toc_md.convert(markdown_content)
        return toc_md.toc if hasattr(toc_md, 'toc') else ""


class WidgetValidator:
    """Enhanced validation system for widgets"""

    @staticmethod
    def required(value: Any) -> bool:
        """Check if value is not empty"""
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        return bool(value)

    @staticmethod
    def min_length(value: str, min_len: int) -> bool:
        """Check minimum length"""
        return len(value or "") >= min_len

    @staticmethod
    def max_length(value: str, max_len: int) -> bool:
        """Check maximum length"""
        return len(value or "") <= max_len

    @staticmethod
    def pattern(value: str, pattern: str) -> bool:
        """Check regex pattern"""
        return bool(re.match(pattern, value or ""))

    @staticmethod
    def email(value: str) -> bool:
        """Validate email format"""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, value or ""))

    @staticmethod
    def url(value: str) -> bool:
        """Validate URL format"""
        url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        return bool(re.match(url_pattern, value or ""))

    @staticmethod
    def numeric(value: str) -> bool:
        """Check if value is numeric"""
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False

    @staticmethod
    def range_check(value: Union[int, float], min_val: Optional[float] = None,
                   max_val: Optional[float] = None) -> bool:
        """Check if value is within range"""
        try:
            num_value = float(value)
            if min_val is not None and num_value < min_val:
                return False
            if max_val is not None and num_value > max_val:
                return False
            return True
        except (ValueError, TypeError):
            return False


class BaseWidget(ABC):
    """Enhanced base widget class with advanced features"""

    def __init__(self, name: str, widget_type: WidgetType, **kwargs):
        self.name = name
        self.widget_type = widget_type
        self.attributes = WidgetAttributes(name=name, **kwargs)
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.validators: List[Callable] = []
        self.theme = kwargs.get('theme', WidgetTheme.DEFAULT)
        self.size = kwargs.get('size', WidgetSize.MEDIUM)
        self.custom_css: Dict[str, str] = kwargs.get('custom_css', {})
        self.custom_js: str = kwargs.get('custom_js', '')
        self.dependencies: List[str] = []
        self.is_secure = True

        # Security features
        self.csrf_token = kwargs.get('csrf_token')
        self.nonce = WidgetSecurity.generate_nonce()

        # Initialize
        self._setup_widget()

    def _setup_widget(self):
        """Setup widget with default configurations"""
        # Add theme class
        self.add_class(f'widget-theme-{self.theme.value}')
        self.add_class(f'widget-size-{self.size.value}')

        # Add security attributes
        self.attributes.nonce = self.nonce

        # Set up data attributes
        self.set_data_attribute('widget-type', self.widget_type.value)
        self.set_data_attribute('theme', self.theme.value)
        self.set_data_attribute('size', self.size.value)

    def add_validator(self, validator: Callable, error_message: str = None):
        """Add a validation function with custom error message"""
        self.validators.append({
            'validator': validator,
            'error_message': error_message or "Validation failed"
        })

    def validate(self, value: Any) -> bool:
        """Enhanced validation with detailed error reporting"""
        self.errors = []
        self.warnings = []

        for validator_config in self.validators:
            validator = validator_config['validator']
            error_message = validator_config['error_message']

            try:
                if not validator(value):
                    self.errors.append(error_message)
                    return False
            except Exception as e:
                self.errors.append(f"Validation error: {str(e)}")
                return False

        return True

    def add_class(self, css_class: str):
        """Add CSS class"""
        if css_class and css_class not in self.attributes.classes:
            self.attributes.classes.append(css_class)

    def remove_class(self, css_class: str):
        """Remove CSS class"""
        if css_class in self.attributes.classes:
            self.attributes.classes.remove(css_class)

    def add_style(self, property: str, value: str):
        """Add CSS style"""
        self.attributes.styles[property] = value

    def set_data_attribute(self, key: str, value: str):
        """Set data attribute"""
        self.attributes.data_attributes[key] = value

    def add_dependency(self, dependency: str):
        """Add CSS/JS dependency"""
        if dependency not in self.dependencies:
            self.dependencies.append(dependency)

    def set_theme(self, theme: WidgetTheme):
        """Change widget theme"""
        # Remove old theme class
        self.remove_class(f'widget-theme-{self.theme.value}')
        # Set new theme
        self.theme = theme
        self.add_class(f'widget-theme-{self.theme.value}')
        self.set_data_attribute('theme', self.theme.value)

    def set_size(self, size: WidgetSize):
        """Change widget size"""
        # Remove old size class
        self.remove_class(f'widget-size-{self.size.value}')
        # Set new size
        self.size = size
        self.add_class(f'widget-size-{self.size.value}')
        self.set_data_attribute('size', self.size.value)

    def get_value(self) -> Any:
        """Get the widget value"""
        return self.attributes.value

    def set_value(self, value: Any):
        """Set the widget value"""
        self.attributes.value = value

    def is_valid(self) -> bool:
        """Check if widget is valid"""
        return len(self.errors) == 0

    def get_errors(self) -> List[str]:
        """Get validation errors"""
        return self.errors.copy()

    def get_warnings(self) -> List[str]:
        """Get validation warnings"""
        return self.warnings.copy()

    def to_dict(self) -> Dict[str, Any]:
        """Convert widget to dictionary for serialization"""
        return {
            'name': self.name,
            'type': self.widget_type.value,
            'value': self.attributes.value,
            'theme': self.theme.value,
            'size': self.size.value,
            'errors': self.errors,
            'warnings': self.warnings,
            'is_valid': self.is_valid(),
            'dependencies': self.dependencies
        }

    def to_json(self) -> str:
        """Convert widget to JSON"""
        return json.dumps(self.to_dict(), indent=2)

    @abstractmethod
    def render(self) -> str:
        """Render the widget to HTML"""
        pass

    def render_with_dependencies(self) -> str:
        """Render widget with all dependencies"""
        html_parts = []

        # Add CSS dependencies
        for dep in self.dependencies:
            if dep.endswith('.css'):
                html_parts.append(f'<link rel="stylesheet" href="{dep}">')

        # Render widget
        html_parts.append(self.render())

        # Add JavaScript dependencies
        for dep in self.dependencies:
            if dep.endswith('.js'):
                html_parts.append(f'<script src="{dep}"></script>')

        # Add custom JavaScript
        if self.custom_js:
            csp_hash = WidgetSecurity.generate_csp_hash(self.custom_js)
            html_parts.append(f'<script nonce="{self.nonce}" data-csp-hash="{csp_hash}">{self.custom_js}</script>')

        return '\n'.join(html_parts)


class WidgetFactory:
    """Enhanced factory for creating widgets with advanced features"""

    _registry: Dict[str, type] = {}

    @staticmethod
    def register(widget_type: str, widget_class: type):
        """Register a widget class"""
        WidgetFactory._registry[widget_type] = widget_class

    @staticmethod
    def create(widget_type: str, name: str, **kwargs) -> BaseWidget:
        """Create a widget instance"""
        if widget_type not in WidgetFactory._registry:
            raise ValueError(f"Unknown widget type: {widget_type}")

        widget_class = WidgetFactory._registry[widget_type]
        return widget_class(name, **kwargs)

    @staticmethod
    def get_available_types() -> List[str]:
        """Get list of available widget types"""
        return list(WidgetFactory._registry.keys())

    @staticmethod
    def create_from_config(config: Dict[str, Any]) -> BaseWidget:
        """Create widget from configuration dictionary"""
        widget_type = config.pop('type')
        name = config.pop('name')
        return WidgetFactory.create(widget_type, name, **config)


# Export key classes
__all__ = [
    'BaseWidget', 'WidgetType', 'ContentFormat', 'WidgetAttributes',
    'WidgetSecurity', 'MarkdownProcessor', 'WidgetValidator', 'WidgetFactory',
    'WidgetTheme', 'WidgetSize'
]

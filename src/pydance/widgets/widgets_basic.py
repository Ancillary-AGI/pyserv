"""
Basic Rich Widgets for Pydance Framework
========================================

Simple but effective rich widgets with security and good UX.
"""
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum

import markdown
import bleach
from bs4 import BeautifulSoup


class WidgetType(Enum):
    """Widget type enumeration"""
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


class ContentFormat(Enum):
    """Content format for rich widgets"""
    HTML = "html"
    MARKDOWN = "markdown"
    PLAIN = "plain"


@dataclass
class WidgetAttributes:
    """Widget HTML attributes"""
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


class WidgetSecurity:
    """Security utilities for widgets"""

    # Allowed HTML tags for rich content
    ALLOWED_TAGS = [
        'p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li', 'blockquote', 'code', 'pre', 'hr', 'a', 'img',
        'table', 'thead', 'tbody', 'tr', 'th', 'td', 'span', 'div'
    ]

    # Allowed HTML attributes
    ALLOWED_ATTRIBUTES = {
        'a': ['href', 'title', 'target'],
        'img': ['src', 'alt', 'title', 'width', 'height'],
        'table': ['border', 'cellpadding', 'cellspacing'],
        'td': ['colspan', 'rowspan'],
        'th': ['colspan', 'rowspan'],
        'span': ['class'],
        'div': ['class'],
        '*': ['class', 'id', 'title']
    }

    @staticmethod
    def sanitize_html(html_content: str) -> str:
        """Sanitize HTML content to prevent XSS attacks"""
        return bleach.clean(
            html_content,
            tags=WidgetSecurity.ALLOWED_TAGS,
            attributes=WidgetSecurity.ALLOWED_ATTRIBUTES,
            strip=True
        )

    @staticmethod
    def validate_markdown(markdown_content: str) -> bool:
        """Validate markdown content for security"""
        # Check for potentially dangerous patterns
        dangerous_patterns = [
            r'javascript:',  # JavaScript URLs
            r'data:',        # Data URLs (can contain scripts)
            r'vbscript:',    # VBScript
            r'on\w+\s*=',    # Event handlers
            r'<script',      # Script tags
            r'<iframe',      # Iframes
            r'<object',      # Object tags
            r'<embed',       # Embed tags
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, markdown_content, re.IGNORECASE):
                return False
        return True

    @staticmethod
    def escape_html(text: str) -> str:
        """Escape HTML special characters"""
        return bleach.clean(text, tags=[], strip=False)


class MarkdownProcessor:
    """Markdown processing utilities"""

    @staticmethod
    def markdown_to_html(markdown_content: str) -> str:
        """Convert markdown to HTML"""
        # Configure markdown extensions
        extensions = [
            'extra',           # Extra features
            'codehilite',      # Code highlighting
            'toc',            # Table of contents
            'tables',         # Tables support
            'fenced_code',    # Fenced code blocks
            'footnotes',      # Footnotes
        ]

        # Convert to HTML
        html = markdown.markdown(markdown_content, extensions=extensions)

        # Sanitize the HTML
        return WidgetSecurity.sanitize_html(html)

    @staticmethod
    def html_to_markdown(html_content: str) -> str:
        """Convert HTML to markdown (basic conversion)"""
        # This is a simplified conversion - in production you might want to use
        # a more sophisticated library like html2text
        soup = BeautifulSoup(html_content, 'html.parser')

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        # Convert common elements
        conversions = {
            'strong': '**',
            'em': '*',
            'h1': '# ',
            'h2': '## ',
            'h3': '### ',
            'h4': '#### ',
            'h5': '##### ',
            'h6': '###### ',
            'li': '- ',
            'blockquote': '> ',
            'code': '`',
            'pre': '```\n',
        }

        text = soup.get_text()

        # Basic link conversion
        for a in soup.find_all('a'):
            if a.get('href'):
                text = text.replace(a.get_text(), f"[{a.get_text()}]({a['href']})")

        return text.strip()


class BaseWidget(ABC):
    """Base widget class"""

    def __init__(self, name: str, widget_type: WidgetType, **kwargs):
        self.name = name
        self.widget_type = widget_type
        self.attributes = WidgetAttributes(name=name, **kwargs)
        self.errors: List[str] = []
        self.validators: List[callable] = []

    def add_validator(self, validator: callable):
        """Add a validation function"""
        self.validators.append(validator)

    def validate(self, value: Any) -> bool:
        """Validate the widget value"""
        self.errors = []
        for validator in self.validators:
            try:
                if not validator(value):
                    self.errors.append(f"Validation failed for {self.name}")
                    return False
            except Exception as e:
                self.errors.append(str(e))
                return False
        return True

    def add_class(self, css_class: str):
        """Add CSS class"""
        if css_class not in self.attributes.classes:
            self.attributes.classes.append(css_class)

    def add_style(self, property: str, value: str):
        """Add CSS style"""
        self.attributes.styles[property] = value

    def set_data_attribute(self, key: str, value: str):
        """Set data attribute"""
        self.attributes.data_attributes[key] = value

    @abstractmethod
    def render(self) -> str:
        """Render the widget to HTML"""
        pass

    def get_value(self) -> Any:
        """Get the widget value"""
        return self.attributes.value

    def set_value(self, value: Any):
        """Set the widget value"""
        self.attributes.value = value

    def is_valid(self) -> bool:
        """Check if widget is valid"""
        return len(self.errors) == 0


class TextWidget(BaseWidget):
    """Basic text input widget"""

    def __init__(self, name: str, **kwargs):
        super().__init__(name, WidgetType.TEXT, **kwargs)

    def render(self) -> str:
        """Render text input"""
        attrs = self._build_attributes()
        return f'<input type="text" {attrs} />'

    def _build_attributes(self) -> str:
        """Build HTML attributes string"""
        attrs = [f'name="{self.attributes.name}"']

        if self.attributes.id:
            attrs.append(f'id="{self.attributes.id}"')
        if self.attributes.value:
            attrs.append(f'value="{WidgetSecurity.escape_html(str(self.attributes.value))}"')
        if self.attributes.placeholder:
            attrs.append(f'placeholder="{WidgetSecurity.escape_html(self.attributes.placeholder)}"')
        if self.attributes.maxlength:
            attrs.append(f'maxlength="{self.attributes.maxlength}"')
        if self.attributes.minlength:
            attrs.append(f'minlength="{self.attributes.minlength}"')
        if self.attributes.pattern:
            attrs.append(f'pattern="{self.attributes.pattern}"')
        if self.attributes.required:
            attrs.append('required')
        if self.attributes.disabled:
            attrs.append('disabled')
        if self.attributes.readonly:
            attrs.append('readonly')
        if self.attributes.autocomplete:
            attrs.append(f'autocomplete="{self.attributes.autocomplete}"')
        if self.attributes.classes:
            attrs.append(f'class="{" ".join(self.attributes.classes)}"')
        if self.attributes.aria_label:
            attrs.append(f'aria-label="{WidgetSecurity.escape_html(self.attributes.aria_label)}"')
        if self.attributes.aria_describedby:
            attrs.append(f'aria-describedby="{self.attributes.aria_describedby}"')

        # Add data attributes
        for key, value in self.attributes.data_attributes.items():
            attrs.append(f'data-{key}="{WidgetSecurity.escape_html(value)}"')

        # Add inline styles
        if self.attributes.styles:
            style_str = '; '.join(f'{k}: {v}' for k, v in self.attributes.styles.items())
            attrs.append(f'style="{style_str}"')

        return ' '.join(attrs)


class RichTextWidget(BaseWidget):
    """Rich text widget with Markdown/HTML support"""

    def __init__(self, name: str, format: ContentFormat = ContentFormat.HTML, **kwargs):
        super().__init__(name, WidgetType.RICHTEXT, **kwargs)
        self.format = format
        self.markdown_processor = MarkdownProcessor()

    def render(self) -> str:
        """Render rich text widget"""
        attrs = self._build_attributes()

        # Add rich text specific classes
        self.add_class('rich-text-widget')
        self.set_data_attribute('format', self.format.value)

        html = f'''
        <div class="rich-text-container">
            <div class="rich-text-toolbar">
                <button type="button" class="rich-text-btn" data-command="bold" title="Bold">
                    <strong>B</strong>
                </button>
                <button type="button" class="rich-text-btn" data-command="italic" title="Italic">
                    <em>I</em>
                </button>
                <button type="button" class="rich-text-btn" data-command="underline" title="Underline">
                    <u>U</u>
                </button>
                <button type="button" class="rich-text-btn" data-command="link" title="Link">
                    🔗
                </button>
                <button type="button" class="rich-text-btn" data-command="image" title="Image">
                    🖼️
                </button>
                <button type="button" class="rich-text-btn" data-command="code" title="Code">
                    </>
                </button>
                <button type="button" class="rich-text-btn" data-command="list" title="List">
                    📝
                </button>
                <button type="button" class="rich-text-btn" data-command="heading" title="Heading">
                    H
                </button>
            </div>
            <div class="rich-text-editor" contenteditable="true" {attrs}>
                {self._get_initial_content()}
            </div>
            <div class="rich-text-preview" style="display: none;"></div>
            <div class="rich-text-format-toggle">
                <button type="button" class="format-btn active" data-format="html">HTML</button>
                <button type="button" class="format-btn" data-format="markdown">Markdown</button>
            </div>
        </div>
        '''

        return html

    def _get_initial_content(self) -> str:
        """Get initial content for the editor"""
        if not self.attributes.value:
            return ""

        if self.format == ContentFormat.HTML:
            return WidgetSecurity.sanitize_html(str(self.attributes.value))
        elif self.format == ContentFormat.MARKDOWN:
            return WidgetSecurity.escape_html(str(self.attributes.value))
        else:
            return WidgetSecurity.escape_html(str(self.attributes.value))

    def get_content(self, format: ContentFormat = None) -> str:
        """Get content in specified format"""
        if format is None:
            format = self.format

        content = str(self.attributes.value or "")

        if format == ContentFormat.HTML:
            if self.format == ContentFormat.MARKDOWN:
                return self.markdown_processor.markdown_to_html(content)
            else:
                return WidgetSecurity.sanitize_html(content)
        elif format == ContentFormat.MARKDOWN:
            if self.format == ContentFormat.HTML:
                return self.markdown_processor.html_to_markdown(content)
            else:
                return content
        else:
            return content

    def set_content(self, content: str, format: ContentFormat = None):
        """Set content from specified format"""
        if format is None:
            format = self.format

        if format == ContentFormat.HTML:
            # Validate and sanitize HTML
            if not WidgetSecurity.validate_markdown(content):
                raise ValueError("Invalid HTML content")
            self.attributes.value = WidgetSecurity.sanitize_html(content)
        elif format == ContentFormat.MARKDOWN:
            # Validate markdown
            if not WidgetSecurity.validate_markdown(content):
                raise ValueError("Invalid Markdown content")
            self.attributes.value = content
        else:
            self.attributes.value = WidgetSecurity.escape_html(content)

    def _build_attributes(self) -> str:
        """Build HTML attributes string"""
        attrs = [f'name="{self.attributes.name}"']

        if self.attributes.id:
            attrs.append(f'id="{self.attributes.id}"')
        if self.attributes.placeholder:
            attrs.append(f'placeholder="{WidgetSecurity.escape_html(self.attributes.placeholder)}"')
        if self.attributes.maxlength:
            attrs.append(f'maxlength="{self.attributes.maxlength}"')
        if self.attributes.required:
            attrs.append('required')
        if self.attributes.disabled:
            attrs.append('disabled')
        if self.attributes.readonly:
            attrs.append('readonly')

        # Add classes
        all_classes = ['rich-text-editor']
        if self.attributes.classes:
            all_classes.extend(self.attributes.classes)
        attrs.append(f'class="{" ".join(all_classes)}"')

        # Add data attributes
        for key, value in self.attributes.data_attributes.items():
            attrs.append(f'data-{key}="{WidgetSecurity.escape_html(value)}"')

        return ' '.join(attrs)


class RichSelectWidget(BaseWidget):
    """Rich select widget with advanced features"""

    def __init__(self, name: str, options: List[Tuple[str, str]] = None, **kwargs):
        super().__init__(name, WidgetType.RICHSELECT, **kwargs)
        self.options = options or []
        self.allow_multiple = kwargs.get('multiple', False)
        self.searchable = kwargs.get('searchable', True)
        self.placeholder = kwargs.get('placeholder', 'Select an option...')

    def add_option(self, value: str, label: str, group: str = None):
        """Add an option to the select"""
        self.options.append((value, label, group))

    def render(self) -> str:
        """Render rich select widget"""
        self.add_class('rich-select-widget')
        self.set_data_attribute('searchable', 'true' if self.searchable else 'false')
        self.set_data_attribute('multiple', 'true' if self.allow_multiple else 'false')

        options_html = self._build_options_html()

        html = f'''
        <div class="rich-select-container">
            <div class="rich-select-display" tabindex="0">
                <span class="rich-select-placeholder">{WidgetSecurity.escape_html(self.placeholder)}</span>
                <span class="rich-select-arrow">▼</span>
            </div>
            <div class="rich-select-dropdown" style="display: none;">
                {self._build_search_input()}
                <div class="rich-select-options">
                    {options_html}
                </div>
            </div>
            <select name="{self.attributes.name}" style="display: none;" {"multiple" if self.allow_multiple else ""}>
                {self._build_native_options()}
            </select>
        </div>
        '''

        return html

    def _build_options_html(self) -> str:
        """Build HTML for rich select options"""
        html_parts = []
        current_group = None

        for option in self.options:
            if len(option) == 3:
                value, label, group = option
            else:
                value, label = option
                group = None

            if group != current_group:
                if current_group is not None:
                    html_parts.append('</div>')
                if group:
                    html_parts.append(f'<div class="rich-select-group" data-group="{WidgetSecurity.escape_html(group)}">')
                    html_parts.append(f'<div class="rich-select-group-label">{WidgetSecurity.escape_html(group)}</div>')
                current_group = group

            selected = 'selected' if str(self.attributes.value) == str(value) else ''
            html_parts.append(f'''
                <div class="rich-select-option {selected}"
                     data-value="{WidgetSecurity.escape_html(str(value))}"
                     data-label="{WidgetSecurity.escape_html(label)}">
                    {WidgetSecurity.escape_html(label)}
                </div>
            ''')

        if current_group is not None:
            html_parts.append('</div>')

        return '\n'.join(html_parts)

    def _build_native_options(self) -> str:
        """Build HTML for native select options (for form submission)"""
        html_parts = []

        for option in self.options:
            if len(option) == 3:
                value, label, group = option
            else:
                value, label = option

            selected = 'selected' if str(self.attributes.value) == str(value) else ''
            html_parts.append(f'<option value="{WidgetSecurity.escape_html(str(value))}" {selected}>'
                            f'{WidgetSecurity.escape_html(label)}</option>')

        return '\n'.join(html_parts)

    def _build_search_input(self) -> str:
        """Build search input for searchable select"""
        if not self.searchable:
            return ""

        return f'''
        <div class="rich-select-search">
            <input type="text" class="rich-select-search-input"
                   placeholder="Search options..."
                   autocomplete="off">
        </div>
        '''


class RichTitleWidget(BaseWidget):
    """Rich title widget with formatting options"""

    def __init__(self, name: str, level: int = 1, **kwargs):
        super().__init__(name, WidgetType.RICHTITLE, **kwargs)
        self.level = max(1, min(6, level))  # H1 to H6

    def render(self) -> str:
        """Render rich title widget"""
        self.add_class('rich-title-widget')
        self.set_data_attribute('level', str(self.level))

        attrs = self._build_attributes()

        html = f'''
        <div class="rich-title-container">
            <div class="rich-title-toolbar">
                <select class="rich-title-level">
                    <option value="1" {"selected" if self.level == 1 else ""}>H1</option>
                    <option value="2" {"selected" if self.level == 2 else ""}>H2</option>
                    <option value="3" {"selected" if self.level == 3 else ""}>H3</option>
                    <option value="4" {"selected" if self.level == 4 else ""}>H4</option>
                    <option value="5" {"selected" if self.level == 5 else ""}>H5</option>
                    <option value="6" {"selected" if self.level == 6 else ""}>H6</option>
                </select>
                <button type="button" class="rich-title-btn" data-command="bold" title="Bold">
                    <strong>B</strong>
                </button>
                <button type="button" class="rich-title-btn" data-command="italic" title="Italic">
                    <em>I</em>
                </button>
                <button type="button" class="rich-title-btn" data-command="link" title="Link">
                    🔗
                </button>
            </div>
            <h{self.level} class="rich-title-editor" contenteditable="true" {attrs}>
                {WidgetSecurity.escape_html(str(self.attributes.value or ""))}
            </h{self.level}>
        </div>
        '''

        return html

    def _build_attributes(self) -> str:
        """Build HTML attributes string"""
        attrs = [f'name="{self.attributes.name}"']

        if self.attributes.id:
            attrs.append(f'id="{self.attributes.id}"')
        if self.attributes.placeholder:
            attrs.append(f'placeholder="{WidgetSecurity.escape_html(self.attributes.placeholder)}"')
        if self.attributes.maxlength:
            attrs.append(f'maxlength="{self.attributes.maxlength}"')
        if self.attributes.required:
            attrs.append('required')
        if self.attributes.disabled:
            attrs.append('disabled')
        if self.attributes.readonly:
            attrs.append('readonly')

        # Add classes
        all_classes = ['rich-title-editor']
        if self.attributes.classes:
            all_classes.extend(self.attributes.classes)
        attrs.append(f'class="{" ".join(all_classes)}"')

        return ' '.join(attrs)


class WidgetFactory:
    """Factory for creating widgets"""

    @staticmethod
    def create_text(name: str, **kwargs) -> TextWidget:
        """Create a text input widget"""
        return TextWidget(name, **kwargs)

    @staticmethod
    def create_password(name: str, **kwargs) -> TextWidget:
        """Create a password input widget"""
        kwargs['type'] = 'password'
        return TextWidget(name, **kwargs)

    @staticmethod
    def create_email(name: str, **kwargs) -> TextWidget:
        """Create an email input widget"""
        kwargs['type'] = 'email'
        return TextWidget(name, **kwargs)

    @staticmethod
    def create_richtext(name: str, format: ContentFormat = ContentFormat.HTML, **kwargs) -> RichTextWidget:
        """Create a rich text widget"""
        return RichTextWidget(name, format, **kwargs)

    @staticmethod
    def create_richselect(name: str, options: List[Tuple[str, str]] = None, **kwargs) -> RichSelectWidget:
        """Create a rich select widget"""
        return RichSelectWidget(name, options, **kwargs)

    @staticmethod
    def create_richtitle(name: str, level: int = 1, **kwargs) -> RichTitleWidget:
        """Create a rich title widget"""
        return RichTitleWidget(name, level, **kwargs)


# Convenience functions
def Text(name: str, **kwargs) -> TextWidget:
    """Create text widget"""
    return WidgetFactory.create_text(name, **kwargs)

def Password(name: str, **kwargs) -> TextWidget:
    """Create password widget"""
    return WidgetFactory.create_password(name, **kwargs)

def Email(name: str, **kwargs) -> TextWidget:
    """Create email widget"""
    return WidgetFactory.create_email(name, **kwargs)

def RichText(name: str, format: ContentFormat = ContentFormat.HTML, **kwargs) -> RichTextWidget:
    """Create rich text widget"""
    return WidgetFactory.create_richtext(name, format, **kwargs)

def RichSelect(name: str, options: List[Tuple[str, str]] = None, **kwargs) -> RichSelectWidget:
    """Create rich select widget"""
    return WidgetFactory.create_richselect(name, options, **kwargs)

def RichTitle(name: str, level: int = 1, **kwargs) -> RichTitleWidget:
    """Create rich title widget"""
    return WidgetFactory.create_richtitle(name, level, **kwargs)

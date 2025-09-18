"""
Enhanced Rich Widgets - Advanced Form Widgets with Rich Features
===============================================================

Comprehensive collection of secure, feature-rich form widgets with enhanced
functionality, better security, and improved user experience.
"""

from typing import List, Tuple, Optional, Dict, Any, Union
from .core import (
    BaseWidget, WidgetType, ContentFormat, WidgetSecurity,
    MarkdownProcessor, WidgetValidator, WidgetTheme, WidgetSize
)


class TextWidget(BaseWidget):
    """Enhanced text input widget with advanced features"""

    def __init__(self, name: str, **kwargs):
        super().__init__(name, WidgetType.TEXT, **kwargs)
        self.input_type = kwargs.get('input_type', 'text')
        self.masked = kwargs.get('masked', False)
        self.autocomplete_options = kwargs.get('autocomplete_options', [])
        self.validation_rules = kwargs.get('validation_rules', {})

        # Add dependencies
        self.add_dependency('/static/css/widgets.css')
        self.add_dependency('/static/js/widgets.js')

        # Setup validation
        self._setup_validation()

    def _setup_validation(self):
        """Setup validation rules"""
        if self.attributes.required:
            self.add_validator(
                lambda v: WidgetValidator.required(v),
                "This field is required"
            )

        if self.attributes.minlength:
            self.add_validator(
                lambda v: WidgetValidator.min_length(v, self.attributes.minlength),
                f"Minimum length is {self.attributes.minlength} characters"
            )

        if self.attributes.maxlength:
            self.add_validator(
                lambda v: WidgetValidator.max_length(v, self.attributes.maxlength),
                f"Maximum length is {self.attributes.maxlength} characters"
            )

        if self.attributes.pattern:
            self.add_validator(
                lambda v: WidgetValidator.pattern(v, self.attributes.pattern),
                "Invalid format"
            )

        # Type-specific validation
        if self.input_type == 'email':
            self.add_validator(
                lambda v: not v or WidgetValidator.email(v),
                "Invalid email address"
            )
        elif self.input_type == 'url':
            self.add_validator(
                lambda v: not v or WidgetValidator.url(v),
                "Invalid URL format"
            )
        elif self.input_type in ['number', 'range']:
            if 'min' in self.validation_rules:
                min_val = self.validation_rules['min']
                self.add_validator(
                    lambda v: WidgetValidator.range_check(v, min_val=min_val),
                    f"Value must be at least {min_val}"
                )
            if 'max' in self.validation_rules:
                max_val = self.validation_rules['max']
                self.add_validator(
                    lambda v: WidgetValidator.range_check(v, max_val=max_val),
                    f"Value must be at most {max_val}"
                )

    def render(self) -> str:
        """Render enhanced text input"""
        self.add_class('enhanced-text-widget')

        # Set input type
        input_type = self.input_type
        if self.masked:
            input_type = 'password'

        # Build attributes
        attrs = self._build_attributes()
        attrs_str = ' '.join(attrs)

        # Autocomplete datalist
        datalist_html = ""
        if self.autocomplete_options:
            datalist_id = f"{self.attributes.id or self.name}_list"
            datalist_html = f'<datalist id="{datalist_id}">'
            for option in self.autocomplete_options:
                if isinstance(option, tuple):
                    value, label = option
                else:
                    value = label = option
                datalist_html += f'<option value="{WidgetSecurity.escape_html(str(value))}">'
                if value != label:
                    datalist_html += f' {WidgetSecurity.escape_html(label)}'
                datalist_html += '</option>'
            datalist_html += '</datalist>'
            attrs.append(f'list="{datalist_id}"')

        # Validation feedback
        feedback_html = ""
        if self.errors:
            feedback_html = f'<div class="widget-feedback error">{self.errors[0]}</div>'
        elif self.warnings:
            feedback_html = f'<div class="widget-feedback warning">{self.warnings[0]}</div>'

        # Character counter
        counter_html = ""
        if self.attributes.maxlength:
            counter_html = f'''
            <div class="character-counter">
                <span class="counter-current">{len(str(self.attributes.value or ""))}</span>
                <span class="counter-max">/{self.attributes.maxlength}</span>
            </div>
            '''

        html = f'''
        <div class="enhanced-text-container">
            <input type="{input_type}" {attrs_str} />
            {datalist_html}
            {counter_html}
            {feedback_html}
        </div>
        '''

        return html

    def _build_attributes(self) -> List[str]:
        """Build HTML attributes with enhanced features"""
        attrs = [f'name="{self.attributes.name}"']

        if self.attributes.id:
            attrs.append(f'id="{self.attributes.id}"')
        if self.attributes.value is not None:
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

        # Add validation attributes
        if 'min' in self.validation_rules:
            attrs.append(f'min="{self.validation_rules["min"]}"')
        if 'max' in self.validation_rules:
            attrs.append(f'max="{self.validation_rules["max"]}"')
        if 'step' in self.validation_rules:
            attrs.append(f'step="{self.validation_rules["step"]}"')

        # Add classes
        all_classes = ['enhanced-text-input']
        if self.attributes.classes:
            all_classes.extend(self.attributes.classes)
        attrs.append(f'class="{" ".join(all_classes)}"')

        # Add data attributes
        for key, value in self.attributes.data_attributes.items():
            attrs.append(f'data-{key}="{WidgetSecurity.escape_html(value)}"')

        # Add security attributes
        if self.attributes.nonce:
            attrs.append(f'nonce="{self.attributes.nonce}"')

        return attrs


class RichTextWidget(BaseWidget):
    """Enhanced rich text editor with advanced features"""

    def __init__(self, name: str, **kwargs):
        super().__init__(name, WidgetType.RICHTEXT, **kwargs)
        self.format = kwargs.get('format', ContentFormat.HTML)
        self.markdown_processor = MarkdownProcessor()
        self.toolbar_config = kwargs.get('toolbar_config', self._get_default_toolbar())
        self.plugins = kwargs.get('plugins', [])
        self.max_content_length = kwargs.get('max_content_length', 100000)
        self.allowed_formats = kwargs.get('allowed_formats', ['html', 'markdown'])

        # Add dependencies
        self.add_dependency('/static/css/widgets.css')
        self.add_dependency('/static/js/widgets.js')

        # Setup validation
        self._setup_validation()

    def _get_default_toolbar(self) -> List[Dict[str, Any]]:
        """Get default toolbar configuration"""
        return [
            {'name': 'format', 'buttons': ['bold', 'italic', 'underline', 'strikethrough']},
            {'name': 'heading', 'buttons': ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']},
            {'name': 'list', 'buttons': ['ul', 'ol', 'indent', 'outdent']},
            {'name': 'link', 'buttons': ['link', 'unlink', 'image']},
            {'name': 'media', 'buttons': ['video', 'table', 'code', 'blockquote']},
            {'name': 'tools', 'buttons': ['undo', 'redo', 'fullscreen', 'help']}
        ]

    def _setup_validation(self):
        """Setup validation rules"""
        if self.attributes.required:
            self.add_validator(
                lambda v: WidgetValidator.required(v),
                "Content is required"
            )

        # Content length validation
        self.add_validator(
            lambda v: len(str(v or "")) <= self.max_content_length,
            f"Content exceeds maximum length of {self.max_content_length} characters"
        )

    def render(self) -> str:
        """Render enhanced rich text editor"""
        self.add_class('enhanced-rich-text-widget')
        self.set_data_attribute('format', self.format.value)
        self.set_data_attribute('max-length', str(self.max_content_length))

        # Build toolbar
        toolbar_html = self._build_toolbar()

        # Build format selector
        format_selector_html = ""
        if len(self.allowed_formats) > 1:
            format_options = []
            for fmt in self.allowed_formats:
                selected = 'selected' if fmt == self.format.value else ''
                format_options.append(f'<option value="{fmt}" {selected}>{fmt.title()}</option>')
            format_selector_html = f'''
            <select class="rich-text-format-selector">
                {''.join(format_options)}
            </select>
            '''

        # Content area
        content_html = self._get_initial_content()

        # Word count and statistics
        stats_html = '''
        <div class="rich-text-stats">
            <span class="word-count">Words: <span class="count">0</span></span>
            <span class="char-count">Characters: <span class="count">0</span></span>
        </div>
        '''

        # Preview mode
        preview_html = '<div class="rich-text-preview" style="display: none;"></div>'

        html = f'''
        <div class="enhanced-rich-text-container">
            <div class="rich-text-toolbar">
                {toolbar_html}
                {format_selector_html}
            </div>
            <div class="rich-text-editor-container">
                <div class="rich-text-editor" contenteditable="true"
                     data-placeholder="{WidgetSecurity.escape_html(self.attributes.placeholder or '')}">
                    {content_html}
                </div>
                {preview_html}
            </div>
            {stats_html}
            <input type="hidden" name="{self.attributes.name}" value="{WidgetSecurity.escape_html(str(self.attributes.value or ''))}" />
        </div>
        '''

        return html

    def _build_toolbar(self) -> str:
        """Build toolbar HTML"""
        toolbar_groups = []

        for group in self.toolbar_config:
            group_name = group['name']
            buttons = group['buttons']

            button_html = []
            for button in buttons:
                button_config = self._get_button_config(button)
                if button_config:
                    button_html.append(button_config)

            if button_html:
                toolbar_groups.append(f'''
                <div class="toolbar-group toolbar-group-{group_name}">
                    {''.join(button_html)}
                </div>
                ''')

        return ''.join(toolbar_groups)

    def _get_button_config(self, button_name: str) -> str:
        """Get button configuration"""
        button_configs = {
            'bold': '<button type="button" class="rich-text-btn" data-command="bold" title="Bold"><strong>B</strong></button>',
            'italic': '<button type="button" class="rich-text-btn" data-command="italic" title="Italic"><em>I</em></button>',
            'underline': '<button type="button" class="rich-text-btn" data-command="underline" title="Underline"><u>U</u></button>',
            'strikethrough': '<button type="button" class="rich-text-btn" data-command="strikethrough" title="Strikethrough"><s>S</s></button>',
            'h1': '<button type="button" class="rich-text-btn" data-command="formatBlock" data-value="h1" title="Heading 1">H1</button>',
            'h2': '<button type="button" class="rich-text-btn" data-command="formatBlock" data-value="h2" title="Heading 2">H2</button>',
            'h3': '<button type="button" class="rich-text-btn" data-command="formatBlock" data-value="h3" title="Heading 3">H3</button>',
            'h4': '<button type="button" class="rich-text-btn" data-command="formatBlock" data-value="h4" title="Heading 4">H4</button>',
            'h5': '<button type="button" class="rich-text-btn" data-command="formatBlock" data-value="h5" title="Heading 5">H5</button>',
            'h6': '<button type="button" class="rich-text-btn" data-command="formatBlock" data-value="h6" title="Heading 6">H6</button>',
            'ul': '<button type="button" class="rich-text-btn" data-command="insertUnorderedList" title="Bullet List">•</button>',
            'ol': '<button type="button" class="rich-text-btn" data-command="insertOrderedList" title="Numbered List">1.</button>',
            'indent': '<button type="button" class="rich-text-btn" data-command="indent" title="Increase Indent">→</button>',
            'outdent': '<button type="button" class="rich-text-btn" data-command="outdent" title="Decrease Indent">←</button>',
            'link': '<button type="button" class="rich-text-btn" data-command="createLink" title="Insert Link">🔗</button>',
            'unlink': '<button type="button" class="rich-text-btn" data-command="unlink" title="Remove Link">🔓</button>',
            'image': '<button type="button" class="rich-text-btn" data-command="insertImage" title="Insert Image">🖼️</button>',
            'video': '<button type="button" class="rich-text-btn" data-command="insertVideo" title="Insert Video">🎥</button>',
            'table': '<button type="button" class="rich-text-btn" data-command="insertTable" title="Insert Table">📊</button>',
            'code': '<button type="button" class="rich-text-btn" data-command="formatBlock" data-value="pre" title="Code Block"></></button>',
            'blockquote': '<button type="button" class="rich-text-btn" data-command="formatBlock" data-value="blockquote" title="Quote">"</button>',
            'undo': '<button type="button" class="rich-text-btn" data-command="undo" title="Undo">↶</button>',
            'redo': '<button type="button" class="rich-text-btn" data-command="redo" title="Redo">↷</button>',
            'fullscreen': '<button type="button" class="rich-text-btn" data-command="fullscreen" title="Fullscreen">⛶</button>',
            'help': '<button type="button" class="rich-text-btn" data-command="help" title="Help">?</button>',
        }

        return button_configs.get(button_name)

    def _get_initial_content(self) -> str:
        """Get initial content for the editor"""
        if not self.attributes.value:
            return ""

        content = str(self.attributes.value)

        if self.format == ContentFormat.HTML:
            return WidgetSecurity.sanitize_html(content)
        elif self.format == ContentFormat.MARKDOWN:
            return WidgetSecurity.escape_html(content)
        else:
            return WidgetSecurity.escape_html(content)

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
            is_valid, messages = WidgetSecurity.validate_markdown(content)
            if not is_valid:
                raise ValueError(f"Invalid HTML content: {messages}")
            self.attributes.value = WidgetSecurity.sanitize_html(content)
        elif format == ContentFormat.MARKDOWN:
            # Validate markdown
            is_valid, messages = WidgetSecurity.validate_markdown(content)
            if not is_valid:
                raise ValueError(f"Invalid Markdown content: {messages}")
            self.attributes.value = content
        else:
            self.attributes.value = WidgetSecurity.escape_html(content)


class RichSelectWidget(BaseWidget):
    """Enhanced rich select widget with advanced features"""

    def __init__(self, name: str, **kwargs):
        super().__init__(name, WidgetType.RICHSELECT, **kwargs)
        self.options = kwargs.get('options', [])
        self.allow_multiple = kwargs.get('multiple', False)
        self.searchable = kwargs.get('searchable', True)
        self.placeholder = kwargs.get('placeholder', 'Select an option...')
        self.groups = kwargs.get('groups', {})
        self.max_selections = kwargs.get('max_selections', None)
        self.allow_custom = kwargs.get('allow_custom', False)

        # Add dependencies
        self.add_dependency('/static/css/widgets.css')
        self.add_dependency('/static/js/widgets.js')

    def add_option(self, value: str, label: str, group: str = None):
        """Add an option to the select"""
        self.options.append((value, label, group))

    def add_group(self, group_name: str, options: List[Tuple[str, str]]):
        """Add a group of options"""
        self.groups[group_name] = options

    def render(self) -> str:
        """Render enhanced rich select widget"""
        self.add_class('enhanced-rich-select-widget')
        self.set_data_attribute('searchable', 'true' if self.searchable else 'false')
        self.set_data_attribute('multiple', 'true' if self.allow_multiple else 'false')
        self.set_data_attribute('allow-custom', 'true' if self.allow_custom else 'false')

        if self.max_selections:
            self.set_data_attribute('max-selections', str(self.max_selections))

        # Build options HTML
        options_html = self._build_options_html()

        # Search input
        search_html = ""
        if self.searchable:
            search_html = '''
            <div class="rich-select-search">
                <input type="text" class="rich-select-search-input"
                       placeholder="Search options..."
                       autocomplete="off">
                <div class="search-icon">🔍</div>
            </div>
            '''

        # Selected values display
        display_html = self._build_display_html()

        # Hidden inputs for form submission
        hidden_inputs = self._build_hidden_inputs()

        html = f'''
        <div class="enhanced-rich-select-container">
            <div class="rich-select-display" tabindex="0">
                {display_html}
                <div class="rich-select-arrow">▼</div>
            </div>
            <div class="rich-select-dropdown" style="display: none;">
                {search_html}
                <div class="rich-select-options">
                    {options_html}
                </div>
                {self._build_actions_html()}
            </div>
            {hidden_inputs}
        </div>
        '''

        return html

    def _build_display_html(self) -> str:
        """Build display HTML for selected values"""
        if self.allow_multiple:
            selected_options = self._get_selected_options()
            if selected_options:
                display_items = []
                for value, label in selected_options[:3]:  # Show max 3
                    display_items.append(f'<span class="selected-item">{WidgetSecurity.escape_html(label)}</span>')

                if len(selected_options) > 3:
                    display_items.append(f'<span class="more-items">+{len(selected_options) - 3} more</span>')

                return f'<div class="selected-items">{''.join(display_items)}</div>'
            else:
                return f'<span class="rich-select-placeholder">{WidgetSecurity.escape_html(self.placeholder)}</span>'
        else:
            selected = self._get_selected_option()
            if selected:
                return f'<span class="selected-value">{WidgetSecurity.escape_html(selected[1])}</span>'
            else:
                return f'<span class="rich-select-placeholder">{WidgetSecurity.escape_html(self.placeholder)}</span>'

    def _build_options_html(self) -> str:
        """Build HTML for rich select options"""
        html_parts = []

        # Add grouped options
        for group_name, group_options in self.groups.items():
            html_parts.append(f'<div class="rich-select-group" data-group="{WidgetSecurity.escape_html(group_name)}">')
            html_parts.append(f'<div class="rich-select-group-label">{WidgetSecurity.escape_html(group_name)}</div>')

            for value, label in group_options:
                selected = 'selected' if self._is_selected(value) else ''
                html_parts.append(f'''
                <div class="rich-select-option {selected}"
                     data-value="{WidgetSecurity.escape_html(str(value))}"
                     data-label="{WidgetSecurity.escape_html(label)}">
                    <div class="option-content">
                        <span class="option-label">{WidgetSecurity.escape_html(label)}</span>
                        {f'<span class="option-group">{WidgetSecurity.escape_html(group_name)}</span>' if group_name else ''}
                    </div>
                    {f'<div class="option-check">✓</div>' if selected else ''}
                </div>
                ''')

            html_parts.append('</div>')

        # Add individual options
        for option in self.options:
            if len(option) == 3:
                value, label, group = option
            else:
                value, label = option
                group = None

            if group in self.groups:  # Skip if already in a group
                continue

            selected = 'selected' if self._is_selected(value) else ''
            html_parts.append(f'''
            <div class="rich-select-option {selected}"
                 data-value="{WidgetSecurity.escape_html(str(value))}"
                 data-label="{WidgetSecurity.escape_html(label)}">
                <div class="option-content">
                    <span class="option-label">{WidgetSecurity.escape_html(label)}</span>
                    {f'<span class="option-group">{WidgetSecurity.escape_html(group)}</span>' if group else ''}
                </div>
                {f'<div class="option-check">✓</div>' if selected else ''}
            </div>
            ''')

        return '\n'.join(html_parts)

    def _build_actions_html(self) -> str:
        """Build actions HTML"""
        actions = []

        if self.allow_multiple:
            actions.append('<button type="button" class="rich-select-action select-all">Select All</button>')
            actions.append('<button type="button" class="rich-select-action clear-all">Clear All</button>')

        actions.append('<button type="button" class="rich-select-action done">Done</button>')

        return f'<div class="rich-select-actions">{''.join(actions)}</div>'

    def _build_hidden_inputs(self) -> str:
        """Build hidden inputs for form submission"""
        inputs = []

        if self.allow_multiple:
            selected_values = [value for value, _ in self._get_selected_options()]
            for i, value in enumerate(selected_values):
                inputs.append(f'<input type="hidden" name="{self.attributes.name}" value="{WidgetSecurity.escape_html(str(value))}" />')
        else:
            selected = self._get_selected_option()
            if selected:
                inputs.append(f'<input type="hidden" name="{self.attributes.name}" value="{WidgetSecurity.escape_html(str(selected[0]))}" />')

        return '\n'.join(inputs)

    def _get_selected_options(self) -> List[Tuple[str, str]]:
        """Get selected options"""
        if not self.attributes.value:
            return []

        if isinstance(self.attributes.value, list):
            selected_values = self.attributes.value
        else:
            selected_values = [str(self.attributes.value)]

        selected_options = []
        for value in selected_values:
            option = self._find_option_by_value(value)
            if option:
                selected_options.append(option)

        return selected_options

    def _get_selected_option(self) -> Optional[Tuple[str, str]]:
        """Get selected option (single)"""
        if not self.attributes.value:
            return None

        return self._find_option_by_value(str(self.attributes.value))

    def _find_option_by_value(self, value: str) -> Optional[Tuple[str, str]]:
        """Find option by value"""
        # Search in groups
        for group_options in self.groups.values():
            for opt_value, opt_label in group_options:
                if str(opt_value) == value:
                    return (opt_value, opt_label)

        # Search in individual options
        for option in self.options:
            if len(option) >= 2:
                opt_value, opt_label = option[0], option[1]
                if str(opt_value) == value:
                    return (opt_value, opt_label)

        return None

    def _is_selected(self, value: str) -> bool:
        """Check if value is selected"""
        if not self.attributes.value:
            return False

        if self.allow_multiple:
            if isinstance(self.attributes.value, list):
                return str(value) in [str(v) for v in self.attributes.value]
            else:
                return str(value) == str(self.attributes.value)
        else:
            return str(value) == str(self.attributes.value)


class RichTitleWidget(BaseWidget):
    """Enhanced rich title widget with advanced formatting"""

    def __init__(self, name: str, **kwargs):
        super().__init__(name, WidgetType.RICHTITLE, **kwargs)
        self.level = max(1, min(6, kwargs.get('level', 1)))
        self.allow_formatting = kwargs.get('allow_formatting', True)
        self.max_length = kwargs.get('max_length', 200)
        self.auto_slug = kwargs.get('auto_slug', False)

        # Add dependencies
        self.add_dependency('/static/css/widgets.css')
        self.add_dependency('/static/js/widgets.js')

        # Setup validation
        self._setup_validation()

    def _setup_validation(self):
        """Setup validation rules"""
        if self.attributes.required:
            self.add_validator(
                lambda v: WidgetValidator.required(v),
                "Title is required"
            )

        self.add_validator(
            lambda v: WidgetValidator.max_length(v, self.max_length),
            f"Title exceeds maximum length of {self.max_length} characters"
        )

    def render(self) -> str:
        """Render enhanced rich title widget"""
        self.add_class('enhanced-rich-title-widget')
        self.set_data_attribute('level', str(self.level))
        self.set_data_attribute('allow-formatting', 'true' if self.allow_formatting else 'false')
        self.set_data_attribute('auto-slug', 'true' if self.auto_slug else 'false')

        # Level selector
        level_selector = ""
        if self.allow_formatting:
            level_options = []
            for i in range(1, 7):
                selected = 'selected' if i == self.level else ''
                level_options.append(f'<option value="{i}" {selected}>H{i}</option>')
            level_selector = f'''
            <select class="rich-title-level-selector">
                {''.join(level_options)}
            </select>
            '''

        # Formatting toolbar
        toolbar_html = ""
        if self.allow_formatting:
            toolbar_html = '''
            <div class="rich-title-toolbar">
                <button type="button" class="rich-title-btn" data-command="bold" title="Bold">
                    <strong>B</strong>
                </button>
                <button type="button" class="rich-title-btn" data-command="italic" title="Italic">
                    <em>I</em>
                </button>
                <button type="button" class="rich-title-btn" data-command="link" title="Link">
                    🔗
                </button>
                <button type="button" class="rich-title-btn" data-command="clear" title="Clear Formatting">
                    ⌫
                </button>
            </div>
            '''

        # Slug field
        slug_html = ""
        if self.auto_slug:
            slug_html = f'''
            <div class="title-slug-container">
                <input type="text" class="title-slug" placeholder="URL slug"
                       value="{WidgetSecurity.escape_html(self._generate_slug(str(self.attributes.value or '')))}"
                       readonly />
            </div>
            '''

        # Character counter
        counter_html = f'''
        <div class="title-counter">
            <span class="counter-current">{len(str(self.attributes.value or ''))}</span>
            <span class="counter-max">/{self.max_length}</span>
        </div>
        '''

        html = f'''
        <div class="enhanced-rich-title-container">
            <div class="title-controls">
                {level_selector}
                {toolbar_html}
            </div>
            <h{self.level} class="rich-title-editor" contenteditable="true"
                data-placeholder="{WidgetSecurity.escape_html(self.attributes.placeholder or '')}">
                {WidgetSecurity.escape_html(str(self.attributes.value or ''))}
            </h{self.level}>
            {slug_html}
            {counter_html}
            <input type="hidden" name="{self.attributes.name}"
                   value="{WidgetSecurity.escape_html(str(self.attributes.value or ''))}" />
        </div>
        '''

        return html

    def _generate_slug(self, title: str) -> str:
        """Generate URL slug from title"""
        if not title:
            return ""

        # Convert to lowercase and replace spaces with hyphens
        slug = title.lower().replace(' ', '-')

        # Remove special characters
        import re
        slug = re.sub(r'[^a-z0-9-]', '', slug)

        # Remove multiple consecutive hyphens
        slug = re.sub(r'-+', '-', slug)

        # Remove leading/trailing hyphens
        slug = slug.strip('-')

        return slug


# Register widgets with factory
from .core import WidgetFactory

WidgetFactory.register('text', TextWidget)
WidgetFactory.register('richtext', RichTextWidget)
WidgetFactory.register('richselect', RichSelectWidget)
WidgetFactory.register('richtitle', RichTitleWidget)

__all__ = [
    'TextWidget', 'RichTextWidget', 'RichSelectWidget', 'RichTitleWidget'
]

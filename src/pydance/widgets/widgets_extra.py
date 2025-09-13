"""
Enhanced Rich Widgets - Advanced Form Widgets with Rich Features
===============================================================

Comprehensive collection of advanced rich widgets with enhanced security,
customization options, and professional-grade functionality.
"""

from typing import List, Tuple, Optional, Dict, Any, Union
from datetime import datetime, date, time
import uuid
import json

from .core import (
    BaseWidget, WidgetType, ContentFormat, WidgetSecurity,
    MarkdownProcessor, WidgetValidator, WidgetTheme, WidgetSize
)


class RichFileWidget(BaseWidget):
    """Enhanced rich file upload widget with advanced features"""

    def __init__(self, name: str, **kwargs):
        super().__init__(name, WidgetType.FILE, **kwargs)
        self.multiple = kwargs.get('multiple', False)
        self.accept = kwargs.get('accept', '*/*')
        self.max_size = kwargs.get('max_size', 10 * 1024 * 1024)  # 10MB default
        self.allowed_types = kwargs.get('allowed_types', [])
        self.max_files = kwargs.get('max_files', 10)
        self.show_preview = kwargs.get('show_preview', True)
        self.allow_drag_drop = kwargs.get('allow_drag_drop', True)
        self.chunk_size = kwargs.get('chunk_size', 1024 * 1024)  # 1MB chunks
        self.auto_upload = kwargs.get('auto_upload', False)
        self.upload_url = kwargs.get('upload_url', '')
        self.progress_callback = kwargs.get('progress_callback', None)

        # Add dependencies
        self.add_dependency('/static/css/widgets.css')
        self.add_dependency('/static/js/widgets.js')

        # Setup validation
        self._setup_validation()

    def _setup_validation(self):
        """Setup validation rules"""
        if self.attributes.required:
            self.add_validator(
                lambda v: self._validate_required_files(v),
                "At least one file is required"
            )

    def _validate_required_files(self, value) -> bool:
        """Validate required files"""
        if not value:
            return False

        # Check if value contains file data
        if isinstance(value, list):
            return len(value) > 0
        elif isinstance(value, dict):
            return bool(value.get('files', []))
        else:
            return bool(value)

    def render(self) -> str:
        """Render enhanced rich file widget"""
        self.add_class('enhanced-rich-file-widget')
        self.set_data_attribute('multiple', 'true' if self.multiple else 'false')
        self.set_data_attribute('max-size', str(self.max_size))
        self.set_data_attribute('max-files', str(self.max_files))
        self.set_data_attribute('accept', self.accept)
        self.set_data_attribute('auto-upload', 'true' if self.auto_upload else 'false')
        self.set_data_attribute('chunk-size', str(self.chunk_size))

        if self.upload_url:
            self.set_data_attribute('upload-url', self.upload_url)

        # File input
        multiple_attr = 'multiple' if self.multiple else ''
        file_input = f'''
        <input type="file" name="{self.attributes.name}" {multiple_attr}
               accept="{self.accept}" style="display: none;"
               data-max-size="{self.max_size}" data-max-files="{self.max_files}" />
        '''

        # Drop zone
        dropzone_classes = ['rich-file-dropzone']
        if self.allow_drag_drop:
            dropzone_classes.append('drag-drop-enabled')

        dropzone_content = self._build_dropzone_content()
        dropzone_html = f'''
        <div class="{' '.join(dropzone_classes)}" data-dropzone>
            {dropzone_content}
        </div>
        '''

        # File list
        file_list_html = '''
        <div class="rich-file-list" style="display: none;">
            <div class="file-list-header">
                <span class="file-count">0 files selected</span>
                <button type="button" class="clear-all-files">Clear All</button>
            </div>
            <div class="file-items"></div>
        </div>
        '''

        # Progress
        progress_html = '''
        <div class="rich-file-progress" style="display: none;">
            <div class="progress-container">
                <div class="progress-bar">
                    <div class="progress-fill"></div>
                </div>
                <div class="progress-text">Uploading...</div>
                <div class="progress-details"></div>
            </div>
        </div>
        '''

        # Actions
        actions_html = self._build_actions_html()

        html = f'''
        <div class="enhanced-rich-file-container">
            {file_input}
            {dropzone_html}
            {file_list_html}
            {progress_html}
            {actions_html}
        </div>
        '''

        return html

    def _build_dropzone_content(self) -> str:
        """Build dropzone content"""
        icon_html = '<div class="file-upload-icon">📁</div>'

        text_html = '<div class="file-upload-text">'
        if self.multiple:
            text_html += f'<div class="primary-text">Drop files here or <span class="browse-link">browse</span></div>'
            text_html += f'<div class="secondary-text">Select up to {self.max_files} files</div>'
        else:
            text_html += f'<div class="primary-text">Drop file here or <span class="browse-link">browse</span></div>'
            text_html += f'<div class="secondary-text">Select one file</div>'
        text_html += '</div>'

        constraints_html = '<div class="file-constraints">'
        constraints = []
        if self.allowed_types:
            type_names = []
            for mime_type in self.allowed_types:
                if mime_type.startswith('image/'):
                    type_names.append('Images')
                elif mime_type.startswith('video/'):
                    type_names.append('Videos')
                elif mime_type.startswith('audio/'):
                    type_names.append('Audio')
                elif mime_type == 'application/pdf':
                    type_names.append('PDFs')
                else:
                    type_names.append(mime_type.split('/')[-1].upper())
            constraints.append(f"Types: {', '.join(type_names)}")

        constraints.append(f"Max size: {self._format_file_size(self.max_size)}")
        constraints_html += ' • '.join(constraints)
        constraints_html += '</div>'

        return f'{icon_html}{text_html}{constraints_html}'

    def _build_actions_html(self) -> str:
        """Build actions HTML"""
        actions = []

        if self.multiple:
            actions.append('<button type="button" class="file-action select-all">Select All</button>')
            actions.append('<button type="button" class="file-action select-none">Select None</button>')

        if self.auto_upload and self.upload_url:
            actions.append('<button type="button" class="file-action start-upload">Start Upload</button>')
            actions.append('<button type="button" class="file-action pause-upload" style="display: none;">Pause</button>')
            actions.append('<button type="button" class="file-action resume-upload" style="display: none;">Resume</button>')

        if actions:
            return f'<div class="file-actions">{"".join(actions)}</div>'

        return ''

    def _format_file_size(self, bytes_size: int) -> str:
        """Format file size for display"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_size < 1024.0:
                return ".1f"
            bytes_size /= 1024.0
        return ".1f"


class RichDateWidget(BaseWidget):
    """Enhanced rich date picker widget with advanced features"""

    def __init__(self, name: str, **kwargs):
        super().__init__(name, WidgetType.RICHDATE, **kwargs)
        self.date_format = kwargs.get('date_format', 'YYYY-MM-DD')
        self.time_format = kwargs.get('time_format', 'HH:mm')
        self.min_date = kwargs.get('min_date', None)
        self.max_date = kwargs.get('max_date', None)
        self.show_time = kwargs.get('show_time', False)
        self.show_seconds = kwargs.get('show_seconds', False)
        self.first_day_of_week = kwargs.get('first_day_of_week', 0)  # 0 = Sunday
        self.disabled_dates = kwargs.get('disabled_dates', [])
        self.highlighted_dates = kwargs.get('highlighted_dates', [])
        self.locale = kwargs.get('locale', 'en')
        self.timezone = kwargs.get('timezone', 'UTC')

        # Add dependencies
        self.add_dependency('/static/css/widgets.css')
        self.add_dependency('/static/js/widgets.js')

    def render(self) -> str:
        """Render enhanced rich date widget"""
        self.add_class('enhanced-rich-date-widget')
        self.set_data_attribute('date-format', self.date_format)
        self.set_data_attribute('time-format', self.time_format)
        self.set_data_attribute('show-time', 'true' if self.show_time else 'false')
        self.set_data_attribute('show-seconds', 'true' if self.show_seconds else 'false')
        self.set_data_attribute('first-day', str(self.first_day_of_week))
        self.set_data_attribute('locale', self.locale)
        self.set_data_attribute('timezone', self.timezone)

        if self.min_date:
            self.set_data_attribute('min-date', str(self.min_date))
        if self.max_date:
            self.set_data_attribute('max-date', str(self.max_date))

        # Input field
        attrs = self._build_attributes()
        input_html = f'<input type="text" {attrs} readonly />'

        # Calendar popup
        calendar_html = self._build_calendar_html()

        # Time picker (if enabled)
        time_html = ""
        if self.show_time:
            time_html = self._build_time_picker_html()

        # Quick selection buttons
        quick_select_html = self._build_quick_select_html()

        # Actions
        actions_html = '''
        <div class="date-actions">
            <button type="button" class="date-action today">Today</button>
            <button type="button" class="date-action clear">Clear</button>
            <button type="button" class="date-action apply">Apply</button>
        </div>
        '''

        html = f'''
        <div class="enhanced-rich-date-container">
            <div class="date-input-container">
                {input_html}
                <div class="date-toggle">📅</div>
            </div>
            <div class="date-picker-popup" style="display: none;">
                {calendar_html}
                {time_html}
                {quick_select_html}
                {actions_html}
            </div>
        </div>
        '''

        return html

    def _build_attributes(self) -> str:
        """Build input attributes"""
        attrs = [f'name="{self.attributes.name}"']

        if self.attributes.id:
            attrs.append(f'id="{self.attributes.id}"')
        if self.attributes.value:
            # Format the value according to our format
            formatted_value = self._format_date_value(self.attributes.value)
            attrs.append(f'value="{WidgetSecurity.escape_html(formatted_value)}"')
        if self.attributes.placeholder:
            attrs.append(f'placeholder="{WidgetSecurity.escape_html(self.attributes.placeholder)}"')
        if self.attributes.required:
            attrs.append('required')
        if self.attributes.disabled:
            attrs.append('disabled')

        # Add classes
        all_classes = ['rich-date-input']
        if self.attributes.classes:
            all_classes.extend(self.attributes.classes)
        attrs.append(f'class="{" ".join(all_classes)}"')

        return ' '.join(attrs)

    def _build_calendar_html(self) -> str:
        """Build calendar HTML"""
        # Month/Year navigation
        nav_html = '''
        <div class="calendar-nav">
            <button type="button" class="nav-prev">‹</button>
            <div class="current-month-year">Month Year</div>
            <button type="button" class="nav-next">›</button>
        </div>
        '''

        # Weekday headers
        weekday_names = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa']
        if self.first_day_of_week == 1:  # Monday first
            weekday_names = ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su']

        weekday_html = '<div class="calendar-weekdays">'
        for day in weekday_names:
            weekday_html += f'<div class="weekday">{day}</div>'
        weekday_html += '</div>'

        # Days grid
        days_html = '<div class="calendar-days"></div>'

        return f'''
        <div class="calendar-container">
            {nav_html}
            {weekday_html}
            {days_html}
        </div>
        '''

    def _build_time_picker_html(self) -> str:
        """Build time picker HTML"""
        time_format = self.time_format
        show_seconds = self.show_seconds

        time_html = '<div class="time-picker">'

        if 'HH' in time_format:
            time_html += '''
            <div class="time-input-group">
                <label>Hours</label>
                <input type="number" class="time-hours" min="0" max="23" value="12">
            </div>
            '''

        if 'mm' in time_format:
            time_html += '''
            <div class="time-input-group">
                <label>Minutes</label>
                <input type="number" class="time-minutes" min="0" max="59" value="0">
            </div>
            '''

        if show_seconds and 'ss' in time_format:
            time_html += '''
            <div class="time-input-group">
                <label>Seconds</label>
                <input type="number" class="time-seconds" min="0" max="59" value="0">
            </div>
            '''

        time_html += '''
        <div class="time-period">
            <button type="button" class="period-am active">AM</button>
            <button type="button" class="period-pm">PM</button>
        </div>
        '''

        time_html += '</div>'

        return time_html

    def _build_quick_select_html(self) -> str:
        """Build quick selection buttons"""
        quick_dates = [
            ('today', 'Today'),
            ('yesterday', 'Yesterday'),
            ('tomorrow', 'Tomorrow'),
            ('week_start', 'Start of Week'),
            ('week_end', 'End of Week'),
            ('month_start', 'Start of Month'),
            ('month_end', 'End of Month'),
        ]

        quick_html = '<div class="quick-dates">'
        for value, label in quick_dates:
            quick_html += f'<button type="button" class="quick-date" data-value="{value}">{label}</button>'
        quick_html += '</div>'

        return quick_html

    def _format_date_value(self, value) -> str:
        """Format date value according to specified format"""
        if not value:
            return ""

        try:
            if isinstance(value, str):
                # Try to parse the string
                dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            elif isinstance(value, datetime):
                dt = value
            elif isinstance(value, date):
                dt = datetime.combine(value, time.min)
            else:
                return str(value)

            # Format according to our format
            format_map = {
                'YYYY': '%Y',
                'MM': '%m',
                'DD': '%d',
                'HH': '%H',
                'mm': '%M',
                'ss': '%S'
            }

            format_str = self.date_format
            if self.show_time:
                format_str += ' ' + self.time_format

            for pydance_token, strftime_token in format_map.items():
                format_str = format_str.replace(pydance_token, strftime_token)

            return dt.strftime(format_str)

        except (ValueError, TypeError):
            return str(value)


class RichColorWidget(BaseWidget):
    """Enhanced rich color picker widget with advanced features"""

    def __init__(self, name: str, **kwargs):
        super().__init__(name, WidgetType.RICHCOLOR, **kwargs)
        self.default_color = kwargs.get('default_color', '#000000')
        self.show_palette = kwargs.get('show_palette', True)
        self.show_picker = kwargs.get('show_picker', True)
        self.palette = kwargs.get('palette', [
            '#000000', '#FFFFFF', '#FF0000', '#00FF00', '#0000FF',
            '#FFFF00', '#FF00FF', '#00FFFF', '#FFA500', '#800080',
            '#FFC0CB', '#A52A2A', '#808080', '#000080', '#008000'
        ])
        self.recent_colors = kwargs.get('recent_colors', [])
        self.allow_transparency = kwargs.get('allow_transparency', False)
        self.show_hex_input = kwargs.get('show_hex_input', True)
        self.show_rgb_input = kwargs.get('show_rgb_input', False)

        # Add dependencies
        self.add_dependency('/static/css/widgets.css')
        self.add_dependency('/static/js/widgets.js')

    def render(self) -> str:
        """Render enhanced rich color widget"""
        self.add_class('enhanced-rich-color-widget')
        self.set_data_attribute('default-color', self.default_color)
        self.set_data_attribute('allow-transparency', 'true' if self.allow_transparency else 'false')

        # Color display
        display_html = self._build_display_html()

        # Color picker popup
        picker_html = self._build_picker_html()

        html = f'''
        <div class="enhanced-rich-color-container">
            {display_html}
            <div class="color-picker-popup" style="display: none;">
                {picker_html}
            </div>
        </div>
        '''

        return html

    def _build_display_html(self) -> str:
        """Build color display HTML"""
        current_color = self.attributes.value or self.default_color

        display_html = f'''
        <div class="color-display">
            <div class="color-preview" style="background-color: {current_color};"
                 data-color="{current_color}"></div>
            <input type="text" class="color-hex-input"
                   value="{current_color}" readonly />
            <button type="button" class="color-toggle">🎨</button>
        </div>
        '''

        return display_html

    def _build_picker_html(self) -> str:
        """Build color picker HTML"""
        picker_parts = []

        # Color palette
        if self.show_palette:
            palette_html = '<div class="color-palette">'
            for color in self.palette:
                palette_html += f'<div class="color-swatch" data-color="{color}" style="background-color: {color};"></div>'
            palette_html += '</div>'
            picker_parts.append(palette_html)

        # Recent colors
        if self.recent_colors:
            recent_html = '<div class="recent-colors"><div class="section-title">Recent</div>'
            for color in self.recent_colors:
                recent_html += f'<div class="color-swatch" data-color="{color}" style="background-color: {color};"></div>'
            recent_html += '</div>'
            picker_parts.append(recent_html)

        # Native color picker
        if self.show_picker:
            picker_html = '''
            <div class="native-color-picker">
                <input type="color" class="color-input" value="#000000" />
            </div>
            '''
            picker_parts.append(picker_html)

        # Manual inputs
        inputs_html = '<div class="color-inputs">'

        if self.show_hex_input:
            inputs_html += '''
            <div class="input-group">
                <label>Hex</label>
                <input type="text" class="hex-input" placeholder="#000000" />
            </div>
            '''

        if self.show_rgb_input:
            inputs_html += '''
            <div class="rgb-inputs">
                <div class="input-group">
                    <label>R</label>
                    <input type="number" class="rgb-r" min="0" max="255" />
                </div>
                <div class="input-group">
                    <label>G</label>
                    <input type="number" class="rgb-g" min="0" max="255" />
                </div>
                <div class="input-group">
                    <label>B</label>
                    <input type="number" class="rgb-b" min="0" max="255" />
                </div>
            </div>
            '''

        if self.allow_transparency:
            inputs_html += '''
            <div class="input-group">
                <label>Alpha</label>
                <input type="number" class="alpha-input" min="0" max="1" step="0.1" />
            </div>
            '''

        inputs_html += '</div>'
        picker_parts.append(inputs_html)

        # Actions
        actions_html = '''
        <div class="color-actions">
            <button type="button" class="color-action apply">Apply</button>
            <button type="button" class="color-action cancel">Cancel</button>
            <button type="button" class="color-action reset">Reset</button>
        </div>
        '''
        picker_parts.append(actions_html)

        return '\n'.join(picker_parts)


class RichRatingWidget(BaseWidget):
    """Enhanced rich rating widget with advanced features"""

    def __init__(self, name: str, **kwargs):
        super().__init__(name, WidgetType.RICHRATING, **kwargs)
        self.max_rating = kwargs.get('max_rating', 5)
        self.min_rating = kwargs.get('min_rating', 1)
        self.step = kwargs.get('step', 1)
        self.show_half = kwargs.get('show_half', False)
        self.icon = kwargs.get('icon', '★')
        self.empty_icon = kwargs.get('empty_icon', '☆')
        self.hover_effect = kwargs.get('hover_effect', True)
        self.show_value = kwargs.get('show_value', True)
        self.allow_clear = kwargs.get('allow_clear', True)
        self.size = kwargs.get('size', 'medium')  # small, medium, large
        self.color = kwargs.get('color', '#ffc107')
        self.labels = kwargs.get('labels', {})  # Custom labels for ratings

        # Add dependencies
        self.add_dependency('/static/css/widgets.css')
        self.add_dependency('/static/js/widgets.js')

    def render(self) -> str:
        """Render enhanced rich rating widget"""
        self.add_class('enhanced-rich-rating-widget')
        self.set_data_attribute('max-rating', str(self.max_rating))
        self.set_data_attribute('min-rating', str(self.min_rating))
        self.set_data_attribute('step', str(self.step))
        self.set_data_attribute('show-half', 'true' if self.show_half else 'false')
        self.set_data_attribute('hover-effect', 'true' if self.hover_effect else 'false')
        self.set_data_attribute('allow-clear', 'true' if self.allow_clear else 'false')
        self.set_data_attribute('size', self.size)
        self.set_data_attribute('color', self.color)

        # Rating stars
        stars_html = self._build_stars_html()

        # Value display
        value_html = ""
        if self.show_value:
            current_value = self.attributes.value or 0
            value_html = f'<div class="rating-value">{current_value}/{self.max_rating}</div>'

        # Labels
        labels_html = ""
        if self.labels:
            labels_html = '<div class="rating-labels">'
            for rating, label in self.labels.items():
                labels_html += f'<div class="rating-label" data-rating="{rating}">{label}</div>'
            labels_html += '</div>'

        # Clear button
        clear_html = ""
        if self.allow_clear:
            clear_html = '<button type="button" class="rating-clear" title="Clear rating">✕</button>'

        html = f'''
        <div class="enhanced-rich-rating-container">
            <div class="rating-stars" style="--rating-color: {self.color}; --rating-size: {self._get_size_value()}">
                {stars_html}
            </div>
            {value_html}
            {labels_html}
            {clear_html}
            <input type="hidden" name="{self.attributes.name}" value="{self.attributes.value or ''}" />
        </div>
        '''

        return html

    def _build_stars_html(self) -> str:
        """Build rating stars HTML"""
        stars = []
        current_rating = float(self.attributes.value or 0)

        for i in range(self.min_rating, self.max_rating + 1):
            star_class = 'rating-star'
            if current_rating >= i:
                star_class += ' active'
            elif self.show_half and current_rating >= i - 0.5:
                star_class += ' half'

            star_html = f'''
            <span class="{star_class}" data-rating="{i}"
                  data-half="{i - 0.5 if self.show_half else i}"
                  title="Rate {i} star{'s' if i > 1 else ''}">
                {self.icon}
            </span>
            '''
            stars.append(star_html)

        return '\n'.join(stars)

    def _get_size_value(self) -> str:
        """Get CSS size value"""
        size_map = {
            'small': '16px',
            'medium': '24px',
            'large': '32px'
        }
        return size_map.get(self.size, '24px')


class RichTagsWidget(BaseWidget):
    """Enhanced rich tags input widget with advanced features"""

    def __init__(self, name: str, **kwargs):
        super().__init__(name, WidgetType.RICHTAGS, **kwargs)
        self.placeholder = kwargs.get('placeholder', 'Add tags...')
        self.max_tags = kwargs.get('max_tags', 10)
        self.min_tags = kwargs.get('min_tags', 0)
        self.allow_duplicates = kwargs.get('allow_duplicates', False)
        self.suggestions = kwargs.get('suggestions', [])
        self.max_suggestion_count = kwargs.get('max_suggestion_count', 5)
        self.allow_spaces = kwargs.get('allow_spaces', False)
        self.tag_separator = kwargs.get('tag_separator', ',')
        self.case_sensitive = kwargs.get('case_sensitive', False)
        self.sort_tags = kwargs.get('sort_tags', False)
        self.tag_colors = kwargs.get('tag_colors', {})
        self.allow_edit = kwargs.get('allow_edit', True)

        # Add dependencies
        self.add_dependency('/static/css/widgets.css')
        self.add_dependency('/static/js/widgets.js')

        # Setup validation
        self._setup_validation()

    def _setup_validation(self):
        """Setup validation rules"""
        if self.attributes.required:
            self.add_validator(
                lambda v: self._validate_required_tags(v),
                "At least one tag is required"
            )

        self.add_validator(
            lambda v: self._validate_max_tags(v),
            f"Maximum {self.max_tags} tags allowed"
        )

        if self.min_tags > 0:
            self.add_validator(
                lambda v: self._validate_min_tags(v),
                f"At least {self.min_tags} tags required"
            )

    def _validate_required_tags(self, value) -> bool:
        """Validate required tags"""
        if not value:
            return False

        tags = self._parse_tags(value)
        return len(tags) > 0

    def _validate_max_tags(self, value) -> bool:
        """Validate maximum tags"""
        if not value:
            return True

        tags = self._parse_tags(value)
        return len(tags) <= self.max_tags

    def _validate_min_tags(self, value) -> bool:
        """Validate minimum tags"""
        if not value:
            return self.min_tags == 0

        tags = self._parse_tags(value)
        return len(tags) >= self.min_tags

    def _parse_tags(self, value) -> List[str]:
        """Parse tags from value"""
        if not value:
            return []

        if isinstance(value, str):
            tags = [tag.strip() for tag in value.split(self.tag_separator) if tag.strip()]
        elif isinstance(value, list):
            tags = [str(tag).strip() for tag in value if tag]
        else:
            tags = []

        return tags

    def render(self) -> str:
        """Render enhanced rich tags widget"""
        self.add_class('enhanced-rich-tags-widget')
        self.set_data_attribute('max-tags', str(self.max_tags))
        self.set_data_attribute('min-tags', str(self.min_tags))
        self.set_data_attribute('allow-duplicates', 'true' if self.allow_duplicates else 'false')
        self.set_data_attribute('allow-spaces', 'true' if self.allow_spaces else 'false')
        self.set_data_attribute('case-sensitive', 'true' if self.case_sensitive else 'false')
        self.set_data_attribute('allow-edit', 'true' if self.allow_edit else 'false')

        # Parse existing tags
        existing_tags = self._parse_tags(self.attributes.value)

        # Tags display
        tags_html = self._build_tags_html(existing_tags)

        # Input field
        input_html = f'''
        <input type="text" class="tags-input"
               placeholder="{WidgetSecurity.escape_html(self.placeholder)}"
               autocomplete="off" />
        '''

        # Suggestions dropdown
        suggestions_html = ""
        if self.suggestions:
            suggestions_html = self._build_suggestions_html()

        # Hidden input for form submission
        hidden_value = self.tag_separator.join(existing_tags)
        hidden_html = f'<input type="hidden" name="{self.attributes.name}" value="{WidgetSecurity.escape_html(hidden_value)}" />'

        # Counter
        counter_html = f'''
        <div class="tags-counter">
            <span class="tags-count">{len(existing_tags)}</span>
            <span class="tags-max">/{self.max_tags}</span>
        </div>
        '''

        html = f'''
        <div class="enhanced-rich-tags-container">
            <div class="tags-display">
                {tags_html}
                {input_html}
            </div>
            {suggestions_html}
            {counter_html}
            {hidden_html}
        </div>
        '''

        return html

    def _build_tags_html(self, tags: List[str]) -> str:
        """Build tags HTML"""
        if not tags:
            return ""

        tag_html_parts = []
        for tag in tags:
            color = self._get_tag_color(tag)
            style = f'background-color: {color};' if color else ''

            tag_html = f'''
            <span class="tag" data-tag="{WidgetSecurity.escape_html(tag)}" style="{style}">
                <span class="tag-text">{WidgetSecurity.escape_html(tag)}</span>
                <span class="tag-remove" title="Remove tag">×</span>
            </span>
            '''
            tag_html_parts.append(tag_html)

        return '\n'.join(tag_html_parts)

    def _build_suggestions_html(self) -> str:
        """Build suggestions dropdown HTML"""
        if not self.suggestions:
            return ""

        suggestion_html_parts = []
        for suggestion in self.suggestions[:self.max_suggestion_count]:
            suggestion_html_parts.append(f'''
            <div class="tag-suggestion" data-tag="{WidgetSecurity.escape_html(suggestion)}">
                {WidgetSecurity.escape_html(suggestion)}
            </div>
            ''')

        return f'''
        <div class="tags-suggestions" style="display: none;">
            {''.join(suggestion_html_parts)}
        </div>
        '''

    def _get_tag_color(self, tag: str) -> Optional[str]:
        """Get color for tag"""
        # Check if specific color is assigned
        if tag in self.tag_colors:
            return self.tag_colors[tag]

        # Generate color based on tag content (simple hash)
        if self.tag_colors.get('auto_generate', False):
            hash_value = hash(tag) % 360
            return f'hsl({hash_value}, 70%, 60%)'

        return None


class RichSliderWidget(BaseWidget):
    """Enhanced rich slider/range widget with advanced features"""

    def __init__(self, name: str, **kwargs):
        super().__init__(name, WidgetType.RICHSLIDER, **kwargs)
        self.min_value = kwargs.get('min_value', 0)
        self.max_value = kwargs.get('max_value', 100)
        self.step = kwargs.get('step', 1)
        self.default_value = kwargs.get('default_value', self.min_value)
        self.show_value = kwargs.get('show_value', True)
        self.show_range = kwargs.get('show_range', False)
        self.orientation = kwargs.get('orientation', 'horizontal')
        self.track_color = kwargs.get('track_color', '#007bff')
        self.thumb_size = kwargs.get('thumb_size', 'medium')
        self.show_ticks = kwargs.get('show_ticks', False)
        self.tick_interval = kwargs.get('tick_interval', None)
        self.labels = kwargs.get('labels', {})

        # Add dependencies
        self.add_dependency('/static/css/widgets.css')
        self.add_dependency('/static/js/widgets.js')

    def render(self) -> str:
        """Render enhanced rich slider widget"""
        self.add_class('enhanced-rich-slider-widget')
        self.set_data_attribute('min', str(self.min_value))
        self.set_data_attribute('max', str(self.max_value))
        self.set_data_attribute('step', str(self.step))
        self.set_data_attribute('orientation', self.orientation)
        self.set_data_attribute('thumb-size', self.thumb_size)

        # Calculate current value and percentage
        current_value = self.attributes.value if self.attributes.value is not None else self.default_value
        percentage = self._calculate_percentage(current_value)

        # Track
        track_html = f'''
        <div class="slider-track" style="--track-color: {self.track_color};">
            <div class="slider-fill" style="width: {percentage}%;"></div>
            <div class="slider-thumb" style="left: {percentage}%; --thumb-size: {self._get_thumb_size()};"></div>
        </div>
        '''

        # Ticks
        ticks_html = ""
        if self.show_ticks:
            ticks_html = self._build_ticks_html()

        # Labels
        labels_html = ""
        if self.labels:
            labels_html = self._build_labels_html()

        # Value display
        value_html = ""
        if self.show_value:
            value_html = f'<div class="slider-value">{current_value}</div>'

        # Range display
        range_html = ""
        if self.show_range:
            range_html = f'<div class="slider-range">{self.min_value} - {self.max_value}</div>'

        # Hidden input
        input_html = f'<input type="hidden" name="{self.attributes.name}" value="{current_value}" />'

        html = f'''
        <div class="enhanced-rich-slider-container" data-orientation="{self.orientation}">
            {range_html}
            <div class="slider-wrapper">
                {track_html}
                {ticks_html}
            </div>
            {labels_html}
            {value_html}
            {input_html}
        </div>
        '''

        return html

    def _calculate_percentage(self, value: float) -> float:
        """Calculate percentage for value"""
        return ((value - self.min_value) / (self.max_value - self.min_value)) * 100

    def _get_thumb_size(self) -> str:
        """Get thumb size CSS value"""
        size_map = {
            'small': '16px',
            'medium': '20px',
            'large': '24px'
        }
        return size_map.get(self.thumb_size, '20px')

    def _build_ticks_html(self) -> str:
        """Build ticks HTML"""
        if not self.show_ticks:
            return ""

        ticks = []
        interval = self.tick_interval or ((self.max_value - self.min_value) / 10)

        current = self.min_value
        while current <= self.max_value:
            percentage = self._calculate_percentage(current)
            ticks.append(f'<div class="slider-tick" style="left: {percentage}%;"></div>')
            current += interval

        return f'<div class="slider-ticks">{"".join(ticks)}</div>'

    def _build_labels_html(self) -> str:
        """Build labels HTML"""
        if not self.labels:
            return ""

        labels_html = '<div class="slider-labels">'
        for value, label in self.labels.items():
            try:
                num_value = float(value)
                percentage = self._calculate_percentage(num_value)
                labels_html += f'<div class="slider-label" style="left: {percentage}%;">{WidgetSecurity.escape_html(label)}</div>'
            except (ValueError, TypeError):
                continue
        labels_html += '</div>'

        return labels_html


class RichCodeWidget(BaseWidget):
    """Enhanced rich code editor widget with advanced features"""

    def __init__(self, name: str, **kwargs):
        super().__init__(name, WidgetType.RICHCODE, **kwargs)
        self.language = kwargs.get('language', 'javascript')
        self.theme = kwargs.get('theme', 'default')
        self.line_numbers = kwargs.get('line_numbers', True)
        self.word_wrap = kwargs.get('word_wrap', True)
        self.auto_indent = kwargs.get('auto_indent', True)
        self.syntax_check = kwargs.get('syntax_check', True)
        self.code_folding = kwargs.get('code_folding', False)
        self.minimap = kwargs.get('minimap', False)
        self.font_size = kwargs.get('font_size', 14)
        self.tab_size = kwargs.get('tab_size', 4)
        self.readonly = kwargs.get('readonly', False)

        # Add dependencies
        self.add_dependency('/static/css/widgets.css')
        self.add_dependency('/static/js/widgets.js')

    def render(self) -> str:
        """Render enhanced rich code widget"""
        self.add_class('enhanced-rich-code-widget')
        self.set_data_attribute('language', self.language)
        self.set_data_attribute('theme', self.theme)
        self.set_data_attribute('line-numbers', 'true' if self.line_numbers else 'false')
        self.set_data_attribute('word-wrap', 'true' if self.word_wrap else 'false')
        self.set_data_attribute('auto-indent', 'true' if self.auto_indent else 'false')
        self.set_data_attribute('syntax-check', 'true' if self.syntax_check else 'false')
        self.set_data_attribute('code-folding', 'true' if self.code_folding else 'false')
        self.set_data_attribute('minimap', 'true' if self.minimap else 'false')
        self.set_data_attribute('font-size', str(self.font_size))
        self.set_data_attribute('tab-size', str(self.tab_size))

        # Toolbar
        toolbar_html = self._build_toolbar_html()

        # Editor container
        editor_html = f'''
        <div class="code-editor-container">
            <textarea class="code-textarea" name="{self.attributes.name}"
                      style="font-size: {self.font_size}px;"
                      {"readonly" if self.readonly else ""}>
{WidgetSecurity.escape_html(str(self.attributes.value or ""))}
            </textarea>
            <pre class="code-highlighted"><code></code></pre>
        </div>
        '''

        # Status bar
        status_html = self._build_status_bar_html()

        html = f'''
        <div class="enhanced-rich-code-container">
            {toolbar_html}
            {editor_html}
            {status_html}
        </div>
        '''

        return html

    def _build_toolbar_html(self) -> str:
        """Build toolbar HTML"""
        toolbar_buttons = {
            'format': [
                ('bold', 'Bold', 'Ctrl+B'),
                ('italic', 'Italic', 'Ctrl+I'),
                ('underline', 'Underline', 'Ctrl+U'),
            ],
            'edit': [
                ('undo', 'Undo', 'Ctrl+Z'),
                ('redo', 'Redo', 'Ctrl+Y'),
                ('find', 'Find', 'Ctrl+F'),
                ('replace', 'Replace', 'Ctrl+H'),
            ],
            'view': [
                ('fullscreen', 'Fullscreen', 'F11'),
                ('word-wrap', 'Word Wrap', None),
                ('line-numbers', 'Line Numbers', None),
            ],
            'tools': [
                ('format-code', 'Format Code', 'Shift+Alt+F'),
                ('copy', 'Copy', 'Ctrl+C'),
                ('help', 'Help', 'F1'),
            ]
        }

        toolbar_html = '<div class="code-toolbar">'

        for group_name, buttons in toolbar_buttons.items():
            toolbar_html += f'<div class="toolbar-group toolbar-group-{group_name}">'

            for button_id, title, shortcut in buttons:
                shortcut_attr = f' data-shortcut="{shortcut}"' if shortcut else ''
                toolbar_html += f'''
                <button type="button" class="code-btn" data-command="{button_id}"
                        title="{title}{f' ({shortcut})' if shortcut else ''}"{shortcut_attr}>
                    {self._get_button_icon(button_id)}
                </button>
                '''

            toolbar_html += '</div>'

        # Language selector
        languages = ['javascript', 'python', 'html', 'css', 'json', 'sql', 'php', 'java', 'cpp', 'ruby']
        lang_options = []
        for lang in languages:
            selected = 'selected' if lang == self.language else ''
            lang_options.append(f'<option value="{lang}" {selected}>{lang.title()}</option>')

        toolbar_html += f'''
        <div class="toolbar-group toolbar-group-language">
            <select class="code-language-selector">
                {''.join(lang_options)}
            </select>
        </div>
        '''

        toolbar_html += '</div>'

        return toolbar_html

    def _get_button_icon(self, button_id: str) -> str:
        """Get button icon HTML"""
        icons = {
            'bold': '𝐁',
            'italic': '𝐼',
            'underline': 'U̲',
            'undo': '↶',
            'redo': '↷',
            'find': '🔍',
            'replace': '🔄',
            'fullscreen': '⛶',
            'word-wrap': '↵',
            'line-numbers': '📄',
            'format-code': '🎨',
            'copy': '📋',
            'help': '❓'
        }
        return icons.get(button_id, button_id.upper())

    def _build_status_bar_html(self) -> str:
        """Build status bar HTML"""
        return '''
        <div class="code-status-bar">
            <div class="status-left">
                <span class="cursor-position">Ln 1, Col 1</span>
                <span class="selection-info"></span>
            </div>
            <div class="status-right">
                <span class="encoding">UTF-8</span>
                <span class="line-ending">LF</span>
                <span class="language-display">JavaScript</span>
            </div>
        </div>
        '''


# Register enhanced widgets
from ..widgets.core import WidgetFactory

WidgetFactory.register('richfile', RichFileWidget)
WidgetFactory.register('richdate', RichDateWidget)
WidgetFactory.register('richcolor', RichColorWidget)
WidgetFactory.register('richrating', RichRatingWidget)
WidgetFactory.register('richtags', RichTagsWidget)
WidgetFactory.register('richslider', RichSliderWidget)
WidgetFactory.register('richcode', RichCodeWidget)

# Convenience functions
def RichFile(name: str, **kwargs) -> RichFileWidget:
    """Create rich file widget"""
    return WidgetFactory.create('richfile', name, **kwargs)

def RichDate(name: str, **kwargs) -> RichDateWidget:
    """Create rich date widget"""
    return WidgetFactory.create('richdate', name, **kwargs)

def RichColor(name: str, **kwargs) -> RichColorWidget:
    """Create rich color widget"""
    return WidgetFactory.create('richcolor', name, **kwargs)

def RichRating(name: str, **kwargs) -> RichRatingWidget:
    """Create rich rating widget"""
    return WidgetFactory.create('richrating', name, **kwargs)

def RichTags(name: str, **kwargs) -> RichTagsWidget:
    """Create rich tags widget"""
    return WidgetFactory.create('richtags', name, **kwargs)

def RichSlider(name: str, **kwargs) -> RichSliderWidget:
    """Create rich slider widget"""
    return WidgetFactory.create('richslider', name, **kwargs)

def RichCode(name: str, **kwargs) -> RichCodeWidget:
    """Create rich code widget"""
    return WidgetFactory.create('richcode', name, **kwargs)

__all__ = [
    'RichFileWidget', 'RichDateWidget', 'RichColorWidget', 'RichRatingWidget',
    'RichTagsWidget', 'RichSliderWidget', 'RichCodeWidget',
    'RichFile', 'RichDate', 'RichColor', 'RichRating', 'RichTags', 'RichSlider', 'RichCode'
]

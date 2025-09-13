"""
Widget Forms Integration - Form Handling with Rich Widgets
=========================================================

Advanced form handling system that integrates seamlessly with rich widgets,
providing validation, CSRF protection, and secure form processing.
"""

from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
import json

from .core import BaseWidget, WidgetSecurity, WidgetValidator


@dataclass
class FormField:
    """Form field configuration"""
    name: str
    widget: BaseWidget
    label: Optional[str] = None
    help_text: Optional[str] = None
    required: bool = False
    validators: List[Callable] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    conditional_logic: Optional[Dict[str, Any]] = None


@dataclass
class FormConfig:
    """Form configuration"""
    name: str
    method: str = 'POST'
    action: str = ''
    enctype: str = 'application/x-www-form-urlencoded'
    csrf_token: Optional[str] = None
    theme: str = 'default'
    classes: List[str] = field(default_factory=list)


class WidgetForm:
    """Enhanced form class with rich widget integration"""

    def __init__(self, config: FormConfig):
        self.config = config
        self.fields: Dict[str, FormField] = {}
        self.errors: Dict[str, List[str]] = {}
        self.data: Dict[str, Any] = {}
        self.is_valid = True
        self.csrf_token = config.csrf_token or WidgetSecurity.generate_nonce()

    def add_field(self, name: str, widget: BaseWidget, **kwargs):
        """Add a field to the form"""
        field = FormField(
            name=name,
            widget=widget,
            **kwargs
        )

        # Set widget properties based on field config
        if field.required:
            widget.attributes.required = True
        if field.label:
            widget.attributes.aria_label = field.label

        # Add field validators to widget
        for validator in field.validators:
            widget.add_validator(validator)

        self.fields[name] = field

    def remove_field(self, name: str):
        """Remove a field from the form"""
        if name in self.fields:
            del self.fields[name]

    def get_field(self, name: str) -> Optional[FormField]:
        """Get a field by name"""
        return self.fields.get(name)

    def set_data(self, data: Dict[str, Any]):
        """Set form data"""
        self.data = data.copy()

        # Update widget values
        for field_name, field in self.fields.items():
            if field_name in data:
                field.widget.set_value(data[field_name])

    def validate(self) -> bool:
        """Validate the entire form"""
        self.errors = {}
        self.is_valid = True

        for field_name, field in self.fields.items():
            # Validate widget
            if not field.widget.validate(field.widget.get_value()):
                self.errors[field_name] = field.widget.get_errors()
                self.is_valid = False

            # Run additional field validators
            for validator in field.validators:
                try:
                    if not validator(field.widget.get_value()):
                        if field_name not in self.errors:
                            self.errors[field_name] = []
                        self.errors[field_name].append("Validation failed")
                        self.is_valid = False
                except Exception as e:
                    if field_name not in self.errors:
                        self.errors[field_name] = []
                    self.errors[field_name].append(str(e))
                    self.is_valid = False

        return self.is_valid

    def get_errors(self) -> Dict[str, List[str]]:
        """Get all form errors"""
        return self.errors.copy()

    def get_cleaned_data(self) -> Dict[str, Any]:
        """Get cleaned form data"""
        if not self.is_valid:
            return {}

        cleaned_data = {}
        for field_name, field in self.fields.items():
            cleaned_data[field_name] = field.widget.get_value()

        return cleaned_data

    def render(self) -> str:
        """Render the complete form"""
        # Build form attributes
        form_attrs = [
            f'method="{self.config.method}"',
            f'name="{self.config.name}"',
            f'id="form-{self.config.name}"'
        ]

        if self.config.action:
            form_attrs.append(f'action="{self.config.action}"')
        if self.config.enctype:
            form_attrs.append(f'enctype="{self.config.enctype}"')

        # Add classes
        all_classes = ['widget-form', f'form-theme-{self.config.theme}']
        if self.config.classes:
            all_classes.extend(self.config.classes)
        form_attrs.append(f'class="{" ".join(all_classes)}"')

        form_attrs_str = ' '.join(form_attrs)

        # Build form content
        form_content = []

        # CSRF token
        if self.config.csrf_token:
            form_content.append(f'<input type="hidden" name="csrf_token" value="{WidgetSecurity.escape_html(self.csrf_token)}" />')

        # Render fields
        for field_name, field in self.fields.items():
            field_html = self._render_field(field)
            form_content.append(field_html)

        # Form actions
        actions_html = self._render_form_actions()
        form_content.append(actions_html)

        # Combine everything
        form_html = f'''
        <form {form_attrs_str}>
            {''.join(form_content)}
        </form>
        '''

        return form_html

    def _render_field(self, field: FormField) -> str:
        """Render a single field"""
        # Field label
        label_html = ""
        if field.label:
            required_mark = '<span class="required-mark">*</span>' if field.required else ''
            label_html = f'''
            <label for="{field.widget.attributes.id or field.name}" class="field-label">
                {WidgetSecurity.escape_html(field.label)}{required_mark}
            </label>
            '''

        # Field widget
        widget_html = field.widget.render()

        # Field help text
        help_html = ""
        if field.help_text:
            help_html = f'<div class="field-help">{WidgetSecurity.escape_html(field.help_text)}</div>'

        # Field errors
        errors_html = ""
        if field.name in self.errors:
            error_items = [f'<li>{WidgetSecurity.escape_html(error)}</li>' for error in self.errors[field.name]]
            errors_html = f'<ul class="field-errors">{''.join(error_items)}</ul>'

        # Field container
        field_classes = ['form-field']
        if field.name in self.errors:
            field_classes.append('field-error')
        if field.required:
            field_classes.append('field-required')

        return f'''
        <div class="{' '.join(field_classes)}" data-field="{field.name}">
            {label_html}
            <div class="field-input">
                {widget_html}
                {help_html}
                {errors_html}
            </div>
        </div>
        '''

    def _render_form_actions(self) -> str:
        """Render form action buttons"""
        return '''
        <div class="form-actions">
            <button type="submit" class="btn btn-primary">Submit</button>
            <button type="reset" class="btn btn-secondary">Reset</button>
        </div>
        '''

    def to_dict(self) -> Dict[str, Any]:
        """Convert form to dictionary"""
        return {
            'config': {
                'name': self.config.name,
                'method': self.config.method,
                'action': self.config.action,
                'enctype': self.config.enctype,
                'theme': self.config.theme,
                'classes': self.config.classes
            },
            'fields': {
                name: {
                    'name': field.name,
                    'label': field.label,
                    'required': field.required,
                    'help_text': field.help_text,
                    'widget_type': field.widget.widget_type.value,
                    'value': field.widget.get_value(),
                    'errors': field.widget.get_errors()
                }
                for name, field in self.fields.items()
            },
            'errors': self.errors,
            'is_valid': self.is_valid,
            'csrf_token': self.csrf_token
        }

    def to_json(self) -> str:
        """Convert form to JSON"""
        return json.dumps(self.to_dict(), indent=2)


class FormBuilder:
    """Form builder for easy form creation"""

    def __init__(self, name: str, **config_kwargs):
        self.config = FormConfig(name=name, **config_kwargs)
        self.form = WidgetForm(self.config)

    def add_text(self, name: str, **kwargs) -> 'FormBuilder':
        """Add text input field"""
        from .widgets import TextWidget
        widget = TextWidget(name, **kwargs)
        self.form.add_field(name, widget, **kwargs)
        return self

    def add_email(self, name: str, **kwargs) -> 'FormBuilder':
        """Add email input field"""
        from .widgets import TextWidget
        widget = TextWidget(name, input_type='email', **kwargs)
        self.form.add_field(name, widget, **kwargs)
        return self

    def add_password(self, name: str, **kwargs) -> 'FormBuilder':
        """Add password input field"""
        from .widgets import TextWidget
        widget = TextWidget(name, input_type='password', masked=True, **kwargs)
        self.form.add_field(name, widget, **kwargs)
        return self

    def add_richtext(self, name: str, **kwargs) -> 'FormBuilder':
        """Add rich text field"""
        from .widgets import RichTextWidget
        widget = RichTextWidget(name, **kwargs)
        self.form.add_field(name, widget, **kwargs)
        return self

    def add_richselect(self, name: str, **kwargs) -> 'FormBuilder':
        """Add rich select field"""
        from .widgets import RichSelectWidget
        widget = RichSelectWidget(name, **kwargs)
        self.form.add_field(name, widget, **kwargs)
        return self

    def add_richtitle(self, name: str, **kwargs) -> 'FormBuilder':
        """Add rich title field"""
        from .widgets import RichTitleWidget
        widget = RichTitleWidget(name, **kwargs)
        self.form.add_field(name, widget, **kwargs)
        return self

    def add_field(self, name: str, widget: BaseWidget, **kwargs) -> 'FormBuilder':
        """Add custom field"""
        self.form.add_field(name, widget, **kwargs)
        return self

    def set_theme(self, theme: str) -> 'FormBuilder':
        """Set form theme"""
        self.config.theme = theme
        return self

    def add_class(self, css_class: str) -> 'FormBuilder':
        """Add CSS class to form"""
        if css_class not in self.config.classes:
            self.config.classes.append(css_class)
        return self

    def set_action(self, action: str) -> 'FormBuilder':
        """Set form action"""
        self.config.action = action
        return self

    def set_method(self, method: str) -> 'FormBuilder':
        """Set form method"""
        self.config.method = method
        return self

    def build(self) -> WidgetForm:
        """Build the form"""
        return self.form


# Convenience functions
def create_form(name: str, **kwargs) -> FormBuilder:
    """Create a new form builder"""
    return FormBuilder(name, **kwargs)


def quick_form(name: str, fields: Dict[str, Dict[str, Any]], **form_kwargs) -> WidgetForm:
    """Create a form quickly from field definitions"""
    builder = FormBuilder(name, **form_kwargs)

    for field_name, field_config in fields.items():
        field_type = field_config.pop('type', 'text')
        label = field_config.pop('label', field_name.title())

        if field_type == 'text':
            builder.add_text(field_name, label=label, **field_config)
        elif field_type == 'email':
            builder.add_email(field_name, label=label, **field_config)
        elif field_type == 'password':
            builder.add_password(field_name, label=label, **field_config)
        elif field_type == 'richtext':
            builder.add_richtext(field_name, label=label, **field_config)
        elif field_type == 'richselect':
            builder.add_richselect(field_name, label=label, **field_config)
        elif field_type == 'richtitle':
            builder.add_richtitle(field_name, label=label, **field_config)

    return builder.build()


__all__ = [
    'FormField', 'FormConfig', 'WidgetForm', 'FormBuilder',
    'create_form', 'quick_form'
]

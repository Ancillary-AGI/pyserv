# server_framework/templating/languages/jinja.py
import jinja2
from typing import Dict, Any
from pathlib import Path
from ...i18n import gettext, ngettext, format_date, format_number, format_currency
from ..engine import AbstractTemplateEngine

class JinjaTemplateEngine(AbstractTemplateEngine):
    """Jinja2 template engine implementation"""
    
    def __init__(self, template_dir: Path, **options):
        super().__init__(template_dir, **options)
        
        # Set up Jinja2 environment
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(self.template_dir)),
            autoescape=jinja2.select_autoescape(['html', 'xml']),
            **options
        )
        
        # Add i18n functions to Jinja2 environment
        self.env.globals.update({
            '_': gettext,
            'gettext': gettext,
            'ngettext': ngettext,
            'format_date': format_date,
            'format_number': format_number,
            'format_currency': format_currency,
        })
    
    async def render(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render a template with Jinja2"""
        template = self.env.get_template(template_name)
        return template.render(**context)
    
    async def render_string(self, template_string: str, context: Dict[str, Any]) -> str:
        """Render a template string with Jinja2"""
        template = self.env.from_string(template_string)
        return template.render(**context)

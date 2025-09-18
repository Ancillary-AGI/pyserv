"""
Email template engine integration.
"""

from typing import Optional, Dict, Any

from ..core.templating.engine import TemplateEngine


class EmailTemplateEngine:
    """Email template engine using Pydance's template system"""

    def __init__(self, template_engine: Optional[TemplateEngine] = None):
        self.template_engine = template_engine

    async def render_subject(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render email subject template"""
        if self.template_engine:
            return await self.template_engine.render_template(f"emails/{template_name}_subject.txt", context)
        else:
            # Fallback to simple string formatting
            return template_name.format(**context)

    async def render_body(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render email body template"""
        if self.template_engine:
            return await self.template_engine.render_template(f"emails/{template_name}_body.txt", context)
        else:
            # Fallback to simple string formatting
            return template_name.format(**context)

    async def render_html_body(self, template_name: str, context: Dict[str, Any]) -> Optional[str]:
        """Render email HTML body template"""
        if self.template_engine:
            try:
                return await self.template_engine.render_template(f"emails/{template_name}_body.html", context)
            except FileNotFoundError:
                return None
        else:
            # Fallback to simple string formatting
            return template_name.format(**context)

    async def render_template(self, template_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Render complete email template"""
        subject = await self.render_subject(template_name, context)
        body = await self.render_body(template_name, context)
        html_body = await self.render_html_body(template_name, context)

        return {
            'subject': subject,
            'body': body,
            'html_body': html_body,
        }

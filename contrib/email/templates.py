"""
Enhanced Email template engine integration with markdown support.

This module provides a comprehensive email template system that supports:
- Plain text email templates
- HTML email templates
- Markdown to HTML conversion
- Template inheritance and composition
- Context-aware rendering
- Fallback mechanisms for missing templates
"""

import re
from typing import Optional, Dict, Any, List, Union
from pathlib import Path

from pyserv.templating.engine import TemplateEngine


class MarkdownRenderer:
    """Simple markdown to HTML renderer for email content"""

    def __init__(self):
        # Basic markdown patterns for email-friendly HTML
        self.patterns = [
            # Headers
            (r'^### (.*)$', r'<h3>\1</h3>'),
            (r'^## (.*)$', r'<h2>\1</h2>'),
            (r'^# (.*)$', r'<h1>\1</h1>'),

            # Bold and Italic
            (r'\*\*(.*?)\*\*', r'<strong>\1</strong>'),
            (r'\*(.*?)\*', r'<em>\1</em>'),

            # Links
            (r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>'),

            # Lists
            (r'^\* (.*)$', r'<li>\1</li>'),
            (r'^[0-9]+\. (.*)$', r'<li>\1</li>'),

            # Line breaks
            (r'\n\n', r'<br><br>'),
            (r'\n', r'<br>'),
        ]

    def render(self, markdown_text: str) -> str:
        """Convert markdown to HTML"""
        if not markdown_text:
            return ""

        html = markdown_text

        # Apply patterns
        for pattern, replacement in self.patterns:
            html = re.sub(pattern, replacement, html, flags=re.MULTILINE)

        # Wrap lists
        html = self._wrap_lists(html)

        return html

    def _wrap_lists(self, html: str) -> str:
        """Wrap consecutive list items in <ul> or <ol> tags"""
        lines = html.split('\n')
        result = []
        in_list = False
        list_type = None

        for line in lines:
            if line.strip().startswith('<li>'):
                if not in_list:
                    # Start new list
                    if line.strip().startswith('<li>') and not any(c.isdigit() for c in line[:10]):
                        result.append('<ul>')
                        list_type = 'ul'
                    else:
                        result.append('<ol>')
                        list_type = 'ol'
                    in_list = True
                result.append(line)
            else:
                if in_list:
                    # Close previous list
                    result.append(f'</{list_type}>')
                    in_list = False
                    list_type = None
                result.append(line)

        # Close any remaining list
        if in_list:
            result.append(f'</{list_type}>')

        return '\n'.join(result)


class EmailTemplateEngine:
    """
    Enhanced email template engine using Pyserv 's template system with markdown support.

    Features:
    - Plain text and HTML template rendering
    - Markdown to HTML conversion
    - Template inheritance and composition
    - Context-aware rendering with fallbacks
    - Support for multiple template formats
    """

    def __init__(self, template_engine: Optional[TemplateEngine] = None):
        self.template_engine = template_engine
        self.markdown_renderer = MarkdownRenderer()

    async def render_subject(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render email subject template"""
        if self.template_engine:
            try:
                template = self.template_engine.from_file(f"templates/emails/{template_name}_subject.txt")
                return template.render(**context)
            except FileNotFoundError:
                # Fallback to simple string formatting
                return template_name.format(**context)
        else:
            # Fallback to simple string formatting
            return template_name.format(**context)

    async def render_body(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render email body template (plain text)"""
        if self.template_engine:
            try:
                template = self.template_engine.from_file(f"templates/emails/{template_name}_body.txt")
                return template.render(**context)
            except FileNotFoundError:
                # Fallback to simple string formatting
                return template_name.format(**context)
        else:
            # Fallback to simple string formatting
            return template_name.format(**context)

    async def render_html_body(self, template_name: str, context: Dict[str, Any]) -> Optional[str]:
        """Render email HTML body template"""
        if self.template_engine:
            try:
                template = self.template_engine.from_file(f"templates/emails/{template_name}_body.html")
                return template.render(**context)
            except FileNotFoundError:
                return None
        else:
            # Fallback to simple string formatting
            return template_name.format(**context)

    async def render_markdown_body(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render email body from markdown template"""
        if self.template_engine:
            try:
                template = self.template_engine.from_file(f"templates/emails/{template_name}_body.md")
                markdown_content = template.render(**context)
                return self.markdown_renderer.render(markdown_content)
            except FileNotFoundError:
                # Fallback to plain text
                return await self.render_body(template_name, context)
        else:
            # Fallback to simple string formatting
            return template_name.format(**context)

    async def render_template(self, template_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Render complete email template with all formats"""
        subject = await self.render_subject(template_name, context)
        body = await self.render_body(template_name, context)
        html_body = await self.render_html_body(template_name, context)
        markdown_body = await self.render_markdown_body(template_name, context)

        return {
            'subject': subject,
            'body': body,
            'html_body': html_body,
            'markdown_body': markdown_body,
        }

    async def render_multipart_template(self, template_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Render a multipart email template with both text and HTML versions.

        This method intelligently chooses the best available format:
        1. HTML template if available
        2. Markdown template converted to HTML if available
        3. Plain text template as fallback
        """
        template_data = await self.render_template(template_name, context)

        # Determine the best HTML content
        html_content = template_data.get('html_body')
        if not html_content:
            html_content = template_data.get('markdown_body')

        return {
            'subject': template_data['subject'],
            'text_body': template_data['body'],
            'html_body': html_content,
            'has_html': bool(html_content),
        }

    async def render_with_fallback(self, template_name: str, context: Dict[str, Any],
                                 preferred_format: str = 'html') -> Dict[str, Any]:
        """
        Render template with intelligent fallback chain.

        Args:
            template_name: Base name of the template
            context: Template context
            preferred_format: Preferred format ('html', 'markdown', 'text')

        Returns:
            Dict with rendered content and metadata about which format was used
        """
        formats = ['html', 'markdown', 'text']
        if preferred_format not in formats:
            preferred_format = 'html'

        # Reorder formats based on preference
        format_order = [preferred_format] + [f for f in formats if f != preferred_format]

        result = {
            'subject': await self.render_subject(template_name, context),
            'content': '',
            'format_used': None,
            'available_formats': []
        }

        # Try each format in order
        for fmt in format_order:
            try:
                if fmt == 'html':
                    content = await self.render_html_body(template_name, context)
                elif fmt == 'markdown':
                    content = await self.render_markdown_body(template_name, context)
                else:  # text
                    content = await self.render_body(template_name, context)

                if content:
                    result['content'] = content
                    result['format_used'] = fmt
                    break
            except Exception:
                continue

        # Check which formats are available
        for fmt in formats:
            try:
                if fmt == 'html':
                    await self.render_html_body(template_name, context)
                elif fmt == 'markdown':
                    await self.render_markdown_body(template_name, context)
                else:
                    await self.render_body(template_name, context)
                result['available_formats'].append(fmt)
            except Exception:
                continue

        return result

    def get_template_info(self, template_name: str) -> Dict[str, bool]:
        """Get information about available template formats"""
        if not self.template_engine:
            return {'text': False, 'html': False, 'markdown': False}

        # This would need to be implemented based on the template engine's capabilities
        # For now, return a basic structure
        return {
            'text': True,  # Assume text is always available as fallback
            'html': True,  # Assume HTML is available
            'markdown': True,  # Assume markdown is available
        }

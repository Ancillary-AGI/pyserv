"""
Email Template Engine Demo

This demo shows how to use the enhanced EmailTemplateEngine with markdown support.
It demonstrates various features including:
- Basic template rendering
- Markdown to HTML conversion
- Multipart email creation
- Template fallback mechanisms
- Context-aware rendering
"""

import asyncio
from pathlib import Path
from typing import Dict, Any

from pyserv.templating.engine import TemplateEngine
from pyserv.contrib.email.templates import EmailTemplateEngine


class EmailTemplateDemo:
    """Demo class showing email template engine usage"""

    def __init__(self):
        # Initialize template engine (in real app, this would be injected)
        self.template_engine = TemplateEngine()
        self.email_engine = EmailTemplateEngine(self.template_engine)

    async def demo_basic_rendering(self):
        """Demo basic template rendering"""
        print("=== Basic Template Rendering ===")

        context = {
            'user_name': 'John Doe',
            'company': 'Acme Corp',
            'login_url': 'https://example.com/login',
            'support_email': 'support@example.com'
        }

        # Render a welcome email template
        result = await self.email_engine.render_template('welcome', context)

        print(f"Subject: {result['subject']}")
        print(f"Text Body:\n{result['body']}")
        print(f"Has HTML: {'Yes' if result['html_body'] else 'No'}")
        print(f"Has Markdown: {'Yes' if result['markdown_body'] else 'No'}")
        print()

    async def demo_markdown_rendering(self):
        """Demo markdown template rendering"""
        print("=== Markdown Template Rendering ===")

        context = {
            'user_name': 'Jane Smith',
            'features': [
                'High-performance caching',
                'Real-time notifications',
                'Advanced security features',
                '24/7 monitoring'
            ],
            'dashboard_url': 'https://example.com/dashboard',
            'docs_url': 'https://docs.example.com'
        }

        # Render markdown template
        markdown_result = await self.email_engine.render_markdown_body('product_update', context)
        print("Markdown rendered as HTML:")
        print(markdown_result)
        print()

    async def demo_multipart_email(self):
        """Demo multipart email creation"""
        print("=== Multipart Email Creation ===")

        context = {
            'recipient_name': 'Alice Johnson',
            'order_id': 'ORD-2024-001',
            'items': [
                {'name': 'Widget A', 'quantity': 2, 'price': 29.99},
                {'name': 'Widget B', 'quantity': 1, 'price': 49.99}
            ],
            'total': 109.97,
            'tracking_url': 'https://example.com/track/ORD-2024-001'
        }

        # Render multipart template
        multipart = await self.email_engine.render_multipart_template('order_confirmation', context)

        print(f"Subject: {multipart['subject']}")
        print(f"Has HTML: {multipart['has_html']}")
        print(f"Text Body Preview: {multipart['text_body'][:100]}...")
        if multipart['html_body']:
            print(f"HTML Body Preview: {multipart['html_body'][:100]}...")
        print()

    async def demo_fallback_rendering(self):
        """Demo template fallback mechanisms"""
        print("=== Template Fallback Rendering ===")

        context = {
            'user_name': 'Bob Wilson',
            'reset_token': 'abc123def456'
        }

        # Try different preferred formats
        for preferred_format in ['html', 'markdown', 'text']:
            result = await self.email_engine.render_with_fallback(
                'password_reset', context, preferred_format
            )
            print(f"Preferred format: {preferred_format}")
            print(f"Format used: {result['format_used']}")
            print(f"Available formats: {result['available_formats']}")
            print(f"Content preview: {result['content'][:50]}...")
            print()

    async def demo_template_info(self):
        """Demo template information retrieval"""
        print("=== Template Information ===")

        info = self.email_engine.get_template_info('newsletter')
        print(f"Template info for 'newsletter': {info}")
        print()

    async def demo_markdown_features(self):
        """Demo specific markdown features"""
        print("=== Markdown Features Demo ===")

        # Sample markdown content
        markdown_content = """
# Welcome to Pyserv !

This is a **bold statement** and this is *emphasized text*.

## Features

Here are some key features:

* High-performance caching
* Real-time notifications
* Advanced security features
* 24/7 monitoring

## Getting Started

1. Visit our [dashboard](https://example.com/dashboard)
2. Read the [documentation](https://docs.example.com)
3. Contact [support](mailto:support@example.com)

## Code Example

```python
from pyserv import Application

app = Application()
app.run()
```

---

*This email was sent to you because you subscribed to our newsletter.*
        """

        # Render markdown
        html_output = self.email_engine.markdown_renderer.render(markdown_content)
        print("Original Markdown:")
        print(markdown_content)
        print("\nRendered HTML:")
        print(html_output)
        print()

    async def run_all_demos(self):
        """Run all demo methods"""
        print("🚀 Email Template Engine Demo")
        print("=" * 50)

        try:
            await self.demo_basic_rendering()
            await self.demo_markdown_rendering()
            await self.demo_multipart_email()
            await self.demo_fallback_rendering()
            await self.demo_template_info()
            await self.demo_markdown_features()

            print("✅ All demos completed successfully!")

        except Exception as e:
            print(f"❌ Demo failed with error: {e}")
            print("Note: This demo requires template files to be present.")
            print("Create template files in your templates/emails/ directory.")


def create_sample_templates():
    """Create sample template files for the demo"""
    templates_dir = Path("templates/emails")
    templates_dir.mkdir(parents=True, exist_ok=True)

    # Welcome email subject template
    subject_template = "Welcome to {{ company }}, {{ user_name }}!"
    (templates_dir / "welcome_subject.txt").write_text(subject_template)

    # Welcome email text body template
    text_template = """
Hello {{ user_name }},

Welcome to {{ company }}! We're excited to have you on board.

To get started, please visit: {{ login_url }}

If you have any questions, feel free to contact us at {{ support_email }}.

Best regards,
The {{ company }} Team
    """
    (templates_dir / "welcome_body.txt").write_text(text_template)

    # Welcome email HTML body template
    html_template = """
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <h2>Welcome to {{ company }}, {{ user_name }}!</h2>
    <p>We're excited to have you on board.</p>
    <p><a href="{{ login_url }}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Get Started</a></p>
    <p>If you have any questions, contact us at <a href="mailto:{{ support_email }}">{{ support_email }}</a></p>
    <p>Best regards,<br>The {{ company }} Team</p>
</div>
    """
    (templates_dir / "welcome_body.html").write_text(html_template)

    # Welcome email markdown template
    markdown_template = """
# Welcome to {{ company }}, {{ user_name }}!

We're excited to have you on board.

## Getting Started

1. Visit your [dashboard]({{ login_url }})
2. Complete your profile
3. Start exploring features

## Need Help?

Contact our support team at [{{ support_email }}](mailto:{{ support_email }})

---

*Best regards,*  
*The {{ company }} Team*
    """
    (templates_dir / "welcome_body.md").write_text(markdown_template)

    print(f"✅ Sample templates created in {templates_dir}")


async def main():
    """Main demo function"""
    print("Email Template Engine Demo")
    print("=" * 50)

    # Create sample templates
    create_sample_templates()

    # Run demos
    demo = EmailTemplateDemo()
    await demo.run_all_demos()

    # Show usage examples
    print("\n" + "=" * 50)
    print("📖 USAGE EXAMPLES")
    print("=" * 50)

    print("""
## Basic Usage

```python
from pyserv.contrib.email.templates import EmailTemplateEngine

# Initialize with template engine
email_engine = EmailTemplateEngine(template_engine)

# Render complete template
context = {'user_name': 'John', 'company': 'Acme'}
result = await email_engine.render_template('welcome', context)

# Access rendered content
print(result['subject'])
print(result['body'])
print(result['html_body'])
```

## Markdown Rendering

```python
# Render markdown template
markdown_html = await email_engine.render_markdown_body('newsletter', context)
```

## Multipart Emails

```python
# Create multipart email
multipart = await email_engine.render_multipart_template('order', context)
email_data = {
    'subject': multipart['subject'],
    'text_body': multipart['text_body'],
    'html_body': multipart['html_body'] if multipart['has_html'] else None
}
```

## Fallback Rendering

```python
# Render with fallback preferences
result = await email_engine.render_with_fallback(
    'notification', context, preferred_format='html'
)
print(f"Used format: {result['format_used']}")
```

## Template File Structure

Create templates in your template directory:

```
templates/
└── emails/
    ├── welcome_subject.txt      # Email subject
    ├── welcome_body.txt         # Plain text body
    ├── welcome_body.html        # HTML body
    └── welcome_body.md          # Markdown body (optional)
```

## Markdown Features Supported

- Headers (# ## ###)
- Bold and italic (**bold**, *italic*)
- Links [text](url)
- Lists (* item, 1. item)
- Code blocks
- Line breaks
    """)


if __name__ == "__main__":
    asyncio.run(main())

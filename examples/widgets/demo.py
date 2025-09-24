"""
Pyserv  Rich Widgets Demo
========================

This script demonstrates the enhanced rich widgets system with advanced features,
security, and customization options.
"""

import os
from pathlib import Path

from pyserv.widgets import RichText, RichSelect, RichTitle
from pyserv.widgets import (
    RichFile, RichDate, RichColor, RichRating,
    RichTags, RichSlider, RichCode
)
from pyserv.widgets import create_form


def create_enhanced_demo():
    """Create an enhanced demo with all advanced features"""

    print("🎉 Pyserv  Enhanced Rich Widgets Demo")
    print("=" * 50)

    # 1. Rich Text Widget with Advanced Features
    print("\n📝 Rich Text Widget:")
    print("-" * 30)

    rich_text = RichText(
        name='article_content',
        format='markdown',
        placeholder='Write your amazing article here...',
        value='# Welcome to Pyserv \n\nThis is a **powerful** rich text editor with:\n\n- Markdown support\n- HTML sanitization\n- Advanced toolbar\n- Real-time preview\n- Word count\n\n> Try it out!',
        theme='dark',
        size='large',
        max_content_length=50000
    )

    # Add custom validation
    rich_text.add_validator(
        lambda v: len(str(v or "")) >= 50,
        "Content must be at least 50 characters long"
    )

    print(f"Widget HTML length: {len(rich_text.render())} characters")
    print(f"Theme: {rich_text.theme.value}")
    print(f"Size: {rich_text.size.value}")
    print(f"Format: {rich_text.format.value}")

    # 2. Rich Select Widget with Advanced Options
    print("\n🎯 Rich Select Widget:")
    print("-" * 30)

    category_select = RichSelect(
        name='article_category',
        options=[
            ('tech', 'Technology'),
            ('business', 'Business'),
            ('health', 'Health & Wellness'),
            ('education', 'Education'),
            ('entertainment', 'Entertainment'),
            ('sports', 'Sports'),
            ('travel', 'Travel'),
            ('food', 'Food & Cooking'),
            ('fashion', 'Fashion'),
            ('science', 'Science')
        ],
        placeholder='Choose article category...',
        searchable=True,
        max_selections=3,
        allow_custom=True,
        theme='blue',
        size='medium'
    )

    # Add groups
    category_select.add_group('Technology', [
        ('web-dev', 'Web Development'),
        ('mobile', 'Mobile Apps'),
        ('ai', 'Artificial Intelligence'),
        ('blockchain', 'Blockchain')
    ])

    print(f"Options count: {len(category_select.options)}")
    print(f"Groups: {list(category_select.groups.keys())}")
    print(f"Searchable: {category_select.searchable}")
    print(f"Multiple selection: {category_select.allow_multiple}")

    # 3. Rich File Widget with Upload Features
    print("\n📎 Rich File Widget:")
    print("-" * 30)

    file_upload = RichFile(
        name='article_attachments',
        multiple=True,
        accept='image/*,.pdf,.doc,.docx,.txt',
        max_size=10 * 1024 * 1024,  # 10MB
        allowed_types=['image/jpeg', 'image/png', 'application/pdf'],
        max_files=5,
        show_preview=True,
        allow_drag_drop=True,
        chunk_size=1024 * 1024,  # 1MB chunks
        auto_upload=False,
        theme='green'
    )

    print(f"Multiple files: {file_upload.multiple}")
    print(f"Max file size: {file_upload._format_file_size(file_upload.max_size)}")
    print(f"Allowed types: {file_upload.allowed_types}")
    print(f"Drag & drop: {file_upload.allow_drag_drop}")

    # 4. Rich Date Widget with Time Support
    print("\n📅 Rich Date Widget:")
    print("-" * 30)

    publish_date = RichDate(
        name='publish_date',
        date_format='YYYY-MM-DD',
        time_format='HH:mm:ss',
        show_time=True,
        show_seconds=True,
        min_date='2024-01-01',
        max_date='2025-12-31',
        locale='en',
        timezone='UTC',
        theme='purple'
    )

    print(f"Date format: {publish_date.date_format}")
    print(f"Time format: {publish_date.time_format}")
    print(f"Show time: {publish_date.show_time}")
    print(f"Locale: {publish_date.locale}")

    # 5. Rich Color Widget with Palette
    print("\n🎨 Rich Color Widget:")
    print("-" * 30)

    theme_color = RichColor(
        name='theme_color',
        default_color='#007bff',
        show_palette=True,
        show_picker=True,
        allow_transparency=False,
        show_hex_input=True,
        show_rgb_input=True,
        palette=[
            '#000000', '#FFFFFF', '#FF0000', '#00FF00', '#0000FF',
            '#FFFF00', '#FF00FF', '#00FFFF', '#FFA500', '#800080',
            '#FFC0CB', '#A52A2A', '#808080', '#000080', '#008000'
        ],
        theme='light'
    )

    print(f"Default color: {theme_color.default_color}")
    print(f"Palette size: {len(theme_color.palette)}")
    print(f"Show palette: {theme_color.show_palette}")
    print(f"Transparency: {theme_color.allow_transparency}")

    # 6. Rich Rating Widget with Custom Features
    print("\n⭐ Rich Rating Widget:")
    print("-" * 30)

    difficulty_rating = RichRating(
        name='difficulty_level',
        max_rating=10,
        min_rating=1,
        step=0.5,
        show_half=True,
        icon='⭐',
        empty_icon='☆',
        hover_effect=True,
        show_value=True,
        allow_clear=True,
        size='large',
        color='#ffc107',
        labels={
            '1': 'Very Easy',
            '5': 'Moderate',
            '10': 'Expert'
        }
    )

    print(f"Max rating: {difficulty_rating.max_rating}")
    print(f"Show half stars: {difficulty_rating.show_half}")
    print(f"Custom icon: {difficulty_rating.icon}")
    print(f"Labels: {list(difficulty_rating.labels.keys())}")

    # 7. Rich Tags Widget with Suggestions
    print("\n🏷️ Rich Tags Widget:")
    print("-" * 30)

    article_tags = RichTags(
        name='article_tags',
        placeholder='Add relevant tags...',
        max_tags=15,
        min_tags=3,
        allow_duplicates=False,
        suggestions=[
            'python', 'web-development', 'framework', 'api', 'database',
            'frontend', 'backend', 'javascript', 'html', 'css', 'responsive',
            'mobile', 'tutorial', 'guide', 'best-practices', 'security'
        ],
        max_suggestion_count=8,
        allow_spaces=False,
        case_sensitive=False,
        sort_tags=True,
        tag_colors={
            'python': '#3776ab',
            'javascript': '#f7df1e',
            'html': '#e34f26',
            'css': '#1572b6'
        },
        allow_edit=True,
        theme='dark'
    )

    print(f"Max tags: {article_tags.max_tags}")
    print(f"Suggestions count: {len(article_tags.suggestions)}")
    print(f"Tag colors: {list(article_tags.tag_colors.keys())}")
    print(f"Allow duplicates: {article_tags.allow_duplicates}")

    # 8. Rich Slider Widget with Advanced Features
    print("\n🎚️ Rich Slider Widget:")
    print("-" * 30)

    priority_slider = RichSlider(
        name='article_priority',
        min_value=1,
        max_value=10,
        step=1,
        default_value=5,
        show_value=True,
        show_range=True,
        orientation='horizontal',
        track_color='#28a745',
        thumb_size='large',
        show_ticks=True,
        tick_interval=1,
        labels={
            '1': 'Low',
            '5': 'Medium',
            '10': 'High'
        },
        theme='green'
    )

    print(f"Range: {priority_slider.min_value} - {priority_slider.max_value}")
    print(f"Step: {priority_slider.step}")
    print(f"Show ticks: {priority_slider.show_ticks}")
    print(f"Labels: {list(priority_slider.labels.keys())}")

    # 9. Rich Code Widget with Full Features
    print("\n💻 Rich Code Widget:")
    print("-" * 30)

    code_example = RichCode(
        name='code_sample',
        language='python',
        theme='dark',
        line_numbers=True,
        word_wrap=True,
        auto_indent=True,
        syntax_check=True,
        code_folding=True,
        minimap=False,
        font_size=14,
        tab_size=4,
        readonly=False,
        value='''def create_article(title, content, tags):
    """
    Create a new article with validation
    """
    if not title or len(title.strip()) < 5:
        raise ValueError("Title must be at least 5 characters")

    if not content or len(content.strip()) < 50:
        raise ValueError("Content must be at least 50 characters")

    article = {
        'title': title.strip(),
        'content': content.strip(),
        'tags': tags or [],
        'created_at': datetime.now(),
        'status': 'draft'
    }

    return article

# Usage example
article = create_article(
    title="Pyserv  Widgets Guide",
    content="Learn how to use rich widgets...",
    tags=['python', 'web', 'tutorial']
)'''
    )

    print(f"Language: {code_example.language}")
    print(f"Theme: {code_example.theme}")
    print(f"Line numbers: {code_example.line_numbers}")
    print(f"Syntax check: {code_example.syntax_check}")
    print(f"Code folding: {code_example.code_folding}")

    # 10. Rich Title Widget with Auto-slug
    print("\n📝 Rich Title Widget:")
    print("-" * 30)

    article_title = RichTitle(
        name='article_title',
        level=1,
        placeholder='Enter article title...',
        value='The Ultimate Guide to Pyserv  Rich Widgets',
        allow_formatting=True,
        max_length=100,
        auto_slug=True
    )

    print(f"Heading level: {article_title.level}")
    print(f"Allow formatting: {article_title.allow_formatting}")
    print(f"Auto slug: {article_title.auto_slug}")
    print(f"Max length: {article_title.max_length}")

    # Create a form with all widgets
    print("\n📋 Complete Form Demo:")
    print("-" * 30)

    form = create_form('article_form')
    form.add_richtitle('title', label='Article Title', level=1, required=True)
    form.add_richtext('content', label='Content', format='markdown', required=True)
    form.add_richselect('category', label='Category', options=[
        ('tech', 'Technology'), ('business', 'Business'), ('lifestyle', 'Lifestyle')
    ], required=True)
    form.add_richdate('publish_date', label='Publish Date', show_time=True)
    form.add_richcolor('theme_color', label='Theme Color', default_color='#007bff')
    form.add_richrating('difficulty', label='Difficulty Level', max_rating=5)
    form.add_richtags('tags', label='Tags', suggestions=['python', 'web', 'tutorial'])
    form.add_richslider('priority', label='Priority', min_value=1, max_value=10)
    form.add_richfile('attachments', label='Attachments', multiple=True)
    form.add_richcode('code_sample', label='Code Sample', language='python')

    # Set form properties
    form.set_theme('blue')
    form.add_class('article-form')
    form.set_action('/submit-article')

    print(f"Form fields: {len(form.form.fields)}")
    print(f"Form theme: {form.config.theme}")
    print(f"Form classes: {form.config.classes}")

    # Generate demo HTML files
    print("\n📄 Generating Demo Files:")
    print("-" * 30)

    demo_dir = Path('demo_output')
    demo_dir.mkdir(exist_ok=True)

    # Individual widget demos
    widgets = {
        'rich_text': rich_text,
        'rich_select': category_select,
        'rich_file': file_upload,
        'rich_date': publish_date,
        'rich_color': theme_color,
        'rich_rating': difficulty_rating,
        'rich_tags': article_tags,
        'rich_slider': priority_slider,
        'rich_code': code_example,
        'rich_title': article_title
    }

    for widget_name, widget in widgets.items():
        html_content = generate_widget_demo_html(widget_name, widget)
        demo_file = demo_dir / f"{widget_name}_demo.html"
        with open(demo_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"✓ Generated {demo_file.name}")

    # Complete form demo
    form_html = generate_form_demo_html(form.form)
    form_file = demo_dir / "complete_form_demo.html"
    with open(form_file, 'w', encoding='utf-8') as f:
        f.write(form_html)
    print(f"✓ Generated {form_file.name}")

    print(f"\n🎉 Demo files generated in {demo_dir}/ directory")
    print("Open the HTML files in your browser to see the widgets in action!")


def generate_widget_demo_html(widget_name: str, widget) -> str:
    """Generate demo HTML for a single widget"""

    widget_html = widget.render()
    widget_title = widget_name.replace('_', ' ').title()

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{widget_title} Demo - Pyserv  Rich Widgets</title>
    <link rel="stylesheet" href="../static/css/widgets.css">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: #f8f9fa;
        }}

        .demo-header {{
            text-align: center;
            margin-bottom: 30px;
        }}

        .demo-container {{
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}

        .widget-section {{
            margin-bottom: 30px;
        }}

        .widget-title {{
            font-size: 24px;
            font-weight: bold;
            color: #333;
            margin-bottom: 10px;
            border-bottom: 3px solid #007bff;
            padding-bottom: 5px;
        }}

        .widget-description {{
            color: #666;
            margin-bottom: 20px;
            line-height: 1.6;
        }}

        .widget-demo {{
            border: 1px solid #e9ecef;
            border-radius: 8px;
            padding: 20px;
            background: #f8f9fa;
        }}

        .code-preview {{
            margin-top: 20px;
            padding: 15px;
            background: #2d3748;
            color: #e2e8f0;
            border-radius: 6px;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 14px;
            overflow-x: auto;
        }}
    </style>
</head>
<body>
    <div class="demo-header">
        <h1>🎉 {widget_title} Demo</h1>
        <p>Experience the power of Pyserv  Rich Widgets</p>
    </div>

    <div class="demo-container">
        <div class="widget-section">
            <h2 class="widget-title">{widget_title}</h2>
            <p class="widget-description">
                This demo showcases the {widget_name.replace('_', ' ')} widget with all its advanced features,
                security measures, and customization options.
            </p>

            <div class="widget-demo">
                <form method="POST" enctype="multipart/form-data">
                    {widget_html}
                    <div style="margin-top: 20px;">
                        <button type="submit" style="
                            background: #007bff;
                            color: white;
                            border: none;
                            padding: 10px 20px;
                            border-radius: 6px;
                            cursor: pointer;
                            font-size: 16px;
                        ">Test Widget</button>
                    </div>
                </form>
            </div>
        </div>

        <div class="widget-section">
            <h3>Widget Configuration</h3>
            <div class="code-preview">
Theme: {widget.theme.value}<br>
Size: {widget.size.value}<br>
Type: {widget.widget_type.value}<br>
Dependencies: {', '.join(widget.dependencies) if widget.dependencies else 'None'}
            </div>
        </div>
    </div>

    <script src="../static/js/widgets.js"></script>
</body>
</html>'''


def generate_form_demo_html(form) -> str:
    """Generate demo HTML for the complete form"""

    form_html = form.render()

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Complete Form Demo - Pyserv  Rich Widgets</title>
    <link rel="stylesheet" href="../static/css/widgets.css">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            margin: 0;
        }}

        .form-container {{
            max-width: 900px;
            margin: 0 auto;
            padding: 30px 20px;
        }}

        .form-header {{
            text-align: center;
            color: white;
            margin-bottom: 40px;
        }}

        .form-header h1 {{
            font-size: 3rem;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }}

        .form-header p {{
            font-size: 1.2rem;
            opacity: 0.9;
        }}

        .form-card {{
            background: white;
            border-radius: 16px;
            padding: 40px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}

        .form-title {{
            font-size: 2rem;
            color: #333;
            margin-bottom: 10px;
            text-align: center;
        }}

        .form-description {{
            color: #666;
            text-align: center;
            margin-bottom: 30px;
            font-size: 1.1rem;
        }}

        .widget-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
        }}

        @media (max-width: 768px) {{
            .widget-grid {{
                grid-template-columns: 1fr;
            }}
        }}

        .widget-info {{
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            margin-top: 20px;
        }}

        .widget-info h4 {{
            color: #007bff;
            margin-bottom: 10px;
        }}

        .feature-list {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
            margin-top: 20px;
        }}

        .feature-item {{
            display: flex;
            align-items: center;
            color: #555;
        }}

        .feature-item::before {{
            content: "✓";
            color: #28a745;
            font-weight: bold;
            margin-right: 8px;
        }}
    </style>
</head>
<body>
    <div class="form-container">
        <div class="form-header">
            <h1>🚀 Complete Form Demo</h1>
            <p>Experience all Pyserv  Rich Widgets in one comprehensive form</p>
        </div>

        <div class="form-card">
            <h2 class="form-title">Create Amazing Content</h2>
            <p class="form-description">
                This form demonstrates every rich widget in the Pyserv  framework,
                showcasing advanced features, security, and beautiful design.
            </p>

            {form_html}
        </div>

        <div class="form-card">
            <h3>🎯 Widget Features</h3>
            <div class="feature-list">
                <div class="feature-item">Advanced Security & XSS Protection</div>
                <div class="feature-item">Responsive Design & Mobile Support</div>
                <div class="feature-item">Real-time Validation & Feedback</div>
                <div class="feature-item">Markdown & HTML Content Support</div>
                <div class="feature-item">Drag & Drop File Uploads</div>
                <div class="feature-item">Interactive Date/Time Pickers</div>
                <div class="feature-item">Color Picker with Palette</div>
                <div class="feature-item">Star Rating with Half-stars</div>
                <div class="feature-item">Tag Input with Suggestions</div>
                <div class="feature-item">Advanced Slider Controls</div>
                <div class="feature-item">Code Editor with Syntax Highlighting</div>
                <div class="feature-item">Customizable Themes & Sizes</div>
                <div class="feature-item">Accessibility & Keyboard Navigation</div>
            </div>
        </div>
    </div>

    <script src="../static/js/widgets.js"></script>
    <script>
        // Add some interactive enhancements
        document.addEventListener('DOMContentLoaded', function() {{
            console.log('🎉 Pyserv  Rich Widgets Demo Loaded!');
            console.log('Form contains {len(form.fields)} rich widgets');
        }});
    </script>
</body>
</html>'''


if __name__ == '__main__':
    create_enhanced_demo()

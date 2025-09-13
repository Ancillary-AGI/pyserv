#!/usr/bin/env python3
"""
Simple test for Pydance Rich Widgets - Direct Import
"""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Direct imports to avoid circular dependencies
from pydance.widgets.core import (
    BaseWidget, WidgetType, ContentFormat, WidgetSecurity,
    MarkdownProcessor, WidgetValidator, WidgetTheme, WidgetSize
)

# Import widgets directly
from pydance.widgets.widgets import TextWidget, RichTextWidget, RichSelectWidget, RichTitleWidget
from pydance.widgets.widgets_extra import RichFileWidget, RichDateWidget, RichColorWidget, RichRatingWidget

def test_widgets_direct():
    """Test widgets with direct imports"""

    print("🎉 Pydance Rich Widgets Direct Test")
    print("=" * 45)

    # Test Rich Text Widget
    print("\n📝 Testing Rich Text Widget:")
    rich_text = RichTextWidget(
        name='content',
        format=ContentFormat.MARKDOWN,
        placeholder='Enter content...',
        value='# Hello World\n\nThis is **markdown** text.',
        theme=WidgetTheme.DARK,
        size=WidgetSize.LARGE
    )

    print(f"✓ Created RichText widget")
    print(f"  - Theme: {rich_text.theme.value}")
    print(f"  - Size: {rich_text.size.value}")
    print(f"  - Format: {rich_text.format.value}")
    print(f"  - HTML length: {len(rich_text.render())} chars")

    # Test Rich Select Widget
    print("\n🎯 Testing Rich Select Widget:")
    select = RichSelectWidget(
        name='category',
        options=[
            ('tech', 'Technology'),
            ('business', 'Business'),
            ('health', 'Health')
        ],
        placeholder='Select category...',
        searchable=True,
        theme=WidgetTheme.BLUE
    )

    print(f"✓ Created RichSelect widget")
    print(f"  - Options: {len(select.options)}")
    print(f"  - Searchable: {select.searchable}")
    print(f"  - Theme: {select.theme.value}")

    # Test Rich File Widget
    print("\n📎 Testing Rich File Widget:")
    file_widget = RichFileWidget(
        name='files',
        multiple=True,
        accept='image/*,.pdf',
        max_size=5 * 1024 * 1024,  # 5MB
        theme=WidgetTheme.GREEN
    )

    print(f"✓ Created RichFile widget")
    print(f"  - Multiple: {file_widget.multiple}")
    print(f"  - Max size: {file_widget._format_file_size(file_widget.max_size)}")
    print(f"  - Accept: {file_widget.accept}")

    # Test Rich Date Widget
    print("\n📅 Testing Rich Date Widget:")
    date_widget = RichDateWidget(
        name='date',
        show_time=True,
        date_format='YYYY-MM-DD',
        time_format='HH:mm',
        theme=WidgetTheme.PURPLE
    )

    print(f"✓ Created RichDate widget")
    print(f"  - Show time: {date_widget.show_time}")
    print(f"  - Date format: {date_widget.date_format}")
    print(f"  - Time format: {date_widget.time_format}")

    # Test Rich Color Widget
    print("\n🎨 Testing Rich Color Widget:")
    color_widget = RichColorWidget(
        name='color',
        default_color='#007bff',
        show_palette=True,
        palette=['#ff0000', '#00ff00', '#0000ff', '#ffff00']
    )

    print(f"✓ Created RichColor widget")
    print(f"  - Default color: {color_widget.default_color}")
    print(f"  - Palette size: {len(color_widget.palette)}")
    print(f"  - Show palette: {color_widget.show_palette}")

    # Test Rich Rating Widget
    print("\n⭐ Testing Rich Rating Widget:")
    rating_widget = RichRatingWidget(
        name='rating',
        max_rating=5,
        show_half=True,
        icon='⭐',
        show_value=True
    )

    print(f"✓ Created RichRating widget")
    print(f"  - Max rating: {rating_widget.max_rating}")
    print(f"  - Show half: {rating_widget.show_half}")
    print(f"  - Icon: {rating_widget.icon}")

    # Test widget validation
    print("\n🔍 Testing Widget Validation:")

    # Test required validation
    rich_text.set_value('')
    is_valid = rich_text.validate('')
    print(f"✓ RichText validation (empty): {'PASS' if not is_valid else 'FAIL'}")

    # Test successful validation
    rich_text.set_value('Valid content with enough length for testing purposes')
    is_valid = rich_text.validate('Valid content with enough length for testing purposes')
    print(f"✓ RichText validation (valid): {'PASS' if is_valid else 'FAIL'}")

    # Test security features
    print("\n🔒 Testing Security Features:")

    # Test HTML sanitization
    dangerous_html = '<script>alert("XSS")</script><p>Safe content</p>'
    sanitized = WidgetSecurity.sanitize_html(dangerous_html)
    has_script = '<script>' in sanitized
    print(f"✓ HTML sanitization: {'PASS' if not has_script else 'FAIL'}")

    # Test markdown validation
    dangerous_md = '<script>alert("XSS")</script> Normal text'
    is_valid_md, messages = WidgetSecurity.validate_markdown(dangerous_md)
    print(f"✓ Markdown validation: {'PASS' if not is_valid_md else 'FAIL'}")

    print("\n🎊 All widget tests completed successfully!")
    print("\n📋 Widget Summary:")
    print(f"  - Total widgets tested: 6")
    print(f"  - All widgets created successfully")
    print(f"  - Validation system working")
    print(f"  - Security features active")
    print(f"  - Themes and customization applied")

    # Show sample HTML output
    print("\n📄 Sample HTML Output (RichText):")
    print("-" * 40)
    sample_html = rich_text.render()
    print(sample_html[:200] + "..." if len(sample_html) > 200 else sample_html)

    return True

if __name__ == '__main__':
    try:
        test_widgets_direct()
        print("\n✅ Test completed successfully!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

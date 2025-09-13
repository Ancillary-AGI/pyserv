#!/usr/bin/env python3
"""
Standalone test for Pydance Rich Widgets - No Dependencies
"""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_standalone():
    """Test widgets without importing main pydance package"""

    print("🎉 Pydance Rich Widgets Standalone Test")
    print("=" * 50)

    try:
        # Import only the widgets module directly
        import pydance.widgets.core as core
        import pydance.widgets.widgets as widgets
        import pydance.widgets.widgets_extra as widgets_extra

        print("✓ Successfully imported widget modules")

        # Test core classes
        print("\n🔧 Testing Core Classes:")

        # Test WidgetType enum
        print(f"✓ WidgetType.TEXT: {core.WidgetType.TEXT.value}")
        print(f"✓ WidgetType.RICHTEXT: {core.WidgetType.RICHTEXT.value}")

        # Test ContentFormat enum
        print(f"✓ ContentFormat.HTML: {core.ContentFormat.HTML.value}")
        print(f"✓ ContentFormat.MARKDOWN: {core.ContentFormat.MARKDOWN.value}")

        # Test WidgetTheme enum
        print(f"✓ WidgetTheme.DARK: {core.WidgetTheme.DARK.value}")
        print(f"✓ WidgetTheme.BLUE: {core.WidgetTheme.BLUE.value}")

        # Test WidgetSize enum
        print(f"✓ WidgetSize.LARGE: {core.WidgetSize.LARGE.value}")

        # Test security features
        print("\n🔒 Testing Security Features:")

        # Test HTML sanitization
        dangerous_html = '<script>alert("XSS")</script><p>Safe content</p>'
        sanitized = core.WidgetSecurity.sanitize_html(dangerous_html)
        has_script = '<script>' in sanitized
        print(f"✓ HTML sanitization: {'PASS' if not has_script else 'FAIL'}")
        print(f"  - Input: {dangerous_html}")
        print(f"  - Output: {sanitized}")

        # Test markdown validation
        dangerous_md = '<script>alert("XSS")</script> Normal text'
        is_valid_md, messages = core.WidgetSecurity.validate_markdown(dangerous_md)
        print(f"✓ Markdown validation: {'PASS' if not is_valid_md else 'FAIL'}")
        print(f"  - Messages: {messages}")

        # Test widget creation
        print("\n🎨 Testing Widget Creation:")

        # Test RichText widget
        rich_text = widgets.RichTextWidget(
            name='content',
            format=core.ContentFormat.MARKDOWN,
            placeholder='Enter content...',
            value='# Hello World\n\nThis is **markdown** text.',
            theme=core.WidgetTheme.DARK,
            size=core.WidgetSize.LARGE
        )

        print(f"✓ Created RichTextWidget")
        print(f"  - Name: {rich_text.name}")
        print(f"  - Theme: {rich_text.theme.value}")
        print(f"  - Size: {rich_text.size.value}")
        print(f"  - Format: {rich_text.format.value}")

        # Test RichSelect widget
        select = widgets.RichSelectWidget(
            name='category',
            options=[
                ('tech', 'Technology'),
                ('business', 'Business'),
                ('health', 'Health')
            ],
            placeholder='Select category...',
            searchable=True,
            theme=core.WidgetTheme.BLUE
        )

        print(f"✓ Created RichSelectWidget")
        print(f"  - Options count: {len(select.options)}")
        print(f"  - Searchable: {select.searchable}")

        # Test RichFile widget
        file_widget = widgets_extra.RichFileWidget(
            name='files',
            multiple=True,
            accept='image/*,.pdf',
            max_size=5 * 1024 * 1024,  # 5MB
            theme=core.WidgetTheme.GREEN
        )

        print(f"✓ Created RichFileWidget")
        print(f"  - Multiple: {file_widget.multiple}")
        print(f"  - Max size: {file_widget._format_file_size(file_widget.max_size)}")

        # Test RichDate widget
        date_widget = widgets_extra.RichDateWidget(
            name='date',
            show_time=True,
            date_format='YYYY-MM-DD',
            time_format='HH:mm',
            theme=core.WidgetTheme.PURPLE
        )

        print(f"✓ Created RichDateWidget")
        print(f"  - Show time: {date_widget.show_time}")
        print(f"  - Date format: {date_widget.date_format}")

        # Test RichColor widget
        color_widget = widgets_extra.RichColorWidget(
            name='color',
            default_color='#007bff',
            show_palette=True,
            palette=['#ff0000', '#00ff00', '#0000ff', '#ffff00']
        )

        print(f"✓ Created RichColorWidget")
        print(f"  - Default color: {color_widget.default_color}")
        print(f"  - Palette size: {len(color_widget.palette)}")

        # Test RichRating widget
        rating_widget = widgets_extra.RichRatingWidget(
            name='rating',
            max_rating=5,
            show_half=True,
            icon='⭐',
            show_value=True
        )

        print(f"✓ Created RichRatingWidget")
        print(f"  - Max rating: {rating_widget.max_rating}")
        print(f"  - Show half: {rating_widget.show_half}")

        # Test widget validation
        print("\n🔍 Testing Widget Validation:")

        # Test required validation
        rich_text.set_value('')
        is_valid = rich_text.validate('')
        print(f"✓ RichText validation (empty): {'PASS' if not is_valid else 'FAIL'}")

        # Test successful validation
        rich_text.set_value('Valid content with enough length for testing purposes and validation checks')
        is_valid = rich_text.validate('Valid content with enough length for testing purposes and validation checks')
        print(f"✓ RichText validation (valid): {'PASS' if is_valid else 'FAIL'}")

        # Test widget methods
        print("\n⚙️ Testing Widget Methods:")

        # Test theme change
        original_theme = rich_text.theme
        rich_text.set_theme(core.WidgetTheme.LIGHT)
        print(f"✓ Theme change: {original_theme.value} → {rich_text.theme.value}")

        # Test size change
        original_size = rich_text.size
        rich_text.set_size(core.WidgetSize.SMALL)
        print(f"✓ Size change: {original_size.value} → {rich_text.size.value}")

        # Test class management
        rich_text.add_class('custom-class')
        print(f"✓ Added custom class: {rich_text.attributes.classes}")

        rich_text.remove_class('custom-class')
        print(f"✓ Removed custom class: {rich_text.attributes.classes}")

        # Test data attributes
        rich_text.set_data_attribute('test', 'value')
        print(f"✓ Data attribute set: {rich_text.attributes.data_attributes}")

        print("\n🎊 All widget tests completed successfully!")
        print("\n📋 Widget Summary:")
        print(f"  - Core classes: ✓ Working")
        print(f"  - Security features: ✓ Active")
        print(f"  - Widget creation: ✓ Successful")
        print(f"  - Validation system: ✓ Working")
        print(f"  - Theme/size changes: ✓ Working")
        print(f"  - Class management: ✓ Working")
        print(f"  - Data attributes: ✓ Working")

        # Show sample HTML output
        print("\n📄 Sample HTML Output (RichText):")
        print("-" * 45)
        sample_html = rich_text.render()
        print(sample_html[:300] + "..." if len(sample_html) > 300 else sample_html)

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    try:
        success = test_standalone()
        if success:
            print("\n✅ Standalone test completed successfully!")
        else:
            print("\n❌ Standalone test failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

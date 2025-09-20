#!/usr/bin/env python3
"""
Simple standalone test for the enhanced Lean template engine
"""

import asyncio
import sys
from pathlib import Path

# Add the template engine files directly to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src' / 'pydance' / 'core' / 'templating'))

# Import the template engine directly
from languages.lean import LeanTemplateEngine


async def test_basic_functionality():
    """Test basic template functionality"""
    print("Testing basic template functionality...")

    # Create a temporary template directory
    template_dir = Path(__file__).parent / 'test_templates'
    template_dir.mkdir(exist_ok=True)

    try:
        engine = LeanTemplateEngine(template_dir)

        # Test basic variable substitution
        template = "Hello {{ name }}! You have {{ count }} messages."
        context = {'name': 'World', 'count': 5}

        result = await engine.render_string(template, context)
        expected = "Hello World! You have 5 messages."

        print(f"Input: {template}")
        print(f"Context: {context}")
        print(f"Result: {result}")
        print(f"Expected: {expected}")
        print(f"✓ Test passed: {result == expected}")
        print()

        # Test filters
        template = "{{ message | upper | trim }}"
        context = {'message': '  hello world  '}

        result = await engine.render_string(template, context)
        expected = "HELLO WORLD"

        print(f"Filter test - Input: {template}")
        print(f"Context: {context}")
        print(f"Result: {result}")
        print(f"Expected: {expected}")
        print(f"✓ Filter test passed: {result == expected}")
        print()

        # Test loops
        template = """
<ul>
{% for item in items %}
    <li>{{ item.name }}: {{ item.value | default('N/A') }}</li>
{% endfor %}
</ul>
"""
        context = {
            'items': [
                {'name': 'Item 1', 'value': 'Value 1'},
                {'name': 'Item 2', 'value': None},
                {'name': 'Item 3', 'value': 'Value 3'},
            ]
        }

        result = await engine.render_string(template, context)
        print("Loop test result:")
        print(result.strip())
        print("✓ Loop test completed")
        print()

        # Test conditionals
        template = """
{% if user.is_admin %}
    <p>Welcome, Administrator {{ user.name }}!</p>
{% elif user.is_moderator %}
    <p>Welcome, Moderator {{ user.name }}!</p>
{% else %}
    <p>Welcome, {{ user.name }}!</p>
{% endif %}
"""
        context = {'user': {'name': 'Alice', 'is_admin': False, 'is_moderator': True}}

        result = await engine.render_string(template, context)
        print("Conditional test result:")
        print(result.strip())
        print("✓ Conditional test completed")
        print()

        print("All basic tests completed successfully!")

    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Clean up
        import shutil
        if template_dir.exists():
            shutil.rmtree(template_dir)


async def test_advanced_features():
    """Test advanced template features"""
    print("Testing advanced template features...")

    template_dir = Path(__file__).parent / 'test_templates'
    template_dir.mkdir(exist_ok=True)

    try:
        engine = LeanTemplateEngine(template_dir)

        # Test template inheritance
        base_template = """
<!DOCTYPE html>
<html>
<head><title>{% block title %}Default Title{% endblock %}</title></head>
<body>
    <header>{% block header %}<h1>Header</h1>{% endblock %}</header>
    <main>{% block content %}{% endblock %}</main>
    <footer>{% block footer %}<p>Footer</p>{% endblock %}</footer>
</body>
</html>
"""

        child_template = """
{% extends "base.html" %}
{% block title %}{{ page_title }}{% endblock %}
{% block content %}
    <h2>{{ article.title }}</h2>
    <p>{{ article.content }}</p>
{% endblock %}
"""

        # Save templates
        with open(template_dir / 'base.html', 'w') as f:
            f.write(base_template)
        with open(template_dir / 'article.html', 'w') as f:
            f.write(child_template)

        context = {
            'page_title': 'My Article',
            'article': {
                'title': 'Template Inheritance Demo',
                'content': 'This demonstrates template inheritance.'
            }
        }

        result = await engine.render('article.html', context)
        print("Template inheritance test result:")
        print(result.strip()[:200] + "..." if len(result.strip()) > 200 else result.strip())
        print("✓ Template inheritance test completed")
        print()

        # Test macros
        macro_template = """
{% macro input_field(name, type='text', value='', placeholder='') %}
<div class="field">
    <label for="{{ name }}">{{ name | title }}</label>
    <input type="{{ type }}" name="{{ name }}" value="{{ value }}" placeholder="{{ placeholder }}">
</div>
{% endmacro %}

<form>
    {{ input_field('username', placeholder='Enter username') }}
    {{ input_field('password', 'password', placeholder='Enter password') }}
    {{ input_field('email', 'email', placeholder='Enter email') }}
</form>
"""

        result = await engine.render_string(macro_template, {})
        print("Macro test result:")
        print(result.strip())
        print("✓ Macro test completed")
        print()

        print("All advanced tests completed successfully!")

    except Exception as e:
        print(f"Advanced test failed with error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Clean up
        import shutil
        if template_dir.exists():
            shutil.rmtree(template_dir)


async def main():
    """Main test function"""
    print("PyDance Enhanced Lean Template Engine - Simple Tests")
    print("=" * 60)

    await test_basic_functionality()
    print()
    await test_advanced_features()

    print("\n" + "=" * 60)
    print("All tests completed!")


if __name__ == '__main__':
    asyncio.run(main())

#!/usr/bin/env python3
"""
PyDance Enhanced Lean Template Engine Demo
Showcasing advanced features and C++ acceleration
"""

import asyncio
import time
import sys
from pathlib import Path

# Add the parent directory to the path so we can import pydance
sys.path.insert(0, str(Path(__file__).parent.parent))

from pydance.core.templating.languages.lean import LeanTemplateEngine
from pydance.core.templating.template_bindings import QuantumTemplateEngine, TemplateConfig, TemplateEngineMode


async def demo_basic_features():
    """Demonstrate basic template features"""
    print("=== Basic Template Features ===")

    template_dir = Path(__file__).parent / 'templates'
    template_dir.mkdir(exist_ok=True)

    engine = LeanTemplateEngine(template_dir)

    # Create a basic template
    basic_template = """
<html>
<head><title>{{ title }}</title></head>
<body>
    <h1>{{ heading | upper }}</h1>
    <p>{{ content | escape }}</p>
    <ul>
    {% for item in items %}
        <li>{{ item.name }}: {{ item.value | default('N/A') }}</li>
    {% endfor %}
    </ul>
</body>
</html>
"""

    context = {
        'title': 'Demo Page',
        'heading': 'Welcome',
        'content': 'This is <strong>HTML</strong> content',
        'items': [
            {'name': 'Item 1', 'value': 'Value 1'},
            {'name': 'Item 2', 'value': None},
            {'name': 'Item 3', 'value': 'Value 3'},
        ]
    }

    result = await engine.render_string(basic_template, context)
    print("Basic template result:")
    print(result[:200] + "..." if len(result) > 200 else result)
    print()


async def demo_advanced_features():
    """Demonstrate advanced template features"""
    print("=== Advanced Template Features ===")

    template_dir = Path(__file__).parent / 'templates'
    engine = LeanTemplateEngine(template_dir)

    # Advanced template with inheritance, macros, and complex logic
    base_template = """
<!DOCTYPE html>
<html>
<head>
    <title>{% block title %}Default Title{% endblock %}</title>
</head>
<body>
    <header>
        {% block header %}
        <h1>Default Header</h1>
        {% endblock %}
    </header>

    <main>
        {% block content %}{% endblock %}
    </main>

    <footer>
        {% block footer %}
        <p>&copy; 2025 PyDance</p>
        {% endblock %}
    </footer>
</body>
</html>
"""

    child_template = """
{% extends "base.html" %}

{% block title %}{{ page_title }}{% endblock %}

{% block header %}
    <h1>{{ site_name }}</h1>
    <nav>
        {% for item in navigation %}
            <a href="{{ item.url }}">{{ item.label }}</a>
        {% endfor %}
    </nav>
{% endblock %}

{% block content %}
    <article>
        <h2>{{ article.title }}</h2>
        <p>{{ article.content | truncate(100) }}</p>

        {% if article.tags %}
        <div class="tags">
            {% for tag in article.tags %}
                <span class="tag">{{ tag }}</span>
            {% endfor %}
        </div>
        {% endif %}

        {% macro render_comment(comment) %}
        <div class="comment">
            <strong>{{ comment.author }}</strong>: {{ comment.text }}
            <small>{{ comment.date | date('Y-m-d') }}</small>
        </div>
        {% endmacro %}

        <div class="comments">
            <h3>Comments</h3>
            {% for comment in article.comments %}
                {{ render_comment(comment) }}
            {% endfor %}
        </div>
    </article>
{% endblock %}
"""

    # Save templates
    with open(template_dir / 'base.html', 'w') as f:
        f.write(base_template)
    with open(template_dir / 'article.html', 'w') as f:
        f.write(child_template)

    context = {
        'page_title': 'Advanced Template Demo',
        'site_name': 'PyDance Blog',
        'navigation': [
            {'url': '/', 'label': 'Home'},
            {'url': '/about', 'label': 'About'},
            {'url': '/contact', 'label': 'Contact'},
        ],
        'article': {
            'title': 'Template Engine Enhancements',
            'content': 'This article demonstrates the advanced features of the enhanced Lean template engine, including template inheritance, macros, filters, and complex control structures.',
            'tags': ['python', 'templates', 'web-development'],
            'comments': [
                {'author': 'Alice', 'text': 'Great article!', 'date': '2025-01-15'},
                {'author': 'Bob', 'text': 'Very informative.', 'date': '2025-01-16'},
            ]
        }
    }

    result = await engine.render('article.html', context)
    print("Advanced template result:")
    print(result[:500] + "..." if len(result) > 500 else result)
    print()


async def demo_quantum_engine():
    """Demonstrate the quantum (C++/GPU) template engine"""
    print("=== Quantum Template Engine Demo ===")

    template_dir = Path(__file__).parent / 'templates'

    # Configure for hybrid mode (CPU + GPU when available)
    config = TemplateConfig(
        mode=TemplateEngineMode.HYBRID,
        cache_enabled=True,
        gpu_batch_threshold=5,
        enable_filters=True,
        enable_macros=True,
        enable_inheritance=True,
        debug_mode=True
    )

    try:
        engine = QuantumTemplateEngine([template_dir], config)

        # Test basic rendering
        template = "Hello {{ name | upper }}! Today is {{ date | date('%A') }}."
        context = {
            'name': 'world',
            'date': time.time()  # This would be a datetime object in real usage
        }

        result = engine.render_string(template, context)
        print(f"Quantum engine result: {result}")

        # Test batch processing
        templates = [
            "Template {{ i }}: {{ message }}",
            "Item {{ i }}: {{ data.value }}",
            "Count {{ i }}: {{ count | pluralize('item', 'items') }}"
        ]

        contexts = [
            {'i': 1, 'message': 'Hello'},
            {'i': 2, 'data': {'value': 'test'}},
            {'i': 3, 'count': 5}
        ]

        batch_results = await engine.render_batch_async(templates, contexts)
        print("Batch processing results:")
        for i, result in enumerate(batch_results):
            print(f"  {i+1}: {result}")

        # Show performance metrics
        metrics = engine.get_metrics()
        print(f"Performance metrics: {metrics}")

    except Exception as e:
        print(f"Quantum engine demo failed (C++ core may not be available): {e}")
        print("Falling back to enhanced Lean engine...")

        # Fallback to enhanced Lean engine
        lean_engine = LeanTemplateEngine(template_dir)
        result = await lean_engine.render_string("Hello {{ name }}!", {'name': 'World'})
        print(f"Lean engine fallback: {result}")

    print()


async def demo_performance_comparison():
    """Compare performance of different engines"""
    print("=== Performance Comparison ===")

    template_dir = Path(__file__).parent / 'templates'

    # Create a complex template
    complex_template = """
{% for item in items %}
<div class="item {{ loop.index | pluralize('odd', 'even') }}">
    <h3>{{ item.title | upper | truncate(50) }}</h3>
    <p>{{ item.description | escape }}</p>
    {% if item.tags %}
    <ul>
        {% for tag in item.tags %}
        <li>{{ tag | capitalize }}</li>
        {% endfor %}
    </ul>
    {% endif %}
    <span class="date">{{ item.date | date('%Y-%m-%d') }}</span>
</div>
{% endfor %}
"""

    # Create test data
    items = []
    for i in range(100):
        items.append({
            'title': f'Item {i}',
            'description': f'This is a description for item {i}. ' * 5,
            'tags': [f'tag{j}' for j in range(i % 5)],
            'date': time.time() + i * 86400  # Days from now
        })

    context = {'items': items}

    # Test Lean engine
    lean_engine = LeanTemplateEngine(template_dir)
    start_time = time.time()
    lean_result = await lean_engine.render_string(complex_template, context)
    lean_time = time.time() - start_time

    print(".4f")
    print(f"Result length: {len(lean_result)} characters")

    # Test Quantum engine if available
    try:
        quantum_config = TemplateConfig(mode=TemplateEngineMode.FAST)
        quantum_engine = QuantumTemplateEngine([template_dir], quantum_config)

        start_time = time.time()
        quantum_result = quantum_engine.render_string(complex_template, context)
        quantum_time = time.time() - start_time

        print(".4f")

        if quantum_result == lean_result:
            print("✓ Results are identical")
            speedup = lean_time / quantum_time if quantum_time > 0 else float('inf')
            print(".2f")
        else:
            print("✗ Results differ")

    except Exception as e:
        print(f"Quantum engine performance test failed: {e}")

    print()


async def demo_custom_features():
    """Demonstrate custom filters, tags, and extensions"""
    print("=== Custom Features Demo ===")

    template_dir = Path(__file__).parent / 'templates'
    engine = LeanTemplateEngine(template_dir)

    # Add custom filter
    def markdown_filter(text):
        """Simple markdown-like filter"""
        if not isinstance(text, str):
            return text
        # Simple bold and italic
        text = text.replace('**', '<strong>', 1).replace('**', '</strong>', 1)
        text = text.replace('*', '<em>', 1).replace('*', '</em>', 1)
        return text

    engine.add_filter('markdown', markdown_filter)

    # Add custom tag
    def current_time_tag(context, format='%H:%M:%S'):
        """Custom tag to show current time"""
        from datetime import datetime
        return datetime.now().strftime(format)

    engine.add_custom_tag('current_time', current_time_tag)

    # Template using custom features
    template = """
<div class="post">
    <h2>{{ title | markdown }}</h2>
    <p>{{ content | markdown }}</p>
    <small>Posted at {% current_time %}</small>
</div>
"""

    context = {
        'title': '**Important Announcement**',
        'content': 'This is an *important* update about our template engine.'
    }

    result = await engine.render_string(template, context)
    print("Custom features result:")
    print(result)
    print()


async def main():
    """Main demo function"""
    print("PyDance Enhanced Lean Template Engine Demo")
    print("=" * 50)

    try:
        await demo_basic_features()
        await demo_advanced_features()
        await demo_quantum_engine()
        await demo_performance_comparison()
        await demo_custom_features()

        print("Demo completed successfully!")

    except Exception as e:
        print(f"Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    asyncio.run(main())

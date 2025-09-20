# tests/test_lean_templates.py
import pytest
from pathlib import Path
from pydance.core.templating.languages.lean import LeanTemplateEngine

@pytest.fixture
def template_engine(tmp_path):
    """Create a template engine for testing"""
    return LeanTemplateEngine(tmp_path)

@pytest.mark.asyncio
async def test_basic_variable_replacement(template_engine, tmp_path):
    """Test basic variable replacement"""
    template_file = tmp_path / "test.html"
    template_file.write_text("Hello, {{ name }}!")
    
    result = await template_engine.render("test.html", {"name": "World"})
    assert result == "Hello, World!"

@pytest.mark.asyncio
async def test_nested_variable_replacement(template_engine, tmp_path):
    """Test nested variable replacement"""
    template_file = tmp_path / "test.html"
    template_file.write_text("Hello, {{ user.name }}! Your age is {{ user.age }}.")
    
    context = {
        "user": {
            "name": "John",
            "age": 30
        }
    }
    
    result = await template_engine.render("test.html", context)
    assert result == "Hello, John! Your age is 30."

@pytest.mark.asyncio
async def test_if_blocks(template_engine, tmp_path):
    """Test if blocks"""
    template_file = tmp_path / "test.html"
    template_file.write_text("""
{% if user.logged_in %}
    Welcome back, {{ user.name }}!
{% endif %}
{% if not user.logged_in %}
    Please log in.
{% endif %}
""")
    
    context = {
        "user": {
            "name": "John",
            "logged_in": True
        }
    }
    
    result = await template_engine.render("test.html", context)
    assert "Welcome back, John!" in result
    assert "Please log in." not in result

@pytest.mark.asyncio
async def test_for_loops(template_engine, tmp_path):
    """Test for loops"""
    template_file = tmp_path / "test.html"
    template_file.write_text("""
<ul>
{% for item in items %}
    <li>{{ item }}</li>
{% endfor %}
</ul>
""")
    
    context = {
        "items": ["Apple", "Banana", "Cherry"]
    }
    
    result = await template_engine.render("test.html", context)
    assert "<li>Apple</li>" in result
    assert "<li>Banana</li>" in result
    assert "<li>Cherry</li>" in result

@pytest.mark.asyncio
async def test_includes(template_engine, tmp_path):
    """Test include directives"""
    header_file = tmp_path / "header.html"
    header_file.write_text("<header>Welcome</header>")
    
    template_file = tmp_path / "test.html"
    template_file.write_text("""
{% include "header.html" %}
<main>Content</main>
""")
    
    result = await template_engine.render("test.html", {})
    assert "<header>Welcome</header>" in result
    assert "<main>Content</main>" in result

@pytest.mark.asyncio
async def test_filters(template_engine, tmp_path):
    """Test filters"""
    template_file = tmp_path / "test.html"
    template_file.write_text("""
{{ name | upper }}
{{ name | lower }}
{{ number | default:0 }}
""")
    
    context = {
        "name": "Hello",
        "number": None
    }
    
    result = await template_engine.render("test.html", context)
    assert "HELLO" in result
    assert "hello" in result
    assert "0" in result

@pytest.mark.asyncio
async def test_template_inheritance(template_engine, tmp_path):
    """Test template inheritance"""
    base_file = tmp_path / "base.html"
    base_file.write_text("""
<!DOCTYPE html>
<html>
<head>
    <title>{% block title %}Default Title{% endblock %}</title>
</head>
<body>
    {% block content %}{% endblock %}
</body>
</html>
""")
    
    child_file = tmp_path / "child.html"
    child_file.write_text("""
{% extends "base.html" %}
{% block title %}My Page{% endblock %}
{% block content %}
    <h1>Welcome</h1>
{% endblock %}
""")
    
    result = await template_engine.render("child.html", {})
    assert "<title>My Page</title>" in result
    assert "<h1>Welcome</h1>" in result
    assert "Default Title" not in result

@pytest.mark.asyncio
async def test_macros(template_engine, tmp_path):
    """Test macros"""
    template_file = tmp_path / "test.html"
    template_file.write_text("""
{% macro greeting(name) %}
    Hello, {{ name }}!
{% endmacro %}
{% call greeting("World") %}
""")
    
    result = await template_engine.render("test.html", {})
    assert "Hello, World!" in result

@pytest.mark.asyncio
async def test_autoescaping(template_engine, tmp_path):
    """Test HTML autoescaping"""
    template_file = tmp_path / "test.html"
    template_file.write_text("{{ html_content }}")
    
    context = {
        "html_content": "<script>alert('XSS')</script>"
    }
    
    result = await template_engine.render("test.html", context)
    assert "&lt;script&gt;alert(&#x27;XSS&#x27;)&lt;/script&gt;" in result
    assert "<script>" not in result

@pytest.mark.asyncio
async def test_comments(template_engine, tmp_path):
    """Test comment removal"""
    template_file = tmp_path / "test.html"
    template_file.write_text("""
Hello{# This is a comment #}World
""")
    
    result = await template_engine.render("test.html", {})
    assert "HelloWorld" in result
    assert "comment" not in result

@pytest.mark.asyncio
async def test_set_blocks(template_engine, tmp_path):
    """Test set blocks for variable assignment"""
    template_file = tmp_path / "test.html"
    template_file.write_text("""
{% set greeting = "Hello" %}
{% set name = "World" %}
{{ greeting }}, {{ name }}!
""")
    
    result = await template_engine.render("test.html", {})
    assert "Hello, World!" in result

@pytest.mark.asyncio
async def test_raw_blocks(template_engine, tmp_path):
    """Test raw blocks for disabling template processing"""
    template_file = tmp_path / "test.html"
    template_file.write_text("""
{% raw %}
    {{ This will not be processed }}
    {% if nor this %}
{% endraw %}
""")
    
    result = await template_engine.render("test.html", {})
    assert "{{ This will not be processed }}" in result
    assert "{% if nor this %}" in result

@pytest.mark.asyncio
async def test_loop_variables(template_engine, tmp_path):
    """Test loop variables in for loops"""
    template_file = tmp_path / "test.html"
    template_file.write_text("""
{% for item in items %}
    {{ loop.index }}: {{ item }}
{% endfor %}
""")
    
    context = {
        "items": ["A", "B", "C"]
    }
    
    result = await template_engine.render("test.html", context)
    assert "1: A" in result
    assert "2: B" in result
    assert "3: C" in result

def test_custom_filters(template_engine):
    """Test adding custom filters"""
    def custom_filter(value, suffix):
        return f"{value}-{suffix}"
    
    template_engine.add_filter("custom", custom_filter)
    
    # Test the custom filter
    result = template_engine.filters["custom"]("test", "suffix")
    assert result == "test-suffix"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

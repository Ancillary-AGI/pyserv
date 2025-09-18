#!/usr/bin/env python3
"""
Static File Serving Demo for Pydance Framework
==============================================

This script demonstrates how to serve static files (CSS, JS, images) in Pydance,
including the widget static files.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.pydance import Application
from src.pydance.core import setup_static_files
from src.pydance.widgets import RichText, RichSelect, RichTitle

# Create application
app = Application()

# Method 1: Quick setup (RECOMMENDED)
# This automatically sets up both middleware and routes for static files
setup_static_files(app, "src/pydance/static", "/static")

# Alternative methods (if you need more control):

# Method 2: Manual middleware setup
# from pydance.core import StaticFileMiddleware
# middleware = StaticFileMiddleware("src/pydance/static", "/static")
# app.add_middleware(middleware)

# Method 3: Manual route setup
# from pydance.core import create_static_route
# static_handler = create_static_route("src/pydance/static", "/static")
# app.router.add_route("/static/{path:path}", static_handler, ["GET"])


@app.route('/')
async def home(request):
    """Home page with rich widgets that use static files"""

    # Create some widgets
    title = RichTitle('page_title', level=1, placeholder='Page Title')
    title.set_value('Pydance Static File Demo')

    content = RichText('content', format='markdown')
    content.set_value("""
# Welcome to Pydance!

This page demonstrates **rich widgets** with **static file serving**.

## Features:
- ✅ Automatic CSS/JS loading
- ✅ Rich text editing with Markdown
- ✅ Interactive form elements
- ✅ Responsive design
- ✅ Security & performance optimized

Try editing this content!
    """)

    category = RichSelect('category', options=[
        ('demo', 'Demo'),
        ('tutorial', 'Tutorial'),
        ('docs', 'Documentation')
    ], placeholder='Select category')

    # Generate HTML with widget static files
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Pydance Static Demo</title>

        <!-- Widget CSS (served via static middleware) -->
        <link rel="stylesheet" href="/static/css/widgets.css">

        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background: #f8f9fa;
            }}

            .demo-section {{
                background: white;
                border-radius: 12px;
                padding: 30px;
                margin-bottom: 20px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }}

            .demo-title {{
                color: #007bff;
                border-bottom: 3px solid #007bff;
                padding-bottom: 10px;
                margin-bottom: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="demo-section">
            <h1 class="demo-title">🎉 Pydance Static File Demo</h1>
            <p>This demo shows how static files (CSS, JS) are automatically served for rich widgets.</p>
        </div>

        <div class="demo-section">
            <h2>📝 Rich Title Widget</h2>
            {title.render()}
        </div>

        <div class="demo-section">
            <h2>📄 Rich Text Widget</h2>
            {content.render()}
        </div>

        <div class="demo-section">
            <h2>🎯 Rich Select Widget</h2>
            {category.render()}
        </div>

        <div class="demo-section">
            <h2>🔗 Static File URLs</h2>
            <p>The widgets automatically include these static files:</p>
            <ul>
                <li><code>/static/css/widgets.css</code> - Widget styles</li>
                <li><code>/static/js/widgets.js</code> - Widget JavaScript</li>
            </ul>
            <p><strong>Check your browser's Network tab to see these files being served!</strong></p>
        </div>

        <!-- Widget JavaScript (served via static middleware) -->
        <script src="/static/js/widgets.js"></script>
    </body>
    </html>
    """

    return html


@app.route('/api/files')
async def list_static_files(request):
    """API endpoint to list available static files"""
    import json
    from pathlib import Path

    static_dir = Path("src/pydance/static")
    files = []

    if static_dir.exists():
        for file_path in static_dir.rglob("*"):
            if file_path.is_file():
                relative_path = file_path.relative_to(static_dir)
                files.append({
                    'path': str(relative_path),
                    'url': f'/static/{relative_path}',
                    'size': file_path.stat().st_size
                })

    return json.dumps({
        'static_directory': str(static_dir),
        'files': files,
        'total_files': len(files)
    })


@app.route('/test-static')
async def test_static(request):
    """Test page to verify static files are working"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Static File Test</title>
        <link rel="stylesheet" href="/static/css/widgets.css">
    </head>
    <body style="padding: 20px;">
        <h1>Static File Test</h1>
        <p>If you can see styled widgets below, static files are working!</p>

        <div style="border: 1px solid #ddd; padding: 20px; margin: 20px 0;">
            <h3>Test Widget</h3>
            <div class="rich-widget">This should be styled by /static/css/widgets.css</div>
        </div>

        <script src="/static/js/widgets.js"></script>
        <script>
            console.log('Static JS loaded successfully!');
        </script>
    </body>
    </html>
    """


if __name__ == '__main__':
    print("🚀 Starting Pydance server with static file serving...")
    print("\n📁 Static files will be served from: src/pydance/static/")
    print("🌐 Available URLs:")
    print("  - http://localhost:8000/ (Main demo)")
    print("  - http://localhost:8000/test-static (Static file test)")
    print("  - http://localhost:8000/api/files (List static files)")
    print("  - http://localhost:8000/static/css/widgets.css")
    print("  - http://localhost:8000/static/js/widgets.js")
    print("\nPress Ctrl+C to stop the server\n")

    # Run the server
    app.run(host='0.0.0.0', port=8000, debug=True)

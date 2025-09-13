# Static File Serving in Pydance

This guide explains how to serve static files (CSS, JS, images, etc.) in the Pydance framework.

## Quick Start

The easiest way to enable static file serving:

```python
from pydance import Application
from pydance.core import setup_static_files

app = Application()

# Enable static file serving
setup_static_files(app, "static", "/static")

# Your static files will now be available at:
# /static/css/style.css
# /static/js/app.js
# /static/images/logo.png
```

## Directory Structure

```
your_project/
├── static/           # Static files directory
│   ├── css/
│   ├── js/
│   ├── images/
│   └── fonts/
└── app.py           # Your Pydance application
```

## Setup Methods

### Method 1: Quick Setup (Recommended)

```python
from pydance.core import setup_static_files

# This sets up both middleware and route-based serving
setup_static_files(app, "static", "/static")
```

### Method 2: Middleware Only

```python
from pydance.core import StaticFileMiddleware

middleware = StaticFileMiddleware(
    static_dir="static",
    url_prefix="/static",
    cache_max_age=86400  # 24 hours
)
app.add_middleware(middleware)
```

### Method 3: Route-Based

```python
from pydance.core import create_static_route

static_handler = create_static_route("static", "/static")
app.router.add_route("/static/{path:path}", static_handler, ["GET"])
```

## Configuration Options

### StaticFileMiddleware Options

```python
StaticFileMiddleware(
    static_dir="static",        # Directory containing files
    url_prefix="/static",       # URL prefix for files
    cache_max_age=86400,        # Cache duration in seconds
    enable_etag=True,           # Enable ETag headers
    enable_compression=True     # Enable compression
)
```

### setup_static_files Options

```python
setup_static_files(
    app,                        # Your Pydance app
    static_dir="static",        # Static files directory
    url_prefix="/static"        # URL prefix
)
```

## Usage in HTML Templates

```html
<!DOCTYPE html>
<html>
<head>
    <title>My App</title>

    <!-- CSS Files -->
    <link rel="stylesheet" href="/static/css/bootstrap.css">
    <link rel="stylesheet" href="/static/css/app.css">

    <!-- JavaScript Files -->
    <script src="/static/js/jquery.js"></script>
    <script src="/static/js/app.js"></script>
</head>
<body>
    <!-- Images -->
    <img src="/static/images/logo.png" alt="Logo">

    <!-- Other files -->
    <link rel="icon" href="/static/favicon.ico">
</body>
</html>
```

## Rich Widgets Integration

The rich widgets system automatically uses static file serving:

```python
from pydance.widgets import RichText

# Widgets automatically include their CSS/JS
editor = RichText('content', format='markdown')
html = editor.render()

# This will include:
# <link rel="stylesheet" href="/static/css/widgets.css">
# <script src="/static/js/widgets.js"></script>
```

## Security Features

- ✅ **Directory Traversal Protection**: Prevents `../../../etc/passwd` attacks
- ✅ **Security Headers**: `X-Content-Type-Options: nosniff`
- ✅ **Path Validation**: Only serves files within the static directory
- ✅ **MIME Type Detection**: Automatic content-type headers

## Performance Features

- ✅ **Caching Headers**: `Cache-Control`, `Expires`, `ETag`, `Last-Modified`
- ✅ **Conditional Requests**: Supports `If-None-Match` and `If-Modified-Since`
- ✅ **304 Not Modified**: Automatic cache validation
- ✅ **Content-Length**: Proper content length headers

## Examples

### Basic Static File Serving

```python
from pydance import Application
from pydance.core import setup_static_files

app = Application()
setup_static_files(app, "static", "/static")

@app.route('/')
async def home(request):
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <link rel="stylesheet" href="/static/css/style.css">
    </head>
    <body>
        <h1>Hello World!</h1>
        <script src="/static/js/app.js"></script>
    </body>
    </html>
    '''

if __name__ == '__main__':
    app.run()
```

### Advanced Configuration

```python
from pydance.core import StaticFileMiddleware

# Custom middleware with specific settings
middleware = StaticFileMiddleware(
    static_dir="public/assets",
    url_prefix="/assets",
    cache_max_age=3600,  # 1 hour cache
    enable_etag=True,
    enable_compression=True
)

app.add_middleware(middleware)
```

### Multiple Static Directories

```python
# You can serve multiple static directories
setup_static_files(app, "static", "/static")
setup_static_files(app, "uploads", "/media")

# Now you have:
# /static/css/style.css
# /media/user_uploads/image.jpg
```

## Testing Static Files

Create a test page to verify static files are working:

```python
@app.route('/test-static')
async def test_static(request):
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Static File Test</title>
        <link rel="stylesheet" href="/static/css/test.css">
    </head>
    <body>
        <h1>Static Files Test</h1>
        <p>If you see styled text, static files are working!</p>
        <script src="/static/js/test.js"></script>
    </body>
    </html>
    '''
```

## Troubleshooting

### Files Not Loading

1. Check that the static directory exists
2. Verify the URL prefix matches your setup
3. Ensure files have correct permissions
4. Check browser developer tools for 404 errors

### Cache Issues

1. Hard refresh your browser (Ctrl+F5)
2. Clear browser cache
3. Check cache headers in browser dev tools

### Security Errors

1. Ensure static directory is within your project
2. Check file permissions
3. Verify no directory traversal in URLs

## Best Practices

1. **Organize Files**: Use subdirectories (css/, js/, images/)
2. **Use Versioning**: Add version numbers to filenames for cache busting
3. **Compress Files**: Use minified CSS/JS in production
4. **CDN Integration**: Consider using CDNs for common libraries
5. **Cache Strategy**: Set appropriate cache durations

## Integration with Build Tools

For development with build tools like Webpack:

```python
# Development setup
if app.config.debug:
    setup_static_files(app, "static", "/static")
    setup_static_files(app, "dist", "/dist")  # Built files
else:
    setup_static_files(app, "dist", "/static")  # Production files
```

This allows you to serve both source files (for development) and built/optimized files (for production).

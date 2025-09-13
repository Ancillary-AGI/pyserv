# Pydance

A comprehensive web framework with MVC architecture.

## Installation

```bash
pip install -r requirements.txt
pip install -e .  # For development
```

## Quick Start

```python
from pydance import Application

app = Application()

@app.route('/')
async def hello(request):
    return 'Hello World!'

if __name__ == '__main__':
    app.run()
```

## CLI Commands

Pydance provides a comprehensive CLI for development and production use.

### Development Commands

```bash
# Start development server with auto-reload
python manage.py start --reload

# Start server on specific host/port
python manage.py start --host 0.0.0.0 --port 8000

# Start with multiple workers
python manage.py start --workers 4

# Stop the server
python manage.py stop

# Restart the server
python manage.py restart

# Check server status
python manage.py status

# Start interactive shell
python manage.py shell
```

### Production Commands

```bash
# Install the package
pip install .

# Start production server
pydance start --host 0.0.0.0 --port 80 --workers 4

# Start with SSL
pydance start --ssl-certfile cert.pem --ssl-keyfile key.pem
```

### Management Commands

```bash
# Run database migrations
python manage.py migrate

# Create a new application
python manage.py createapp myapp

# Collect static files
python manage.py collectstatic
```

### CLI Options

```
Usage: pydance [OPTIONS] COMMAND [ARGS]...

Options:
  --config TEXT    Path to config file (default: config.py)
  --app TEXT       Application module path (default: app:app)
  --help           Show this message and exit.

Commands:
  start        Start the server
  stop         Stop the server
  restart      Restart the server
  status       Show server status
  shell        Start interactive shell
  migrate      Run database migrations
  createapp    Create a new application
  collectstatic Collect static files
```

### Start Command Options

```
Usage: pydance start [OPTIONS]

Options:
  --host TEXT     Host to bind to (default: 127.0.0.1)
  --port INTEGER  Port to bind to (default: 8000)
  --workers INTEGER  Number of workers (default: 1)
  --reload        Enable auto-reload
  --debug         Enable debug mode
  --help          Show this message and exit.
```

## Testing

Pydance includes comprehensive testing support with multiple test types:

### Test Types

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test component interactions
- **System Tests**: End-to-end testing of the complete system
- **Performance Tests**: Benchmarking and performance validation
- **Load Tests**: Using Locust for load testing scenarios
- **Stress Tests**: Testing system limits and failure points
- **Security Tests**: Vulnerability assessment and security validation
- **Regression Tests**: Ensure previously fixed bugs don't reappear

### Running Tests

```bash
# Run all tests
python manage.py test

# Run specific test types
python manage.py test --unit
python manage.py test --integration
python manage.py test --performance
python manage.py test --security
python manage.py test --regression

# Run with coverage
python manage.py test --coverage

# Run load tests
python manage.py test --load

# Run tests with specific markers
python manage.py test --markers "slow and database"
```

### Test Structure

```
tests/
├── conftest.py              # Test configuration and fixtures
├── unit/                    # Unit tests
│   ├── test_application.py
│   └── test_routing.py
├── integration/             # Integration tests
│   └── test_full_application.py
├── system/                  # System tests
│   └── test_system.py
├── performance/             # Performance tests
│   └── test_performance.py
├── load/                    # Load tests
│   └── locustfile.py
├── security/                # Security tests
│   └── test_security.py
└── regression/              # Regression tests
    └── test_regression.py
```

### Load Testing

For load and stress testing, Pydance uses Locust:

```bash
# Install Locust
pip install locust

# Run load tests
locust -f tests/load/locustfile.py

# Or via CLI
python manage.py test --load
```

### Performance Benchmarking

Performance tests use pytest-benchmark:

```bash
# Run performance tests
python manage.py test --performance

# Generate performance report
pytest tests/performance/ --benchmark-json=perf.json
```

### Security Testing

Security tests include:

- SQL injection protection
- XSS prevention
- CSRF protection
- Authentication bypass testing
- Directory traversal protection
- Input validation
- Secure headers validation
- Error information leakage prevention

### Test Configuration

Tests are configured in `pytest.ini` with:

- Custom markers for different test types
- Async test support
- Coverage reporting
- Warning filters
- Test discovery patterns

## Internationalization (i18n)

Pydance includes built-in internationalization support for multi-language applications.

### Setting Up Translations

1. Create translation files in `src/pydance/translations/`:
```json
// es.json
{
  "bad_request": "Solicitud Incorrecta",
  "not_found": "No Encontrado",
  "invalid_credentials": "Credenciales inválidas"
}
```

2. Set locale in your application:
```python
from pydance.core.i18n import set_locale, _

# Set Spanish locale
set_locale('es')

# Use translations
error_msg = _('invalid_credentials')
```

### Available Locales

- `en` - English (default)
- `es` - Spanish (example)

### Translation Keys

All error messages and user-facing strings support translation. Add new translation files by creating JSON files in the `translations/` directory.

## Exception Handling

Pydance provides a comprehensive exception hierarchy with proper HTTP status codes and internationalization support.

### Exception Types

- **HTTP Exceptions**: `BadRequest`, `Unauthorized`, `Forbidden`, `NotFound`, `InternalServerError`
- **User Exceptions**: `UserNotFound`, `InvalidCredentials`, `PasswordTooWeak`, `EmailAlreadyExists`
- **Validation Exceptions**: `ValidationError`, `InvalidEmailFormat`, `InvalidUsernameFormat`
- **Database Exceptions**: `DatabaseError`, `RecordNotFound`
- **Authentication Exceptions**: `TokenExpired`, `TokenInvalid`, `PermissionDenied`
- **File Exceptions**: `FileTooLarge`, `InvalidFileType`
- **Rate Limiting**: `TooManyRequests`

### Usage

```python
from pydance.core.exceptions import BadRequest, UserNotFound
from pydance.core.i18n import _

# Raise with automatic translation
raise BadRequest(_('invalid_json'))

# Custom message
raise UserNotFound("User with ID 123 not found")
```

## Static File Serving

Pydance provides built-in static file serving with security, caching, and performance optimizations.

### Quick Setup

```python
from pydance import Application
from pydance.core import setup_static_files

app = Application()

# Enable static file serving (recommended)
setup_static_files(app, "static", "/static")
```

### Manual Setup Options

```python
# Option 1: Middleware approach
from pydance.core import StaticFileMiddleware
middleware = StaticFileMiddleware("static", "/static")
app.add_middleware(middleware)

# Option 2: Route-based approach
from pydance.core import create_static_route
static_handler = create_static_route("static", "/static")
app.router.add_route("/static/{path:path}", static_handler, ["GET"])
```

### Features

- ✅ **Security**: Directory traversal protection, security headers
- ✅ **Performance**: ETag, Last-Modified, and Cache-Control headers
- ✅ **MIME Types**: Automatic content-type detection
- ✅ **Caching**: Configurable cache duration with browser optimization
- ✅ **Compression**: Support for compressed responses

### Usage in Templates

```html
<!-- CSS files -->
<link rel="stylesheet" href="/static/css/style.css">
<link rel="stylesheet" href="/static/css/widgets.css">

<!-- JavaScript files -->
<script src="/static/js/app.js"></script>
<script src="/static/js/widgets.js"></script>

<!-- Images -->
<img src="/static/images/logo.png" alt="Logo">
```

## Rich Widgets System

Pydance includes a comprehensive rich widgets system that provides secure, efficient, and well-designed form widgets with advanced functionality.

### Available Rich Widgets

#### 📝 Rich Text Widget
Full-featured rich text editor with Markdown/HTML support:
```python
from pydance.widgets import RichText

editor = RichText(
    name='content',
    format='markdown',  # or 'html'
    placeholder='Enter your content...',
    value='# Hello World\n\nThis is **markdown** content.'
)

# Get content in different formats
html_content = editor.get_content('html')
markdown_content = editor.get_content('markdown')
```

#### 🎯 Rich Select Widget
Advanced dropdown with search and grouping:
```python
from pydance.widgets import RichSelect

select = RichSelect(
    name='category',
    options=[
        ('tech', 'Technology'),
        ('business', 'Business'),
        ('health', 'Health & Wellness')
    ],
    placeholder='Select a category...',
    searchable=True,
    multiple=False
)
```

#### 📅 Rich Date Widget
Interactive calendar picker with time selection:
```python
from pydance.widgets import RichDate

date_picker = RichDate(
    name='publish_date',
    date_format='YYYY-MM-DD',
    show_time=True,
    min_date='2024-01-01',
    max_date='2025-12-31'
)
```

#### 🎨 Rich Color Widget
Color picker with palette and custom colors:
```python
from pydance.widgets import RichColor

color_picker = RichColor(
    name='theme_color',
    default_color='#007bff',
    show_palette=True,
    palette=['#000000', '#FFFFFF', '#FF0000', '#00FF00', '#0000FF']
)
```

#### ⭐ Rich Rating Widget
Star rating with half-stars and custom icons:
```python
from pydance.widgets import RichRating

rating = RichRating(
    name='difficulty',
    max_rating=5,
    show_half=True,
    icon='⭐',
    empty_icon='☆'
)
```

#### 🏷️ Rich Tags Widget
Tag input with suggestions and validation:
```python
from pydance.widgets import RichTags

tags = RichTags(
    name='tags',
    placeholder='Add tags...',
    max_tags=10,
    suggestions=['python', 'web', 'framework', 'api'],
    allow_duplicates=False
)
```

#### 📎 Rich File Widget
Drag & drop file upload with validation:
```python
from pydance.widgets import RichFile

file_upload = RichFile(
    name='attachments',
    multiple=True,
    accept='image/*,.pdf,.doc,.docx',
    max_size=5 * 1024 * 1024,  # 5MB
    allowed_types=['image/jpeg', 'image/png', 'application/pdf']
)
```

#### 🎚️ Rich Slider Widget
Range slider with custom values:
```python
from pydance.widgets import RichSlider

slider = RichSlider(
    name='priority',
    min_value=1,
    max_value=10,
    step=1,
    show_value=True,
    orientation='horizontal'
)
```

#### 💻 Rich Code Widget
Code editor with syntax highlighting:
```python
from pydance.widgets import RichCode

code_editor = RichCode(
    name='code_sample',
    language='python',
    theme='default',
    line_numbers=True,
    value='def hello():\n    print("Hello, World!")'
)
```

#### 📝 Rich Title Widget
Dynamic title with formatting options:
```python
from pydance.widgets import RichTitle

title = RichTitle(
    name='title',
    level=1,  # H1 to H6
    placeholder='Enter your title...',
    value='My Awesome Article'
)
```

### Widget Features

#### Security & Validation
- **XSS Protection**: All HTML output is sanitized using bleach
- **Input Validation**: Comprehensive validation for all widget types
- **File Upload Security**: Strict file type and size validation
- **Markdown Security**: Dangerous patterns are filtered out

#### Content Format Support
- **Markdown Processing**: Convert between Markdown and HTML
- **HTML Sanitization**: Safe HTML rendering with allowed tags
- **Format Conversion**: Seamless conversion between formats

#### User Experience
- **Responsive Design**: Works on all screen sizes
- **Keyboard Navigation**: Full keyboard accessibility
- **Touch Support**: Mobile-friendly interactions
- **Loading States**: Visual feedback for async operations
- **Error Handling**: Clear error messages and validation feedback

### Usage Examples

#### Basic Form with Rich Widgets
```python
from pydance.widgets import RichText, RichSelect, RichTitle, RichFile, RichDate

# Create widgets
title = RichTitle('title', level=1, placeholder='Article title...')
content = RichText('content', format='markdown')
category = RichSelect('category', options=[('tech', 'Technology'), ('business', 'Business')])
publish_date = RichDate('publish_date', show_time=True)
attachments = RichFile('files', multiple=True, accept='image/*,.pdf')

# Render in template
html = f"""
<form method="POST" enctype="multipart/form-data">
    {title.render()}
    {content.render()}
    {category.render()}
    {publish_date.render()}
    {attachments.render()}
    <button type="submit">Publish</button>
</form>
<script src="/static/js/widgets.js"></script>
<link rel="stylesheet" href="/static/css/widgets.css">
"""
```

#### Advanced Widget Configuration
```python
# Rich text with custom toolbar
editor = RichText(
    name='article',
    format='html',
    placeholder='Write your article...',
    value='<h1>Title</h1><p>Content...</p>'
)

# Add custom validation
editor.add_validator(lambda x: len(x) > 10)

# Custom styling
editor.add_class('custom-editor')
editor.add_style('min-height', '300px')
editor.set_data_attribute('custom', 'value')

# Render
html = editor.render()
```

### Widget Integration

#### With Templates
```python
# In your route handler
@app.route('/create-post')
async def create_post(request):
    widgets = {
        'title': RichTitle('title', placeholder='Post title...'),
        'content': RichText('content', format='markdown'),
        'tags': RichTags('tags', suggestions=['python', 'web', 'tutorial'])
    }

    return await render_template('create_post.html', widgets=widgets)
```

#### Form Processing
```python
@app.route('/create-post', methods=['POST'])
async def process_post(request):
    form_data = await request.form()

    # Widgets automatically handle form data
    title = RichTitle('title')
    title.set_value(form_data.get('title', ''))

    content = RichText('content', format='markdown')
    content.set_value(form_data.get('content', ''))

    # Validate
    if not title.validate(title.get_value()):
        return {'error': title.errors}

    if not content.validate(content.get_value()):
        return {'error': content.errors}

    # Process content
    html_content = content.get_content('html')

    # Save to database...
    return {'success': True}
```

### Static Files

Include these files in your HTML for rich widgets to work:

```html
<!-- CSS -->
<link rel="stylesheet" href="/static/css/widgets.css">

<!-- JavaScript -->
<script src="/static/js/widgets.js"></script>
```

### Customization

#### Custom Styling
```css
/* Custom widget styles */
.rich-text-container {
    border: 2px solid #007bff;
    border-radius: 12px;
}

.rich-text-toolbar {
    background: linear-gradient(45deg, #007bff, #0056b3);
}

/* Dark theme */
@media (prefers-color-scheme: dark) {
    .rich-widget {
        background: #343a40;
        color: #fff;
    }
}
```

#### Custom Validation
```python
def custom_validator(value):
    if len(value) < 10:
        return False
    if '<script' in value.lower():
        return False
    return True

widget.add_validator(custom_validator)
```

#### Extending Widgets
```python
from pydance.widgets import BaseWidget, WidgetType

class CustomWidget(BaseWidget):
    def __init__(self, name, **kwargs):
        super().__init__(name, WidgetType.TEXT, **kwargs)
        # Custom initialization

    def render(self) -> str:
        # Custom rendering logic
        return f'<div class="custom-widget">{self.attributes.value}</div>'
```

## Features

- ASGI compatible
- MVC architecture
- Database support (PostgreSQL, MySQL, MongoDB, SQLite)
- Templating engines (Jinja2, Lean)
- Middleware support
- WebSocket support
- Security features (CSRF, authentication, encryption)
- CLI management tools
- Auto-reload for development
- Multi-worker support
- Process management (start/stop/restart)
- Comprehensive testing suite
- Performance benchmarking
- Load and stress testing
- Security testing and validation
- Internationalization (i18n) support
- Comprehensive exception hierarchy
- Multi-language error messages
- **Rich Widgets System** - Advanced form widgets with rich functionality

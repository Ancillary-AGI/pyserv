# Pyserv Framework

![Pyserv Logo](https://img.shields.io/badge/Pyserv-High--Performance-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.8+-green?style=flat-square)
![C/C++](https://img.shields.io/badge/C%2FC%2B%2B-Extensions-orange?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-red?style=flat-square)

**Pyserv** is a modern, production-ready web framework with enterprise-grade features, advanced security, and comprehensive architecture. Built with performance, security, and developer experience in mind.

## 🎯 **Framework Status: Production Ready**

The Pyserv framework has been completely refactored with a modern architecture that provides enterprise-grade features while maintaining simplicity and developer experience.

### **✅ Complete Refactoring Achieved**

- **Modern ASGI Application** with proper lifecycle management
- **Advanced Dependency Injection Container** with service registration
- **Configuration Management System** with environment support
- **Plugin System** for extensibility
- **Event System** for inter-component communication
- **Enhanced Request/Response System** with better type hints
- **Advanced Routing System** with route groups and namespaces
- **Comprehensive Middleware System** with priorities and phases
- **Enterprise Security Layer** with multi-method authentication
- **GraphQL Integration** with schema management
- **gRPC Services** with load balancing and health checking
- **Server-Sent Events (SSE)** with real-time streaming
- **Session Management** with encryption and multiple backends
- **Monitoring & Observability** with metrics and health checks

## 🚀 Key Features

### ⚡ High Performance
- **C/C++ HTTP Server Core** with epoll/kqueue support
- **SIMD Optimizations** for cryptographic operations
- **Memory Pool Management** for efficient allocations
- **Zero-Copy Operations** where possible
- **Thread Pool Execution** for CPU-bound tasks

### 🔒 Enterprise Security
- **IAM (Identity & Access Management)** with RBAC/ABAC
- **Elliptic Curve Cryptography (ECC)** with SHA3 hashing
- **Zero Trust Network Architecture**
- **Hardware Security Module (HSM)** integration
- **Automated Certificate Management**
- **SIEM Integration** for centralized monitoring
- **Compliance Automation** (GDPR, HIPAA, SOC2)
- **Defense in Depth** security layers

### 🌐 Web3 & Blockchain
- **Multi-Blockchain Support** (Ethereum, Polygon, BSC, etc.)
- **Smart Contract Integration**
- **DeFi Protocol Support** (lending, staking, yield farming)
- **NFT Management** and trading
- **DAO Governance** tools
- **Decentralized Identity**

### 📊 Monitoring & Observability
- **Real-time Metrics Collection**
- **Distributed Tracing**
- **Structured Logging**
- **Performance Monitoring**
- **Health Checks**
- **Alert Management**

### 🏗️ Modern Architecture
- **MVC Pattern** with clean separation
- **Dependency Injection** container
- **GraphQL API** support
- **RESTful API** generation
- **Microservices** architecture support
- **Database Migrations** with schema versioning
- **Internationalization (i18n)** support

## 📦 Installation

### Basic Installation
```bash
pip install pyserv 
```

### With All Features
```bash
pip install pyserv [dev,security,performance,database,web3,monitoring]
```

### From Source (with C extensions)
```bash
git clone https://github.com/pyserv /pyserv .git
cd pyserv 

# Install build dependencies
# Ubuntu/Debian
sudo apt-get install build-essential python3-dev libssl-dev

# macOS
brew install openssl

# Windows (with MSVC)
# Install Visual Studio Build Tools

# Build and install
pip install -e .
```

## 🚀 Quick Start

### Basic HTTP Server
```python
from pyserv.core.server_bindings import create_default_server

# Create server with default routes
server = create_default_server()

# Add custom routes
@server.get("/api/users")
def get_users(request):
    return {
        'status_code': 200,
        'content_type': 'application/json',
        'body': '{"users": [{"id": 1, "name": "John"}]}'
    }

@server.post("/api/users")
def create_user(request):
    return {
        'status_code': 201,
        'content_type': 'application/json',
        'body': '{"message": "User created"}'
    }

# Start server
if __name__ == "__main__":
    server.run()
```

### MVC Application
```python
from pyserv.controllers import Controller
from pyserv.core.application import Application
from pyserv.models import Model, Field
from pyserv.views import TemplateView

# Define model
class User(Model):
    name = Field(str)
    email = Field(str)
    created_at = Field(datetime)

# Define controller
class UserController(Controller):
    @get('/users')
    async def index(self):
        users = await User.all()
        return self.json({'users': users})

    @post('/users')
    async def create(self):
        data = await self.request.json()
        user = await User.create(data)
        return self.json({'user': user}, status_code=201)

# Define view
class HomeView(TemplateView):
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Welcome to Pyserv '
        return context

# Create application
app = Application()

# Register routes
UserController.register_routes(app)
app.add_route('/', HomeView.as_view())

# Run application
if __name__ == "__main__":
    app.run()
```

### Security Integration
```python
from pyserv.security import (
    get_iam_system, get_crypto_manager,
    get_zero_trust_network, get_defense_in_depth
)

# Initialize security systems
iam = get_iam_system()
crypto = get_crypto_manager()
zero_trust = get_zero_trust_network()
defense = get_defense_in_depth()

# Create secure user
user = iam.create_user("john@example.com", "john_doe")
iam.assign_role_to_user(user.id, "user")

# Hash password
password_hash = crypto.hash_password("secure_password")

# Add security middleware
app.add_middleware(defense.process_request)
app.add_middleware(zero_trust.authorize_request)
```

### Web3 Integration
```python
from pyserv.security.web3 import get_web3_manager

web3 = get_web3_manager()

# Add blockchain networks
web3.add_network(BlockchainNetwork.ETHEREUM, "https://mainnet.infura.io/v3/YOUR_KEY")
web3.add_network(BlockchainNetwork.POLYGON, "https://polygon-rpc.com")

# Create wallet
wallet = web3.create_wallet(BlockchainNetwork.ETHEREUM)

# Transfer tokens
tx_hash = await web3.transfer_tokens(wallet, "0x...", Decimal("1.0"))

# Deploy smart contract
contract_address = await web3.deploy_contract(wallet, bytecode, abi)

# Interact with DeFi
rate = await web3.defi.get_lending_rate("Compound", "USDC")
tx = await web3.defi.supply_liquidity(wallet, "Uniswap", "ETH", Decimal("1.0"))
```

## 🏗️ Architecture

### Core Components

```
Pyserv  Framework
├── Core Engine (C/C++)
│   ├── HTTP Server (epoll/kqueue)
│   ├── SSL/TLS Implementation
│   ├── Memory Management
│   └── SIMD Optimizations
├── Python Framework
│   ├── MVC Architecture
│   ├── Dependency Injection
│   ├── Template Engine
│   └── ORM
├── Security Layer
│   ├── IAM & Authentication
│   ├── Cryptography (ECC/SHA3)
│   ├── Zero Trust Network
│   └── Compliance
├── Enterprise Features
│   ├── Monitoring & Metrics
│   ├── Database Migrations
│   ├── Microservices
│   └── Web3 Integration
└── Development Tools
    ├── CLI Tools
    ├── Testing Framework
    ├── Documentation
    └── Deployment
```

### Performance Optimizations

- **C/C++ HTTP Server**: Native implementation with epoll/kqueue
- **SIMD Instructions**: Hardware-accelerated cryptographic operations
- **Memory Pools**: Efficient memory allocation and reuse
- **Thread Pools**: Optimized CPU-bound task execution
- **Zero-Copy Operations**: Direct buffer operations where possible
- **Connection Pooling**: Efficient connection management

## 🔒 Security Features

### Identity & Access Management
```python
# Role-based access control
admin_role = iam.create_role("admin", permissions={
    Permission("*", "*")  # Full access
})

user_role = iam.create_role("user", permissions={
    Permission("user", "read", {"user_id": "self"}),
    Permission("post", "create")
})

# Policy-based access control
policy = iam.create_policy("data_access", [
    {
        "Effect": "Allow",
        "Action": "read",
        "Resource": "user_data",
        "Condition": {"StringEquals": {"department": "engineering"}}
    }
])
```

### Cryptographic Operations
```python
# ECC key generation and signing
ecc_keys = crypto.generate_ecc_keypair()
signature = crypto.ecc.sign("message", private_key)
verified = crypto.ecc.verify("message", signature, public_key)

# Password hashing with SHA3
password_hash = crypto.hash_password("password")
verified = crypto.verify_password("password", password_hash)
```

### Zero Trust Implementation
```python
# Device fingerprinting
fingerprint = DeviceFingerprint(
    user_agent=request.headers.get('User-Agent'),
    ip_address=get_client_ip(request),
    location=get_location_data(ip_address)
)

# Continuous verification
auth_result = await zero_trust.authorize_request(
    user_id=user.id,
    resource="/api/admin",
    action="DELETE",
    device_fingerprint=fingerprint
)
```

### Quantum Security (Advanced)
```python
from pyserv.security.quantum_security import (
    generate_quantum_keypair,
    establish_secure_channel,
    quantum_authenticate
)

# Generate quantum-resistant keypair
keys = await generate_quantum_keypair("kyber")
print(f"Generated {keys['algorithm']} keypair")

# Establish quantum-secure channel
channel = await establish_secure_channel()
print(f"Channel established: {channel['channel_id']}")

# Perform quantum authentication
auth = await quantum_authenticate("user123")
print(f"Authenticated: {auth['identity']}")
```

### Distributed Consensus
```python
from pyserv.microservices import RaftConsensus, DistributedLock

# Initialize consensus
consensus = RaftConsensus("node1", ["node2", "node3"])
await consensus.start()

# Use distributed lock
lock = DistributedLock(consensus, "resource_lock")
if await lock.acquire("node1"):
    try:
        # Critical section
        pass
    finally:
        await lock.release("node1")
```

### Event Sourcing & CQRS
```python
from pyserv.microservices import Event, EventStore, Aggregate, Repository

class UserAggregate(Aggregate):
    async def handle_command(self, command):
        if command['type'] == 'create_user':
            event = Event(
                event_type='user_created',
                aggregate_id=self.aggregate_id,
                payload=command
            )
            return [event]

# Usage
event_store = EventStore()
repository = Repository(event_store, UserAggregate)

user = UserAggregate("user_123")
events = await user.handle_command({'type': 'create_user', 'name': 'John'})
await event_store.append_events(events)
```

## 📊 Monitoring & Metrics

### Real-time Metrics
```python
from pyserv.monitoring import get_metrics_collector

metrics = get_metrics_collector()

# Built-in metrics
request_counter = metrics.create_counter("http_requests_total", "Total HTTP requests")
response_time = metrics.create_histogram("http_response_time", "Response time histogram")

# Custom metrics
active_users = metrics.create_gauge("active_users", "Number of active users")
error_rate = metrics.create_counter("error_rate", "Application error rate")
```

### Structured Logging
```python
from pyserv.monitoring import get_structured_logger

logger = get_structured_logger()

logger.info("User login successful", {
    'user_id': user.id,
    'ip_address': request.client_ip,
    'user_agent': request.headers.get('User-Agent'),
    'timestamp': datetime.utcnow().isoformat()
})
```

## 🌐 API Development

### RESTful APIs
```python
class ArticleController(Controller):
    @get('/articles')
    async def index(self):
        articles = await Article.all()
        return self.json({'articles': articles})

    @post('/articles')
    async def create(self):
        data = await self.request.json()
        article = await Article.create(data)
        return self.json({'article': article}, status_code=201)

    @get('/articles/{id}')
    async def show(self, id: int):
        article = await Article.find(id)
        if not article:
            return self.not_found({'error': 'Article not found'})
        return self.json({'article': article})
```

### GraphQL APIs
```python
from pyserv.graphql import Schema, Query, ObjectType, Field

class ArticleType(ObjectType):
    def __init__(self):
        super().__init__('Article', {
            'id': Field(ID()),
            'title': Field(String()),
            'content': Field(String()),
            'author': Field(UserType())
        })

class QueryType(Query):
    def __init__(self):
        super().__init__({
            'articles': Field(List(ArticleType), resolver=self.resolve_articles),
            'article': Field(ArticleType, args={'id': ID()}, resolver=self.resolve_article)
        })

    async def resolve_articles(self, parent, info):
        return await Article.all()

    async def resolve_article(self, parent, info, id):
        return await Article.find(id)

schema = Schema(query=QueryType())
```

## 🎨 Template Engine

### Lean Template Engine
Pyserv  includes a high-performance template engine with C++ acceleration and GPU support:

```python
from pyserv.templating import TemplateEngine

# Create engine with C++ acceleration
engine = TemplateEngine(template_dirs=['templates'])

# Render template
template = """
<html>
<body>
    <h1>{{ title | upper }}</h1>
    {% for item in items %}
        <li>{{ item.name }}: {{ item.value | default('N/A') }}</li>
    {% endfor %}
</body>
</html>
"""

context = {
    'title': 'My Page',
    'items': [{'name': 'Item 1', 'value': 'Value 1'}]
}

result = await engine.render_string(template, context)
```

### Advanced Features
- **Template Inheritance**: `{% extends %}`, `{% block %}`
- **Macros**: `{% macro %}`, `{% call %}`
- **Custom Filters**: Extensible filter system
- **GPU Acceleration**: Batch processing with CUDA/OpenCL
- **Security**: XSS prevention, injection protection

### Template Syntax
```jinja
<!-- Variables -->
{{ variable }}
{{ object.attribute }}
{{ list[0] }}

<!-- Filters -->
{{ value | filter }}
{{ value | upper | trim }}

<!-- Control Structures -->
{% if condition %}Content{% endif %}
{% for item in items %}{{ item }}{% endfor %}

<!-- Template Inheritance -->
{% extends "base.html" %}
{% block content %}Custom content{% endblock %}

<!-- Macros -->
{% macro input(name) %}
<input name="{{ name }}">
{% endmacro %}
```

## 📧 Email Template Engine

### Overview
The enhanced Email Template Engine for Pyserv  provides a comprehensive solution for creating and rendering email templates with support for multiple formats including plain text, HTML, and Markdown. It includes intelligent fallback mechanisms and a built-in markdown renderer for creating rich email content.

### Features
- ✅ **Multiple Template Formats**: Support for `.txt`, `.html`, and `.md` templates
- ✅ **Markdown Rendering**: Built-in markdown to HTML conversion
- ✅ **Intelligent Fallbacks**: Automatic fallback when preferred formats aren't available
- ✅ **Multipart Email Support**: Easy creation of text + HTML email combinations
- ✅ **Template Inheritance**: Support for template composition and inheritance
- ✅ **Context-Aware Rendering**: Dynamic content based on template context
- ✅ **Error Handling**: Graceful handling of missing templates

### Quick Start

```python
from pyserv.core.templating.engine import TemplateEngine
from pyserv.contrib.email.templates import EmailTemplateEngine

# Initialize the template engine
template_engine = TemplateEngine()
email_engine = EmailTemplateEngine(template_engine)

# Prepare context data
context = {
    'user_name': 'John Doe',
    'company': 'Acme Corp',
    'login_url': 'https://example.com/login'
}

# Render email template
result = await email_engine.render_template('welcome', context)

# Access rendered content
print(f"Subject: {result['subject']}")
print(f"Text Body: {result['body']}")
print(f"HTML Body: {result['html_body']}")
```

### Template File Structure

Create your email templates in the following structure:

```
templates/
└── emails/
    ├── welcome_subject.txt      # Email subject line
    ├── welcome_body.txt         # Plain text body
    ├── welcome_body.html        # HTML body (optional)
    └── welcome_body.md          # Markdown body (optional)
```

### Template Naming Convention

For a template named `welcome`, create these files:
- `welcome_subject.txt` - Subject line template
- `welcome_body.txt` - Plain text body template
- `welcome_body.html` - HTML body template (optional)
- `welcome_body.md` - Markdown body template (optional)

### Template Syntax

#### Plain Text Templates
```txt
Hello {{ user_name }},

Welcome to {{ company }}! We're excited to have you on board.

To get started, please visit: {{ login_url }}

If you have any questions, feel free to contact us at {{ support_email }}.

Best regards,
The {{ company }} Team
```

#### HTML Templates
```html
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <h2>Welcome to {{ company }}, {{ user_name }}!</h2>
    <p>We're excited to have you on board.</p>
    <p>
        <a href="{{ login_url }}"
           style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
            Get Started
        </a>
    </p>
    <p>If you have any questions, contact us at <a href="mailto:{{ support_email }}">{{ support_email }}</a></p>
    <p>Best regards,<br>The {{ company }} Team</p>
</div>
```

#### Markdown Templates
```markdown
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
```

### Advanced Usage

#### Fallback Rendering
```python
# Render with fallback preferences
result = await email_engine.render_with_fallback(
    'notification',
    context,
    preferred_format='html'  # Try HTML first, then markdown, then text
)
```

#### Template Information
```python
template_info = email_engine.get_template_info('newsletter')
print(template_info)
# Output: {'text': True, 'html': True, 'markdown': False}
```

### Integration Examples

#### With Email Service
```python
class EmailService:
    def __init__(self, email_engine: EmailTemplateEngine):
        self.email_engine = email_engine

    async def send_welcome_email(self, user_email: str, user_name: str):
        context = {
            'user_name': user_name,
            'company': 'My Company',
            'login_url': 'https://myapp.com/login'
        }

        # Render email content
        template_data = await self.email_engine.render_multipart_template('welcome', context)

        # Send email using your email provider
        await self.send_email(
            to=user_email,
            subject=template_data['subject'],
            text_body=template_data['text_body'],
            html_body=template_data['html_body']
        )
```

### Best Practices

1. **Template Organization**:
```
templates/
└── emails/
    ├── transactional/        # Transactional emails
    ├── marketing/           # Marketing emails
    └── notifications/       # Notifications
```

2. **Context Data**:
```python
context = {
    'user': {'name': 'John Doe', 'email': 'john@example.com'},
    'urls': {'login': 'https://example.com/login'},
    'branding': {'company_name': 'My Company'}
}
```

3. **Error Handling**:
```python
try:
    email_data = await email_engine.render_template('welcome', context)
except Exception as e:
    # Fallback to simple text
    email_data = {'subject': f'Welcome {context.get("user_name", "User")}!', 'body': 'Welcome to our platform!'}
```

### Performance Considerations
- **Template Caching**: The underlying template engine caches compiled templates
- **Lazy Loading**: Templates are only loaded when needed
- **Memory Efficient**: Markdown rendering is done on-demand
- **Fallback Strategy**: Reduces the need for multiple template files

## 🔐 Session Management

### Overview
Pyserv provides a comprehensive session management system with enterprise-grade security, multiple storage backends, and automatic session handling through middleware.

### Features
- ✅ **Multiple Storage Backends**: Memory, Database, Redis, Filesystem
- ✅ **Session Encryption**: AES-256 encryption with PBKDF2 key derivation
- ✅ **Integrity Verification**: HMAC-based session integrity checking
- ✅ **Automatic Cleanup**: Background cleanup of expired sessions
- ✅ **Session Middleware**: Automatic session handling in requests
- ✅ **Secure Cookies**: HTTP-only, secure, same-site cookies
- ✅ **Session Security**: CSRF protection, session fixation protection
- ✅ **User Session Management**: Track and manage user sessions
- ✅ **Session Analytics**: Monitor session usage and patterns

### Quick Start

```python
from pyserv.server.application import Application
from pyserv.server.session import SessionConfig, get_session_manager

# Create application
app = Application()

# Configure session manager
session_config = SessionConfig(
    secret_key='your-secret-key-here',  # Required for encryption
    max_age=3600,  # 1 hour
    secure=True,   # HTTPS only
    http_only=True,  # JavaScript cannot access
    same_site='Lax'  # CSRF protection
)

# Get session manager
session_manager = get_session_manager(session_config)

# Add session middleware
from pyserv.server.session import SessionMiddleware
app.add_middleware(SessionMiddleware, session_manager=session_manager)
```

### Session Operations

#### Basic Session Usage
```python
@app.route('/session/set')
async def set_session_data(request):
    """Set session data"""
    request.session['user_id'] = 123
    request.session['preferences'] = {'theme': 'dark'}
    return {'status': 'Session data set'}

@app.route('/session/get')
async def get_session_data(request):
    """Get session data"""
    user_id = request.session.get('user_id')
    preferences = request.session.get('preferences', {})
    return {
        'user_id': user_id,
        'preferences': preferences,
        'session_id': request.session.session_id
    }

@app.route('/session/delete')
async def delete_session_data(request):
    """Delete session data"""
    if 'user_id' in request.session:
        del request.session['user_id']
    return {'status': 'Session data deleted'}
```

#### User Authentication with Sessions
```python
@app.route('/login')
async def login(request):
    """Login user and create session"""
    # Authenticate user (implement your auth logic)
    user = await authenticate_user(request)

    if user:
        # Create session
        session = await session_manager.create_session(
            user_id=user.id,
            data={
                'logged_in': True,
                'user_role': user.role,
                'login_time': time.time()
            },
            ip_address=request.client_ip,
            user_agent=request.headers.get('User-Agent')
        )

        return {'status': 'logged_in', 'user_id': user.id}
    else:
        return {'error': 'Invalid credentials'}, 401

@app.route('/logout')
async def logout(request):
    """Logout user and invalidate session"""
    if request.session:
        request.session.flush()  # Mark session for deletion
        return {'status': 'logged_out'}
    return {'error': 'No active session'}, 400

@app.route('/profile')
async def profile(request):
    """Protected route requiring authentication"""
    if not request.session.get('logged_in'):
        return {'error': 'Not authenticated'}, 401

    user_id = request.session.get('user_id')
    user_role = request.session.get('user_role', 'user')

    return {
        'user_id': user_id,
        'role': user_role,
        'login_time': request.session.get('login_time')
    }
```

#### Session Management
```python
@app.route('/admin/sessions')
async def admin_sessions(request):
    """Admin endpoint to manage user sessions"""
    if not request.session.get('user_role') == 'admin':
        return {'error': 'Admin access required'}, 403

    user_id = request.query_params.get('user_id')
    if not user_id:
        return {'error': 'User ID required'}, 400

    # Get all sessions for a user
    sessions = await session_manager.get_user_sessions(user_id)

    # Invalidate all sessions for a user
    invalidated_count = await session_manager.invalidate_user_sessions(user_id)

    return {
        'user_id': user_id,
        'sessions_count': len(sessions),
        'invalidated_count': invalidated_count
    }
```

### Session Configuration

#### Basic Configuration
```python
from pyserv.server.session import SessionConfig

config = SessionConfig(
    secret_key='your-very-secure-secret-key-here',  # Required
    session_name='myapp_session',  # Cookie name
    max_age=3600,  # Session lifetime in seconds
    secure=True,   # HTTPS only
    http_only=True,  # Prevent XSS
    same_site='Lax',  # CSRF protection
    domain='example.com',  # Cookie domain
    path='/',  # Cookie path
    backend=SessionBackend.MEMORY  # Storage backend
)
```

#### Advanced Configuration
```python
config = SessionConfig(
    secret_key='your-secret-key',
    max_age=7200,  # 2 hours
    session_timeout=1800,  # 30 minutes of inactivity
    max_sessions_per_user=5,  # Limit concurrent sessions
    cleanup_interval=300,  # Cleanup every 5 minutes
    enable_encryption=True,  # Encrypt session data
    compression_enabled=True,  # Compress session data
    backend=SessionBackend.DATABASE,  # Use database storage
    database_table='user_sessions',  # Database table name
    redis_url='redis://localhost:6379/0'  # Redis connection
)
```

### Session Storage Backends

#### Memory Backend (Default)
```python
from pyserv.server.session import SessionConfig, MemorySessionStore

config = SessionConfig(
    secret_key='your-secret-key',
    backend=SessionBackend.MEMORY
)

store = MemorySessionStore()
session_manager = SessionManager(config, store)
```

#### Database Backend
```python
from pyserv.server.session import SessionConfig, DatabaseSessionStore
from pyserv.database import DatabaseConnection

# Create database connection
db_connection = DatabaseConnection.get_instance(DatabaseConfig('sqlite:///sessions.db'))

config = SessionConfig(
    secret_key='your-secret-key',
    backend=SessionBackend.DATABASE,
    database_table='sessions'
)

store = DatabaseSessionStore(db_connection)
session_manager = SessionManager(config, store)
```

#### Redis Backend
```python
from pyserv.server.session import SessionConfig, RedisSessionStore

config = SessionConfig(
    secret_key='your-secret-key',
    backend=SessionBackend.REDIS,
    redis_url='redis://localhost:6379/0'
)

store = RedisSessionStore('redis://localhost:6379/0')
session_manager = SessionManager(config, store)
```

### Session Security

#### Session Encryption
```python
from pyserv.server.session import SessionCrypto

crypto = SessionCrypto('your-secret-key')

# Encrypt session data
data = {'user_id': 123, 'role': 'admin'}
encrypted = crypto.encrypt(data)
print(f"Encrypted: {encrypted}")

# Decrypt session data
decrypted = crypto.decrypt(encrypted)
print(f"Decrypted: {decrypted}")
```

#### Session Integrity
```python
# Sessions include HMAC for integrity verification
# If session data is tampered with, decryption will fail
try:
    decrypted = crypto.decrypt(tampered_encrypted_data)
except ValueError as e:
    print(f"Session integrity check failed: {e}")
```

#### Session Fixation Protection
```python
@app.route('/login')
async def login(request):
    """Login with session fixation protection"""
    user = await authenticate_user(request)

    if user:
        # Create new session (old session ID becomes invalid)
        session = await session_manager.create_session(
            user_id=user.id,
            data={'logged_in': True}
        )

        # Session fixation protection: cycle the session key
        await request.session.cycle_key()

        return {'status': 'logged_in'}
```

### Session Middleware

#### Automatic Session Handling
```python
from pyserv.server.session import SessionMiddleware

# Add session middleware to application
app.add_middleware(SessionMiddleware, session_manager=session_manager)

# Now all requests will have automatic session handling:
# - Session loaded from cookie
# - Session attached to request.session
# - Session saved on response
# - Session cookie set for new sessions
```

#### Custom Session Middleware
```python
class CustomSessionMiddleware:
    def __init__(self, session_manager):
        self.session_manager = session_manager

    async def __call__(self, request, call_next):
        # Custom session loading logic
        session_id = request.cookies.get('custom_session_id')
        session = None

        if session_id:
            session = await self.session_manager.get_session(session_id)

        # Attach custom session interface
        request.custom_session = SessionInterface(session, self.session_manager)

        response = await call_next(request)

        # Custom session saving logic
        if hasattr(request.custom_session, '_modified'):
            await request.custom_session.save()

        return response
```

### Session Analytics

#### Session Statistics
```python
@app.route('/admin/session-stats')
async def session_stats(request):
    """Get session statistics"""
    stats = session_manager.get_stats()

    return {
        'active_sessions': len(session_manager.store.sessions),
        'cleanup_interval': stats['cleanup_interval'],
        'max_sessions_per_user': stats['max_sessions_per_user'],
        'session_timeout': stats['session_timeout']
    }
```

#### User Session Tracking
```python
@app.route('/user/sessions')
async def user_sessions(request):
    """Get current user's sessions"""
    if not request.session.get('logged_in'):
        return {'error': 'Not authenticated'}, 401

    user_id = request.session.get('user_id')
    sessions = await session_manager.get_user_sessions(user_id)

    return {
        'user_id': user_id,
        'sessions': [
            {
                'session_id': s.session_id,
                'created_at': s.created_at,
                'updated_at': s.updated_at,
                'ip_address': s.ip_address,
                'user_agent': s.user_agent
            }
            for s in sessions
        ]
    }
```

### Best Practices

#### Security Best Practices
1. **Use Strong Secret Keys**: Generate cryptographically secure secret keys
2. **HTTPS Only**: Always use secure cookies in production
3. **Session Timeouts**: Set appropriate session timeouts
4. **Limit Concurrent Sessions**: Prevent session hijacking
5. **Session Rotation**: Rotate session keys on sensitive operations

#### Performance Best Practices
1. **Choose Right Backend**: Use Redis for high-traffic applications
2. **Cleanup Regularly**: Configure appropriate cleanup intervals
3. **Monitor Session Usage**: Track session creation and cleanup
4. **Database Indexing**: Index session tables for database backend

#### Development Best Practices
1. **Test Session Behavior**: Test session handling in development
2. **Handle Session Errors**: Gracefully handle session corruption
3. **Log Session Events**: Log important session events
4. **Session Validation**: Validate session data before use

### Error Handling

#### Session Errors
```python
@app.exception_handler(SessionError)
async def handle_session_error(exc: SessionError):
    """Handle session-related errors"""
    logger.error(f"Session error: {exc}")

    if isinstance(exc, SessionNotFoundError):
        return {'error': 'Session not found'}, 404
    elif isinstance(exc, SessionExpiredError):
        return {'error': 'Session expired'}, 401
    elif isinstance(exc, SessionCorruptedError):
        return {'error': 'Session corrupted'}, 400
    else:
        return {'error': 'Session error'}, 500
```

#### Graceful Degradation
```python
@app.route('/profile')
async def profile(request):
    """Profile with graceful session handling"""
    try:
        user_id = request.session.get('user_id')
        if not user_id:
            return {'error': 'Not authenticated'}, 401

        user = await get_user_by_id(user_id)
        return {'user': user}

    except KeyError:
        # Session not available
        return {'error': 'Session required'}, 401
    except Exception as e:
        # Other errors
        logger.error(f"Profile error: {e}")
        return {'error': 'Internal server error'}, 500
```

### Integration Examples

#### With Authentication System
```python
class AuthService:
    def __init__(self, session_manager):
        self.session_manager = session_manager

    async def login(self, username: str, password: str, request) -> dict:
        """Authenticate user and create session"""
        user = await authenticate_user(username, password)

        if user:
            session = await self.session_manager.create_session(
                user_id=user.id,
                data={
                    'user_id': user.id,
                    'username': user.username,
                    'role': user.role,
                    'logged_in': True
                },
                ip_address=request.client_ip,
                user_agent=request.headers.get('User-Agent')
            )

            return {
                'status': 'success',
                'user': user,
                'session_id': session.session_id
            }

        return {'status': 'failed', 'error': 'Invalid credentials'}

    async def logout(self, request) -> dict:
        """Logout user and invalidate session"""
        if request.session:
            await self.session_manager.delete_session(request.session.session_id)
            return {'status': 'success'}

        return {'status': 'failed', 'error': 'No active session'}
```

#### With Rate Limiting
```python
class RateLimitedSessionMiddleware:
    def __init__(self, session_manager, rate_limiter):
        self.session_manager = session_manager
        self.rate_limiter = rate_limiter

    async def __call__(self, request, call_next):
        # Check rate limit before session processing
        client_key = request.client_ip
        if not await self.rate_limiter.check_limit(client_key):
            return Response('Rate limit exceeded', status_code=429)

        # Process session normally
        session_id = request.cookies.get('session_id')
        session = await self.session_manager.get_session(session_id)
        request.session = SessionInterface(session, self.session_manager)

        response = await call_next(request)

        # Save session
        if hasattr(request.session, '_modified'):
            await request.session.save()

        return response
```

### Client-Side Session Handling

#### JavaScript Session Management
```javascript
class SessionManager {
    constructor(sessionName = 'pyserv_session') {
        this.sessionName = sessionName;
    }

    // Get session cookie
    getSessionId() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === this.sessionName) {
                return value;
            }
        }
        return null;
    }

    // Set session data via API
    async setSessionData(key, value) {
        const sessionId = this.getSessionId();
        if (!sessionId) {
            throw new Error('No active session');
        }

        const response = await fetch('/session/set', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ key, value }),
            credentials: 'include'  // Include cookies
        });

        if (!response.ok) {
            throw new Error('Failed to set session data');
        }

        return await response.json();
    }

    // Get session data via API
    async getSessionData() {
        const response = await fetch('/session', {
            credentials: 'include'
        });

        if (!response.ok) {
            throw new Error('Failed to get session data');
        }

        return await response.json();
    }

    // Login
    async login(username, password) {
        const response = await fetch('/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ username, password }),
            credentials: 'include'
        });

        if (!response.ok) {
            throw new Error('Login failed');
        }

        return await response.json();
    }

    // Logout
    async logout() {
        const response = await fetch('/logout', {
            credentials: 'include'
        });

        if (!response.ok) {
            throw new Error('Logout failed');
        }

        return await response.json();
    }
}

// Usage
const sessionManager = new SessionManager();

// Set session data
await sessionManager.setSessionData('theme', 'dark');

// Get session data
const sessionData = await sessionManager.getSessionData();
console.log('User ID:', sessionData.user_id);

// Login
await sessionManager.login('username', 'password');

// Logout
await sessionManager.logout();
```

#### React Session Hook
```javascript
import { useState, useEffect } from 'react';

function useSession() {
    const [session, setSession] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchSessionData();
    }, []);

    const fetchSessionData = async () => {
        try {
            const response = await fetch('/session', {
                credentials: 'include'
            });

            if (response.ok) {
                const data = await response.json();
                setSession(data);
            } else {
                setSession(null);
            }
        } catch (error) {
            console.error('Failed to fetch session:', error);
            setSession(null);
        } finally {
            setLoading(false);
        }
    };

    const setSessionData = async (key, value) => {
        try {
            const response = await fetch('/session/set', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ key, value }),
                credentials: 'include'
            });

            if (response.ok) {
                await fetchSessionData(); // Refresh session data
                return true;
            }
        } catch (error) {
            console.error('Failed to set session data:', error);
        }
        return false;
    };

    const login = async (username, password) => {
        try {
            const response = await fetch('/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ username, password }),
                credentials: 'include'
            });

            if (response.ok) {
                await fetchSessionData(); // Refresh session data
                return true;
            }
        } catch (error) {
            console.error('Login failed:', error);
        }
        return false;
    };

    const logout = async () => {
        try {
            const response = await fetch('/logout', {
                credentials: 'include'
            });

            if (response.ok) {
                setSession(null);
                return true;
            }
        } catch (error) {
            console.error('Logout failed:', error);
        }
        return false;
    };

    return {
        session,
        loading,
        setSessionData,
        login,
        logout,
        isAuthenticated: !!session?.user_id
    };
}

// Usage in React component
function App() {
    const { session, loading, login, logout, isAuthenticated } = useSession();

    if (loading) {
        return <div>Loading...</div>;
    }

    if (!isAuthenticated) {
        return (
            <LoginForm onLogin={login} />
        );
    }

    return (
        <div>
            <p>Welcome, {session.user_id}!</p>
            <button onClick={logout}>Logout</button>
        </div>
    );
}
```

### Performance Considerations
- **Session Encryption**: Encryption adds CPU overhead but ensures security
- **Database Storage**: Database backends are slower than memory but persistent
- **Redis Storage**: Redis provides the best performance for distributed applications
- **Cleanup Frequency**: Balance between memory usage and cleanup frequency
- **Session Size**: Keep session data minimal to reduce storage overhead

## 🗄️ Database Integration

### ORM Usage
```python
from pyserv.models import Model, Field

class User(Model):
    __table__ = 'users'

    id = Field(int, primary_key=True)
    username = Field(str, unique=True, max_length=50)
    email = Field(str, unique=True)
    password_hash = Field(str)
    created_at = Field(datetime, default=datetime.utcnow)
    is_active = Field(bool, default=True)

# CRUD operations
user = await User.create({
    'username': 'john_doe',
    'email': 'john@example.com',
    'password_hash': crypto.hash_password('password')
})

users = await User.filter(is_active=True).order_by('-created_at')
user = await User.find(1)
```

### Migrations
```python
from pyserv.migrations import get_migration_framework

migrator = get_migration_framework()

# Create migration
await migrator.create_migration("add_user_email", "add_column",
                               table_name="users",
                               column_name="email",
                               column_def="VARCHAR(255) UNIQUE")

# Run migrations
await migrator.migrate()
```

## 🚀 Deployment

### Docker Deployment
```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy application
WORKDIR /app
COPY . .

# Install Pyserv  with C extensions
RUN pip install -e .

# Expose port
EXPOSE 8000

# Run application
CMD ["python", "-m", "pyserv .core.server_bindings"]
```

### Production Configuration
```python
from pyserv.core.server_bindings import PythonServerConfig

config = PythonServerConfig(
    host="0.0.0.0",
    port=8000,
    max_connections=10000,
    worker_threads=8,
    enable_ssl=True,
    ssl_cert="/path/to/cert.pem",
    ssl_key="/path/to/key.pem"
)

server = HighPerformanceServer(config)
server.run()
```

## 🔧 Development

### Project Structure
```
pyserv /
├── core/                    # Core framework (C/C++ + Python)
│   ├── server_core.c       # C HTTP server implementation
│   ├── server_bindings.py  # Python bindings
│   └── __init__.py
├── security/               # Security modules
│   ├── iam.py             # Identity & Access Management
│   ├── cryptography.py    # ECC & SHA3 cryptography
│   ├── zero_trust.py      # Zero Trust implementation
│   ├── web3.py            # Blockchain integration
│   └── __init__.py
├── models/                # ORM and database
├── controllers/           # MVC controllers
├── views/                 # Template views
├── graphql/               # GraphQL implementation
├── monitoring/            # Metrics and logging
├── migrations/            # Database migrations
├── microservices/         # Service discovery
├── i18n/                  # Internationalization
├── static/                # Static files
├── templates/             # HTML templates
└── tests/                 # Test suite
```

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=pyserv  --cov-report=html

# Run specific test categories
pytest tests/unit/          # Unit tests
pytest tests/integration/   # Integration tests
pytest tests/security/      # Security tests
pytest tests/performance/   # Performance tests
```

### Building Documentation
```bash
# Install documentation dependencies
pip install -e .[dev]

# Build documentation
cd docs
make html

# View documentation
open _build/html/index.html
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup
```bash
git clone https://github.com/pyserv /pyserv .git
cd pyserv 

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e .[dev]

# Run tests
pytest

# Start development server
python -m pyserv .core.server_bindings
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **C/C++ HTTP Server**: Inspired by high-performance servers like nginx and lighttpd
- **Security Architecture**: Based on industry best practices and standards
- **Cryptography**: Built on the excellent `cryptography` library
- **Web3 Integration**: Powered by Web3.py and related libraries

## 📞 Support

- **Documentation**: [https://pyserv .dev/docs](https://pyserv .dev/docs)
- **Issues**: [https://github.com/pyserv /pyserv /issues](https://github.com/pyserv /pyserv /issues)
- **Discussions**: [https://github.com/pyserv /pyserv /discussions](https://github.com/pyserv /pyserv /discussions)
- **Email**: team@pyserv .dev

---

**Pyserv ** - Where Python meets C/C++ performance with enterprise-grade security! 🚀

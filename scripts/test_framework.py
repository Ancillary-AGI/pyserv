#!/usr/bin/env python3
"""
Comprehensive test to verify Pyserv framework is working correctly.
Tests core functionality, imports, and basic operations.
"""

import asyncio
import sys
import traceback
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test that all core imports work"""
    print("Testing imports...")
    
    try:
        # Core framework
        from pyserv import Application, AppConfig, Router, Route
        from pyserv.http import Request, Response
        from pyserv.server import Server
        print("[OK] Core framework imports")
        
        # Security
        from pyserv.security import SecurityManager, FileValidator
        from pyserv.security.middleware import SecurityMiddleware
        print("[OK] Security imports")
        
        # Session management
        from pyserv.server.session import SessionManager, SessionConfig
        print("[OK] Session imports")
        
        # Database/Models
        from pyserv.models import BaseModel, StringField, IntegerField
        print("[OK] Model imports")
        
        # Middleware
        from pyserv.middleware import MiddlewareManager
        print("[OK] Middleware imports")
        
        # Templates
        from pyserv.templating import TemplateEngine
        print("[OK] Template imports")
        
        # Events and plugins
        from pyserv.events import EventBus, Event
        from pyserv.plugins import PluginManager
        print("[OK] Events/Plugins imports")
        
        # WebSocket and SSE
        from pyserv.websocket import WebSocket
        from pyserv.server.sse import SSEManager
        print("[OK] WebSocket/SSE imports")
        
        # Exceptions
        from pyserv.exceptions import HTTPException, BadRequest, NotFound
        print("[OK] Exception imports")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Import failed: {e}")
        traceback.print_exc()
        return False

def test_basic_application():
    """Test basic application creation and configuration"""
    print("\nTesting basic application...")
    
    try:
        from pyserv import Application, Response
        
        # Create application
        app = Application()
        
        # Add a simple route
        @app.route('/')
        async def home(request):
            return Response.text("Hello, Pyserv!")
        
        @app.route('/json')
        async def json_endpoint(request):
            return Response.json({"message": "success", "framework": "Pyserv"})
        
        # Check routes were added
        assert len(app.router.routes) >= 2
        print("[OK] Application creation and routing")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Application test failed: {e}")
        traceback.print_exc()
        return False

def test_models():
    """Test model system"""
    print("\nTesting models...")
    
    try:
        from pyserv.models import BaseModel, StringField, IntegerField, DateTimeField
        
        class User(BaseModel):
            name = StringField(max_length=100, nullable=False)
            email = StringField(max_length=255, unique=True)
            age = IntegerField(min_value=0, max_value=150)
            created_at = DateTimeField(auto_now_add=True)
        
        # Create instance
        user = User(name="John Doe", email="john@example.com", age=30)
        
        # Test field access
        assert user.name == "John Doe"
        assert user.email == "john@example.com"
        assert user.age == 30
        
        # Test to_dict
        user_dict = user.to_dict()
        assert user_dict['name'] == "John Doe"
        
        print("[OK] Model system working")
        return True
        
    except Exception as e:
        print(f"[FAIL] Model test failed: {e}")
        traceback.print_exc()
        return False

def test_middleware():
    """Test middleware system"""
    print("\nTesting middleware...")
    
    try:
        from pyserv import Application
        from pyserv.middleware.manager import PerformanceMonitoringMiddleware
        from pyserv.security.middleware import SecurityHeadersMiddleware
        
        app = Application()
        
        # Add middleware
        app.add_middleware(PerformanceMonitoringMiddleware)
        app.add_middleware(SecurityHeadersMiddleware)
        
        # Check middleware was added
        assert len(app.middleware_manager.http_middlewares) >= 2
        
        print("[OK] Middleware system working")
        return True
        
    except Exception as e:
        print(f"[FAIL] Middleware test failed: {e}")
        traceback.print_exc()
        return False

def test_security():
    """Test security features"""
    print("\nTesting security...")
    
    try:
        from pyserv.security import get_security_manager, BasicFileValidator
        from pyserv.security.middleware import SecurityConfig
        
        # Test security manager
        security = get_security_manager()
        assert security is not None
        
        # Test file validator
        validator = BasicFileValidator()
        assert validator is not None
        
        # Test security config
        config = SecurityConfig()
        assert config.csrf_enabled == True
        
        print("[OK] Security system working")
        return True
        
    except Exception as e:
        print(f"[FAIL] Security test failed: {e}")
        traceback.print_exc()
        return False

def test_sessions():
    """Test session management"""
    print("\nTesting sessions...")
    
    try:
        from pyserv.server.session import SessionManager, SessionConfig, MemorySessionStore
        
        # Create session manager
        config = SessionConfig(secret_key="test-key")
        store = MemorySessionStore()
        manager = SessionManager(config, store)
        
        assert manager is not None
        assert manager.config.secret_key == "test-key"
        
        print("[OK] Session system working")
        return True
        
    except Exception as e:
        print(f"[FAIL] Session test failed: {e}")
        traceback.print_exc()
        return False

def test_templates():
    """Test template system"""
    print("\nTesting templates...")
    
    try:
        from pyserv.templating import TemplateEngine
        
        engine = TemplateEngine()
        
        # Test simple template
        template = engine.from_string("Hello {{name}}!")
        result = template.render(name="World")
        assert result == "Hello World!"
        
        print("[OK] Template system working")
        return True
        
    except Exception as e:
        print(f"[FAIL] Template test failed: {e}")
        traceback.print_exc()
        return False

async def test_async_features():
    """Test async features like events and SSE"""
    print("\nTesting async features...")
    
    try:
        from pyserv.events import EventBus, Event
        from pyserv.server.sse import SSEManager
        
        # Test event bus
        bus = EventBus()
        event = Event(event_type="test", data={"message": "hello"})
        assert event.event_type == "test"
        
        # Test SSE manager
        sse = SSEManager()
        assert sse is not None
        
        print("[OK] Async features working")
        return True
        
    except Exception as e:
        print(f"[FAIL] Async test failed: {e}")
        traceback.print_exc()
        return False

def test_exceptions():
    """Test exception system"""
    print("\nTesting exceptions...")
    
    try:
        from pyserv.exceptions import HTTPException, BadRequest, NotFound, ValidationError
        
        # Test basic exception
        exc = BadRequest("Invalid input")
        assert exc.status_code == 400
        assert exc.message == "Invalid input"
        
        # Test exception to dict
        exc_dict = exc.to_dict()
        assert exc_dict['error']['status_code'] == 400
        
        print("[OK] Exception system working")
        return True
        
    except Exception as e:
        print(f"[FAIL] Exception test failed: {e}")
        traceback.print_exc()
        return False

async def main():
    """Run all tests"""
    print("Testing Pyserv Framework Functionality\n")
    
    tests = [
        test_imports,
        test_basic_application,
        test_models,
        test_middleware,
        test_security,
        test_sessions,
        test_templates,
        test_async_features,
        test_exceptions
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if asyncio.iscoroutinefunction(test):
                result = await test()
            else:
                result = test()
            
            if result:
                passed += 1
        except Exception as e:
            print(f"[CRASH] Test {test.__name__} crashed: {e}")
    
    print(f"\nTest Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("All tests passed! Pyserv framework is working correctly.")
        return True
    else:
        print("Some tests failed. Check the output above for details.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
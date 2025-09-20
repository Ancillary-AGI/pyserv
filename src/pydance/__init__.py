"""
Pydance - A comprehensive web framework with MVC architecture.

Pydance is a high-performance web framework built with Python that provides
a complete MVC (Model-View-Controller) architecture for building scalable
web applications. It includes features like:

- High-performance HTTP server with C extensions
- MVC architecture with controllers, models, and views
- Template engine with multiple language support
- Database ORM with migration support
- Security middleware and authentication
- WebSocket support
- Internationalization (i18n)
- NeuralForge AI integration
- Widget system for UI components
- Microservices support
- Monitoring and metrics
- Quantum security features

Example:
    >>> from pydance import Application
    >>>
    >>> app = Application()
    >>>
    >>> @app.route('/')
    ... def hello(request):
    ...     return 'Hello, World!'
    >>>
    >>> if __name__ == '__main__':
    ...     app.run()
"""

__version__ = "0.1.0"

# Core framework imports
from pydance.core.server.application import Application
from pydance.core.server.config import AppConfig
from pydance.core.routing import Router, Route
from pydance.core.middleware import HTTPMiddleware, WebSocketMiddleware
from pydance.core.exceptions import HTTPException, BadRequest, NotFound, Forbidden
from pydance.core.templating import TemplateEngine
from pydance.core.security import Security, CryptoUtils

# Performance optimization imports
from pydance.core.database_pool import get_pooled_connection, PoolConfig, OptimizedDatabaseConnection
from pydance.core.distributed_cache import get_distributed_cache, CacheConfig
from pydance.core.load_balancer import get_load_balancer, LoadBalancerConfig
from pydance.microservices.grpc_service import GRPCService, GRPCConfig
from pydance.core.performance_optimizer import init_performance_monitoring, get_performance_monitor
from pydance.core.profiling import get_profiler, get_load_tester, profile_function, benchmark
from pydance.core.performance_anti_patterns import get_anti_pattern_monitor

# Utility imports
from pydance.core.utilities import (
    NumberUtils, StringUtils, DateTimeUtils,
    FastList, FastDict, CircularBuffer, BloomFilter,
    Sanitizer, CSRFUtils,
    csrf_exempt, csrf_exempt_endpoint,
    CompressionUtils, EncodingUtils
)

# Form validation imports
from pydance.core.form_validation import (
    Form, ModelForm, Field, CharField, EmailField, IntegerField,
    FloatField, DateField, FileField, CSRFToken, Sanitizer as FormSanitizer
)

# NeuralForge AI Framework
from pydance.neuralforge import (
    NeuralForge, NeuralAgent, AgentCapability, AgentState, AgentMemory,
    LLMEngine, LLMConfig, LLMResponse, LLMProvider,
    MCPServer, AgentCommunicator, EconomySystem
)

# Widgets system
from pydance.widgets import (
    RichText, RichSelect, RichTitle, RichFile, RichDate,
    RichColor, RichRating, RichTags, RichSlider, RichCode
)

__all__ = [
    # Core framework
    'Application', 'AppConfig', 'Router', 'Route', 'HTTPMiddleware', 'WebSocketMiddleware',
    'HTTPException', 'BadRequest', 'NotFound', 'Forbidden',
    'TemplateEngine', 'Security', 'CryptoUtils',

    # Performance optimizations
    'get_pooled_connection', 'PoolConfig', 'OptimizedDatabaseConnection',
    'get_distributed_cache', 'CacheConfig',
    'get_load_balancer', 'LoadBalancerConfig',
    'GRPCService', 'GRPCConfig',
    'init_performance_monitoring', 'get_performance_monitor',
    'get_profiler', 'get_load_tester', 'profile_function', 'benchmark',
    'get_anti_pattern_monitor',

    # Utilities
    'NumberUtils', 'StringUtils', 'DateTimeUtils',
    'FastList', 'FastDict', 'CircularBuffer', 'BloomFilter',
    'Sanitizer', 'CSRFUtils',
    'csrf_exempt', 'csrf_exempt_endpoint',
    'CompressionUtils', 'EncodingUtils',

    # Form validation
    'Form', 'ModelForm', 'Field', 'CharField', 'EmailField', 'IntegerField',
    'FloatField', 'DateField', 'FileField', 'CSRFToken', 'FormSanitizer',

    # NeuralForge AI
    'NeuralForge', 'NeuralAgent', 'AgentCapability', 'AgentState', 'AgentMemory',
    'LLMEngine', 'LLMConfig', 'LLMResponse', 'LLMProvider',
    'MCPServer', 'AgentCommunicator', 'EconomySystem',

    # Widgets
    'RichText', 'RichSelect', 'RichTitle', 'RichFile', 'RichDate',
    'RichColor', 'RichRating', 'RichTags', 'RichSlider', 'RichCode'
]

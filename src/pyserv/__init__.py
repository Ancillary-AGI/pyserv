"""
Pyserv - A comprehensive web framework with MVC architecture.

Pyserv is a high-performance web framework built with Python that provides
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
    >>> from pyserv import Application
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

__version__: str = "0.1.0"

# Core framework imports
from pyserv.server.application import Application
from pyserv.server.config import AppConfig
from pyserv.routing import Router, Route
from pyserv.middleware import (
    HTTPMiddleware, WebSocketMiddleware,
    ThrottleMiddleware, ThrottleConfig
)
from pyserv.exceptions import HTTPException, BadRequest, NotFound, Forbidden
from pyserv.templating import TemplateEngine
from pyserv.security import (
    EncryptionService, AuditLogger,
    RateLimiter, CSRFProtection, SecurityHeaders
)
from pyserv.auth import (
    AuthManager, AuthenticationMiddleware, AuthorizationMiddleware,
    login_required, permission_required, role_required,
    LoginForm, RegistrationForm, auth_manager
)
from pyserv.resilience import (
    CircuitBreaker, CircuitBreakerConfig, CircuitBreakerState,
    CircuitBreakerManager, CircuitBreakerOpenException, CircuitBreakerTimeoutException,
    RetryMechanism, RetryConfig, RetryStrategy, RetryCondition,
    RetryManager, with_exponential_backoff, with_fixed_retry,
    GracefulDegradation, DegradationStrategy, DegradationRule,
    AutoRecoveryManager, HealthCheck, HealthStatus, RecoveryStrategy, SystemMetrics,
    LoadBalancer, LoadBalancingStrategy, BackendServer, LoadBalancerManager
)
from pyserv.caching import (
    CacheManager, CacheConfig, CacheLevel,
    MemoryCache, RedisCache, CDNCache,
    cache_result, invalidate_cache, cache_key,
    CacheMetricsCollector
)
from pyserv.performance import (
    PerformanceMonitor, PerformanceMetrics,
    Profiler, profile_function, benchmark,
    PerformanceOptimizer,
    PerformanceAntiPatternDetector
)
from pyserv.payment import (
    PaymentProcessor, PaymentConfig,
    StripeProcessor, PayPalProcessor, CryptoProcessor,
    PaymentSecurity, PCICompliance,
    TransactionManager, WebhookHandler
)
from pyserv.deployment import (
    DeploymentManager, DeploymentConfig,
    DockerManager, KubernetesManager,
    CICDPipeline, PipelineStage,
    DeploymentMonitor, RollbackManager
)
from pyserv.monitoring import (
    MonitoringManager, MonitoringConfig,
    MetricsCollector, AlertManager, AlertRule,
    DashboardGenerator, LogAggregator, TraceManager
)
from pyserv.iot import (
    MQTTClient, MQTTConfig,
    CoAPServer, CoAPConfig,
    WebSocketP2P, P2PConfig,
    DeviceManager, DeviceConfig,
    ProtocolGateway, ProtocolGatewayConfig
)

# Performance optimization imports
from pyserv.database.connections import DatabaseConnection, PoolConfig
from pyserv.caching.distributed_cache import get_distributed_cache
from pyserv.microservices.grpc_service import GRPCService, GRPCConfig
from pyserv.performance.performance_optimizer import init_performance_monitoring, get_performance_monitor
from pyserv.performance.profiling import get_profiler, get_load_tester
from pyserv.performance.performance_anti_patterns import get_anti_pattern_monitor

# Utility imports - only import what exists
from pyserv.utils.di import Container, inject, service
from pyserv.utils.form_validation import Form, Field
from pyserv.i18n.manager import I18n
from pyserv.utils.queues import Queue

# NeuralForge AI Framework
from pyserv.neuralforge import (
    NeuralForge, NeuralAgent, AgentCapability, AgentState, AgentMemory,
    LLMEngine, LLMConfig, LLMResponse, LLMProvider,
    MCPServer, AgentCommunicator, EconomySystem
)

# Widgets system
from pyserv.widgets import (
    RichText, RichSelect, RichTitle, RichFile, RichDate,
    RichColor, RichRating, RichTags, RichSlider, RichCode
)

__all__ = [
    # Core framework
    'Application', 'AppConfig', 'Router', 'Route', 'HTTPMiddleware', 'WebSocketMiddleware',
    'ThrottleMiddleware', 'ThrottleConfig',
    'HTTPException', 'BadRequest', 'NotFound', 'Forbidden',
    'TemplateEngine',

    # Enhanced Security Framework
    'AuthManager', 'AuthenticationMiddleware', 'AuthorizationMiddleware',
    'login_required', 'permission_required', 'role_required',
    'LoginForm', 'RegistrationForm', 'auth_manager',
    'EncryptionService', 'AuditLogger',
    'RateLimiter', 'CSRFProtection', 'SecurityHeaders',

    # Resilience & Fault Tolerance
    'CircuitBreaker', 'CircuitBreakerConfig', 'CircuitBreakerState',
    'CircuitBreakerManager', 'CircuitBreakerOpenException', 'CircuitBreakerTimeoutException',
    'RetryMechanism', 'RetryConfig', 'RetryStrategy', 'RetryCondition',
    'RetryManager', 'with_exponential_backoff', 'with_fixed_retry',
    'GracefulDegradation', 'DegradationStrategy', 'DegradationRule',
    'AutoRecoveryManager', 'HealthCheck', 'HealthStatus', 'RecoveryStrategy', 'SystemMetrics',
    'LoadBalancer', 'LoadBalancingStrategy', 'BackendServer', 'LoadBalancerManager',

    # Multi-level Caching System
    'CacheManager', 'CacheConfig', 'CacheLevel',
    'MemoryCache', 'RedisCache', 'CDNCache',
    'cache_result', 'invalidate_cache', 'cache_key',
    'CacheMetricsCollector',

    # Performance Monitoring & Optimization
    'PerformanceMonitor', 'PerformanceMetrics',
    'Profiler', 'profile_function', 'benchmark',
    'PerformanceOptimizer',
    'PerformanceAntiPatternDetector',

    # Payment Processing System
    'PaymentProcessor', 'PaymentConfig',
    'StripeProcessor', 'PayPalProcessor', 'CryptoProcessor',
    'PaymentSecurity', 'PCICompliance',
    'TransactionManager', 'WebhookHandler',

    # Deployment Automation System
    'DeploymentManager', 'DeploymentConfig',
    'DockerManager', 'KubernetesManager',
    'CICDPipeline', 'PipelineStage',
    'DeploymentMonitor', 'RollbackManager',

    # Advanced Monitoring System
    'MonitoringManager', 'MonitoringConfig',
    'MetricsCollector', 'AlertManager', 'AlertRule',
    'DashboardGenerator', 'LogAggregator', 'TraceManager',

    # IoT Protocols and P2P Communication
    'MQTTClient', 'MQTTConfig',
    'CoAPServer', 'CoAPConfig',
    'WebSocketP2P', 'P2PConfig',
    'DeviceManager', 'DeviceConfig',
    'ProtocolGateway', 'ProtocolGatewayConfig',

    # Performance optimizations
    'PoolConfig', 'DatabaseConnection',
    'get_distributed_cache', 'CacheConfig',
    'GRPCService', 'GRPCConfig',
    'init_performance_monitoring', 'get_performance_monitor',
    'get_profiler', 'get_load_tester', 'profile_function', 'benchmark',
    'get_anti_pattern_monitor',

    # Utilities
    'Container', 'inject', 'service',
    'Form', 'Field',
    'I18n',
    'Queue',

    # NeuralForge AI
    'NeuralForge', 'NeuralAgent', 'AgentCapability', 'AgentState', 'AgentMemory',
    'LLMEngine', 'LLMConfig', 'LLMResponse', 'LLMProvider',
    'MCPServer', 'AgentCommunicator', 'EconomySystem',

    # Widgets
    'RichText', 'RichSelect', 'RichTitle', 'RichFile', 'RichDate',
    'RichColor', 'RichRating', 'RichTags', 'RichSlider', 'RichCode'
]

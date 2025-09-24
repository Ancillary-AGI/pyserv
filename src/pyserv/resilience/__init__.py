"""
Resilience and fault tolerance features for PyServ.
Provides circuit breakers, retry mechanisms, graceful degradation,
auto-recovery, and load balancing for mission-critical applications.
"""

from .circuit_breaker import (
    CircuitBreaker, CircuitBreakerConfig, CircuitBreakerState,
    CircuitBreakerManager, CircuitBreakerOpenException, CircuitBreakerTimeoutException
)
from .retry import (
    RetryMechanism, RetryConfig, RetryStrategy, RetryCondition,
    RetryManager, with_exponential_backoff, with_fixed_retry
)
from .degradation import (
    GracefulDegradation, DegradationStrategy, DegradationRule
)
from .auto_recovery import (
    AutoRecoveryManager, HealthCheck, HealthStatus, RecoveryStrategy, SystemMetrics
)
from .load_balancer import (
    LoadBalancer, LoadBalancingStrategy, BackendServer, LoadBalancerManager
)

__all__ = [
    # Circuit Breaker
    'CircuitBreaker', 'CircuitBreakerConfig', 'CircuitBreakerState',
    'CircuitBreakerManager', 'CircuitBreakerOpenException', 'CircuitBreakerTimeoutException',

    # Retry Mechanisms
    'RetryMechanism', 'RetryConfig', 'RetryStrategy', 'RetryCondition',
    'RetryManager', 'with_exponential_backoff', 'with_fixed_retry',

    # Graceful Degradation
    'GracefulDegradation', 'DegradationStrategy', 'DegradationRule',

    # Auto-Recovery
    'AutoRecoveryManager', 'HealthCheck', 'HealthStatus', 'RecoveryStrategy', 'SystemMetrics',

    # Load Balancing
    'LoadBalancer', 'LoadBalancingStrategy', 'BackendServer', 'LoadBalancerManager'
]

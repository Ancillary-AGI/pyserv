"""
PyServ Resilience & Fault Tolerance Demo

This example demonstrates how to use PyServ's comprehensive resilience features
to build a fault-tolerant, self-healing web application with:

- Circuit breaker pattern for fault tolerance
- Retry mechanisms with exponential backoff
- Graceful degradation for service availability
- Auto-recovery with health monitoring
- Load balancing across multiple instances
"""

import asyncio
import json
import random
import time
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass

from pyserv import Application, Router
from pyserv.resilience import (
    CircuitBreaker, CircuitBreakerConfig, CircuitBreakerState,
    RetryMechanism, RetryConfig, RetryStrategy,
    GracefulDegradation, DegradationStrategy, DegradationRule,
    AutoRecoveryManager, HealthCheck, HealthStatus, RecoveryStrategy,
    LoadBalancer, LoadBalancingStrategy, BackendServer
)
from pyserv.security import RateLimiter, RateLimitRule
from pyserv.middleware import HTTPMiddleware
from pyserv.exceptions import HTTPException
from pyserv.http import Request, Response

# Initialize resilience components
circuit_breaker = CircuitBreaker(CircuitBreakerConfig(
    name="api_service",
    failure_threshold=3,
    recovery_timeout=30.0,
    success_threshold=2
))

retry_mechanism = RetryMechanism(RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    strategy=RetryStrategy.EXPONENTIAL,
    jitter=True
))

graceful_degradation = GracefulDegradation()
auto_recovery_manager = AutoRecoveryManager()

# Load balancer setup
load_balancer = LoadBalancer(LoadBalancingStrategy.ROUND_ROBIN)
load_balancer.add_server(BackendServer("localhost", 8001, weight=2))
load_balancer.add_server(BackendServer("localhost", 8002, weight=1))
load_balancer.add_server(BackendServer("localhost", 8003, weight=1))

# Rate limiter
rate_limiter = RateLimiter()
rate_limiter.add_rule(RateLimitRule(
    name="api_requests",
    requests_per_period=100,
    period_seconds=60,
    strategy=RateLimitRule.RateLimitStrategy.TOKEN_BUCKET
))

# Create application
app = Application()
router = Router()

@dataclass
class ServiceResponse:
    service: str
    status: str
    response_time: float
    timestamp: str
    data: Optional[Dict[str, Any]] = None

# Simulated external services
class ExternalService:
    """Simulated external service that can fail."""

    def __init__(self, name: str, failure_rate: float = 0.1):
        self.name = name
        self.failure_rate = failure_rate
        self.call_count = 0

    async def call(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate service call with potential failure."""
        self.call_count += 1

        # Simulate network delay
        await asyncio.sleep(random.uniform(0.1, 0.5))

        # Simulate occasional failures
        if random.random() < self.failure_rate:
            raise Exception(f"Service {self.name} temporarily unavailable")

        return {
            "service": self.name,
            "endpoint": endpoint,
            "data": data,
            "call_count": self.call_count,
            "timestamp": datetime.now().isoformat()
        }

# Initialize services
user_service = ExternalService("user_service", failure_rate=0.15)
payment_service = ExternalService("payment_service", failure_rate=0.10)
notification_service = ExternalService("notification_service", failure_rate=0.05)

# Resilience middleware
class ResilienceMiddleware(HTTPMiddleware):
    """Middleware that applies resilience patterns."""

    async def process_request(self, request: Request) -> Request:
        """Apply rate limiting."""
        client_ip = request.client_ip or "unknown"
        allowed, rate_info = await rate_limiter.check_rate_limit("api_requests", client_ip)

        if not allowed:
            raise HTTPException(429, f"Rate limit exceeded: {rate_info}")

        return request

    async def process_response(self, request: Request, response: Response) -> Response:
        """Add resilience headers."""
        response.headers["X-Circuit-Breaker-Status"] = circuit_breaker.get_state().value
        response.headers["X-Retry-Mechanism"] = "exponential_backoff"
        return response

# Apply middleware
app.add_middleware(ResilienceMiddleware())

# Routes with resilience patterns
@router.add_route("/api/users", methods=["GET"])
async def get_users(request: Request) -> Response:
    """Get users with circuit breaker protection."""

    try:
        # Use circuit breaker for external service call
        result = await circuit_breaker.call(
            user_service.call,
            "users",
            {"action": "get_all"}
        )

        return Response(json.dumps(result), content_type="application/json")

    except Exception as e:
        # Graceful degradation fallback
        fallback_data = {
            "service": "user_service",
            "status": "degraded",
            "message": "Service temporarily unavailable, using cached data",
            "cached_users": [
                {"id": 1, "name": "John Doe", "cached": True},
                {"id": 2, "name": "Jane Smith", "cached": True}
            ],
            "timestamp": datetime.now().isoformat()
        }

        return Response(json.dumps(fallback_data), content_type="application/json")

@router.add_route("/api/payment/process", methods=["POST"])
async def process_payment(request: Request) -> Response:
    """Process payment with retry mechanism."""

    try:
        data = json.loads(request.body)
        payment_data = {
            "amount": data.get("amount", 0),
            "currency": data.get("currency", "USD"),
            "user_id": data.get("user_id", "unknown")
        }

        # Use retry mechanism for payment processing
        result = await retry_mechanism.execute(
            payment_service.call,
            "process_payment",
            payment_data
        )

        return Response(json.dumps(result), content_type="application/json")

    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON")
    except Exception as e:
        raise HTTPException(500, f"Payment processing failed: {str(e)}")

@router.add_route("/api/notification/send", methods=["POST"])
async def send_notification(request: Request) -> Response:
    """Send notification with graceful degradation."""

    try:
        data = json.loads(request.body)
        notification_data = {
            "type": data.get("type", "email"),
            "recipient": data.get("recipient", ""),
            "message": data.get("message", "")
        }

        # Use graceful degradation for notification service
        result = await graceful_degradation.execute(
            notification_service.call,
            "send_notification",
            notification_data
        )

        return Response(json.dumps(result), content_type="application/json")

    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON")
    except Exception as e:
        # Fallback to degraded response
        fallback_result = {
            "service": "notification_service",
            "status": "queued_offline",
            "message": "Notification queued for offline processing",
            "timestamp": datetime.now().isoformat()
        }

        return Response(json.dumps(fallback_result), content_type="application/json")

@router.add_route("/api/loadbalancer/test", methods=["GET"])
async def test_load_balancer(request: Request) -> Response:
    """Test load balancer functionality."""

    # Get next server from load balancer
    server = load_balancer.get_next_server(request.client_ip)

    if not server:
        raise HTTPException(503, "No healthy servers available")

    # Simulate request to backend server
    backend_response = {
        "server": f"{server.host}:{server.port}",
        "strategy": load_balancer.strategy.value,
        "weight": server.weight,
        "active_connections": server.active_connections,
        "total_requests": server.total_requests,
        "response_time": server.response_time,
        "timestamp": datetime.now().isoformat()
    }

    # Update server stats
    load_balancer.update_server_stats(server, 0.1, True)

    return Response(json.dumps(backend_response), content_type="application/json")

@router.add_route("/api/health", methods=["GET"])
async def health_check(request: Request) -> Response:
    """Comprehensive health check with resilience metrics."""

    # Get circuit breaker status
    circuit_metrics = circuit_breaker.get_metrics()

    # Get load balancer stats
    lb_stats = load_balancer.get_server_stats()

    # Get graceful degradation stats
    degradation_stats = graceful_degradation.get_stats()

    health_data = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "circuit_breaker": {
                "state": circuit_metrics["state"],
                "total_requests": circuit_metrics["total_requests"],
                "success_rate": circuit_metrics["success_rate"],
                "consecutive_failures": circuit_metrics["consecutive_failures"]
            },
            "load_balancer": {
                "strategy": lb_stats["strategy"],
                "total_servers": lb_stats["total_servers"],
                "healthy_servers": lb_stats["healthy_servers"],
                "total_requests": lb_stats["total_requests"]
            },
            "degradation": {
                "total_rules": degradation_stats["total_rules"],
                "cache_size": degradation_stats["cache_size"]
            }
        },
        "resilience_features": [
            "Circuit Breaker Pattern",
            "Retry Mechanisms with Exponential Backoff",
            "Graceful Degradation",
            "Auto-Recovery System",
            "Load Balancing",
            "Rate Limiting",
            "Health Monitoring"
        ]
    }

    return Response(json.dumps(health_data), content_type="application/json")

@router.add_route("/api/resilience/test", methods=["POST"])
async def test_resilience(request: Request) -> Response:
    """Test all resilience features together."""

    try:
        data = json.loads(request.body)
        test_scenario = data.get("scenario", "normal")

        if test_scenario == "circuit_breaker":
            # Test circuit breaker by causing failures
            for i in range(5):
                try:
                    await circuit_breaker.call(
                        user_service.call,
                        "test_failure",
                        {"test": "circuit_breaker"}
                    )
                except Exception:
                    pass  # Expected to fail

            circuit_state = circuit_breaker.get_state()
            return Response(json.dumps({
                "scenario": "circuit_breaker_test",
                "circuit_state": circuit_state.value,
                "message": f"Circuit breaker is now {circuit_state.value}"
            }), content_type="application/json")

        elif test_scenario == "retry":
            # Test retry mechanism
            retry_count = 0

            async def failing_function():
                nonlocal retry_count
                retry_count += 1
                if retry_count < 3:
                    raise Exception("Simulated failure")
                return {"success": True, "attempts": retry_count}

            result = await retry_mechanism.execute(failing_function)

            return Response(json.dumps({
                "scenario": "retry_test",
                "result": result,
                "message": f"Operation succeeded after {retry_count} attempts"
            }), content_type="application/json")

        elif test_scenario == "degradation":
            # Test graceful degradation
            async def failing_service():
                raise Exception("Service unavailable")

            # Add degradation rule
            rule = DegradationRule(
                name="test_degradation",
                condition=lambda e: isinstance(e, Exception),
                strategy=DegradationStrategy.DEGRADED_RESPONSE,
                fallback_data={"degraded": True, "message": "Service degraded"}
            )
            graceful_degradation.add_rule(rule)

            result = await graceful_degradation.execute(failing_service)

            return Response(json.dumps({
                "scenario": "degradation_test",
                "result": result,
                "message": "Graceful degradation working"
            }), content_type="application/json")

        else:
            return Response(json.dumps({
                "scenario": "normal",
                "message": "Normal operation",
                "available_scenarios": ["circuit_breaker", "retry", "degradation"]
            }), content_type="application/json")

    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON")

@router.add_route("/api/metrics", methods=["GET"])
async def get_metrics(request: Request) -> Response:
    """Get comprehensive resilience metrics."""

    metrics = {
        "timestamp": datetime.now().isoformat(),
        "circuit_breaker": circuit_breaker.get_metrics(),
        "load_balancer": load_balancer.get_server_stats(),
        "degradation": graceful_degradation.get_stats(),
        "services": {
            "user_service": {"calls": user_service.call_count},
            "payment_service": {"calls": payment_service.call_count},
            "notification_service": {"calls": notification_service.call_count}
        }
    }

    return Response(json.dumps(metrics), content_type="application/json")

# Setup graceful degradation rules
def setup_degradation_rules():
    """Setup graceful degradation rules."""

    # Rule 1: Cache responses when service is slow
    cache_rule = DegradationRule(
        name="cache_on_timeout",
        condition=lambda e: isinstance(e, asyncio.TimeoutError),
        strategy=DegradationStrategy.CACHED_RESPONSE,
        fallback_data={"cached": True, "message": "Using cached data"},
        priority=1
    )

    # Rule 2: Provide default response for user service failures
    user_fallback_rule = DegradationRule(
        name="user_service_fallback",
        condition=lambda e: "user_service" in str(e),
        strategy=DegradationStrategy.DEGRADED_RESPONSE,
        fallback_data={"users": [], "degraded": True},
        priority=2
    )

    # Rule 3: Queue notifications when service fails
    notification_queue_rule = DegradationRule(
        name="notification_queue",
        condition=lambda e: "notification_service" in str(e),
        strategy=DegradationStrategy.DEGRADED_RESPONSE,
        fallback_data={"status": "queued", "message": "Notification queued"},
        priority=3
    )

    graceful_degradation.add_rule(cache_rule)
    graceful_degradation.add_rule(user_fallback_rule)
    graceful_degradation.add_rule(notification_queue_rule)

# Setup auto-recovery health checks
def setup_health_checks():
    """Setup auto-recovery health checks."""

    async def check_database():
        """Check database connectivity."""
        # Simulate database check
        await asyncio.sleep(0.1)
        return random.random() > 0.05  # 95% healthy

    async def check_external_api():
        """Check external API availability."""
        await asyncio.sleep(0.2)
        return random.random() > 0.1  # 90% healthy

    async def check_memory_usage():
        """Check memory usage."""
        import psutil
        memory = psutil.virtual_memory()
        return memory.percent < 80  # Healthy if < 80%

    # Add health checks
    db_check = HealthCheck(
        name="database",
        check_function=check_database,
        interval=30.0,
        timeout=5.0,
        critical=True,
        recovery_strategy=RecoveryStrategy.RESET_CONNECTIONS
    )

    api_check = HealthCheck(
        name="external_api",
        check_function=check_external_api,
        interval=60.0,
        timeout=10.0,
        critical=False,
        recovery_strategy=RecoveryStrategy.CLEAR_CACHE
    )

    memory_check = HealthCheck(
        name="memory",
        check_function=check_memory_usage,
        interval=10.0,
        timeout=2.0,
        critical=True,
        recovery_strategy=RecoveryStrategy.RESTART_SERVICE
    )

    auto_recovery_manager.add_health_check(db_check)
    auto_recovery_manager.add_health_check(api_check)
    auto_recovery_manager.add_health_check(memory_check)

# Main application
async def main():
    """Main application entry point."""

    print("🚀 PyServ Resilience & Fault Tolerance Demo")
    print("=" * 50)

    # Setup resilience features
    setup_degradation_rules()
    setup_health_checks()

    # Start auto-recovery monitoring
    await auto_recovery_manager.start_monitoring()

    # Add routes to application
    app.add_router(router)

    print("\n📋 Available endpoints:")
    print("  GET  /api/users - Get users (with circuit breaker)")
    print("  POST /api/payment/process - Process payment (with retry)")
    print("  POST /api/notification/send - Send notification (with degradation)")
    print("  GET  /api/loadbalancer/test - Test load balancer")
    print("  GET  /api/health - Health check with resilience metrics")
    print("  POST /api/resilience/test - Test resilience scenarios")
    print("  GET  /api/metrics - Get comprehensive metrics")
    print("\n🛡️ Resilience Features Enabled:")
    print("  ✓ Circuit Breaker Pattern")
    print("  ✓ Retry Mechanisms with Exponential Backoff")
    print("  ✓ Graceful Degradation")
    print("  ✓ Auto-Recovery System")
    print("  ✓ Load Balancing")
    print("  ✓ Rate Limiting")
    print("  ✓ Health Monitoring")
    print("  ✓ Fault Tolerance")
    print("  ✓ Self-Healing Capabilities")

    print("\n🔧 Test Scenarios:")
    print("  POST /api/resilience/test with {'scenario': 'circuit_breaker'}")
    print("  POST /api/resilience/test with {'scenario': 'retry'}")
    print("  POST /api/resilience/test with {'scenario': 'degradation'}")

    # Run application
    await app.run(host="127.0.0.1", port=8000)

if __name__ == "__main__":
    asyncio.run(main())

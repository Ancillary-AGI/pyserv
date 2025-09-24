"""
Circuit Breaker Pattern for fault tolerance and resilience.
Prevents cascade failures by temporarily stopping calls to failing services.
"""

import asyncio
import time
import logging
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta

class CircuitBreakerState(Enum):
    CLOSED = "CLOSED"      # Normal operation
    OPEN = "OPEN"          # Failing, requests blocked
    HALF_OPEN = "HALF_OPEN" # Testing if service recovered

@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    recovery_timeout: float = 60.0  # seconds
    expected_exception: Tuple[type, ...] = (Exception,)
    success_threshold: int = 3
    timeout: float = 30.0
    name: str = "default"

@dataclass
class CircuitBreakerMetrics:
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rejected_requests: int = 0
    last_failure_time: Optional[float] = None
    consecutive_successes: int = 0
    consecutive_failures: int = 0

class CircuitBreaker:
    """
    Circuit breaker implementation for fault tolerance.
    """

    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.metrics = CircuitBreakerMetrics()
        self.logger = logging.getLogger(f"circuit_breaker.{config.name}")
        self._lock = asyncio.Lock()

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""

        async with self._lock:
            if self.state == CircuitBreakerState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitBreakerState.HALF_OPEN
                    self.logger.info(f"Circuit breaker {self.config.name} transitioning to HALF_OPEN")
                else:
                    self.metrics.rejected_requests += 1
                    raise CircuitBreakerOpenException(
                        f"Circuit breaker {self.config.name} is OPEN"
                    )

            try:
                self.metrics.total_requests += 1
                start_time = time.time()

                # Execute with timeout
                try:
                    result = await asyncio.wait_for(
                        func(*args, **kwargs),
                        timeout=self.config.timeout
                    )
                except asyncio.TimeoutError:
                    raise CircuitBreakerTimeoutException(
                        f"Operation timed out after {self.config.timeout}s"
                    )

                execution_time = time.time() - start_time

                # Success handling
                await self._on_success(execution_time)
                return result

            except self.config.expected_exception as e:
                await self._on_failure(e)
                raise
            except (CircuitBreakerOpenException, CircuitBreakerTimeoutException):
                raise

    async def _on_success(self, execution_time: float):
        """Handle successful execution."""
        self.metrics.successful_requests += 1
        self.metrics.consecutive_failures = 0

        if self.state == CircuitBreakerState.HALF_OPEN:
            self.metrics.consecutive_successes += 1
            if self.metrics.consecutive_successes >= self.config.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.logger.info(f"Circuit breaker {self.config.name} transitioned to CLOSED")
        elif self.state == CircuitBreakerState.CLOSED:
            self.metrics.consecutive_successes += 1

        self.logger.debug(f"Successful execution in {execution_time:.3f}s")

    async def _on_failure(self, exception: Exception):
        """Handle failed execution."""
        self.metrics.failed_requests += 1
        self.metrics.last_failure_time = time.time()
        self.metrics.consecutive_successes = 0

        if self.state == CircuitBreakerState.CLOSED:
            self.metrics.consecutive_failures += 1
            if self.metrics.consecutive_failures >= self.config.failure_threshold:
                self.state = CircuitBreakerState.OPEN
                self.logger.warning(
                    f"Circuit breaker {self.config.name} transitioned to OPEN "
                    f"after {self.metrics.consecutive_failures} failures"
                )
        elif self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
            self.logger.warning(
                f"Circuit breaker {self.config.name} transitioned back to OPEN "
                f"during HALF_OPEN state"
            )

        self.logger.error(f"Failed execution: {exception}")

    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt to reset."""
        if self.metrics.last_failure_time is None:
            return True

        time_since_failure = time.time() - self.metrics.last_failure_time
        return time_since_failure >= self.config.recovery_timeout

    def get_state(self) -> CircuitBreakerState:
        """Get current circuit breaker state."""
        return self.state

    def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics."""
        return {
            "state": self.state.value,
            "total_requests": self.metrics.total_requests,
            "successful_requests": self.metrics.successful_requests,
            "failed_requests": self.metrics.failed_requests,
            "rejected_requests": self.metrics.rejected_requests,
            "success_rate": (
                self.metrics.successful_requests / self.metrics.total_requests
                if self.metrics.total_requests > 0 else 0
            ),
            "consecutive_failures": self.metrics.consecutive_failures,
            "consecutive_successes": self.metrics.consecutive_successes,
            "last_failure_time": self.metrics.last_failure_time,
            "recovery_timeout": self.config.recovery_timeout
        }

class CircuitBreakerOpenException(Exception):
    """Exception raised when circuit breaker is open."""
    pass

class CircuitBreakerTimeoutException(Exception):
    """Exception raised when operation times out."""
    pass

class CircuitBreakerManager:
    """
    Manager for multiple circuit breakers.
    """

    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.logger = logging.getLogger("circuit_breaker_manager")

    def create_circuit_breaker(self, name: str, config: CircuitBreakerConfig) -> CircuitBreaker:
        """Create a new circuit breaker."""
        if name in self.circuit_breakers:
            raise ValueError(f"Circuit breaker {name} already exists")

        circuit_breaker = CircuitBreaker(config)
        self.circuit_breakers[name] = circuit_breaker
        self.logger.info(f"Created circuit breaker: {name}")
        return circuit_breaker

    def get_circuit_breaker(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name."""
        return self.circuit_breakers.get(name)

    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all circuit breakers."""
        return {
            name: cb.get_metrics()
            for name, cb in self.circuit_breakers.items()
        }

    def get_open_circuits(self) -> List[str]:
        """Get names of open circuit breakers."""
        return [
            name for name, cb in self.circuit_breakers.items()
            if cb.get_state() == CircuitBreakerState.OPEN
        ]

    def reset_all(self):
        """Reset all circuit breakers to closed state."""
        for name, cb in self.circuit_breakers.items():
            cb.state = CircuitBreakerState.CLOSED
            cb.metrics = CircuitBreakerMetrics()
            self.logger.info(f"Reset circuit breaker: {name}")

# Global circuit breaker manager
circuit_breaker_manager = CircuitBreakerManager()

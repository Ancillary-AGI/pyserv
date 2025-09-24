"""
Advanced retry mechanisms with exponential backoff and jitter.
"""

import asyncio
import random
import logging
from typing import Dict, List, Optional, Any, Callable, Tuple, Union
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta

class RetryStrategy(Enum):
    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    FIBONACCI = "fibonacci"

class RetryCondition(Enum):
    ALWAYS = "always"
    ON_EXCEPTION = "on_exception"
    ON_SPECIFIC_EXCEPTIONS = "on_specific_exceptions"
    ON_RESULT = "on_result"

@dataclass
class RetryConfig:
    max_attempts: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    jitter: bool = True
    jitter_max: float = 0.1  # 10% jitter
    backoff_multiplier: float = 2.0
    retry_condition: RetryCondition = RetryCondition.ON_EXCEPTION
    retryable_exceptions: Tuple[type, ...] = (Exception,)
    retry_on_result: Optional[Callable[[Any], bool]] = None

class RetryMechanism:
    """
    Advanced retry mechanism with multiple strategies.
    """

    def __init__(self, config: RetryConfig):
        self.config = config
        self.logger = logging.getLogger(f"retry.{config.strategy.value}")

    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry logic."""

        last_exception = None
        attempt = 0

        while attempt < self.config.max_attempts:
            attempt += 1

            try:
                result = await func(*args, **kwargs)

                # Check if we should retry based on result
                if (self.config.retry_condition == RetryCondition.ON_RESULT and
                    self.config.retry_on_result and
                    self.config.retry_on_result(result)):
                    if attempt < self.config.max_attempts:
                        await self._delay(attempt)
                        continue
                    else:
                        return result

                # Success
                if attempt > 1:
                    self.logger.info(f"Operation succeeded on attempt {attempt}")
                return result

            except self.config.retryable_exceptions as e:
                last_exception = e

                # Check if we should retry based on exception
                should_retry = (
                    self.config.retry_condition in [RetryCondition.ALWAYS, RetryCondition.ON_EXCEPTION] or
                    (self.config.retry_condition == RetryCondition.ON_SPECIFIC_EXCEPTIONS and
                     isinstance(e, self.config.retryable_exceptions))
                )

                if should_retry and attempt < self.config.max_attempts:
                    delay = self._calculate_delay(attempt)
                    self.logger.warning(
                        f"Attempt {attempt} failed with {type(e).__name__}: {e}. "
                        f"Retrying in {delay:.2f}s"
                    )
                    await self._delay(attempt)
                    continue
                else:
                    break

            except Exception as e:
                # Non-retryable exception
                if attempt == 1:
                    self.logger.error(f"Non-retryable exception on first attempt: {e}")
                raise

        # All retries exhausted
        if last_exception:
            self.logger.error(
                f"All {self.config.max_attempts} attempts failed. "
                f"Last exception: {last_exception}"
            )
            raise last_exception
        else:
            raise RuntimeError(f"Operation failed after {self.config.max_attempts} attempts")

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt."""

        if self.config.strategy == RetryStrategy.FIXED:
            delay = self.config.base_delay
        elif self.config.strategy == RetryStrategy.LINEAR:
            delay = self.config.base_delay * attempt
        elif self.config.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.config.base_delay * (self.config.backoff_multiplier ** (attempt - 1))
        elif self.config.strategy == RetryStrategy.FIBONACCI:
            delay = self._fibonacci(attempt) * self.config.base_delay
        else:
            delay = self.config.base_delay

        # Apply max delay limit
        delay = min(delay, self.config.max_delay)

        # Add jitter
        if self.config.jitter:
            jitter_range = delay * self.config.jitter_max
            jitter = random.uniform(-jitter_range, jitter_range)
            delay += jitter
            delay = max(0, delay)  # Ensure non-negative

        return delay

    def _fibonacci(self, n: int) -> int:
        """Calculate nth Fibonacci number."""
        if n <= 1:
            return 1
        a, b = 1, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b

    async def _delay(self, attempt: int):
        """Delay execution with calculated backoff."""
        delay = self._calculate_delay(attempt)
        await asyncio.sleep(delay)

class RetryManager:
    """
    Manager for multiple retry mechanisms.
    """

    def __init__(self):
        self.retry_mechanisms: Dict[str, RetryMechanism] = {}
        self.logger = logging.getLogger("retry_manager")

    def create_retry_mechanism(self, name: str, config: RetryConfig) -> RetryMechanism:
        """Create a new retry mechanism."""
        if name in self.retry_mechanisms:
            raise ValueError(f"Retry mechanism {name} already exists")

        retry_mechanism = RetryMechanism(config)
        self.retry_mechanisms[name] = retry_mechanism
        self.logger.info(f"Created retry mechanism: {name}")
        return retry_mechanism

    def get_retry_mechanism(self, name: str) -> Optional[RetryMechanism]:
        """Get retry mechanism by name."""
        return self.retry_mechanisms.get(name)

    async def execute_with_retry(self, name: str, func: Callable, *args, **kwargs) -> Any:
        """Execute function with named retry mechanism."""
        retry_mechanism = self.retry_mechanisms.get(name)
        if not retry_mechanism:
            raise ValueError(f"Retry mechanism {name} not found")

        return await retry_mechanism.execute(func, *args, **kwargs)

# Global retry manager
retry_manager = RetryManager()

# Convenience functions for common retry patterns
def with_exponential_backoff(max_attempts: int = 3, base_delay: float = 1.0):
    """Decorator for exponential backoff retry."""
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        strategy=RetryStrategy.EXPONENTIAL
    )
    retry_mechanism = RetryMechanism(config)

    def decorator(func):
        async def wrapper(*args, **kwargs):
            return await retry_mechanism.execute(func, *args, **kwargs)
        return wrapper
    return decorator

def with_fixed_retry(max_attempts: int = 3, delay: float = 1.0):
    """Decorator for fixed delay retry."""
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=delay,
        strategy=RetryStrategy.FIXED
    )
    retry_mechanism = RetryMechanism(config)

    def decorator(func):
        async def wrapper(*args, **kwargs):
            return await retry_mechanism.execute(func, *args, **kwargs)
        return wrapper
    return decorator
    return decorator

"""
Graceful degradation system for maintaining service availability.
"""

import asyncio
import time
import logging
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

class DegradationStrategy(Enum):
    FAIL_FAST = "fail_fast"
    DEGRADED_RESPONSE = "degraded_response"
    FALLBACK_SERVICE = "fallback_service"
    CACHED_RESPONSE = "cached_response"
    DEFAULT_RESPONSE = "default_response"

@dataclass
class DegradationRule:
    name: str
    condition: Callable[[Any], bool]
    strategy: DegradationStrategy
    fallback_data: Any = None
    cache_timeout: float = 300  # 5 minutes
    priority: int = 0

class GracefulDegradation:
    """
    Graceful degradation system for maintaining availability.
    """

    def __init__(self):
        self.rules: List[DegradationRule] = []
        self.cache: Dict[str, Tuple[Any, float]] = {}
        self.logger = logging.getLogger("graceful_degradation")

    def add_rule(self, rule: DegradationRule):
        """Add a degradation rule."""
        self.rules.append(rule)
        # Sort by priority (higher priority first)
        self.rules.sort(key=lambda r: r.priority, reverse=True)
        self.logger.info(f"Added degradation rule: {rule.name}")

    def remove_rule(self, name: str):
        """Remove a degradation rule."""
        self.rules = [rule for rule in self.rules if rule.name != name]
        self.logger.info(f"Removed degradation rule: {name}")

    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with graceful degradation."""

        try:
            result = await func(*args, **kwargs)
            return result

        except Exception as e:
            self.logger.warning(f"Function failed with {type(e).__name__}: {e}")

            # Try degradation rules in priority order
            for rule in self.rules:
                try:
                    if rule.condition(e):
                        return await self._apply_strategy(rule, func, args, kwargs, e)
                except Exception as strategy_error:
                    self.logger.error(f"Strategy {rule.strategy.value} failed: {strategy_error}")
                    continue

            # No degradation strategy worked, re-raise original exception
            raise e

    async def _apply_strategy(self, rule: DegradationRule, func: Callable,
                            args: Tuple, kwargs: Dict, exception: Exception) -> Any:
        """Apply degradation strategy."""

        if rule.strategy == DegradationStrategy.FAIL_FAST:
            raise exception

        elif rule.strategy == DegradationStrategy.DEGRADED_RESPONSE:
            if rule.fallback_data is not None:
                self.logger.info(f"Using degraded response for {rule.name}")
                return rule.fallback_data

        elif rule.strategy == DegradationStrategy.CACHED_RESPONSE:
            cache_key = f"{func.__name__}_{hash(str(args))}_{hash(str(kwargs))}"
            cached_result = self._get_cached_response(cache_key)

            if cached_result is not None:
                self.logger.info(f"Using cached response for {rule.name}")
                return cached_result

            # Try to get fresh result with timeout
            try:
                result = await asyncio.wait_for(func(*args, **kwargs), timeout=5.0)
                self._cache_response(cache_key, result)
                return result
            except asyncio.TimeoutError:
                if rule.fallback_data is not None:
                    self.logger.info(f"Using fallback data due to timeout for {rule.name}")
                    return rule.fallback_data

        elif rule.strategy == DegradationStrategy.DEFAULT_RESPONSE:
            default_response = self._get_default_response(func, args, kwargs)
            self.logger.info(f"Using default response for {rule.name}")
            return default_response

        # Strategy not implemented or no fallback available
        raise exception

    def _get_cached_response(self, cache_key: str) -> Optional[Any]:
        """Get cached response if still valid."""
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if time.time() - timestamp < 300:  # 5 minutes default
                return cached_data
            else:
                del self.cache[cache_key]
        return None

    def _cache_response(self, cache_key: str, data: Any):
        """Cache response data."""
        self.cache[cache_key] = (data, time.time())

    def _get_default_response(self, func: Callable, args: Tuple, kwargs: Dict) -> Any:
        """Get default response based on function signature."""
        # This is a simplified implementation
        # In practice, you'd analyze the function's return type hints
        return None

    def clear_cache(self):
        """Clear all cached responses."""
        self.cache.clear()
        self.logger.info("Cleared degradation cache")

    def get_stats(self) -> Dict[str, Any]:
        """Get degradation statistics."""
        return {
            "total_rules": len(self.rules),
            "cache_size": len(self.cache),
            "cache_keys": list(self.cache.keys())
        }

# Global graceful degradation instance
graceful_degradation = GracefulDegradation()

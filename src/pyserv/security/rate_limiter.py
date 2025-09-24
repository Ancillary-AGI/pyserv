"""
Rate limiting system to prevent abuse and DDoS attacks.
"""

import time
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

class RateLimitStrategy(Enum):
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"

@dataclass
class RateLimitRule:
    name: str
    requests_per_period: int
    period_seconds: int
    strategy: RateLimitStrategy = RateLimitStrategy.FIXED_WINDOW
    burst_limit: Optional[int] = None

@dataclass
class RequestRecord:
    count: int
    window_start: float
    tokens: float = 0.0
    last_refill: float = 0.0

class RateLimiter:
    """
    Advanced rate limiting system with multiple strategies.
    """

    def __init__(self):
        self.rules: Dict[str, RateLimitRule] = {}
        self.records: Dict[str, Dict[str, RequestRecord]] = {}  # rule_name -> identifier -> record
        self.logger = logging.getLogger(__name__)

    def add_rule(self, rule: RateLimitRule):
        """Add a rate limiting rule."""
        self.rules[rule.name] = rule
        self.logger.info(f"Added rate limit rule: {rule.name}")

    def remove_rule(self, rule_name: str):
        """Remove a rate limiting rule."""
        if rule_name in self.rules:
            del self.rules[rule_name]
            self.logger.info(f"Removed rate limit rule: {rule_name}")

    async def check_rate_limit(self, rule_name: str, identifier: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if request is within rate limits.

        Returns:
            (allowed: bool, info: dict)
        """
        rule = self.rules.get(rule_name)
        if not rule:
            return True, {"error": "Rule not found"}

        if rule_name not in self.records:
            self.records[rule_name] = {}

        if identifier not in self.records[rule_name]:
            self.records[rule_name][identifier] = self._create_record(rule)

        record = self.records[rule_name][identifier]

        if rule.strategy == RateLimitStrategy.FIXED_WINDOW:
            return self._check_fixed_window(rule, record, identifier)
        elif rule.strategy == RateLimitStrategy.SLIDING_WINDOW:
            return self._check_sliding_window(rule, record, identifier)
        elif rule.strategy == RateLimitStrategy.TOKEN_BUCKET:
            return self._check_token_bucket(rule, record, identifier)
        elif rule.strategy == RateLimitStrategy.LEAKY_BUCKET:
            return self._check_leaky_bucket(rule, record, identifier)

        return True, {"error": "Unknown strategy"}

    def _create_record(self, rule: RateLimitRule) -> RequestRecord:
        """Create a new request record."""
        current_time = time.time()
        return RequestRecord(
            count=0,
            window_start=current_time,
            tokens=rule.requests_per_period,
            last_refill=current_time
        )

    def _check_fixed_window(self, rule: RateLimitRule, record: RequestRecord, identifier: str) -> Tuple[bool, Dict[str, Any]]:
        """Check fixed window rate limit."""
        current_time = time.time()

        # Check if we need to reset the window
        if current_time - record.window_start >= rule.period_seconds:
            record.count = 0
            record.window_start = current_time

        # Check burst limit
        if rule.burst_limit and record.count >= rule.burst_limit:
            return False, {
                "error": "Burst limit exceeded",
                "current_count": record.count,
                "burst_limit": rule.burst_limit,
                "reset_time": record.window_start + rule.period_seconds
            }

        # Check rate limit
        if record.count >= rule.requests_per_period:
            return False, {
                "error": "Rate limit exceeded",
                "current_count": record.count,
                "limit": rule.requests_per_period,
                "reset_time": record.window_start + rule.period_seconds
            }

        record.count += 1
        return True, {
            "remaining": rule.requests_per_period - record.count,
            "reset_time": record.window_start + rule.period_seconds,
            "current_count": record.count
        }

    def _check_sliding_window(self, rule: RateLimitRule, record: RequestRecord, identifier: str) -> Tuple[bool, Dict[str, Any]]:
        """Check sliding window rate limit."""
        current_time = time.time()

        # This is a simplified sliding window - in production you'd use Redis or similar
        # to track individual request timestamps
        if current_time - record.window_start >= rule.period_seconds:
            record.count = 0
            record.window_start = current_time

        if record.count >= rule.requests_per_period:
            return False, {
                "error": "Rate limit exceeded",
                "current_count": record.count,
                "limit": rule.requests_per_period,
                "reset_time": record.window_start + rule.period_seconds
            }

        record.count += 1
        return True, {
            "remaining": rule.requests_per_period - record.count,
            "reset_time": record.window_start + rule.period_seconds,
            "current_count": record.count
        }

    def _check_token_bucket(self, rule: RateLimitRule, record: RequestRecord, identifier: str) -> Tuple[bool, Dict[str, Any]]:
        """Check token bucket rate limit."""
        current_time = time.time()
        time_passed = current_time - record.last_refill

        # Refill tokens
        refill_rate = rule.requests_per_period / rule.period_seconds
        tokens_to_add = time_passed * refill_rate
        record.tokens = min(rule.requests_per_period, record.tokens + tokens_to_add)
        record.last_refill = current_time

        if record.tokens >= 1:
            record.tokens -= 1
            return True, {
                "remaining_tokens": record.tokens,
                "refill_rate": refill_rate
            }

        return False, {
            "error": "Rate limit exceeded",
            "remaining_tokens": record.tokens,
            "refill_rate": refill_rate
        }

    def _check_leaky_bucket(self, rule: RateLimitRule, record: RequestRecord, identifier: str) -> Tuple[bool, Dict[str, Any]]:
        """Check leaky bucket rate limit."""
        current_time = time.time()
        time_passed = current_time - record.last_refill

        # Leak tokens (process requests)
        leak_rate = rule.requests_per_period / rule.period_seconds
        leaked_tokens = time_passed * leak_rate
        record.tokens = max(0, record.tokens - leaked_tokens)
        record.last_refill = current_time

        # Check if bucket is full
        if record.tokens >= rule.requests_per_period:
            return False, {
                "error": "Rate limit exceeded",
                "current_tokens": record.tokens,
                "bucket_size": rule.requests_per_period
            }

        record.tokens += 1
        return True, {
            "current_tokens": record.tokens,
            "bucket_size": rule.requests_per_period,
            "leak_rate": leak_rate
        }

    def get_stats(self, rule_name: str) -> Dict[str, Any]:
        """Get statistics for a rate limit rule."""
        if rule_name not in self.rules:
            return {"error": "Rule not found"}

        rule = self.rules[rule_name]
        records = self.records.get(rule_name, {})

        return {
            "rule_name": rule_name,
            "requests_per_period": rule.requests_per_period,
            "period_seconds": rule.period_seconds,
            "strategy": rule.strategy.value,
            "total_identifiers": len(records),
            "active_identifiers": sum(1 for r in records.values() if r.count > 0)
        }

    def cleanup_old_records(self, max_age_seconds: int = 3600):
        """Clean up old records to prevent memory leaks."""
        current_time = time.time()
        cutoff_time = current_time - max_age_seconds

        for rule_name in list(self.records.keys()):
            rule_records = self.records[rule_name]
            to_remove = []

            for identifier, record in rule_records.items():
                if record.window_start < cutoff_time and record.count == 0:
                    to_remove.append(identifier)

            for identifier in to_remove:
                del rule_records[identifier]

            if not rule_records:
                del self.records[rule_name]

    async def cleanup_task(self, interval_seconds: int = 300):
        """Run periodic cleanup task."""
        while True:
            try:
                self.cleanup_old_records()
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(interval_seconds)

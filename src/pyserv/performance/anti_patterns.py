"""
Performance anti-pattern detector for PyServ applications.
Identifies common performance issues and suggests improvements.
"""

import asyncio
import inspect
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime

@dataclass
class AntiPattern:
    """Performance anti-pattern definition."""
    name: str
    description: str
    severity: str  # "low", "medium", "high", "critical"
    category: str  # "memory", "cpu", "io", "network", "cache"
    detection_function: Callable
    suggestion: str

class PerformanceAntiPatternDetector:
    """
    Detects performance anti-patterns in PyServ applications.
    """

    def __init__(self):
        self.anti_patterns: List[AntiPattern] = []
        self.logger = logging.getLogger("anti_pattern_detector")
        self._setup_anti_patterns()

    def _setup_anti_patterns(self):
        """Setup known performance anti-patterns."""

        # Anti-pattern 1: N+1 Query Problem
        def detect_n_plus_1(code_metrics):
            # Look for multiple database queries in loops
            return code_metrics.get("db_queries_in_loop", 0) > 0

        n_plus_1_pattern = AntiPattern(
            name="N+1 Query Problem",
            description="Multiple database queries executed inside loops",
            severity="high",
            category="io",
            detection_function=detect_n_plus_1,
            suggestion="Use eager loading or batch queries to reduce database calls"
        )
        self.anti_patterns.append(n_plus_1_pattern)

        # Anti-pattern 2: Memory Leak
        def detect_memory_leak(metrics):
            # Check for continuously growing memory usage
            return metrics.get("memory_growth_rate", 0) > 10  # MB per minute

        memory_leak_pattern = AntiPattern(
            name="Memory Leak",
            description="Continuously growing memory usage",
            severity="critical",
            category="memory",
            detection_function=detect_memory_leak,
            suggestion="Check for objects not being garbage collected"
        )
        self.anti_patterns.append(memory_leak_pattern)

        # Anti-pattern 3: Synchronous I/O in Async Code
        def detect_sync_io(code_analysis):
            # Look for blocking I/O operations
            return code_analysis.get("sync_io_calls", 0) > 0

        sync_io_pattern = AntiPattern(
            name="Synchronous I/O in Async Code",
            description="Blocking I/O operations in async functions",
            severity="high",
            category="io",
            detection_function=detect_sync_io,
            suggestion="Use async I/O operations or run in thread pool"
        )
        self.anti_patterns.append(sync_io_pattern)

        # Anti-pattern 4: Inefficient Data Structures
        def detect_inefficient_data_structures(code_analysis):
            # Look for O(n) operations in loops
            return code_analysis.get("nested_loops", 0) > 2

        inefficient_ds_pattern = AntiPattern(
            name="Inefficient Data Structures",
            description="Using inefficient data structures or algorithms",
            severity="medium",
            category="cpu",
            detection_function=detect_inefficient_data_structures,
            suggestion="Use appropriate data structures (dicts, sets) for lookups"
        )
        self.anti_patterns.append(inefficient_ds_pattern)

        # Anti-pattern 5: Cache Miss Storm
        def detect_cache_miss_storm(metrics):
            # Look for low cache hit rates
            return metrics.get("cache_hit_rate", 1.0) < 0.5

        cache_miss_pattern = AntiPattern(
            name="Cache Miss Storm",
            description="Very low cache hit rate causing performance issues",
            severity="medium",
            category="cache",
            detection_function=detect_cache_miss_storm,
            suggestion="Optimize cache key strategy or increase cache size"
        )
        self.anti_patterns.append(cache_miss_pattern)

    async def analyze_code(self, code_object) -> List[Dict[str, Any]]:
        """Analyze code for performance anti-patterns."""
        issues = []

        try:
            # Get source code
            source = inspect.getsource(code_object)

            # Analyze for common patterns
            code_metrics = self._analyze_code_metrics(source)

            # Check each anti-pattern
            for pattern in self.anti_patterns:
                try:
                    if pattern.detection_function(code_metrics):
                        issues.append({
                            "pattern": pattern.name,
                            "description": pattern.description,
                            "severity": pattern.severity,
                            "category": pattern.category,
                            "suggestion": pattern.suggestion,
                            "location": getattr(code_object, '__name__', 'unknown'),
                            "timestamp": datetime.now().isoformat()
                        })
                except Exception as e:
                    self.logger.warning(f"Error detecting pattern {pattern.name}: {e}")

        except Exception as e:
            self.logger.error(f"Error analyzing code: {e}")

        return issues

    def _analyze_code_metrics(self, source_code: str) -> Dict[str, Any]:
        """Analyze source code for performance metrics."""
        metrics = {
            "db_queries_in_loop": 0,
            "memory_growth_rate": 0,
            "sync_io_calls": 0,
            "nested_loops": 0,
            "cache_hit_rate": 1.0
        }

        lines = source_code.split('\n')

        # Simple analysis for common patterns
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()

            # Check for database queries in loops
            if any(keyword in line_lower for keyword in ['.query', '.find', 'select', 'insert', 'update', 'delete']):
                # Look for loop context
                for j in range(max(0, i-5), min(len(lines), i+5)):
                    if any(loop in lines[j].lower() for loop in ['for', 'while']):
                        metrics["db_queries_in_loop"] += 1
                        break

            # Check for synchronous I/O
            if any(sync_io in line_lower for sync_io in ['.read(', '.write(', 'open(', 'requests.', 'urllib']):
                metrics["sync_io_calls"] += 1

            # Count nested loops (simplified)
            if 'for' in line_lower or 'while' in line_lower:
                # Check indentation level
                indent_level = len(line) - len(line.lstrip())
                if indent_level > 4:  # Nested loop
                    metrics["nested_loops"] += 1

        return metrics

    async def analyze_performance_metrics(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze performance metrics for anti-patterns."""
        issues = []

        for pattern in self.anti_patterns:
            try:
                if pattern.detection_function(metrics):
                    issues.append({
                        "pattern": pattern.name,
                        "description": pattern.description,
                        "severity": pattern.severity,
                        "category": pattern.category,
                        "suggestion": pattern.suggestion,
                        "metrics": metrics,
                        "timestamp": datetime.now().isoformat()
                    })
            except Exception as e:
                self.logger.warning(f"Error detecting pattern {pattern.name}: {e}")

        return issues

    def get_anti_patterns_by_category(self, category: str) -> List[AntiPattern]:
        """Get anti-patterns by category."""
        return [pattern for pattern in self.anti_patterns if pattern.category == category]

    def get_anti_patterns_by_severity(self, severity: str) -> List[AntiPattern]:
        """Get anti-patterns by severity level."""
        return [pattern for pattern in self.anti_patterns if pattern.severity == severity]

    def add_anti_pattern(self, pattern: AntiPattern):
        """Add a custom anti-pattern."""
        self.anti_patterns.append(pattern)
        self.logger.info(f"Added anti-pattern: {pattern.name}")

    def get_all_anti_patterns(self) -> List[Dict[str, Any]]:
        """Get all anti-patterns with metadata."""
        return [
            {
                "name": pattern.name,
                "description": pattern.description,
                "severity": pattern.severity,
                "category": pattern.category,
                "suggestion": pattern.suggestion
            }
            for pattern in self.anti_patterns
        ]

# Global anti-pattern detector
anti_pattern_detector = PerformanceAntiPatternDetector()

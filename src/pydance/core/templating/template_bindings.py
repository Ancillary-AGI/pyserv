"""
PyDance Quantum Template Engine Python Bindings
Ultra-fast template rendering with C++ core and GPU acceleration
"""

import ctypes
import os
import sys
import asyncio
import time
import json
import hashlib
import threading
import concurrent.futures
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from collections import deque, defaultdict
import weakref
import logging

# Load the C++ template core
try:
    if sys.platform == "win32":
        _template_core = ctypes.CDLL("./pydance_template_core.dll")
    else:
        _template_core = ctypes.CDLL("./pydance_template_core.so")
except OSError:
    _template_core = None
    logging.warning("C++ template core not available, using Python fallback")

# Configure C function signatures
if _template_core:
    _template_core.create_template_engine.argtypes = [ctypes.c_size_t]
    _template_core.create_template_engine.restype = ctypes.c_void_p

    _template_core.destroy_template_engine.argtypes = [ctypes.c_void_p]
    _template_core.destroy_template_engine.restype = None

    _template_core.render_template.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
    _template_core.render_template.restype = ctypes.c_char_p

    _template_core.clear_template_cache.argtypes = [ctypes.c_void_p]
    _template_core.clear_template_cache.restype = None


class TemplateEngineMode(Enum):
    """Template engine operation modes"""
    FAST = "fast"          # Pure C++ performance
    GPU = "gpu"           # GPU-accelerated batch processing
    HYBRID = "hybrid"     # Adaptive CPU/GPU based on workload
    COMPATIBLE = "compatible"  # Maximum compatibility with existing templates


@dataclass
class TemplateConfig:
    """Template engine configuration"""
    mode: TemplateEngineMode = TemplateEngineMode.HYBRID
    cache_enabled: bool = True
    auto_reload: bool = False
    gpu_batch_threshold: int = 10
    max_cache_size: int = 1000
    thread_pool_size: int = 4
    enable_filters: bool = True
    enable_macros: bool = True
    enable_inheritance: bool = True
    enable_i18n: bool = True
    debug_mode: bool = False


class Context:
    """Template context with thread-safe operations"""

    def __init__(self, data: Optional[Dict[str, Any]] = None):
        self._data: Dict[str, Any] = data or {}
        self._lock = threading.RLock()
        self._parent: Optional['Context'] = None

    def __getitem__(self, key: str) -> Any:
        with self._lock:
            if key in self._data:
                return self._data[key]
            if self._parent:
                return self._parent[key]
            raise KeyError(f"Key '{key}' not found in context")

    def __setitem__(self, key: str, value: Any) -> None:
        with self._lock:
            self._data[key] = value

    def __contains__(self, key: str) -> bool:
        with self._lock:
            return key in self._data or (self._parent and key in self._parent)

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def update(self, other: Union[Dict[str, Any], 'Context']) -> None:
        with self._lock:
            if isinstance(other, Context):
                self._data.update(other._data)
            else:
                self._data.update(other)

    def push(self) -> 'Context':
        """Create a child context"""
        child = Context()
        child._parent = self
        return child

    def to_json(self) -> str:
        """Convert context to JSON string"""
        with self._lock:
            return json.dumps(self._data, default=str)

    @classmethod
    def from_json(cls, json_str: str) -> 'Context':
        """Create context from JSON string"""
        data = json.loads(json_str)
        return cls(data)


class TemplateLoader:
    """Advanced template loader with multiple sources"""

    def __init__(self, search_paths: List[Union[str, Path]]):
        self.search_paths = [Path(p) for p in search_paths]
        self._cache: Dict[str, Tuple[str, float]] = {}
        self._lock = threading.RLock()

    def load(self, template_name: str) -> str:
        """Load template with caching and search path resolution"""
        cache_key = template_name

        with self._lock:
            # Check cache
            if cache_key in self._cache:
                content, mtime = self._cache[cache_key]
                # Check if file has been modified
                template_path = self._find_template_path(template_name)
                if template_path and template_path.stat().st_mtime <= mtime:
                    return content

        # Load from file
        template_path = self._find_template_path(template_name)
        if not template_path:
            raise FileNotFoundError(f"Template '{template_name}' not found")

        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Cache the content
        mtime = template_path.stat().st_mtime
        with self._lock:
            self._cache[cache_key] = (content, mtime)

        return content

    def _find_template_path(self, template_name: str) -> Optional[Path]:
        """Find template in search paths"""
        for search_path in self.search_paths:
            template_path = search_path / template_name
            if template_path.exists() and template_path.is_file():
                return template_path
        return None

    def clear_cache(self) -> None:
        """Clear template cache"""
        with self._lock:
            self._cache.clear()


class FilterRegistry:
    """Registry for template filters"""

    def __init__(self):
        self._filters: Dict[str, Callable] = {}
        self._lock = threading.RLock()
        self._register_builtin_filters()

    def register(self, name: str, filter_func: Callable) -> None:
        """Register a custom filter"""
        with self._lock:
            self._filters[name] = filter_func

    def get(self, name: str) -> Optional[Callable]:
        """Get a filter by name"""
        with self._lock:
            return self._filters.get(name)

    def apply(self, value: Any, filter_name: str, *args) -> Any:
        """Apply a filter to a value"""
        filter_func = self.get(filter_name)
        if not filter_func:
            raise ValueError(f"Filter '{filter_name}' not registered")
        return filter_func(value, *args)

    def _register_builtin_filters(self) -> None:
        """Register built-in filters"""
        self.register('upper', lambda x: str(x).upper())
        self.register('lower', lambda x: str(x).lower())
        self.register('capitalize', lambda x: str(x).capitalize())
        self.register('title', lambda x: str(x).title())
        self.register('length', lambda x: len(x) if hasattr(x, '__len__') else 0)
        self.register('default', lambda x, default='': x if x is not None else default)
        self.register('trim', lambda x: str(x).strip())
        self.register('escape', self._escape_html)
        self.register('safe', lambda x: x)  # Mark as safe
        self.register('join', lambda x, sep=', ': sep.join(str(i) for i in x) if hasattr(x, '__iter__') else str(x))
        self.register('first', lambda x: x[0] if hasattr(x, '__getitem__') and len(x) > 0 else None)
        self.register('last', lambda x: x[-1] if hasattr(x, '__getitem__') and len(x) > 0 else None)
        self.register('reverse', lambda x: list(reversed(x)) if hasattr(x, '__iter__') else x)
        self.register('sort', lambda x: sorted(x) if hasattr(x, '__iter__') else x)
        self.register('unique', lambda x: list(dict.fromkeys(x)) if hasattr(x, '__iter__') else x)
        self.register('slice', lambda x, start=0, end=None: x[start:end] if hasattr(x, '__getitem__') else x)

    def _escape_html(self, value: str) -> str:
        """Escape HTML special characters"""
        if not isinstance(value, str):
            return str(value)

        escape_map = {
            '&': '&',
            '<': '<',
            '>': '>',
            '"': '"',
            "'": '&#x27;',
            '/': '&#x2F;'
        }

        for char, escape in escape_map.items():
            value = value.replace(char, escape)

        return value


class MacroRegistry:
    """Registry for template macros"""

    def __init__(self):
        self._macros: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

    def register(self, name: str, macro_def: Dict[str, Any]) -> None:
        """Register a macro"""
        with self._lock:
            self._macros[name] = macro_def

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a macro by name"""
        with self._lock:
            return self._macros.get(name)

    def call(self, name: str, context: Context, *args, **kwargs) -> str:
        """Call a macro"""
        macro = self.get(name)
        if not macro:
            raise ValueError(f"Macro '{name}' not registered")

        # Create macro context
        macro_context = Context()
        macro_context._parent = context

        # Bind arguments
        params = macro.get('params', [])
        for i, param in enumerate(params):
            if i < len(args):
                macro_context[param] = args[i]

        macro_context.update(kwargs)

        # Render macro content
        content = macro['content']
        return self._render_macro_content(content, macro_context)

    def _render_macro_content(self, content: str, context: Context) -> str:
        """Simple macro content rendering"""
        # This would use the template engine to render macro content
        # For now, just return the content (would be enhanced)
        return content


class QuantumTemplateEngine:
    """Ultra-fast template engine with C++ core and GPU acceleration"""

    def __init__(self, template_dirs: List[Union[str, Path]], config: Optional[TemplateConfig] = None):
        self.config = config or TemplateConfig()
        self.template_loader = TemplateLoader(template_dirs)
        self.filter_registry = FilterRegistry()
        self.macro_registry = MacroRegistry()

        # C++ engine
        self._cpp_engine = None
        if _template_core:
            self._cpp_engine = _template_core.create_template_engine(self.config.thread_pool_size)

        # Thread pool for async operations
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.config.thread_pool_size)

        # Template cache
        self._render_cache: Dict[str, Tuple[str, float]] = {}
        self._cache_lock = threading.RLock()

        # Performance metrics
        self._metrics = {
            'renders': 0,
            'cache_hits': 0,
            'avg_render_time': 0.0,
            'errors': 0
        }

    def __del__(self):
        if _template_core and self._cpp_engine:
            _template_core.destroy_template_engine(self._cpp_engine)

    async def render_async(self, template_name: str, context: Union[Dict[str, Any], Context]) -> str:
        """Asynchronously render a template"""
        if isinstance(context, dict):
            context = Context(context)

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, self.render, template_name, context)

    def render(self, template_name: str, context: Union[Dict[str, Any], Context]) -> str:
        """Render a template"""
        start_time = time.time()

        try:
            if isinstance(context, dict):
                context = Context(context)

            # Check cache
            cache_key = self._get_cache_key(template_name, context)
            if self.config.cache_enabled:
                cached_result = self._get_cached_result(cache_key)
                if cached_result:
                    self._metrics['cache_hits'] += 1
                    return cached_result

            # Use C++ engine if available
            if self._cpp_engine and self.config.mode in [TemplateEngineMode.FAST, TemplateEngineMode.HYBRID]:
                result = self._render_with_cpp(template_name, context)
            else:
                result = self._render_with_python(template_name, context)

            # Cache result
            if self.config.cache_enabled:
                self._cache_result(cache_key, result)

            render_time = time.time() - start_time
            self._update_metrics(render_time)

            return result

        except Exception as e:
            self._metrics['errors'] += 1
            if self.config.debug_mode:
                logging.error(f"Template rendering error: {e}")
            raise

    async def render_batch_async(self, templates: List[str], contexts: List[Union[Dict[str, Any], Context]]) -> List[str]:
        """Batch render multiple templates with GPU acceleration"""
        if len(templates) >= self.config.gpu_batch_threshold and self.config.mode in [TemplateEngineMode.GPU, TemplateEngineMode.HYBRID]:
            return await self._render_batch_gpu(templates, contexts)
        else:
            # Render individually
            tasks = [self.render_async(template, context) for template, context in zip(templates, contexts)]
            return await asyncio.gather(*tasks)

    def render_string(self, template_string: str, context: Union[Dict[str, Any], Context]) -> str:
        """Render a template string"""
        if isinstance(context, dict):
            context = Context(context)

        # For string rendering, we use Python implementation
        return self._render_string_python(template_string, context)

    def add_filter(self, name: str, filter_func: Callable) -> None:
        """Add a custom filter"""
        self.filter_registry.register(name, filter_func)

    def add_macro(self, name: str, macro_content: str, params: List[str] = None) -> None:
        """Add a custom macro"""
        macro_def = {
            'content': macro_content,
            'params': params or []
        }
        self.macro_registry.register(name, macro_def)

    def clear_cache(self) -> None:
        """Clear all caches"""
        with self._cache_lock:
            self._render_cache.clear()
        self.template_loader.clear_cache()

        if _template_core and self._cpp_engine:
            _template_core.clear_template_cache(self._cpp_engine)

    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        return self._metrics.copy()

    def _render_with_cpp(self, template_name: str, context: Context) -> str:
        """Render using C++ core"""
        if not self._cpp_engine:
            raise RuntimeError("C++ engine not available")

        template_dir = str(self.template_loader.search_paths[0])
        context_json = context.to_json()

        result_ptr = _template_core.render_template(
            self._cpp_engine,
            template_name.encode('utf-8'),
            template_dir.encode('utf-8'),
            context_json.encode('utf-8')
        )

        return ctypes.string_at(result_ptr).decode('utf-8')

    def _render_with_python(self, template_name: str, context: Context) -> str:
        """Fallback Python rendering"""
        template_content = self.template_loader.load(template_name)
        return self._render_string_python(template_content, context)

    def _render_string_python(self, template_string: str, context: Context) -> str:
        """Python implementation of string rendering"""
        # Simple variable replacement for now
        # This would be enhanced to match Lean engine features
        result = template_string

        # Replace variables
        import re
        var_pattern = re.compile(r'\{\{([^}]+)\}\}')

        def replace_var(match):
            var_name = match.group(1).strip()
            try:
                value = context[var_name]
                return str(value)
            except KeyError:
                return f'{{{{{var_name}}}}}'

        result = var_pattern.sub(replace_var, result)
        return result

    async def _render_batch_gpu(self, templates: List[str], contexts: List[Union[Dict[str, Any], Context]]) -> List[str]:
        """GPU-accelerated batch rendering"""
        # This would implement GPU batch processing
        # For now, fall back to individual rendering
        results = []
        for template, ctx in zip(templates, contexts):
            results.append(await self.render_async(template, ctx))
        return results

    def _get_cache_key(self, template_name: str, context: Context) -> str:
        """Generate cache key"""
        context_hash = hashlib.md5(context.to_json().encode()).hexdigest()
        return f"{template_name}:{context_hash}"

    def _get_cached_result(self, cache_key: str) -> Optional[str]:
        """Get cached result"""
        with self._cache_lock:
            if cache_key in self._render_cache:
                result, timestamp = self._render_cache[cache_key]
                # Check if template has been modified
                if not self.config.auto_reload:
                    return result

                # For auto-reload, we'd check file modification time
                # Simplified for now
                return result
        return None

    def _cache_result(self, cache_key: str, result: str) -> None:
        """Cache rendering result"""
        with self._cache_lock:
            if len(self._render_cache) >= self.config.max_cache_size:
                # Simple LRU eviction - remove oldest
                oldest_key = min(self._render_cache.keys(),
                               key=lambda k: self._render_cache[k][1])
                del self._render_cache[oldest_key]

            self._render_cache[cache_key] = (result, time.time())

    def _update_metrics(self, render_time: float) -> None:
        """Update performance metrics"""
        self._metrics['renders'] += 1
        # Exponential moving average for render time
        alpha = 0.1
        self._metrics['avg_render_time'] = (
            alpha * render_time +
            (1 - alpha) * self._metrics['avg_render_time']
        )


# Global template engine instance
_template_engine: Optional[QuantumTemplateEngine] = None

def get_template_engine(template_dirs: List[Union[str, Path]] = None,
                       config: Optional[TemplateConfig] = None) -> QuantumTemplateEngine:
    """Get global template engine instance"""
    global _template_engine
    if _template_engine is None:
        if template_dirs is None:
            template_dirs = ['templates']
        _template_engine = QuantumTemplateEngine(template_dirs, config)
    return _template_engine

def render_template(template_name: str, context: Union[Dict[str, Any], Context],
                   template_dirs: List[Union[str, Path]] = None) -> str:
    """Convenience function for rendering templates"""
    engine = get_template_engine(template_dirs)
    return engine.render(template_name, context)

async def render_template_async(template_name: str, context: Union[Dict[str, Any], Context],
                               template_dirs: List[Union[str, Path]] = None) -> str:
    """Async convenience function for rendering templates"""
    engine = get_template_engine(template_dirs)
    return await engine.render_async(template_name, context)

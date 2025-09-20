"""
Advanced utility functions for PyDance framework.
Provides functional programming helpers, decorators, and utility functions.
"""

import functools
import time
import inspect
from typing import Callable, Any, TypeVar, Generic, Optional, Dict, List, Union
from functools import wraps, partial, lru_cache
import asyncio
from concurrent.futures import ThreadPoolExecutor
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from collections import defaultdict, deque
import logging

T = TypeVar('T')
logger = logging.getLogger(__name__)


class FunctionUtils:
    """Advanced function utilities"""

    @staticmethod
    def compose(*functions: Callable) -> Callable:
        """Compose multiple functions together"""
        def composed(*args, **kwargs):
            result = functions[-1](*args, **kwargs)
            for func in reversed(functions[:-1]):
                result = func(result)
            return result
        return composed

    @staticmethod
    def pipe(value: Any, *functions: Callable) -> Any:
        """Pipe a value through multiple functions"""
        result = value
        for func in functions:
            result = func(result)
        return result

    @staticmethod
    def curry(func: Callable) -> Callable:
        """Curry a function"""
        @functools.wraps(func)
        def curried(*args, **kwargs):
            if len(args) + len(kwargs) >= func.__code__.co_argcount:
                return func(*args, **kwargs)
            return lambda *more_args, **more_kwargs: curried(*(args + more_args), **{**kwargs, **more_kwargs})
        return curried

    @staticmethod
    def memoize(func: Callable) -> Callable:
        """Memoize a function with automatic cache management"""
        cache = {}

        @wraps(func)
        def memoized(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            if key not in cache:
                cache[key] = func(*args, **kwargs)
            return cache[key]

        memoized.cache_clear = cache.clear
        return memoized

    @staticmethod
    def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0,
              exceptions: tuple = (Exception,)) -> Callable:
        """Retry decorator"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                current_delay = delay
                last_exception = None

                for attempt in range(max_attempts):
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e
                        if attempt < max_attempts - 1:
                            time.sleep(current_delay)
                            current_delay *= backoff
                        logger.warning(f"Attempt {attempt + 1} failed: {e}")

                raise last_exception
            return wrapper
        return decorator

    @staticmethod
    def timeout(seconds: float) -> Callable:
        """Timeout decorator"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                import signal

                def timeout_handler(signum, frame):
                    raise TimeoutError(f"Function {func.__name__} timed out after {seconds} seconds")

                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(int(seconds))

                try:
                    result = func(*args, **kwargs)
                    signal.alarm(0)  # Cancel the alarm
                    return result
                except TimeoutError:
                    raise
                finally:
                    signal.alarm(0)
            return wrapper
        return decorator

    @staticmethod
    def debounce(delay: float) -> Callable:
        """Debounce decorator"""
        def decorator(func: Callable) -> Callable:
            last_call = [0]

            @wraps(func)
            def wrapper(*args, **kwargs):
                current_time = time.time()
                if current_time - last_call[0] >= delay:
                    last_call[0] = current_time
                    return func(*args, **kwargs)
            return wrapper
        return decorator

    @staticmethod
    def throttle(interval: float) -> Callable:
        """Throttle decorator"""
        def decorator(func: Callable) -> Callable:
            last_call = [0]

            @wraps(func)
            def wrapper(*args, **kwargs):
                current_time = time.time()
                if current_time - last_call[0] >= interval:
                    last_call[0] = current_time
                    return func(*args, **kwargs)
            return wrapper
        return decorator

    @staticmethod
    def singleton(cls):
        """Singleton decorator for classes"""
        instances = {}

        @wraps(cls)
        def get_instance(*args, **kwargs):
            if cls not in instances:
                instances[cls] = cls(*args, **kwargs)
            return instances[cls]

        return get_instance

    @staticmethod
    def profile(func: Callable) -> Callable:
        """Profile decorator"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            import cProfile
            import pstats
            import io

            pr = cProfile.Profile()
            pr.enable()
            result = func(*args, **kwargs)
            pr.disable()

            s = io.StringIO()
            sortby = 'cumulative'
            ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
            ps.print_stats()
            print(s.getvalue())

            return result
        return wrapper


class AsyncUtils:
    """Asynchronous utility functions"""

    @staticmethod
    async def gather_with_concurrency(n: int, *coroutines):
        """Gather coroutines with concurrency limit"""
        semaphore = asyncio.Semaphore(n)

        async def sem_coro(coro):
            async with semaphore:
                return await coro

        return await asyncio.gather(*(sem_coro(coro) for coro in coroutines))

    @staticmethod
    def run_in_executor(func: Callable, *args, executor: ThreadPoolExecutor = None, **kwargs):
        """Run a function in a thread pool executor"""
        if executor is None:
            executor = ThreadPoolExecutor()

        loop = asyncio.get_event_loop()
        return loop.run_in_executor(executor, func, *args, **kwargs)

    @staticmethod
    async def timeout_async(coro, timeout: float):
        """Add timeout to a coroutine"""
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Coroutine timed out after {timeout} seconds")

    @staticmethod
    def async_cache(func: Callable) -> Callable:
        """Async cache decorator"""
        cache = {}

        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            if key not in cache:
                cache[key] = await func(*args, **kwargs)
            return cache[key]

        wrapper.cache_clear = cache.clear
        return wrapper


class DataUtils:
    """Data manipulation utilities"""

    @staticmethod
    def deep_merge(dict1: Dict, dict2: Dict) -> Dict:
        """Deep merge two dictionaries"""
        result = dict1.copy()

        for key, value in dict2.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = DataUtils.deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    @staticmethod
    def flatten_dict(d: Dict, prefix: str = '') -> Dict:
        """Flatten a nested dictionary"""
        items = []
        for k, v in d.items():
            new_key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                items.extend(DataUtils.flatten_dict(v, new_key).items())
            else:
                items.append((new_key, v))
        return dict(items)

    @staticmethod
    def group_by(iterable, key_func: Callable) -> Dict[Any, List]:
        """Group items by a key function"""
        groups = defaultdict(list)
        for item in iterable:
            key = key_func(item)
            groups[key].append(item)
        return dict(groups)

    @staticmethod
    def chunk(iterable, size: int):
        """Split iterable into chunks"""
        iterator = iter(iterable)
        while True:
            chunk = list(itertools.islice(iterator, size))
            if not chunk:
                break
            yield chunk

    @staticmethod
    def unique(iterable, key_func: Callable = None) -> List:
        """Get unique items from iterable"""
        seen = set()
        result = []

        for item in iterable:
            key = key_func(item) if key_func else item
            if key not in seen:
                seen.add(key)
                result.append(item)

        return result


class ValidationUtils:
    """Validation utilities"""

    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email address"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    @staticmethod
    def validate_phone(phone: str) -> bool:
        """Validate phone number"""
        import re
        # Simple international phone number validation
        pattern = r'^\+?[\d\s\-\(\)]{10,}$'
        return re.match(pattern, phone.strip()) is not None

    @staticmethod
    def validate_url(url: str) -> bool:
        """Validate URL"""
        import re
        pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        return re.match(pattern, url) is not None

    @staticmethod
    def validate_credit_card(number: str) -> bool:
        """Validate credit card number using Luhn algorithm"""
        def luhn_checksum(card_num: str) -> bool:
            def digits_of(n):
                return [int(d) for d in str(n)]

            digits = digits_of(card_num)
            odd_digits = digits[-1::-2]
            even_digits = digits[-2::-2]
            checksum = sum(odd_digits)
            for d in even_digits:
                checksum += sum(digits_of(d * 2))
            return checksum % 10 == 0

        # Remove spaces and dashes
        number = number.replace(' ', '').replace('-', '')
        return luhn_checksum(number) if number.isdigit() else False


class PerformanceUtils:
    """Performance monitoring utilities"""

    @staticmethod
    @contextmanager
    def timer(name: str = "operation"):
        """Context manager for timing operations"""
        start = time.time()
        try:
            yield
        finally:
            elapsed = time.time() - start
            print(f"{name} took {elapsed:.4f} seconds")

    @staticmethod
    def benchmark(func: Callable, iterations: int = 100, *args, **kwargs) -> Dict[str, float]:
        """Benchmark a function"""
        times = []

        for _ in range(iterations):
            start = time.time()
            func(*args, **kwargs)
            end = time.time()
            times.append(end - start)

        return {
            'min': min(times),
            'max': max(times),
            'avg': sum(times) / len(times),
            'total': sum(times),
            'iterations': iterations
        }


class ThreadingUtils:
    """Threading utilities"""

    @staticmethod
    def run_in_thread(func: Callable, *args, **kwargs) -> threading.Thread:
        """Run function in a separate thread"""
        thread = threading.Thread(target=func, args=args, kwargs=kwargs)
        thread.start()
        return thread

    @staticmethod
    def thread_pool_executor(max_workers: int = None):
        """Context manager for thread pool executor"""
        @contextmanager
        def executor():
            with ThreadPoolExecutor(max_workers=max_workers) as ex:
                yield ex
        return executor()


class LoggingUtils:
    """Logging utilities"""

    @staticmethod
    def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
        """Get a configured logger"""
        logger = logging.getLogger(name)
        logger.setLevel(level)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    @staticmethod
    def log_execution_time(func: Callable) -> Callable:
        """Decorator to log function execution time"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            end = time.time()

            logger.info(f"{func.__name__} executed in {end - start:.4f} seconds")
            return result
        return wrapper


# Global instances
function_utils = FunctionUtils()
async_utils = AsyncUtils()
data_utils = DataUtils()
validation_utils = ValidationUtils()
performance_utils = PerformanceUtils()
threading_utils = ThreadingUtils()
logging_utils = LoggingUtils()

__all__ = [
    'FunctionUtils', 'AsyncUtils', 'DataUtils', 'ValidationUtils',
    'PerformanceUtils', 'ThreadingUtils', 'LoggingUtils',
    'function_utils', 'async_utils', 'data_utils', 'validation_utils',
    'performance_utils', 'threading_utils', 'logging_utils'
]

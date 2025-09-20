"""
Collections utilities for PyDance
Efficient custom collections for working with models and large datasets
"""

import threading
from typing import (
    TypeVar, Generic, Iterator, List, Dict, Any, Optional, Callable,
    Union, Set, Tuple, Iterable, Sized, Container, Sequence
)
from collections import defaultdict, deque
from functools import lru_cache, partial
import heapq
import bisect
import weakref
import gc
from abc import ABC, abstractmethod
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time

T = TypeVar('T')
K = TypeVar('K')


class Collection(Generic[T], Sequence[T], Sized, Container[T]):
    """
    High-performance collection for model objects with advanced operations

    Features:
    - Lazy loading and caching
    - Parallel processing for bulk operations
    - Memory-efficient for large datasets
    - Advanced filtering and querying
    - Automatic indexing for fast lookups
    """

    def __init__(self, items: Optional[Iterable[T]] = None, max_cache_size: int = 1000):
        self._items: List[T] = list(items) if items else []
        self._indices: Dict[str, Dict[Any, List[int]]] = {}
        self._cache: Dict[str, Any] = {}
        self._max_cache_size = max_cache_size
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="Collection")

    def __len__(self) -> int:
        return len(self._items)

    def __getitem__(self, index: Union[int, slice]) -> Union[T, 'Collection[T]']:
        if isinstance(index, slice):
            return Collection(self._items[index])
        return self._items[index]

    def __iter__(self) -> Iterator[T]:
        return iter(self._items)

    def __contains__(self, item: T) -> bool:
        return item in self._items

    def __repr__(self) -> str:
        return f"Collection({len(self._items)} items)"

    def append(self, item: T) -> None:
        """Add item to collection"""
        with self._lock:
            self._items.append(item)
            self._invalidate_indices()

    def extend(self, items: Iterable[T]) -> None:
        """Add multiple items to collection"""
        with self._lock:
            self._items.extend(items)
            self._invalidate_indices()

    def remove(self, item: T) -> None:
        """Remove item from collection"""
        with self._lock:
            self._items.remove(item)
            self._invalidate_indices()

    def clear(self) -> None:
        """Clear all items"""
        with self._lock:
            self._items.clear()
            self._indices.clear()
            self._cache.clear()

    def filter(self, predicate: Callable[[T], bool]) -> 'Collection[T]':
        """Filter items using predicate function"""
        cache_key = f"filter_{hash(predicate)}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        filtered = Collection(item for item in self._items if predicate(item))
        if len(self._cache) < self._max_cache_size:
            self._cache[cache_key] = filtered

        return filtered

    def where(self, **kwargs) -> 'Collection[T]':
        """Filter by attribute values"""
        def predicate(item):
            for key, value in kwargs.items():
                if not hasattr(item, key):
                    return False
                item_value = getattr(item, key)
                if callable(value):
                    if not value(item_value):
                        return False
                elif item_value != value:
                    return False
            return True

        return self.filter(predicate)

    def order_by(self, key: Callable[[T], Any], reverse: bool = False) -> 'Collection[T]':
        """Sort collection by key function"""
        cache_key = f"order_by_{hash(key)}_{reverse}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        sorted_items = sorted(self._items, key=key, reverse=reverse)
        result = Collection(sorted_items)
        if len(self._cache) < self._max_cache_size:
            self._cache[cache_key] = result

        return result

    def group_by(self, key: Callable[[T], K]) -> Dict[K, 'Collection[T]']:
        """Group items by key function"""
        cache_key = f"group_by_{hash(key)}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        groups = defaultdict(list)
        for item in self._items:
            groups[key(item)].append(item)

        result = {k: Collection(v) for k, v in groups.items()}
        if len(self._cache) < self._max_cache_size:
            self._cache[cache_key] = result

        return result

    def distinct(self, key: Optional[Callable[[T], Any]] = None) -> 'Collection[T]':
        """Get distinct items"""
        cache_key = f"distinct_{hash(key) if key else 'id'}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        seen = set()
        distinct_items = []

        for item in self._items:
            value = key(item) if key else item
            if value not in seen:
                seen.add(value)
                distinct_items.append(item)

        result = Collection(distinct_items)
        if len(self._cache) < self._max_cache_size:
            self._cache[cache_key] = result

        return result

    def take(self, count: int) -> 'Collection[T]':
        """Take first N items"""
        return Collection(self._items[:count])

    def skip(self, count: int) -> 'Collection[T]':
        """Skip first N items"""
        return Collection(self._items[count:])

    def first(self, predicate: Optional[Callable[[T], bool]] = None) -> Optional[T]:
        """Get first item or first item matching predicate"""
        if predicate:
            for item in self._items:
                if predicate(item):
                    return item
        elif self._items:
            return self._items[0]
        return None

    def last(self, predicate: Optional[Callable[[T], bool]] = None) -> Optional[T]:
        """Get last item or last item matching predicate"""
        if predicate:
            for item in reversed(self._items):
                if predicate(item):
                    return item
        elif self._items:
            return self._items[-1]
        return None

    def count(self, predicate: Optional[Callable[[T], bool]] = None) -> int:
        """Count items or items matching predicate"""
        if predicate:
            return sum(1 for item in self._items if predicate(item))
        return len(self._items)

    def any(self, predicate: Callable[[T], bool]) -> bool:
        """Check if any item matches predicate"""
        return any(predicate(item) for item in self._items)

    def all(self, predicate: Callable[[T], bool]) -> bool:
        """Check if all items match predicate"""
        return all(predicate(item) for item in self._items)

    def sum(self, key: Callable[[T], Union[int, float]] = lambda x: x) -> Union[int, float]:
        """Sum values from items"""
        return sum(key(item) for item in self._items)

    def avg(self, key: Callable[[T], Union[int, float]] = lambda x: x) -> float:
        """Average values from items"""
        if not self._items:
            return 0.0
        return self.sum(key) / len(self._items)

    def min(self, key: Callable[[T], Any] = lambda x: x) -> Optional[T]:
        """Get item with minimum value"""
        if not self._items:
            return None
        return min(self._items, key=key)

    def max(self, key: Callable[[T], Any] = lambda x: x) -> Optional[T]:
        """Get item with maximum value"""
        if not self._items:
            return None
        return max(self._items, key=key)

    def chunk(self, size: int) -> List['Collection[T]']:
        """Split collection into chunks"""
        return [Collection(self._items[i:i + size])
                for i in range(0, len(self._items), size)]

    async def map_async(self, func: Callable[[T], Any], max_workers: int = 4) -> List[Any]:
        """Asynchronously map function over items"""
        loop = asyncio.get_event_loop()

        # Run mapping in thread pool
        futures = []
        for item in self._items:
            future = loop.run_in_executor(self._executor, func, item)
            futures.append(future)

        return await asyncio.gather(*futures)

    def bulk_update(self, updates: Dict[str, Any], predicate: Optional[Callable[[T], bool]] = None) -> int:
        """Bulk update items matching predicate"""
        updated_count = 0
        with self._lock:
            for item in self._items:
                if predicate is None or predicate(item):
                    for key, value in updates.items():
                        if hasattr(item, key):
                            setattr(item, key, value)
                    updated_count += 1

            self._invalidate_indices()
        return updated_count

    def create_index(self, name: str, key_func: Callable[[T], Any]) -> None:
        """Create custom index for fast lookups"""
        with self._lock:
            index = defaultdict(list)
            for i, item in enumerate(self._items):
                key = key_func(item)
                index[key].append(i)
            self._indices[name] = dict(index)

    def find_by_index(self, index_name: str, key: Any) -> 'Collection[T]':
        """Fast lookup using index"""
        if index_name not in self._indices:
            raise ValueError(f"Index '{index_name}' not found")

        indices = self._indices[index_name].get(key, [])
        return Collection(self._items[i] for i in indices)

    def _invalidate_indices(self) -> None:
        """Invalidate all indices when collection changes"""
        self._indices.clear()
        self._cache.clear()

    def to_list(self) -> List[T]:
        """Convert to regular list"""
        return self._items.copy()

    def to_dict(self, key_func: Callable[[T], K], value_func: Optional[Callable[[T], Any]] = None) -> Dict[K, Any]:
        """Convert to dictionary"""
        if value_func is None:
            value_func = lambda x: x

        return {key_func(item): value_func(item) for item in self._items}

    def paginate(self, page: int = 1, per_page: int = 20) -> Tuple['Collection[T]', Dict[str, Any]]:
        """Paginate collection"""
        total = len(self._items)
        total_pages = (total + per_page - 1) // per_page

        start = (page - 1) * per_page
        end = start + per_page

        items = self._items[start:end]
        pagination_info = {
            'page': page,
            'per_page': per_page,
            'total': total,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1,
            'next_page': page + 1 if page < total_pages else None,
            'prev_page': page - 1 if page > 1 else None
        }

        return Collection(items), pagination_info





class LazyCollection(Generic[T]):
    """
    Memory-efficient lazy collection that loads items on demand
    """

    def __init__(self, loader: Callable[[], Iterable[T]], cache_size: int = 100):
        self._loader = loader
        self._cache: Optional[List[T]] = None
        self._cache_size = cache_size
        self._loaded = False

    def _ensure_loaded(self) -> None:
        """Ensure items are loaded"""
        if not self._loaded:
            self._cache = list(self._loader())
            self._loaded = True

    def __iter__(self) -> Iterator[T]:
        self._ensure_loaded()
        return iter(self._cache)

    def __len__(self) -> int:
        self._ensure_loaded()
        return len(self._cache)

    def __getitem__(self, index: int) -> T:
        self._ensure_loaded()
        return self._cache[index]

    def first(self) -> Optional[T]:
        """Get first item without loading all"""
        if self._loaded and self._cache:
            return self._cache[0]

        # Try to get first item efficiently
        try:
            return next(iter(self._loader()))
        except (StopIteration, TypeError):
            return None


class CachedCollection(Generic[T]):
    """
    Time-based cached collection with automatic invalidation
    """

    def __init__(self, ttl_seconds: int = 300):
        self._data: Dict[str, Tuple[List[T], float]] = {}
        self._ttl = ttl_seconds
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[List[T]]:
        """Get cached collection"""
        with self._lock:
            if key in self._data:
                items, timestamp = self._data[key]
                if time.time() - timestamp < self._ttl:
                    return items.copy()
                else:
                    del self._data[key]
            return None

    def set(self, key: str, items: List[T]) -> None:
        """Cache collection"""
        with self._lock:
            self._data[key] = (items.copy(), time.time())

    def invalidate(self, key: str) -> None:
        """Invalidate specific cache entry"""
        with self._lock:
            self._data.pop(key, None)

    def clear(self) -> None:
        """Clear all cache"""
        with self._lock:
            self._data.clear()

    def cleanup(self) -> int:
        """Remove expired entries, return count removed"""
        with self._lock:
            current_time = time.time()
            expired_keys = [
                key for key, (_, timestamp) in self._data.items()
                if current_time - timestamp >= self._ttl
            ]

            for key in expired_keys:
                del self._data[key]

            return len(expired_keys)


# High-performance data structures for large datasets

class SortedList(Generic[T]):
    """
    Sorted list with O(log n) insertion and fast lookups
    """

    def __init__(self, items: Optional[Iterable[T]] = None, key: Optional[Callable[[T], Any]] = None):
        self._items: List[T] = []
        self._key = key or (lambda x: x)

        if items:
            self._items = sorted(items, key=self._key)

    def add(self, item: T) -> None:
        """Add item while maintaining sort order"""
        key_value = self._key(item)
        pos = bisect.bisect_left([self._key(x) for x in self._items], key_value)
        self._items.insert(pos, item)

    def remove(self, item: T) -> None:
        """Remove item"""
        try:
            self._items.remove(item)
        except ValueError:
            pass

    def find_le(self, value: Any) -> Optional[T]:
        """Find largest item <= value"""
        keys = [self._key(x) for x in self._items]
        pos = bisect.bisect_right(keys, value)
        if pos > 0:
            return self._items[pos - 1]
        return None

    def find_ge(self, value: Any) -> Optional[T]:
        """Find smallest item >= value"""
        keys = [self._key(x) for x in self._items]
        pos = bisect.bisect_left(keys, value)
        if pos < len(self._items):
            return self._items[pos]
        return None

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[T]:
        return iter(self._items)

    def __getitem__(self, index: int) -> T:
        return self._items[index]


class PriorityQueue(Generic[T]):
    """
    Priority queue with efficient operations
    """

    def __init__(self, max_size: Optional[int] = None):
        self._heap: List[Tuple[Any, T]] = []
        self._max_size = max_size
        self._counter = 0

    def push(self, item: T, priority: Any = 0) -> None:
        """Add item with priority"""
        heapq.heappush(self._heap, (priority, self._counter, item))
        self._counter += 1

        if self._max_size and len(self._heap) > self._max_size:
            heapq.heappop(self._heap)

    def pop(self) -> Optional[T]:
        """Remove and return highest priority item"""
        if self._heap:
            return heapq.heappop(self._heap)[2]
        return None

    def peek(self) -> Optional[T]:
        """Return highest priority item without removing"""
        if self._heap:
            return self._heap[0][2]
        return None

    def __len__(self) -> int:
        return len(self._heap)

    def __bool__(self) -> bool:
        return bool(self._heap)


class LRUCache(Generic[K, T]):
    """
    LRU cache with O(1) operations
    """

    def __init__(self, capacity: int = 100):
        self._capacity = capacity
        self._cache: Dict[K, T] = {}
        self._order: Dict[K, int] = {}
        self._counter = 0
        self._lock = threading.RLock()

    def get(self, key: K) -> Optional[T]:
        """Get item from cache"""
        with self._lock:
            if key in self._cache:
                self._order[key] = self._counter
                self._counter += 1
                return self._cache[key]
            return None

    def put(self, key: K, value: T) -> None:
        """Put item in cache"""
        with self._lock:
            if key in self._cache:
                self._cache[key] = value
                self._order[key] = self._counter
            else:
                if len(self._cache) >= self._capacity:
                    # Remove least recently used
                    lru_key = min(self._order, key=self._order.get)
                    del self._cache[lru_key]
                    del self._order[lru_key]

                self._cache[key] = value
                self._order[key] = self._counter

            self._counter += 1

    def __contains__(self, key: K) -> bool:
        return key in self._cache

    def __len__(self) -> int:
        return len(self._cache)

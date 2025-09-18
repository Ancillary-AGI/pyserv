"""
Performance Optimization for Cryptographic Operations.
Provides optimized implementations for high-throughput security operations.
"""

from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio
import hashlib
import hmac
import secrets
import threading
import concurrent.futures
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa, padding
from cryptography.hazmat.backends import default_backend
import multiprocessing as mp
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor


@dataclass
class PerformanceMetrics:
    """Performance metrics for cryptographic operations"""
    operation: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: float = 0.0
    success: bool = True
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def complete(self, success: bool = True, error_message: Optional[str] = None):
        """Mark operation as complete"""
        self.end_time = datetime.utcnow()
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        self.success = success
        self.error_message = error_message


class OptimizedCryptoManager:
    """Optimized cryptographic operations manager"""

    def __init__(self, max_workers: int = None):
        self.max_workers = max_workers or min(32, mp.cpu_count() * 2)
        self.thread_pool = ThreadPoolExecutor(max_workers=self.max_workers)
        self.process_pool = ProcessPoolExecutor(max_workers=max_workers // 2)
        self.metrics: List[PerformanceMetrics] = []
        self.operation_cache: Dict[str, Any] = {}
        self.batch_operations: Dict[str, List[Callable]] = {}

    async def hash_batch(self, data_list: List[bytes], algorithm: str = 'sha3_256') -> List[str]:
        """Batch hash multiple data items"""
        start_time = datetime.utcnow()

        def hash_single(data: bytes) -> str:
            return getattr(hashlib, algorithm)(data).hexdigest()

        # Use thread pool for CPU-bound operations
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(self.thread_pool, hash_single, data)
            for data in data_list
        ]

        results = await asyncio.gather(*tasks)

        # Record metrics
        self._record_metric('hash_batch', start_time, len(data_list))

        return results

    async def encrypt_batch(self, data_list: List[bytes], key: bytes) -> List[bytes]:
        """Batch encrypt multiple data items"""
        start_time = datetime.utcnow()

        def encrypt_single(data: bytes) -> bytes:
            # Simple XOR encryption for demo (use AES in production)
            return bytes(a ^ b for a, b in zip(data, key * (len(data) // len(key) + 1)))

        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(self.thread_pool, encrypt_single, data)
            for data in data_list
        ]

        results = await asyncio.gather(*tasks)

        self._record_metric('encrypt_batch', start_time, len(data_list))

        return results

    async def sign_batch(self, messages: List[bytes], private_key_pem: str) -> List[str]:
        """Batch sign multiple messages"""
        start_time = datetime.utcnow()

        # Load private key once
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode(), password=None, backend=default_backend()
        )

        def sign_single(message: bytes) -> str:
            if isinstance(private_key, rsa.RSAPrivateKey):
                signature = private_key.sign(
                    message,
                    padding.PSS(
                        mgf=padding.MGF1(hashes.SHA256()),
                        salt_length=padding.PSS.MAX_LENGTH
                    ),
                    hashes.SHA256()
                )
            else:  # ECC
                signature = private_key.sign(message, ec.ECDSA(hashes.SHA256()))

            return signature.hex()

        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(self.thread_pool, sign_single, msg)
            for msg in messages
        ]

        results = await asyncio.gather(*tasks)

        self._record_metric('sign_batch', start_time, len(messages))

        return results

    async def verify_batch(self, signatures: List[Tuple[bytes, str]], public_key_pem: str) -> List[bool]:
        """Batch verify multiple signatures"""
        start_time = datetime.utcnow()

        # Load public key once
        public_key = serialization.load_pem_public_key(
            public_key_pem.encode(), backend=default_backend()
        )

        def verify_single(message: bytes, signature_hex: str) -> bool:
            try:
                signature = bytes.fromhex(signature_hex)

                if isinstance(public_key, rsa.RSAPublicKey):
                    public_key.verify(
                        signature,
                        message,
                        padding.PSS(
                            mgf=padding.MGF1(hashes.SHA256()),
                            salt_length=padding.PSS.MAX_LENGTH
                        ),
                        hashes.SHA256()
                    )
                else:  # ECC
                    public_key.verify(signature, message, ec.ECDSA(hashes.SHA256()))

                return True
            except Exception:
                return False

        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(self.thread_pool, verify_single, msg, sig)
            for msg, sig in signatures
        ]

        results = await asyncio.gather(*tasks)

        self._record_metric('verify_batch', start_time, len(signatures))

        return results

    def _record_metric(self, operation: str, start_time: datetime, item_count: int):
        """Record performance metric"""
        duration = (datetime.utcnow() - start_time).total_seconds() * 1000

        metric = PerformanceMetrics(
            operation=operation,
            start_time=start_time,
            end_time=datetime.utcnow(),
            duration_ms=duration,
            metadata={'item_count': item_count, 'avg_time_per_item': duration / item_count}
        )

        self.metrics.append(metric)

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        if not self.metrics:
            return {}

        stats = {}
        operations = set(m.operation for m in self.metrics)

        for op in operations:
            op_metrics = [m for m in self.metrics if m.operation == op]
            durations = [m.duration_ms for m in op_metrics]

            stats[op] = {
                'count': len(op_metrics),
                'avg_duration_ms': sum(durations) / len(durations),
                'min_duration_ms': min(durations),
                'max_duration_ms': max(durations),
                'total_items': sum(m.metadata.get('item_count', 1) for m in op_metrics)
            }

        return stats

    async def optimize_key_generation(self, count: int, key_size: int = 2048) -> List[str]:
        """Optimized batch key generation"""
        start_time = datetime.utcnow()

        def generate_single_key() -> str:
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=key_size,
                backend=default_backend()
            )

            pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )

            return pem.decode()

        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(self.thread_pool, generate_single_key)
            for _ in range(count)
        ]

        results = await asyncio.gather(*tasks)

        self._record_metric('key_generation_batch', start_time, count)

        return results

    async def parallel_database_operations(self, operations: List[Callable]) -> List[Any]:
        """Execute database operations in parallel"""
        start_time = datetime.utcnow()

        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(self.thread_pool, op)
            for op in operations
        ]

        results = await asyncio.gather(*tasks)

        self._record_metric('parallel_db_operations', start_time, len(operations))

        return results

    def create_operation_pipeline(self, pipeline_name: str, operations: List[Callable]):
        """Create an operation pipeline for sequential processing"""
        self.batch_operations[pipeline_name] = operations

    async def execute_pipeline(self, pipeline_name: str, input_data: Any) -> Any:
        """Execute operation pipeline"""
        if pipeline_name not in self.batch_operations:
            raise ValueError(f"Pipeline {pipeline_name} not found")

        start_time = datetime.utcnow()
        result = input_data

        for operation in self.batch_operations[pipeline_name]:
            if asyncio.iscoroutinefunction(operation):
                result = await operation(result)
            else:
                result = await asyncio.get_event_loop().run_in_executor(
                    self.thread_pool, operation, result
                )

        self._record_metric(f'pipeline_{pipeline_name}', start_time, 1)

        return result

    async def cleanup(self):
        """Cleanup resources"""
        self.thread_pool.shutdown(wait=True)
        self.process_pool.shutdown(wait=True)


class MemoryPool:
    """Memory pool for optimized allocations"""

    def __init__(self, block_size: int = 65536, max_blocks: int = 100):
        self.block_size = block_size
        self.max_blocks = max_blocks
        self.pool: List[bytes] = []
        self.allocated = 0

    def allocate(self, size: int) -> bytes:
        """Allocate memory from pool"""
        if size > self.block_size:
            # Direct allocation for large blocks
            return bytes(size)

        # Find suitable block
        for i, block in enumerate(self.pool):
            if len(block) >= size:
                # Split block if necessary
                allocated = block[:size]
                remaining = block[size:]

                if remaining:
                    self.pool[i] = remaining
                else:
                    self.pool.pop(i)

                self.allocated += size
                return allocated

        # Allocate new block
        if len(self.pool) < self.max_blocks:
            new_block = bytes(self.block_size)
            self.pool.append(new_block)

            allocated = new_block[:size]
            remaining = new_block[size:]

            if remaining:
                self.pool[-1] = remaining

            self.allocated += size
            return allocated

        # Fallback to direct allocation
        return bytes(size)

    def deallocate(self, data: bytes):
        """Return memory to pool"""
        if len(data) <= self.block_size and len(self.pool) < self.max_blocks:
            self.pool.append(data)
            self.allocated -= len(data)

    def get_stats(self) -> Dict[str, Any]:
        """Get memory pool statistics"""
        return {
            'total_blocks': len(self.pool),
            'allocated_bytes': self.allocated,
            'available_blocks': len(self.pool),
            'utilization_percent': (self.allocated / (len(self.pool) * self.block_size)) * 100 if self.pool else 0
        }


class AsyncLRUCache:
    """Asynchronous LRU cache with optimized operations"""

    def __init__(self, capacity: int = 1000):
        self.capacity = capacity
        self.cache: Dict[str, Any] = {}
        self.access_order: Dict[str, datetime] = {}
        self.lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """Get item from cache"""
        async with self.lock:
            if key in self.cache:
                self.access_order[key] = datetime.utcnow()
                return self.cache[key]
            return None

    async def put(self, key: str, value: Any):
        """Put item in cache"""
        async with self.lock:
            if key in self.cache:
                self.cache[key] = value
                self.access_order[key] = datetime.utcnow()
            else:
                if len(self.cache) >= self.capacity:
                    # Remove least recently used
                    lru_key = min(self.access_order, key=self.access_order.get)
                    del self.cache[lru_key]
                    del self.access_order[lru_key]

                self.cache[key] = value
                self.access_order[key] = datetime.utcnow()

    async def clear(self):
        """Clear cache"""
        async with self.lock:
            self.cache.clear()
            self.access_order.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'size': len(self.cache),
            'capacity': self.capacity,
            'utilization_percent': (len(self.cache) / self.capacity) * 100,
            'hit_rate': 0.0  # Would need to track hits/misses
        }


class OptimizedSecurityPipeline:
    """Optimized security processing pipeline"""

    def __init__(self):
        self.crypto_manager = OptimizedCryptoManager()
        self.memory_pool = MemoryPool()
        self.cache = AsyncLRUCache(capacity=5000)

    async def process_security_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process security request with optimizations"""
        start_time = datetime.utcnow()

        # Check cache first
        cache_key = hashlib.sha256(str(request_data).encode()).hexdigest()
        cached_result = await self.cache.get(cache_key)

        if cached_result:
            return cached_result

        # Process request
        result = await self._process_request(request_data)

        # Cache result
        await self.cache.put(cache_key, result)

        # Record performance
        duration = (datetime.utcnow() - start_time).total_seconds() * 1000
        print(f"Security request processed in {duration:.2f}ms")

        return result

    async def _process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Internal request processing"""
        operations = []

        # Prepare data for batch operations
        if 'hash_data' in request_data:
            operations.append(self._batch_hash_operation(request_data['hash_data']))

        if 'encrypt_data' in request_data:
            operations.append(self._batch_encrypt_operation(request_data['encrypt_data']))

        if 'sign_data' in request_data:
            operations.append(self._batch_sign_operation(request_data['sign_data']))

        # Execute operations in parallel
        results = await asyncio.gather(*operations)

        return {
            'results': results,
            'processed_at': datetime.utcnow().isoformat(),
            'performance_stats': self.crypto_manager.get_performance_stats()
        }

    async def _batch_hash_operation(self, data_list: List[bytes]) -> Dict[str, Any]:
        """Batch hash operation"""
        hashes = await self.crypto_manager.hash_batch(data_list)
        return {'operation': 'hash', 'count': len(data_list), 'results': hashes}

    async def _batch_encrypt_operation(self, data_list: List[bytes]) -> Dict[str, Any]:
        """Batch encrypt operation"""
        key = secrets.token_bytes(32)
        encrypted = await self.crypto_manager.encrypt_batch(data_list, key)
        return {
            'operation': 'encrypt',
            'count': len(data_list),
            'key': key.hex(),
            'results': [e.hex() for e in encrypted]
        }

    async def _batch_sign_operation(self, data_list: List[bytes]) -> Dict[str, Any]:
        """Batch sign operation"""
        # Generate temporary key for demo
        from cryptography.hazmat.primitives.asymmetric import rsa
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )

        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode()

        signatures = await self.crypto_manager.sign_batch(data_list, private_key_pem)
        return {
            'operation': 'sign',
            'count': len(data_list),
            'public_key': private_key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ).decode(),
            'results': signatures
        }

    def get_system_stats(self) -> Dict[str, Any]:
        """Get system performance statistics"""
        return {
            'crypto_performance': self.crypto_manager.get_performance_stats(),
            'memory_pool': self.memory_pool.get_stats(),
            'cache_stats': self.cache.get_stats(),
            'timestamp': datetime.utcnow().isoformat()
        }


# Global optimized security pipeline
_optimized_pipeline = None

def get_optimized_security_pipeline() -> OptimizedSecurityPipeline:
    """Get global optimized security pipeline"""
    global _optimized_pipeline
    if _optimized_pipeline is None:
        _optimized_pipeline = OptimizedSecurityPipeline()
    return _optimized_pipeline

"""
Background processing and queue system for PyDance framework.
Provides job queues, workers, cron scheduling, and task management.
"""

import asyncio
import threading
import time
import uuid
import json
import pickle
from typing import Dict, List, Any, Optional, Callable, Union, Type
from datetime import datetime, timedelta
from functools import wraps
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import heapq
import logging

from ..core.caching import get_cache_manager
from ..core.database import DatabaseConnection


class Job:
    """Represents a background job"""

    def __init__(self, func: Callable, *args, **kwargs):
        self.id = str(uuid.uuid4())
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.created_at = datetime.now()
        self.status = 'pending'  # pending, running, completed, failed
        self.result = None
        self.error = None
        self.retries = 0
        self.max_retries = 3
        self.priority = 0  # Higher number = higher priority
        self.queue_name = 'default'
        self.delay_until = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary for storage"""
        return {
            'id': self.id,
            'func_name': f"{self.func.__module__}.{self.func.__name__}",
            'args': self.args,
            'kwargs': self.kwargs,
            'created_at': self.created_at.isoformat(),
            'status': self.status,
            'result': self.result,
            'error': self.error,
            'retries': self.retries,
            'max_retries': self.max_retries,
            'priority': self.priority,
            'queue_name': self.queue_name,
            'delay_until': self.delay_until.isoformat() if self.delay_until else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Job':
        """Create job from dictionary"""
        # This would need to resolve the function from the name
        # For now, return a placeholder
        job = cls(lambda: None)
        job.id = data['id']
        job.args = data['args']
        job.kwargs = data['kwargs']
        job.created_at = datetime.fromisoformat(data['created_at'])
        job.status = data['status']
        job.result = data['result']
        job.error = data['error']
        job.retries = data['retries']
        job.max_retries = data['max_retries']
        job.priority = data['priority']
        job.queue_name = data['queue_name']
        job.delay_until = datetime.fromisoformat(data['delay_until']) if data['delay_until'] else None
        return job

    def should_retry(self) -> bool:
        """Check if job should be retried"""
        return self.retries < self.max_retries

    def is_ready(self) -> bool:
        """Check if job is ready to be executed"""
        if self.delay_until:
            return datetime.now() >= self.delay_until
        return True


class QueueBackend:
    """Base queue backend"""

    def enqueue(self, job: Job) -> bool:
        """Add job to queue"""
        raise NotImplementedError

    def dequeue(self, queue_name: str = 'default') -> Optional[Job]:
        """Get next job from queue"""
        raise NotImplementedError

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID"""
        raise NotImplementedError

    def update_job(self, job: Job) -> bool:
        """Update job status"""
        raise NotImplementedError

    def get_queue_size(self, queue_name: str = 'default') -> int:
        """Get queue size"""
        raise NotImplementedError


class MemoryQueueBackend(QueueBackend):
    """In-memory queue backend"""

    def __init__(self):
        self.queues: Dict[str, List[Job]] = {}
        self.jobs: Dict[str, Job] = {}
        self.lock = threading.Lock()

    def enqueue(self, job: Job) -> bool:
        """Add job to queue"""
        with self.lock:
            if job.queue_name not in self.queues:
                self.queues[job.queue_name] = []

            # Insert job in priority order (higher priority first)
            queue = self.queues[job.queue_name]
            inserted = False
            for i, existing_job in enumerate(queue):
                if job.priority > existing_job.priority:
                    queue.insert(i, job)
                    inserted = True
                    break

            if not inserted:
                queue.append(job)

            self.jobs[job.id] = job
            return True

    def dequeue(self, queue_name: str = 'default') -> Optional[Job]:
        """Get next job from queue"""
        with self.lock:
            if queue_name not in self.queues:
                return None

            queue = self.queues[queue_name]
            for i, job in enumerate(queue):
                if job.is_ready():
                    queue.pop(i)
                    job.status = 'running'
                    return job

            return None

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID"""
        with self.lock:
            return self.jobs.get(job_id)

    def update_job(self, job: Job) -> bool:
        """Update job status"""
        with self.lock:
            self.jobs[job.id] = job
            return True

    def get_queue_size(self, queue_name: str = 'default') -> int:
        """Get queue size"""
        with self.lock:
            return len(self.queues.get(queue_name, []))


class RedisQueueBackend(QueueBackend):
    """Redis-based queue backend"""

    def __init__(self, redis_client=None):
        self.redis = redis_client
        # This would use redis for actual implementation
        # For now, fall back to memory backend
        self.fallback = MemoryQueueBackend()

    def enqueue(self, job: Job) -> bool:
        """Add job to Redis queue"""
        if self.redis:
            # Redis implementation would go here
            pass
        return self.fallback.enqueue(job)

    def dequeue(self, queue_name: str = 'default') -> Optional[Job]:
        """Get next job from Redis queue"""
        if self.redis:
            # Redis implementation would go here
            pass
        return self.fallback.dequeue(queue_name)

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID from Redis"""
        if self.redis:
            # Redis implementation would go here
            pass
        return self.fallback.get_job(job_id)

    def update_job(self, job: Job) -> bool:
        """Update job status in Redis"""
        if self.redis:
            # Redis implementation would go here
            pass
        return self.fallback.update_job(job)

    def get_queue_size(self, queue_name: str = 'default') -> int:
        """Get queue size from Redis"""
        if self.redis:
            # Redis implementation would go here
            pass
        return self.fallback.get_queue_size(queue_name)


class DatabaseQueueBackend(QueueBackend):
    """Database-based queue backend"""

    def __init__(self, db_connection=None):
        self.db = db_connection or DatabaseConnection.get_instance()
        self.fallback = MemoryQueueBackend()

    def enqueue(self, job: Job) -> bool:
        """Add job to database queue"""
        try:
            # Database implementation would go here
            return self.fallback.enqueue(job)
        except Exception:
            return self.fallback.enqueue(job)

    def dequeue(self, queue_name: str = 'default') -> Optional[Job]:
        """Get next job from database queue"""
        try:
            # Database implementation would go here
            return self.fallback.dequeue(queue_name)
        except Exception:
            return self.fallback.dequeue(queue_name)

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID from database"""
        try:
            # Database implementation would go here
            return self.fallback.get_job(job_id)
        except Exception:
            return self.fallback.get_job(job_id)

    def update_job(self, job: Job) -> bool:
        """Update job status in database"""
        try:
            # Database implementation would go here
            return self.fallback.update_job(job)
        except Exception:
            return self.fallback.update_job(job)

    def get_queue_size(self, queue_name: str = 'default') -> int:
        """Get queue size from database"""
        try:
            # Database implementation would go here
            return self.fallback.get_queue_size(queue_name)
        except Exception:
            return self.fallback.get_queue_size(queue_name)


class Worker:
    """Background worker for processing jobs"""

    def __init__(self, queue_backend: QueueBackend, queue_name: str = 'default',
                 max_concurrent: int = 4):
        self.queue_backend = queue_backend
        self.queue_name = queue_name
        self.max_concurrent = max_concurrent
        self.running = False
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent)
        self.thread = None

    def start(self):
        """Start the worker"""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._run_worker)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        """Stop the worker"""
        self.running = False
        if self.executor:
            self.executor.shutdown(wait=True)

    def _run_worker(self):
        """Main worker loop"""
        while self.running:
            try:
                job = self.queue_backend.dequeue(self.queue_name)
                if job:
                    self.executor.submit(self._execute_job, job)
                else:
                    time.sleep(1)  # Wait before checking again
            except Exception as e:
                logging.error(f"Worker error: {e}")
                time.sleep(5)  # Wait longer on error

    def _execute_job(self, job: Job):
        """Execute a single job"""
        try:
            job.status = 'running'
            self.queue_backend.update_job(job)

            # Execute the job function
            result = job.func(*job.args, **job.kwargs)
            job.result = result
            job.status = 'completed'

        except Exception as e:
            job.error = str(e)
            job.status = 'failed'
            job.retries += 1

            # Retry if possible
            if job.should_retry():
                job.status = 'pending'
                self.queue_backend.enqueue(job)

        finally:
            self.queue_backend.update_job(job)


class QueueManager:
    """Main queue manager"""

    def __init__(self, backend: Optional[QueueBackend] = None):
        self.backend = backend or MemoryQueueBackend()
        self.workers: Dict[str, List[Worker]] = {}
        self.job_registry: Dict[str, Callable] = {}

    def register_job(self, name: str, func: Callable):
        """Register a job function"""
        self.job_registry[name] = func

    def enqueue(self, func: Callable, *args, queue_name: str = 'default',
                priority: int = 0, delay: Optional[timedelta] = None, **kwargs) -> str:
        """Add job to queue"""
        job = Job(func, *args, **kwargs)
        job.queue_name = queue_name
        job.priority = priority

        if delay:
            job.delay_until = datetime.now() + delay

        self.backend.enqueue(job)
        return job.id

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID"""
        return self.backend.get_job(job_id)

    def start_worker(self, queue_name: str = 'default', num_workers: int = 1,
                    max_concurrent: int = 4):
        """Start workers for a queue"""
        if queue_name not in self.workers:
            self.workers[queue_name] = []

        for _ in range(num_workers):
            worker = Worker(self.backend, queue_name, max_concurrent)
            worker.start()
            self.workers[queue_name].append(worker)

    def stop_workers(self, queue_name: str = 'default'):
        """Stop workers for a queue"""
        if queue_name in self.workers:
            for worker in self.workers[queue_name]:
                worker.stop()
            self.workers[queue_name].clear()

    def get_queue_size(self, queue_name: str = 'default') -> int:
        """Get queue size"""
        return self.backend.get_queue_size(queue_name)


class CronScheduler:
    """Cron-like scheduler for periodic tasks"""

    def __init__(self):
        self.jobs: List[Dict[str, Any]] = []
        self.running = False
        self.thread = None

    def add_job(self, func: Callable, cron_expression: str, *args, **kwargs):
        """Add a cron job"""
        # Parse cron expression (simplified)
        # Format: "minute hour day month day_of_week"
        # Example: "0 9 * * 1-5" = 9 AM weekdays
        self.jobs.append({
            'func': func,
            'cron': cron_expression,
            'args': args,
            'kwargs': kwargs,
            'next_run': self._calculate_next_run(cron_expression)
        })

    def start(self):
        """Start the scheduler"""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._run_scheduler)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        """Stop the scheduler"""
        self.running = False

    def _run_scheduler(self):
        """Main scheduler loop"""
        while self.running:
            now = datetime.now()

            for job in self.jobs:
                if now >= job['next_run']:
                    try:
                        job['func'](*job['args'], **job['kwargs'])
                    except Exception as e:
                        logging.error(f"Cron job error: {e}")

                    # Calculate next run
                    job['next_run'] = self._calculate_next_run(job['cron'])

            time.sleep(60)  # Check every minute

    def _calculate_next_run(self, cron_expression: str) -> datetime:
        """Calculate next run time from cron expression"""
        # Simplified cron parsing
        # This would need a full cron parser for production
        parts = cron_expression.split()
        if len(parts) >= 5:
            minute = parts[0]
            hour = parts[1]

            now = datetime.now()
            next_run = now.replace(minute=int(minute) if minute != '*' else 0,
                                 second=0, microsecond=0)

            if hour != '*':
                next_run = next_run.replace(hour=int(hour))

            if next_run <= now:
                next_run += timedelta(days=1)

            return next_run

        return datetime.now() + timedelta(minutes=1)


# Decorators
def job(queue_name: str = 'default', priority: int = 0):
    """Decorator to mark function as a job"""
    def decorator(func: Callable) -> Callable:
        func._is_job = True
        func._queue_name = queue_name
        func._priority = priority

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator


def scheduled(cron_expression: str):
    """Decorator to mark function as scheduled"""
    def decorator(func: Callable) -> Callable:
        func._is_scheduled = True
        func._cron_expression = cron_expression

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator


# Global instances
queue_manager = QueueManager()
cron_scheduler = CronScheduler()

__all__ = [
    'Job', 'QueueBackend', 'MemoryQueueBackend', 'RedisQueueBackend', 'DatabaseQueueBackend',
    'Worker', 'QueueManager', 'CronScheduler', 'job', 'scheduled',
    'queue_manager', 'cron_scheduler'
]

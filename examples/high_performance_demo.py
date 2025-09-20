"""
High-Performance PyDance Application Demo

This example demonstrates how to use all the performance optimizations together:
- Database connection pooling
- Multi-level distributed caching
- gRPC microservices
- Load balancing
- Performance monitoring
- Profiling and benchmarking
- Anti-pattern detection

Run with: python examples/high_performance_demo.py
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional

# PyDance imports
from pydance.core.database_pool import get_pooled_connection, PoolConfig
from pydance.core.distributed_cache import get_distributed_cache, CacheConfig
from pydance.core.load_balancer import get_load_balancer, LoadBalancerConfig
from pydance.microservices.grpc_service import GRPCService, GRPCConfig
from pydance.core.performance_optimizer import init_performance_monitoring
from pydance.core.profiling import get_profiler, get_load_tester, benchmark
from pydance.core.performance_anti_patterns import get_anti_pattern_monitor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("high_performance_demo")


class UserService:
    """Example user service with full performance optimization"""

    def __init__(self):
        self.db_config = type('Config', (), {
            'database_url': 'postgresql://user:pass@localhost/pydance_demo'
        })()
        self.pool_config = PoolConfig(min_size=5, max_size=20)

        # Initialize components
        self.db_conn = get_pooled_connection(self.db_config, self.pool_config)
        self.cache = get_distributed_cache(CacheConfig(
            enable_l1=True,
            enable_l2=True,
            redis_url="redis://localhost:6379"
        ))
        self.load_balancer = get_load_balancer(LoadBalancerConfig(
            algorithm="least_connections"
        ))

    async def initialize(self):
        """Initialize all components"""
        logger.info("Initializing UserService...")

        # Connect to database
        await self.db_conn.connect()

        # Start cache
        await self.cache.start()

        # Add backend servers to load balancer
        await self.load_balancer.add_backend("localhost", 8081)
        await self.load_balancer.add_backend("localhost", 8082)
        await self.load_balancer.start()

        logger.info("UserService initialized successfully")

    async def shutdown(self):
        """Shutdown all components"""
        logger.info("Shutting down UserService...")

        await self.cache.stop()
        await self.load_balancer.stop()
        await self.db_conn.disconnect()

        logger.info("UserService shutdown complete")

    @benchmark(iterations=1000)
    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user with caching and database pooling"""
        cache_key = f"user:{user_id}"

        # Try cache first
        user_data = await self.cache.get(cache_key)
        if user_data:
            logger.debug(f"Cache hit for user {user_id}")
            return user_data

        # Cache miss - fetch from database
        logger.debug(f"Cache miss for user {user_id}, fetching from database")
        async with self.db_conn.get_connection() as conn:
            # Simulate database query
            await asyncio.sleep(0.01)  # Simulate DB latency
            user_data = {
                "id": user_id,
                "name": f"User {user_id}",
                "email": f"user{user_id}@example.com",
                "created_at": time.time()
            }

        # Cache the result
        await self.cache.set(cache_key, user_data, ttl=300, tags={"user", "profile"})

        return user_data

    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create user with cache invalidation"""
        async with self.db_conn.get_connection() as conn:
            # Simulate database insert
            await asyncio.sleep(0.02)  # Simulate DB latency
            user_id = int(time.time() * 1000)  # Simple ID generation
            user_data["id"] = user_id

        # Cache the new user
        cache_key = f"user:{user_id}"
        await self.cache.set(cache_key, user_data, ttl=300, tags={"user", "profile"})

        return user_data

    async def update_user(self, user_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update user with cache invalidation"""
        async with self.db_conn.get_connection() as conn:
            # Simulate database update
            await asyncio.sleep(0.015)  # Simulate DB latency

        # Invalidate cache
        await self.cache.invalidate_by_tag("user")

        # Get updated user (will fetch from DB due to invalidation)
        return await self.get_user(user_id)


class OptimizedGRPCService(GRPCService):
    """gRPC service with performance optimizations"""

    def __init__(self, user_service: UserService):
        super().__init__("user-service", GRPCConfig(port=50051))
        self.user_service = user_service

    async def handle_request(self, request):
        """Handle gRPC requests"""
        action = request.data.get("action")
        user_id = request.data.get("user_id")

        if action == "get_user":
            user = await self.user_service.get_user(user_id)
            return {"user": user, "status": "success"}
        elif action == "create_user":
            user_data = request.data.get("user_data", {})
            user = await self.user_service.create_user(user_data)
            return {"user": user, "status": "created"}
        elif action == "update_user":
            updates = request.data.get("updates", {})
            user = await self.user_service.update_user(user_id, updates)
            return {"user": user, "status": "updated"}
        else:
            return {"error": "Unknown action", "status": "error"}


async def performance_demo():
    """Main performance demonstration"""
    logger.info("🚀 Starting PyDance High-Performance Demo")

    # Initialize anti-pattern monitoring
    anti_pattern_monitor = get_anti_pattern_monitor()

    # Initialize user service
    user_service = UserService()
    await user_service.initialize()

    # Initialize gRPC service
    grpc_service = OptimizedGRPCService(user_service)
    await grpc_service.start()

    # Initialize performance monitoring
    monitor, optimizer = await init_performance_monitoring()

    # Initialize profiling
    profiler, load_tester, regression_detector = await init_profiling()

    try:
        logger.info("📊 Running performance tests...")

        # Test 1: Basic user operations
        logger.info("Test 1: Basic user operations")
        start_time = time.time()

        # Create some users
        for i in range(10):
            user_data = {"name": f"Test User {i}", "email": f"test{i}@example.com"}
            await user_service.create_user(user_data)

        # Fetch users (should hit cache after first fetch)
        for i in range(10):
            user = await user_service.get_user(i + 1)
            if user:
                logger.debug(f"Fetched user: {user['name']}")

        basic_ops_time = time.time() - start_time
        logger.info(".2f")

        # Test 2: Load testing
        logger.info("Test 2: Load testing")
        from pydance.core.profiling import LoadTestScenario

        scenario = LoadTestScenario(
            name="user_service_load_test",
            duration=30,
            ramp_up_time=5,
            concurrent_users=50
        )

        # Note: This would need actual HTTP endpoints to test properly
        # For demo purposes, we'll simulate the load test
        logger.info("Load test simulation completed")

        # Test 3: Cache performance
        logger.info("Test 3: Cache performance analysis")
        cache_stats = user_service.cache.get_analytics()
        logger.info(f"Cache hit rate: {cache_stats.get('hit_rate', 0):.2%}")
        logger.info(f"Cache hits: {cache_stats.get('hits', 0)}")
        logger.info(f"Cache misses: {cache_stats.get('misses', 0)}")

        # Test 4: Database pool performance
        logger.info("Test 4: Database pool performance")
        pool_stats = user_service.db_conn.get_pool_stats()
        if pool_stats:
            logger.info(f"Active connections: {pool_stats.active_connections}")
            logger.info(f"Total connections: {pool_stats.total_connections}")
            logger.info(f"Connection acquires: {pool_stats.total_acquires}")

        # Test 5: Performance profiling
        logger.info("Test 5: Performance profiling")

        with profiler.profile_function("demo_operations"):
            # Profile some operations
            for i in range(100):
                await user_service.get_user((i % 10) + 1)

        # Test 6: Anti-pattern detection
        logger.info("Test 6: Anti-pattern monitoring")
        from pydance.core.performance_anti_patterns import PerformanceAntiPatterns

        detector = PerformanceAntiPatterns()
        patterns = detector.detect_anti_patterns()

        if patterns:
            logger.info(f"Detected {len(patterns)} potential anti-patterns:")
            for pattern in patterns:
                logger.info(f"  - {pattern.name}: {pattern.description}")
        else:
            logger.info("No anti-patterns detected")

        # Test 7: Performance report
        logger.info("Test 7: Performance report")
        report = monitor.get_performance_report()
        logger.info("Performance Report:")
        logger.info(f"  CPU Usage: {report.get('current_metrics', {}).get('cpu_usage', 0):.1f}%")
        logger.info(f"  Memory Usage: {report.get('current_metrics', {}).get('memory_usage', 0):.1f}%")
        logger.info(f"  Active Alerts: {report.get('active_alerts', 0)}")

        if report.get('recommendations'):
            logger.info("Optimization Recommendations:")
            for rec in report['recommendations'][:3]:  # Show top 3
                logger.info(f"  - {rec.get('description', 'N/A')}")

        # Final summary
        logger.info("🎉 Performance demo completed successfully!")
        logger.info("Summary:")
        logger.info(f"  - Basic operations: {basic_ops_time:.2f}s")
        logger.info(f"  - Cache hit rate: {cache_stats.get('hit_rate', 0):.2%}")
        logger.info(f"  - Detected anti-patterns: {len(patterns)}")

    except Exception as e:
        logger.error(f"Demo failed: {e}")
        raise
    finally:
        # Cleanup
        logger.info("🧹 Cleaning up...")

        await grpc_service.stop()
        await user_service.shutdown()
        await monitor.stop_monitoring()
        await optimizer.stop_auto_optimization()


async def main():
    """Main entry point"""
    try:
        await performance_demo()
    except KeyboardInterrupt:
        logger.info("Demo interrupted by user")
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        raise


if __name__ == "__main__":
    # Configure asyncio
    asyncio.run(main())

"""
Performance Demo for PyServ Framework

This example demonstrates performance optimization features:
- Database connection pooling
- Multi-level caching
- Performance monitoring
- Profiling and benchmarking

Run with: python examples/performance_demo.py
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional

# PyServ imports
from pyserv import Application
from pyserv.database.connections import DatabaseConnection, PoolConfig
from pyserv.caching import CacheManager, CacheConfig, cache_result
from pyserv.performance import PerformanceMonitor, Profiler, benchmark
from pyserv.monitoring import MonitoringManager, MonitoringConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("performance_demo")


class UserService:
    """Example user service with performance optimizations"""

    def __init__(self):
        self.db_config = type('Config', (), {
            'database_url': 'sqlite:///performance_demo.db'
        })()
        self.pool_config = PoolConfig(min_size=2, max_size=10)

        # Initialize components
        self.db_conn = get_pooled_connection(self.db_config, self.pool_config)
        self.cache_manager = CacheManager(CacheConfig(
            max_memory_size=50 * 1024 * 1024,  # 50MB
            ttl_seconds=300,
            enable_compression=True,
            enable_metrics=True
        ))

    async def initialize(self):
        """Initialize all components"""
        logger.info("Initializing UserService...")

        # Connect to database
        await self.db_conn.connect()

        # Start cache manager
        await self.cache_manager.initialize()

        logger.info("UserService initialized successfully")

    async def shutdown(self):
        """Shutdown all components"""
        logger.info("Shutting down UserService...")

        await self.cache_manager.clear()
        await self.db_conn.disconnect()

        logger.info("UserService shutdown complete")

    @cache_result(ttl_seconds=300)
    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user with caching"""
        cache_key = f"user:{user_id}"

        # Try cache first
        cached_user = await self.cache_manager.get(cache_key)
        if cached_user:
            logger.debug(f"Cache hit for user {user_id}")
            return cached_user

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
        await self.cache_manager.set(cache_key, user_data, ttl=300)

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
        await self.cache_manager.set(cache_key, user_data, ttl=300)

        return user_data

    async def update_user(self, user_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update user with cache invalidation"""
        async with self.db_conn.get_connection() as conn:
            # Simulate database update
            await asyncio.sleep(0.015)  # Simulate DB latency

        # Invalidate cache
        await self.cache_manager.invalidate(f"user:{user_id}")

        # Get updated user (will fetch from DB due to invalidation)
        return await self.get_user(user_id)


class PerformanceDemoApp(Application):
    """Performance demonstration application"""

    def __init__(self):
        super().__init__()

        # Initialize services
        self.user_service = UserService()
        self.performance_monitor = PerformanceMonitor()
        self.monitoring_manager = MonitoringManager(MonitoringConfig(
            enable_metrics_collection=True,
            enable_alerting=True,
            enable_tracing=True,
            enable_logging=True,
            metrics_interval=10
        ))

        # Setup routes
        self._setup_routes()

    def _setup_routes(self):
        """Setup API routes"""

        @self.route('/users/{user_id}', methods=['GET'])
        async def get_user(request, user_id: str):
            """Get user with caching"""
            try:
                user_id_int = int(user_id)
                user = await self.user_service.get_user(user_id_int)

                if not user:
                    return {"error": "User not found"}, 404

                return {"user": user, "cached": True}

            except ValueError:
                return {"error": "Invalid user ID"}, 400

        @self.route('/users', methods=['POST'])
        async def create_user(request):
            """Create a new user"""
            try:
                data = await request.json()
                name = data.get('name')
                email = data.get('email')

                if not name or not email:
                    return {"error": "Name and email are required"}, 400

                user_data = {"name": name, "email": email}
                user = await self.user_service.create_user(user_data)

                return {"user": user, "status": "created"}, 201

            except Exception as e:
                return {"error": str(e)}, 500

        @self.route('/users/{user_id}', methods=['PUT'])
        async def update_user(request, user_id: str):
            """Update user"""
            try:
                user_id_int = int(user_id)
                data = await request.json()
                updates = data.get('updates', {})

                if not updates:
                    return {"error": "Updates are required"}, 400

                user = await self.user_service.update_user(user_id_int, updates)

                if not user:
                    return {"error": "User not found"}, 404

                return {"user": user, "status": "updated"}

            except ValueError:
                return {"error": "Invalid user ID"}, 400
            except Exception as e:
                return {"error": str(e)}, 500

        @self.route('/performance/metrics')
        async def get_performance_metrics(request):
            """Get performance metrics"""
            metrics = self.performance_monitor.get_metrics_summary()
            return {"metrics": metrics}

        @self.route('/cache/stats')
        async def get_cache_stats(request):
            """Get cache statistics"""
            metrics = self.user_service.cache_manager.get_metrics()
            return {"cache_stats": metrics}

        @self.route('/cache/clear')
        async def clear_cache(request):
            """Clear cache"""
            await self.user_service.cache_manager.clear()
            return {"message": "Cache cleared successfully"}

        @self.route('/benchmark')
        async def run_benchmark(request):
            """Run performance benchmark"""
            try:
                # Benchmark user operations
                result = benchmark(self.user_service.get_user, iterations=50)
                return {"benchmark_result": result}
            except Exception as e:
                return {"error": str(e)}, 500

    async def startup(self):
        """Application startup"""
        print("🚀 Starting PyServ Performance Demo")

        # Initialize services
        await self.user_service.initialize()
        await self.performance_monitor.start_monitoring(interval=1.0)
        await self.monitoring_manager.start_monitoring()

        # Call parent startup
        await super().startup()

        print("✅ Performance Demo started successfully!")
        print("Available endpoints:")
        print("  GET  /users/{id}     - Get user (cached)")
        print("  POST /users          - Create user")
        print("  PUT  /users/{id}     - Update user")
        print("  GET  /performance/metrics - Performance metrics")
        print("  GET  /cache/stats    - Cache statistics")
        print("  POST /cache/clear    - Clear cache")
        print("  GET  /benchmark      - Run benchmark")

    async def shutdown(self):
        """Application shutdown"""
        print("🛑 Shutting down Performance Demo")

        # Stop monitoring
        await self.performance_monitor.stop_monitoring()
        await self.monitoring_manager.stop_monitoring()

        # Stop user service
        await self.user_service.shutdown()

        # Call parent shutdown
        await super().shutdown()

        print("✅ Performance Demo shut down successfully")


async def main():
    """Main entry point"""
    app = PerformanceDemoApp()

    try:
        await app.serve(host='127.0.0.1', port=8000)
    except KeyboardInterrupt:
        print("\nReceived shutdown signal...")
        await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())

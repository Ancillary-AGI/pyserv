"""
PyServ Multi-level Caching System Demo

This example demonstrates how to use PyServ's comprehensive caching system
to build a high-performance web application with:

- Multi-level caching (L1, L2, L3)
- Cache decorators for easy function caching
- Cache invalidation strategies
- Performance monitoring and metrics
- Cache warming and preloading
"""

import asyncio
import json
import random
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from pyserv import Application, Router
from pyserv.caching import (
    CacheManager, CacheConfig, CacheLevel,
    MemoryCache, RedisCache, CDNCache,
    cache_result, invalidate_cache, cache_key,
    CacheMetricsCollector
)
from pyserv.security import RateLimiter, RateLimitRule
from pyserv.middleware import HTTPMiddleware
from pyserv.exceptions import HTTPException
from pyserv.http import Request, Response

# Initialize caching components
cache_config = CacheConfig(
    max_memory_size=50 * 1024 * 1024,  # 50MB
    ttl_seconds=3600,  # 1 hour
    enable_compression=True,
    enable_metrics=True
)

cache_manager = CacheManager(cache_config)

# Rate limiter
rate_limiter = RateLimiter()
rate_limiter.add_rule(RateLimitRule(
    name="api_requests",
    requests_per_period=100,
    period_seconds=60,
    strategy=RateLimitRule.RateLimitStrategy.TOKEN_BUCKET
))

# Create application
app = Application()
router = Router()

@dataclass
class Product:
    id: str
    name: str
    price: float
    category: str
    description: str
    in_stock: bool
    created_at: datetime

@dataclass
class User:
    id: str
    username: str
    email: str
    preferences: Dict[str, Any]
    last_login: datetime

# Simulated data stores
class ProductService:
    """Simulated product service with expensive operations."""

    def __init__(self):
        self.products = {}
        self._generate_sample_data()

    def _generate_sample_data(self):
        """Generate sample product data."""
        categories = ["electronics", "clothing", "books", "home", "sports"]
        for i in range(1000):
            product = Product(
                id=f"prod_{i}",
                name=f"Product {i}",
                price=round(random.uniform(10, 1000), 2),
                category=random.choice(categories),
                description=f"Description for product {i}",
                in_stock=random.choice([True, False]),
                created_at=datetime.now()
            )
            self.products[product.id] = product

    async def get_product(self, product_id: str) -> Optional[Product]:
        """Get product by ID (simulated expensive operation)."""
        # Simulate database query delay
        await asyncio.sleep(random.uniform(0.1, 0.5))

        return self.products.get(product_id)

    async def get_products_by_category(self, category: str) -> List[Product]:
        """Get products by category (simulated expensive operation)."""
        # Simulate complex query delay
        await asyncio.sleep(random.uniform(0.2, 1.0))

        return [p for p in self.products.values() if p.category == category]

    async def search_products(self, query: str) -> List[Product]:
        """Search products (simulated expensive operation)."""
        # Simulate search index query delay
        await asyncio.sleep(random.uniform(0.3, 1.5))

        query_lower = query.lower()
        return [
            p for p in self.products.values()
            if query_lower in p.name.lower() or query_lower in p.description.lower()
        ]

class UserService:
    """Simulated user service with expensive operations."""

    def __init__(self):
        self.users = {}
        self._generate_sample_data()

    def _generate_sample_data(self):
        """Generate sample user data."""
        for i in range(500):
            user = User(
                id=f"user_{i}",
                username=f"user{i}",
                email=f"user{i}@example.com",
                preferences={"theme": random.choice(["light", "dark"])},
                last_login=datetime.now()
            )
            self.users[user.id] = user

    async def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID (simulated expensive operation)."""
        await asyncio.sleep(random.uniform(0.1, 0.3))
        return self.users.get(user_id)

    async def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user preferences (simulated expensive operation)."""
        await asyncio.sleep(random.uniform(0.05, 0.2))
        user = self.users.get(user_id)
        return user.preferences if user else {}

# Initialize services
product_service = ProductService()
user_service = UserService()

# Cache middleware
class CacheMiddleware(HTTPMiddleware):
    """Middleware that adds cache headers."""

    async def process_request(self, request: Request) -> Request:
        """Apply rate limiting."""
        client_ip = request.client_ip or "unknown"
        allowed, rate_info = await rate_limiter.check_rate_limit("api_requests", client_ip)

        if not allowed:
            raise HTTPException(429, f"Rate limit exceeded: {rate_info}")

        return request

    async def process_response(self, request: Request, response: Response) -> Response:
        """Add cache headers."""
        response.headers["X-Cache-Status"] = "enabled"
        response.headers["X-Cache-Level"] = "L1,L2,L3"
        return response

# Apply middleware
app.add_middleware(CacheMiddleware())

# Cached routes using decorators
@router.add_route("/api/products/<product_id>", methods=["GET"])
@cache_result(ttl_seconds=1800)  # Cache for 30 minutes
async def get_product(request, product_id: str) -> Response:
    """Get product with caching."""
    product = await product_service.get_product(product_id)

    if not product:
        raise HTTPException(404, "Product not found")

    return Response(json.dumps({
        "id": product.id,
        "name": product.name,
        "price": product.price,
        "category": product.category,
        "description": product.description,
        "in_stock": product.in_stock,
        "cached_at": datetime.now().isoformat()
    }), content_type="application/json")

@router.add_route("/api/products/category/<category>", methods=["GET"])
@cache_result(ttl_seconds=900)  # Cache for 15 minutes
async def get_products_by_category(request, category: str) -> Response:
    """Get products by category with caching."""
    products = await product_service.get_products_by_category(category)

    return Response(json.dumps({
        "category": category,
        "products": [
            {
                "id": p.id,
                "name": p.name,
                "price": p.price,
                "in_stock": p.in_stock
            }
            for p in products
        ],
        "count": len(products),
        "cached_at": datetime.now().isoformat()
    }), content_type="application/json")

@router.add_route("/api/search", methods=["GET"])
@cache_result(ttl_seconds=300)  # Cache for 5 minutes
async def search_products(request) -> Response:
    """Search products with caching."""
    query = request.query.get("q", "")

    if not query:
        raise HTTPException(400, "Query parameter 'q' is required")

    products = await product_service.search_products(query)

    return Response(json.dumps({
        "query": query,
        "products": [
            {
                "id": p.id,
                "name": p.name,
                "price": p.price,
                "category": p.category
            }
            for p in products[:20]  # Limit results
        ],
        "total_results": len(products),
        "cached_at": datetime.now().isoformat()
    }), content_type="application/json")

@router.add_route("/api/user/<user_id>/preferences", methods=["GET"])
@cache_result(ttl_seconds=600)  # Cache for 10 minutes
async def get_user_preferences(request, user_id: str) -> Response:
    """Get user preferences with caching."""
    preferences = await user_service.get_user_preferences(user_id)

    return Response(json.dumps({
        "user_id": user_id,
        "preferences": preferences,
        "cached_at": datetime.now().isoformat()
    }), content_type="application/json")

# Manual cache management routes
@router.add_route("/api/cache/clear", methods=["POST"])
async def clear_cache(request) -> Response:
    """Clear all cache levels."""
    await cache_manager.clear()

    return Response(json.dumps({
        "message": "Cache cleared successfully",
        "timestamp": datetime.now().isoformat()
    }), content_type="application/json")

@router.add_route("/api/cache/invalidate/<pattern>", methods=["POST"])
async def invalidate_cache_pattern(request, pattern: str) -> Response:
    """Invalidate cache entries matching pattern."""
    await cache_manager.invalidate_pattern(pattern)

    return Response(json.dumps({
        "message": f"Cache invalidated for pattern: {pattern}",
        "timestamp": datetime.now().isoformat()
    }), content_type="application/json")

@router.add_route("/api/cache/warmup", methods=["POST"])
async def warmup_cache(request) -> Response:
    """Warmup cache with sample data."""
    try:
        data = json.loads(request.body)
        warmup_data = data.get("data", {})

        await cache_manager.warmup(warmup_data)

        return Response(json.dumps({
            "message": f"Cache warmed up with {len(warmup_data)} entries",
            "timestamp": datetime.now().isoformat()
        }), content_type="application/json")
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON")

@router.add_route("/api/cache/stats", methods=["GET"])
async def get_cache_stats(request) -> Response:
    """Get comprehensive cache statistics."""
    metrics = cache_manager.get_metrics()

    # Get individual cache stats
    l1_stats = {}
    l2_stats = {}
    l3_stats = {}

    if CacheLevel.L1 in cache_manager.caches:
        l1_stats = cache_manager.caches[CacheLevel.L1].get_stats()

    if CacheLevel.L2 in cache_manager.caches:
        l2_stats = cache_manager.caches[CacheLevel.L2].get_stats()

    if CacheLevel.L3 in cache_manager.caches:
        l3_stats = cache_manager.caches[CacheLevel.L3].get_stats()

    stats = {
        "overall_metrics": metrics,
        "cache_levels": {
            "L1": l1_stats,
            "L2": l2_stats,
            "L3": l3_stats
        },
        "features": [
            "Multi-level caching (L1, L2, L3)",
            "LRU eviction policy",
            "TTL support",
            "Cache decorators",
            "Cache invalidation",
            "Cache warming",
            "Performance metrics",
            "Compression support"
        ],
        "timestamp": datetime.now().isoformat()
    }

    return Response(json.dumps(stats), content_type="application/json")

@router.add_route("/api/cache/test", methods=["POST"])
async def test_cache_performance(request) -> Response:
    """Test cache performance with different scenarios."""
    try:
        data = json.loads(request.body)
        test_type = data.get("type", "read_heavy")

        results = {"test_type": test_type, "results": []}

        if test_type == "read_heavy":
            # Test cache hit performance
            for i in range(100):
                start_time = time.time()
                product = await product_service.get_product(f"prod_{i % 100}")
                response_time = time.time() - start_time
                results["results"].append({
                    "operation": "product_lookup",
                    "response_time": response_time,
                    "cached": product is not None
                })

        elif test_type == "write_heavy":
            # Test cache write performance
            for i in range(50):
                start_time = time.time()
                await cache_manager.set(f"test_key_{i}", {"data": f"value_{i}", "timestamp": datetime.now().isoformat()})
                response_time = time.time() - start_time
                results["results"].append({
                    "operation": "cache_write",
                    "response_time": response_time
                })

        elif test_type == "mixed":
            # Test mixed read/write performance
            for i in range(50):
                # Read operation
                start_time = time.time()
                await cache_manager.get(f"test_key_{i}")
                read_time = time.time() - start_time

                # Write operation
                start_time = time.time()
                await cache_manager.set(f"test_key_{i}", {"updated": True, "timestamp": datetime.now().isoformat()})
                write_time = time.time() - start_time

                results["results"].append({
                    "operation": "mixed",
                    "read_time": read_time,
                    "write_time": write_time
                })

        # Calculate averages
        if results["results"]:
            total_read_time = sum(r.get("read_time", 0) for r in results["results"])
            total_write_time = sum(r.get("write_time", 0) for r in results["results"])
            count = len(results["results"])

            results["summary"] = {
                "total_operations": count,
                "avg_read_time": total_read_time / count if total_read_time > 0 else 0,
                "avg_write_time": total_write_time / count if total_write_time > 0 else 0
            }

        return Response(json.dumps(results), content_type="application/json")

    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON")

# Setup cache warming data
async def setup_cache_warming():
    """Setup cache warming with sample data."""
    warmup_data = {}

    # Warmup popular products
    for i in range(10):
        product = await product_service.get_product(f"prod_{i}")
        if product:
            warmup_data[f"product:{product.id}"] = {
                "id": product.id,
                "name": product.name,
                "price": product.price,
                "category": product.category,
                "in_stock": product.in_stock
            }

    # Warmup categories
    categories = ["electronics", "clothing", "books"]
    for category in categories:
        products = await product_service.get_products_by_category(category)
        warmup_data[f"category:{category}"] = {
            "category": category,
            "product_count": len(products)
        }

    await cache_manager.warmup(warmup_data)
    print(f"Cache warmed up with {len(warmup_data)} entries")

# Main application
async def main():
    """Main application entry point."""

    print("🚀 PyServ Multi-level Caching System Demo")
    print("=" * 50)

    # Initialize cache manager
    await cache_manager.initialize()

    # Setup cache warming
    await setup_cache_warming()

    # Add routes to application
    app.add_router(router)

    print("\n📋 Available endpoints:")
    print("  GET  /api/products/<id> - Get product (cached)")
    print("  GET  /api/products/category/<category> - Get products by category (cached)")
    print("  GET  /api/search?q=<query> - Search products (cached)")
    print("  GET  /api/user/<id>/preferences - Get user preferences (cached)")
    print("  POST /api/cache/clear - Clear all cache")
    print("  POST /api/cache/invalidate/<pattern> - Invalidate cache pattern")
    print("  POST /api/cache/warmup - Warmup cache with data")
    print("  GET  /api/cache/stats - Get cache statistics")
    print("  POST /api/cache/test - Test cache performance")
    print("\n💾 Caching Features Enabled:")
    print("  ✓ Multi-level caching (L1, L2, L3)")
    print("  ✓ LRU eviction policy")
    print("  ✓ TTL support")
    print("  ✓ Cache decorators (@cache_result)")
    print("  ✓ Cache invalidation")
    print("  ✓ Cache warming")
    print("  ✓ Performance metrics")
    print("  ✓ Compression support")
    print("  ✓ Rate limiting")

    print("\n🔧 Cache Levels:")
    print("  L1 - In-memory cache (fastest)")
    print("  L2 - Redis cache (distributed)")
    print("  L3 - CDN cache (global)")

    print("\n⚡ Performance Features:")
    print("  ✓ Automatic cache hierarchy")
    print("  ✓ Cache warming for popular data")
    print("  ✓ Compression for large values")
    print("  ✓ Metrics collection")
    print("  ✓ Configurable TTL")

    # Run application
    await app.run(host="127.0.0.1", port=8000)

if __name__ == "__main__":
    asyncio.run(main())

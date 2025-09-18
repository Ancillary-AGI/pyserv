# PyDance Enhanced Framework - Distributed Systems Integration

This document describes the comprehensive enhancements made to the PyDance framework by integrating advanced distributed systems patterns from the provided distributed streaming framework.

## Overview

The PyDance framework has been significantly enhanced with enterprise-grade distributed systems capabilities, including:

- **Microservices Architecture**: Service discovery, health checks, and lifecycle management
- **Distributed Consensus**: Raft algorithm implementation for leader election and log replication
- **Event Sourcing & CQRS**: Complete event sourcing with command-query responsibility segregation
- **Advanced API Design**: HATEOAS, rate limiting, pagination, and standardized responses
- **Comprehensive Monitoring**: Metrics, tracing, health checks, and alerting
- **Distributed Coordination**: Locks and coordination primitives

## New Modules

### 1. Microservices (`src/pydance/microservices/`)

#### Service Architecture (`service.py`)
- `Service`: Base class for microservices with lifecycle management
- `ServiceDiscovery`: Protocol for service discovery implementations
- `InMemoryServiceDiscovery`: In-memory service discovery for development
- `ServiceInstance`: Service instance representation
- `ServiceStatus`: Enumeration of service states

#### Distributed Consensus (`consensus.py`)
- `RaftConsensus`: Complete Raft consensus algorithm implementation
- `ConsensusState`: Consensus states (Follower, Candidate, Leader)
- `LogEntry`: Consensus log entries
- `DistributedLock`: Distributed locking using consensus

#### Event Sourcing & CQRS (`event_sourcing.py`)
- `Event`: Immutable event representation
- `EventStore`: Durable event storage with subscriptions
- `Aggregate`: Base class for domain aggregates
- `Command`: Command representation
- `Repository`: Aggregate repository pattern
- `EventPublisher`: Event publishing and subscription

#### API Design Patterns (`api_design.py`)
- `APIResponse`: Standardized API responses with HATEOAS
- `APIError`: Structured error handling
- `RateLimiter`: Token bucket rate limiting
- `Link`: HATEOAS link representation
- `Paginator`: Pagination utilities
- `HttpMethod`: HTTP method enumeration

### 2. Enhanced Monitoring (`src/pydance/monitoring/`)

#### Observability (`observability.py`)
- `Metrics`: Comprehensive metrics collection
- `Tracing`: Distributed tracing with spans
- `HealthCheck`: Multi-level health checking
- `AlertManager`: Alert management system
- `MonitoringSystem`: Integrated monitoring solution

## Key Features

### Microservices Architecture

```python
from pydance.microservices import Service, ServiceStatus, InMemoryServiceDiscovery

class MyService(Service):
    def __init__(self, name: str, version: str):
        super().__init__(name, version)
        self.service_discovery = InMemoryServiceDiscovery()

    async def start(self):
        self.status = ServiceStatus.STARTING
        # Register with service discovery
        await self.service_discovery.register_service(self)
        self.status = ServiceStatus.HEALTHY

    async def stop(self):
        self.status = ServiceStatus.STOPPING
        await self.service_discovery.deregister_service(self.name)
        self.status = ServiceStatus.UNHEALTHY
```

### Distributed Consensus

```python
from pydance.microservices import RaftConsensus, DistributedLock

# Initialize consensus
consensus = RaftConsensus("node1", ["node2", "node3"])
await consensus.start()

# Use distributed lock
lock = DistributedLock(consensus, "resource_lock")
if await lock.acquire("node1"):
    try:
        # Critical section
        pass
    finally:
        await lock.release("node1")
```

### Event Sourcing & CQRS

```python
from pydance.microservices import Event, EventStore, Aggregate, Repository

class UserAggregate(Aggregate):
    async def handle_command(self, command):
        if command['type'] == 'create_user':
            event = Event(
                event_type='user_created',
                aggregate_id=self.aggregate_id,
                payload=command
            )
            return [event]

# Usage
event_store = EventStore()
repository = Repository(event_store, UserAggregate)

user = UserAggregate("user_123")
events = await user.handle_command({'type': 'create_user', 'name': 'John'})
await event_store.append_events(events)
```

### Advanced API Design

```python
from pydance.microservices import APIResponse, Link, HttpMethod, RateLimiter

# Rate limiting
rate_limiter = RateLimiter(capacity=100, refill_rate=10)
if not await rate_limiter.acquire():
    raise APIError("Rate limit exceeded", 429)

# HATEOAS response
response = APIResponse.success(data)
response.add_link(Link(
    href="/users/123",
    rel="self",
    method=HttpMethod.GET
))
```

### Comprehensive Monitoring

```python
from pydance.monitoring import MonitoringSystem

monitoring = MonitoringSystem("my-service", [my_service])
await monitoring.start()

# Record metrics
monitoring.metrics.record_request("GET", "/api/users", 200, 0.15)

# Health checks
health = await monitoring.health_check.check()
```

## Example Application

See `examples/enhanced_distributed_app.py` for a complete example that demonstrates:

- User management with event sourcing
- Distributed consensus and locking
- HATEOAS API with rate limiting
- Comprehensive monitoring
- Service discovery and health checks

### Running the Example

```bash
cd examples
python enhanced_distributed_app.py
```

The application will start on `http://localhost:8000` with the following endpoints:

- `GET /health` - Health check
- `GET /metrics` - Application metrics
- `GET /users` - List users (paginated)
- `POST /users` - Create user
- `GET /users/{id}` - Get specific user
- `GET /consensus/status` - Consensus status
- `GET /events/{id}` - Aggregate events

## Integration with Existing PyDance

The enhancements are fully backward compatible. Existing PyDance applications continue to work without changes. The new features are available as additional modules that can be imported and used as needed.

### Migration Guide

1. **Service Discovery**: Replace custom service discovery with the new `ServiceDiscovery` protocol
2. **Health Checks**: Use the new `HealthCheck` class for comprehensive health monitoring
3. **API Responses**: Gradually adopt `APIResponse` for standardized responses
4. **Metrics**: Integrate `MonitoringSystem` for enhanced observability

## Performance Considerations

- **Event Store**: Uses in-memory storage by default; configure persistent storage for production
- **Consensus**: Raft implementation is suitable for small to medium clusters
- **Rate Limiting**: Token bucket algorithm provides smooth rate limiting
- **Monitoring**: Metrics collection is lightweight and async

## Production Deployment

For production deployments, consider:

1. **Persistent Storage**: Configure database backends for event stores
2. **External Service Discovery**: Use Consul, etcd, or ZooKeeper
3. **Monitoring Integration**: Connect to Prometheus, Grafana, etc.
4. **Load Balancing**: Deploy multiple instances with proper load balancing
5. **Security**: Implement authentication and authorization

## Testing

The enhanced framework includes comprehensive testing patterns:

```python
# Test event sourcing
async def test_user_creation():
    event_store = EventStore()
    repository = Repository(event_store, UserAggregate)

    user = UserAggregate("test_user")
    events = await user.handle_command({
        'type': 'create_user',
        'username': 'test',
        'email': 'test@example.com'
    })

    assert len(events) == 1
    assert events[0].event_type == 'user_created'
```

## Contributing

When contributing to the enhanced framework:

1. Follow existing code patterns and async/await conventions
2. Add comprehensive type hints
3. Include docstrings for all public methods
4. Write tests for new functionality
5. Update this documentation

## Future Enhancements

Planned improvements include:

- **GraphQL Integration**: Schema generation from aggregates
- **Saga Pattern**: Distributed transaction management
- **Event Streaming**: Integration with Kafka, RabbitMQ
- **Service Mesh**: Istio integration
- **Auto-scaling**: Dynamic service scaling
- **Multi-region**: Cross-region replication

## Support

For questions and support:

1. Check the examples in the `examples/` directory
2. Review the comprehensive docstrings in each module
3. Refer to the original distributed streaming framework patterns
4. Create issues for bugs or feature requests

---

This enhanced PyDance framework provides enterprise-grade distributed systems capabilities while maintaining the simplicity and elegance of the original framework.

"""
Enhanced microservices support for PyDance framework.

This module provides comprehensive microservices architecture with:
- Service discovery and registration
- Distributed consensus (Raft algorithm)
- Event sourcing and CQRS patterns
- API design with HATEOAS and rate limiting
- Data-intensive processing patterns
"""

# Core service architecture
from .service import (
    Service, ServiceStatus, ServiceDiscovery, ServiceInstance,
    InMemoryServiceDiscovery
)

# Distributed consensus
from .consensus import (
    RaftConsensus, ConsensusState, LogEntry, DistributedLock
)

# Event sourcing and CQRS
from .event_sourcing import (
    Event, EventStore, Aggregate, Command, CommandHandler,
    Repository, EventPublisher
)

# API design patterns
from .rest_api_patterns import (
    HttpMethod, Link, APIResponse, APIError, RateLimiter,
    DistributedRateLimiter, PaginationParams, Paginator,
    APIResource, ValidationError, NotFoundError,
    UnauthorizedError, ForbiddenError
)

# Legacy service discovery (for backward compatibility)
from .service_discovery import ServiceDiscovery as LegacyServiceDiscovery
from .service_discovery import ConsulDiscovery, ZookeeperDiscovery

__all__ = [
    # Service architecture
    'Service', 'ServiceStatus', 'ServiceDiscovery', 'ServiceInstance',
    'InMemoryServiceDiscovery',

    # Distributed consensus
    'RaftConsensus', 'ConsensusState', 'LogEntry', 'DistributedLock',

    # Event sourcing and CQRS
    'Event', 'EventStore', 'Aggregate', 'Command', 'CommandHandler',
    'Repository', 'EventPublisher',

    # API design patterns
    'HttpMethod', 'Link', 'APIResponse', 'APIError', 'RateLimiter',
    'DistributedRateLimiter', 'PaginationParams', 'Paginator',
    'APIResource', 'ValidationError', 'NotFoundError',
    'UnauthorizedError', 'ForbiddenError',

    # Legacy (backward compatibility)
    'LegacyServiceDiscovery', 'ConsulDiscovery', 'ZookeeperDiscovery'
]

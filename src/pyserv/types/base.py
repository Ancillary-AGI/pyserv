"""
Pyserv  Types - Centralized type definitions for the framework.
"""

from typing import Dict, List, Any, Callable, Awaitable, Union, Optional, Set, Type, get_origin, get_args
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, date, time
import uuid
import re
from decimal import Decimal

# ===== ASGI and Core Types =====

# ASGI types
Scope = Dict[str, Any]
Message = Dict[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]

# Handler types
Handler = Callable[..., Any]
AsyncHandler = Callable[..., Awaitable[Any]]

# Middleware types
Middleware = Callable[[Handler], Handler]
AsyncMiddleware = Callable[[AsyncHandler], AsyncHandler]

# Dependency injection types
ServiceFactory = Callable[[], Any]
ServiceLifetime = str

# Route types
RouteHandler = Union[Handler, AsyncHandler]
RouteMethods = List[str]
RouteParams = Dict[str, Any]

# Config types
ConfigValue = Union[str, int, float, bool, List[Any], Dict[str, Any]]

# ===== Database Types =====

class FieldType(str, Enum):
    # Basic types
    INTEGER = "INTEGER"
    BIGINT = "BIGINT"
    SMALLINT = "SMALLINT"
    TEXT = "TEXT"
    VARCHAR = "VARCHAR"
    CHAR = "CHAR"
    BOOLEAN = "BOOLEAN"
    TIMESTAMP = "TIMESTAMP"
    TIMESTAMPTZ = "TIMESTAMPTZ"
    FLOAT = "FLOAT"
    DOUBLE = "DOUBLE"
    DECIMAL = "DECIMAL"
    NUMERIC = "NUMERIC"
    JSON = "JSON"
    JSONB = "JSONB"
    DATE = "DATE"
    TIME = "TIME"
    UUID = "UUID"
    BLOB = "BLOB"
    BYTEA = "BYTEA"

    # Specialized types
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    URL = "URL"
    IP_ADDRESS = "IP_ADDRESS"
    MAC_ADDRESS = "MAC_ADDRESS"
    ENUM = "ENUM"
    ARRAY = "ARRAY"
    RANGE = "RANGE"
    GEOMETRY = "GEOMETRY"
    GEOGRAPHY = "GEOGRAPHY"
    HSTORE = "HSTORE"
    INET = "INET"
    MONEY = "MONEY"

class RelationshipType(str, Enum):
    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_ONE = "many_to_one"
    MANY_TO_MANY = "many_to_many"

class OrderDirection(str, Enum):
    ASC = "ASC"
    DESC = "DESC"

# ===== Routing Types =====

class RouteType(Enum):
    """Types of routes"""
    NORMAL = "normal"
    REDIRECT = "redirect"
    VIEW = "view"
    FALLBACK = "fallback"
    INTENDED = "intended"

@dataclass
class RouteMatch:
    """Route match result with enhanced metadata."""
    handler: Callable
    params: Dict[str, Any] = field(default_factory=dict)
    route: Optional['Route'] = None
    middleware: List[Callable] = field(default_factory=list)

@dataclass
class RouteConfig:
    """Configuration for route behavior."""
    methods: Set[str] = field(default_factory=lambda: {"GET"})
    name: Optional[str] = None
    middleware: List[Callable] = field(default_factory=list)
    cache_timeout: Optional[int] = None
    priority: int = 0

# ===== Widget Types =====

class WidgetType(Enum):
    """Widget type classifications"""
    BASIC = "basic"
    FORM = "form"
    CONTAINER = "container"
    DATA = "data"
    NAVIGATION = "navigation"
    MEDIA = "media"
    CUSTOM = "custom"

# ===== Streaming Types =====

class StreamType(Enum):
    LIVE = "live"
    RECORDED = "recorded"
    DASH = "dash"
    HLS = "hls"

@dataclass
class StreamConfig:
    """Configuration for streaming"""
    type: StreamType = StreamType.LIVE
    bitrate: int = 128000
    format: str = "mp3"
    quality: str = "high"
    buffer_size: int = 8192

@dataclass
class ClientSession:
    """WebSocket client session"""
    id: str
    connected_at: datetime
    last_activity: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

# ===== Security Types =====

@dataclass
class QuantumKeyPair:
    """Quantum-resistant key pair"""
    public_key: str
    private_key: str
    algorithm: str = "kyber"

@dataclass
class QuantumCapability:
    """Quantum security capabilities"""
    algorithm: str
    key_size: int
    resistance_level: str

@dataclass
class DeviceFingerprint:
    """Device fingerprint for zero-trust"""
    device_id: str
    fingerprint: str
    last_seen: datetime
    trust_score: float

@dataclass
class TrustContext:
    """Trust context for zero-trust architecture"""
    user_id: Optional[str] = None
    device_id: Optional[str] = None
    session_id: Optional[str] = None
    risk_level: str = "low"

@dataclass
class Permission:
    """Permission definition"""
    name: str
    description: str
    resource: str
    actions: List[str]

@dataclass
class Role:
    """Role definition"""
    name: str
    description: str
    permissions: List[Permission]
    inherits_from: List[str] = field(default_factory=list)

@dataclass
class Policy:
    """Policy definition"""
    name: str
    description: str
    effect: str  # "allow" or "deny"
    principals: List[str]
    actions: List[str]
    resources: List[str]
    conditions: Dict[str, Any] = field(default_factory=dict)

@dataclass
class IAMUser:
    """IAM user"""
    id: str
    username: str
    roles: List[str]
    permissions: List[str]
    attributes: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SecurityEvent:
    """Security event"""
    id: str
    type: str
    severity: str
    timestamp: datetime
    source: str
    details: Dict[str, Any]

@dataclass
class AlertRule:
    """Alert rule for SIEM"""
    name: str
    condition: str
    severity: str
    actions: List[str]
    enabled: bool = True

@dataclass
class ComplianceRule:
    """Compliance rule"""
    name: str
    standard: str
    requirement: str
    check_function: Callable
    severity: str = "medium"

@dataclass
class DataSubject:
    """Data subject for GDPR"""
    id: str
    type: str  # "user", "customer", etc.
    contact_info: Dict[str, Any]
    data_categories: List[str]

@dataclass
class AuditLogEntry:
    """Audit log entry"""
    id: str
    timestamp: datetime
    user_id: Optional[str]
    action: str
    resource: str
    details: Dict[str, Any]
    ip_address: Optional[str] = None

# ===== Monitoring Types =====

@dataclass
class Metrics:
    """Application metrics"""
    name: str
    value: Union[int, float]
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)

@dataclass
class MetricValue:
    """Metric value"""
    timestamp: datetime
    value: Union[int, float]
    labels: Dict[str, str] = field(default_factory=dict)

# ===== Microservices Types =====

@dataclass
class ServiceInstance:
    """Service instance"""
    id: str
    name: str
    host: str
    port: int
    health_check_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class LogEntry:
    """Consensus log entry"""
    term: int
    index: int
    command: str
    timestamp: datetime

@dataclass
class Event:
    """Event sourcing event"""
    id: str
    type: str
    aggregate_id: str
    data: Dict[str, Any]
    timestamp: datetime
    version: int

@dataclass
class GRPCConfig:
    """gRPC service configuration"""
    host: str = "localhost"
    port: int = 50051
    max_workers: int = 10
    options: Dict[str, Any] = field(default_factory=dict)

# ===== Pagination Types =====

@dataclass
class PaginationParams:
    """Pagination parameters"""
    page: int = 1
    page_size: int = 20
    sort_by: Optional[str] = None
    sort_order: OrderDirection = OrderDirection.ASC

@dataclass
class PaginationMetadata:
    """Pagination metadata"""
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool

@dataclass
class PaginationLink:
    """Pagination link"""
    rel: str
    href: str
    method: str = "GET"

# ===== Performance Types =====

@dataclass
class PerformanceThreshold:
    """Performance threshold"""
    metric: str
    operator: str  # "gt", "lt", "eq", etc.
    value: Union[int, float]
    severity: str = "warning"

@dataclass
class PerformanceSnapshot:
    """Performance snapshot"""
    timestamp: datetime
    metrics: Dict[str, Union[int, float]]
    context: Dict[str, Any] = field(default_factory=dict)

@dataclass
class OptimizationRecommendation:
    """Performance optimization recommendation"""
    type: str
    description: str
    impact: str
    implementation: str
    priority: str = "medium"

@dataclass
class ProfileResult:
    """Profiling result"""
    function_name: str
    calls: int
    total_time: float
    avg_time: float
    max_time: float
    min_time: float

@dataclass
class BenchmarkResult:
    """Benchmark result"""
    name: str
    iterations: int
    total_time: float
    avg_time: float
    throughput: float

@dataclass
class LoadTestScenario:
    """Load test scenario"""
    name: str
    duration: int  # seconds
    users: int
    ramp_up: int  # seconds
    endpoints: List[str]

# ===== Rate Limiting Types =====

class RateLimitAlgorithm(str, Enum):
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"

@dataclass
class RateLimitConfig:
    """Rate limiting configuration"""
    requests: int
    window: int  # seconds
    algorithm: RateLimitAlgorithm = RateLimitAlgorithm.FIXED_WINDOW

@dataclass
class RateLimitResult:
    """Rate limiting result"""
    allowed: bool
    remaining: int
    reset_time: datetime
    retry_after: Optional[int] = None

# ===== Caching Types =====

@dataclass
class CacheConfig:
    """Cache configuration"""
    backend: str = "memory"
    ttl: int = 300  # 5 minutes
    max_size: int = 1000
    options: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CacheEntry:
    """Cache entry"""
    key: str
    value: Any
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

# ===== Load Balancing Types =====

@dataclass
class BackendServer:
    """Backend server for load balancing"""
    host: str
    port: int
    weight: int = 1
    healthy: bool = True
    connections: int = 0
    max_connections: int = 100

@dataclass
class LoadBalancerConfig:
    """Load balancer configuration"""
    algorithm: str = "round_robin"
    health_check_interval: int = 30
    health_check_timeout: int = 5
    sticky_sessions: bool = False

# ===== Database Pool Types =====

@dataclass
class PoolConfig:
    """Database connection pool configuration"""
    min_size: int = 1
    max_size: int = 10
    max_idle_time: int = 300
    max_lifetime: int = 3600
    acquire_timeout: int = 30

@dataclass
class ConnectionStats:
    """Database connection statistics"""
    active: int
    idle: int
    created: int
    destroyed: int
    borrowed: int
    returned: int

# ===== Distributed Cache Types =====

@dataclass
class DistributedCacheConfig:
    """Distributed cache configuration"""
    nodes: List[str]
    replication_factor: int = 1
    consistency_level: str = "quorum"
    ttl: int = 300

# ===== Template Types =====

class TemplateEngine(str, Enum):
    JINJA2 = "jinja2"
    LEAN = "lean"
    DJANGO = "django"

@dataclass
class TemplateConfig:
    """Template engine configuration"""
    engine: TemplateEngine = TemplateEngine.JINJA2
    cache_templates: bool = True
    auto_reload: bool = False
    options: Dict[str, Any] = field(default_factory=dict)

# ===== GraphQL Types =====

class GraphQLType:
    """Base GraphQL type"""
    def __init__(self, nullable: bool = True):
        self.nullable = nullable

class String(GraphQLType):
    def __init__(self, nullable: bool = True):
        super().__init__(nullable)

class Int(GraphQLType):
    def __init__(self, nullable: bool = True):
        super().__init__(nullable)

class Float(GraphQLType):
    def __init__(self, nullable: bool = True):
        super().__init__(nullable)

class Boolean(GraphQLType):
    def __init__(self, nullable: bool = True):
        super().__init__(nullable)

class ID(GraphQLType):
    def __init__(self, nullable: bool = True):
        super().__init__(nullable)

class List(GraphQLType):
    """List type wrapper"""
    def __init__(self, of_type: GraphQLType, nullable: bool = True):
        super().__init__(nullable)
        self.of_type = of_type

class ObjectType(GraphQLType):
    """GraphQL object type"""
    def __init__(self, name: str, fields: Dict[str, GraphQLType], nullable: bool = True):
        super().__init__(nullable)
        self.name = name
        self.fields = fields

class Query(ObjectType):
    """GraphQL Query type"""
    def __init__(self, fields: Dict[str, GraphQLType]):
        super().__init__("Query", fields)

class Mutation(ObjectType):
    """GraphQL Mutation type"""
    def __init__(self, fields: Dict[str, GraphQLType]):
        super().__init__("Mutation", fields)

class Subscription(ObjectType):
    """GraphQL Subscription type"""
    def __init__(self, fields: Dict[str, GraphQLType]):
        super().__init__("Subscription", fields)

# ===== Utility Functions =====

def get_field_from_type(python_type: Type) -> 'Field':
    """Get appropriate Field subclass from Python type"""
    from pyserv.utils.types import Field, IntegerField, StringField, BooleanField, FloatField, DateTimeField, DateField, TimeField, UUIDField, DecimalField, JSONField

    type_map = {
        int: IntegerField,
        str: StringField,
        bool: BooleanField,
        float: FloatField,
        datetime: DateTimeField,
        date: DateField,
        time: TimeField,
        uuid.UUID: UUIDField,
        Decimal: DecimalField,
        dict: JSONField,
        list: JSONField,
    }

    origin = get_origin(python_type) or python_type
    return type_map.get(origin, Field)()

# ===== Re-exports for backward compatibility =====

# Note: Database field types are available from pyserv.utils.types
# Import them directly when needed to avoid circular imports





"""
Enhanced Distributed Application Example for PyDance Framework.

This example demonstrates the integration of advanced distributed systems patterns
into the PyDance framework, including:

- Microservices architecture with service discovery
- Distributed consensus using Raft algorithm
- Event sourcing and CQRS patterns
- HATEOAS API design with rate limiting
- Comprehensive monitoring and observability
- Distributed locks and coordination

Run with: python examples/enhanced_distributed_app.py
"""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime

from pydance import Application
from pydance.microservices import (
    Service, ServiceStatus, InMemoryServiceDiscovery,
    RaftConsensus, ConsensusState, DistributedLock,
    Event, EventStore, Aggregate, Repository,
    HttpMethod, Link, APIResponse, APIError, RateLimiter,
    PaginationParams, Paginator, ValidationError
)
from pydance.monitoring import MonitoringSystem


class UserAggregate(Aggregate):
    """Example aggregate for user management using event sourcing"""

    def __init__(self, aggregate_id: str):
        super().__init__(aggregate_id)
        self.username: str = ""
        self.email: str = ""
        self.is_active: bool = True
        self.created_at: Optional[datetime] = None

    async def handle_command(self, command: Dict[str, Any]) -> List[Event]:
        """Handle user commands and produce events"""
        command_type = command.get('type')

        if command_type == 'create_user':
            return await self._handle_create_user(command)
        elif command_type == 'update_user':
            return await self._handle_update_user(command)
        elif command_type == 'deactivate_user':
            return await self._handle_deactivate_user(command)
        else:
            raise ValidationError(f"Unknown command type: {command_type}")

    async def _handle_create_user(self, command: Dict[str, Any]) -> List[Event]:
        """Handle user creation"""
        if self.username:
            raise ValidationError("User already exists")

        username = command.get('username')
        email = command.get('email')

        if not username or not email:
            raise ValidationError("Username and email are required")

        event = Event(
            event_type='user_created',
            aggregate_id=self.aggregate_id,
            payload={
                'username': username,
                'email': email,
                'created_at': datetime.now().isoformat()
            }
        )

        self.uncommitted_events.append(event)
        return [event]

    async def _handle_update_user(self, command: Dict[str, Any]) -> List[Event]:
        """Handle user update"""
        if not self.username:
            raise ValidationError("User does not exist")

        updates = {}
        if 'username' in command:
            updates['username'] = command['username']
        if 'email' in command:
            updates['email'] = command['email']

        if not updates:
            raise ValidationError("No updates provided")

        event = Event(
            event_type='user_updated',
            aggregate_id=self.aggregate_id,
            payload=updates
        )

        self.uncommitted_events.append(event)
        return [event]

    async def _handle_deactivate_user(self, command: Dict[str, Any]) -> List[Event]:
        """Handle user deactivation"""
        if not self.username:
            raise ValidationError("User does not exist")

        event = Event(
            event_type='user_deactivated',
            aggregate_id=self.aggregate_id,
            payload={'deactivated_at': datetime.now().isoformat()}
        )

        self.uncommitted_events.append(event)
        return [event]

    def apply_event(self, event: Event) -> None:
        """Apply events to update aggregate state"""
        super().apply_event(event)

        if event.event_type == 'user_created':
            self.username = event.payload['username']
            self.email = event.payload['email']
            self.created_at = datetime.fromisoformat(event.payload['created_at'])
            self.is_active = True
        elif event.event_type == 'user_updated':
            if 'username' in event.payload:
                self.username = event.payload['username']
            if 'email' in event.payload:
                self.email = event.payload['email']
        elif event.event_type == 'user_deactivated':
            self.is_active = False


class UserService(Service):
    """User management microservice"""

    def __init__(self, name: str, version: str, node_id: str, peers: List[str]):
        super().__init__(name, version)
        self.node_id = node_id
        self.peers = peers

        # Initialize components
        self.consensus = RaftConsensus(node_id, peers)
        self.event_store = EventStore()
        self.user_repository = Repository(self.event_store, UserAggregate)
        self.rate_limiter = RateLimiter(capacity=100, refill_rate=10)

        # Service discovery
        self.service_discovery = InMemoryServiceDiscovery()

    async def start(self) -> None:
        """Start the user service"""
        print(f"Starting {self.name} service...")

        self.status = ServiceStatus.STARTING
        self.start_time = datetime.now()

        # Start consensus
        await self.consensus.start()

        # Register service
        await self.service_discovery.register_service(self)

        # Start health checks
        await self.service_discovery.start_health_checks()

        self.status = ServiceStatus.HEALTHY
        print(f"{self.name} service started successfully")

    async def stop(self) -> None:
        """Stop the user service"""
        print(f"Stopping {self.name} service...")

        self.status = ServiceStatus.STOPPING

        # Stop consensus
        await self.consensus.stop()

        # Stop health checks
        await self.service_discovery.stop_health_checks()

        # Deregister service
        await self.service_discovery.deregister_service(self.name)

        self.status = ServiceStatus.UNHEALTHY
        print(f"{self.name} service stopped")

    async def create_user(self, username: str, email: str) -> Dict[str, Any]:
        """Create a new user"""
        user_id = f"user_{username}"

        # Check rate limit
        if not await self.rate_limiter.acquire():
            raise APIError("Rate limit exceeded", 429, "rate_limit_exceeded")

        # Use distributed lock for consistency
        lock = DistributedLock(self.consensus, f"user_creation_{user_id}")
        if not await lock.acquire(self.node_id, timeout=5.0):
            raise APIError("Could not acquire lock", 503, "lock_unavailable")

        try:
            # Check if user exists
            if await self.user_repository.exists(user_id):
                raise ValidationError("User already exists")

            # Create user aggregate
            user = UserAggregate(user_id)

            # Handle create command
            command = {
                'type': 'create_user',
                'username': username,
                'email': email
            }

            events = await user.handle_command(command)

            # Append events to store
            success = await self.event_store.append_events(events)
            if not success:
                raise APIError("Failed to create user", 500, "event_store_error")

            # Save aggregate
            await self.user_repository.save(user)

            return {
                'user_id': user_id,
                'username': username,
                'email': email,
                'created_at': user.created_at.isoformat()
            }

        finally:
            await lock.release(self.node_id)

    async def get_user(self, user_id: str) -> Dict[str, Any]:
        """Get user by ID"""
        try:
            user = await self.user_repository.load(user_id)
            return {
                'user_id': user.aggregate_id,
                'username': user.username,
                'email': user.email,
                'is_active': user.is_active,
                'created_at': user.created_at.isoformat() if user.created_at else None
            }
        except Exception:
            raise ValidationError(f"User {user_id} not found")


class EnhancedDistributedApp(Application):
    """Enhanced distributed application with all advanced features"""

    def __init__(self):
        super().__init__()

        # Initialize services
        self.user_service = UserService(
            "user-service",
            "1.0.0",
            "node1",
            ["localhost:8001", "localhost:8002"]
        )

        # Initialize monitoring
        self.monitoring = MonitoringSystem("enhanced-app", [self.user_service])

        # Setup routes
        self._setup_routes()

    def _setup_routes(self):
        """Setup API routes"""

        @self.route('/health')
        async def health_check(request):
            """Health check endpoint"""
            health = await self.monitoring.health_check.check()
            return APIResponse.success(health)

        @self.route('/metrics')
        async def metrics(request):
            """Metrics endpoint"""
            metrics = self.monitoring.metrics.get_summary()
            return APIResponse.success(metrics)

        @self.route('/users', methods=['GET'])
        async def list_users(request):
            """List users with pagination"""
            # Check rate limit
            if not await self.user_service.rate_limiter.acquire():
                raise APIError("Rate limit exceeded", 429, "rate_limit_exceeded")

            # Parse pagination parameters
            page = int(request.query_params.get('page', 1))
            per_page = int(request.query_params.get('per_page', 20))

            pagination = PaginationParams(page=page, per_page=per_page)

            # In a real implementation, you'd query users from a read model
            # For demo purposes, return empty paginated response
            paginator = Paginator([], 0, pagination)
            response = paginator.to_response("/users")

            # Add HATEOAS links
            response.add_link(Link(
                href="/users",
                rel="self",
                method=HttpMethod.GET
            ))
            response.add_link(Link(
                href="/users",
                rel="create",
                method=HttpMethod.POST,
                title="Create User"
            ))

            return response

        @self.route('/users', methods=['POST'])
        async def create_user(request):
            """Create a new user"""
            try:
                data = await request.json()
                username = data.get('username')
                email = data.get('email')

                if not username or not email:
                    raise ValidationError("Username and email are required")

                user_data = await self.user_service.create_user(username, email)

                response = APIResponse.created(user_data)

                # Add HATEOAS links
                user_id = user_data['user_id']
                response.add_link(Link(
                    href=f"/users/{user_id}",
                    rel="self",
                    method=HttpMethod.GET,
                    title="Get User"
                ))
                response.add_link(Link(
                    href=f"/users/{user_id}",
                    rel="edit",
                    method=HttpMethod.PUT,
                    title="Update User"
                ))
                response.add_link(Link(
                    href="/users",
                    rel="collection",
                    method=HttpMethod.GET,
                    title="List Users"
                ))

                return response

            except ValidationError as e:
                raise APIError(e.message, 400, "validation_error", e.details)
            except APIError:
                raise

        @self.route('/users/{user_id}', methods=['GET'])
        async def get_user(request, user_id: str):
            """Get a specific user"""
            try:
                user_data = await self.user_service.get_user(user_id)

                response = APIResponse.success(user_data)

                # Add HATEOAS links
                response.add_link(Link(
                    href=f"/users/{user_id}",
                    rel="self",
                    method=HttpMethod.GET
                ))
                response.add_link(Link(
                    href=f"/users/{user_id}",
                    rel="edit",
                    method=HttpMethod.PUT,
                    title="Update User"
                ))
                response.add_link(Link(
                    href=f"/users/{user_id}",
                    rel="delete",
                    method=HttpMethod.DELETE,
                    title="Delete User"
                ))
                response.add_link(Link(
                    href="/users",
                    rel="collection",
                    method=HttpMethod.GET,
                    title="List Users"
                ))

                return response

            except ValidationError as e:
                raise APIError(e.message, 404, "not_found")

        @self.route('/consensus/status')
        async def consensus_status(request):
            """Get consensus status"""
            status = self.user_service.consensus.get_state_info()
            return APIResponse.success(status)

        @self.route('/events/{aggregate_id}')
        async def get_aggregate_events(request, aggregate_id: str):
            """Get events for an aggregate"""
            events = self.user_service.event_store.get_aggregate_events(aggregate_id)
            event_data = [event.to_dict() for event in events]

            return APIResponse.success({
                "aggregate_id": aggregate_id,
                "events": event_data,
                "event_count": len(event_data)
            })

    async def startup(self):
        """Application startup"""
        print("Starting Enhanced Distributed Application...")

        # Start user service
        await self.user_service.start()

        # Start monitoring
        await self.monitoring.start()

        # Call parent startup
        await super().startup()

        print("Enhanced Distributed Application started successfully!")
        print("Available endpoints:")
        print("  GET  /health      - Health check")
        print("  GET  /metrics     - Application metrics")
        print("  GET  /users       - List users")
        print("  POST /users       - Create user")
        print("  GET  /users/{id}  - Get user")
        print("  GET  /consensus/status - Consensus status")
        print("  GET  /events/{id} - Aggregate events")

    async def shutdown(self):
        """Application shutdown"""
        print("Shutting down Enhanced Distributed Application...")

        # Stop monitoring
        await self.monitoring.stop()

        # Stop user service
        await self.user_service.stop()

        # Call parent shutdown
        await super().shutdown()

        print("Enhanced Distributed Application shut down successfully")


async def main():
    """Main application entry point"""
    app = EnhancedDistributedApp()

    try:
        # Start the server
        await app.serve(host='0.0.0.0', port=8000)
    except KeyboardInterrupt:
        print("\nReceived shutdown signal...")
        await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())

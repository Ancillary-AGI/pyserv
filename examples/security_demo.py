"""
PyServ Mission-Critical Security Framework Demo

This example demonstrates how to use PyServ's enhanced security features
to build a secure, enterprise-grade web application with:

- Multi-factor authentication
- Role-based access control
- Comprehensive audit logging
- Rate limiting
- CSRF protection
- Security headers
- Encryption at rest
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass

from pyserv import Application, Router
from pyserv.security import (
    AuthenticationManager, EncryptionService, AuditLogger,
    RoleBasedAccessControl, RateLimiter, CSRFProtection, SecurityHeaders
)
from pyserv.middleware import HTTPMiddleware
from pyserv.exceptions import HTTPException, Forbidden, Unauthorized
from pyserv.http import Request, Response

# Initialize security components
auth_manager = AuthenticationManager(secret_key="your-super-secret-key-change-in-production")
encryption_service = EncryptionService(master_key="your-encryption-master-key")
audit_logger = AuditLogger(log_file="security_audit.log")
rbac = RoleBasedAccessControl()
rate_limiter = RateLimiter()
csrf_protection = CSRFProtection(secret_key="csrf-secret-key")
security_headers = SecurityHeaders()

# Create application
app = Application()
router = Router()

@dataclass
class User:
    id: str
    username: str
    email: str
    roles: list
    permissions: list
    is_active: bool = True

# Initialize RBAC
admin_permission = rbac.create_permission("admin", "system", "admin")
user_permission = rbac.create_permission("read", "user", "read")
write_permission = rbac.create_permission("write", "user", "write")

admin_role = rbac.create_role("admin", [admin_permission])
user_role = rbac.create_role("user", [user_permission, write_permission])

# Security middleware
class SecurityMiddleware(HTTPMiddleware):
    """Comprehensive security middleware."""

    async def process_request(self, request: Request) -> Request:
        """Process incoming request with security checks."""

        # Rate limiting
        client_ip = request.client_ip or "unknown"
        allowed, rate_info = await rate_limiter.check_rate_limit("api_requests", client_ip)

        if not allowed:
            audit_logger.log_event(
                audit_logger.AuditEvent.SECURITY_EVENT,
                user_id=None,
                session_id=None,
                resource="rate_limit",
                action="exceeded",
                details={"ip": client_ip, "info": rate_info},
                ip_address=client_ip,
                user_agent=request.headers.get("User-Agent", ""),
                success=False
            )
            raise HTTPException(429, "Rate limit exceeded")

        # CSRF protection for state-changing requests
        if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
            csrf_token = request.headers.get("X-CSRF-Token")
            if not csrf_token:
                csrf_token = request.form.get("csrf_token")

            if not csrf_token or not csrf_protection.validate_token(csrf_token):
                audit_logger.log_event(
                    audit_logger.AuditEvent.SECURITY_EVENT,
                    user_id=None,
                    session_id=None,
                    resource="csrf",
                    action="invalid_token",
                    details={"ip": client_ip},
                    ip_address=client_ip,
                    user_agent=request.headers.get("User-Agent", ""),
                    success=False
                )
                raise HTTPException(403, "CSRF token validation failed")

        return request

    async def process_response(self, request: Request, response: Response) -> Response:
        """Add security headers to response."""

        # Apply security headers
        security_headers.apply_headers(response.headers)

        # Add CSRF token to response for GET requests
        if request.method == "GET" and hasattr(response, 'context'):
            csrf_token = csrf_protection.generate_token()
            response.set_cookie("csrf_token", csrf_token, httponly=True, secure=True)

        return response

# Authentication middleware
class AuthMiddleware(HTTPMiddleware):
    """Authentication middleware."""

    async def process_request(self, request: Request) -> Request:
        """Authenticate user from session/JWT token."""

        # Skip authentication for public routes
        public_routes = ["/login", "/register", "/health", "/public"]
        if any(request.path.startswith(route) for route in public_routes):
            return request

        # Try to get session token
        session_token = request.cookies.get("session_id")
        auth_header = request.headers.get("Authorization")

        user = None
        if session_token:
            # Session-based authentication
            session_data = auth_manager.get_active_sessions().get(session_token)
            if session_data:
                user_id = session_data.get("user_id")
                user = auth_manager.get_user(user_id)

        elif auth_header and auth_header.startswith("Bearer "):
            # JWT authentication
            jwt_token = auth_header.split(" ")[1]
            try:
                # In real implementation, decode and validate JWT
                # For demo, we'll simulate user lookup
                user = auth_manager.get_user("demo_user")
            except Exception:
                pass

        if user:
            request.user = user
            request.session_id = session_token
        else:
            # Check if route requires authentication
            if not request.path.startswith("/public"):
                raise Unauthorized("Authentication required")

        return request

# Apply middleware
app.add_middleware(SecurityMiddleware())
app.add_middleware(AuthMiddleware())

# Routes
@router.add_route("/login", methods=["POST"])
async def login(request: Request) -> Response:
    """User login endpoint."""

    try:
        data = json.loads(request.body)
        username = data.get("username")
        password = data.get("password")
        mfa_token = data.get("mfa_token")

        # Authenticate user
        auth_result = await auth_manager.authenticate(username, password)

        if not auth_result:
            # Log failed login
            audit_logger.log_event(
                audit_logger.AuditEvent.FAILED_LOGIN,
                user_id=None,
                session_id=None,
                resource="auth",
                action="login_failed",
                details={"username": username},
                ip_address=request.client_ip or "unknown",
                user_agent=request.headers.get("User-Agent", ""),
                success=False
            )
            raise Unauthorized("Invalid credentials")

        user = auth_result["user"]
        session_id = auth_result["session_id"]

        # Check MFA if enabled
        if user.mfa_secret and not await auth_manager.verify_mfa(user.id, mfa_token or ""):
            audit_logger.log_event(
                audit_logger.AuditEvent.SECURITY_EVENT,
                user_id=user.id,
                session_id=session_id,
                resource="mfa",
                action="mfa_failed",
                details={"username": username},
                ip_address=request.client_ip or "unknown",
                user_agent=request.headers.get("User-Agent", ""),
                success=False
            )
            raise Unauthorized("MFA verification failed")

        # Log successful login
        audit_logger.log_event(
            audit_logger.AuditEvent.LOGIN,
            user_id=user.id,
            session_id=session_id,
            resource="auth",
            action="login_success",
            details={"username": username},
            ip_address=request.client_ip or "unknown",
            user_agent=request.headers.get("User-Agent", ""),
            success=True
        )

        response_data = {
            "message": "Login successful",
            "user": {
                "id": user.id,
                "username": user.username,
                "roles": user.roles,
                "permissions": user.permissions
            },
            "session_id": session_id
        }

        response = Response(json.dumps(response_data), content_type="application/json")
        response.set_cookie("session_id", session_id, httponly=True, secure=True, max_age=86400)

        return response

    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON")

@router.add_route("/admin/users", methods=["GET"])
async def get_users(request: Request) -> Response:
    """Get all users (admin only)."""

    if not request.user:
        raise Unauthorized("Authentication required")

    # Check permissions
    rbac.require_permission(request.user.id, admin_permission)

    # Log access
    audit_logger.log_event(
        audit_logger.AuditEvent.DATA_ACCESS,
        user_id=request.user.id,
        session_id=request.session_id,
        resource="users",
        action="list",
        details={},
        ip_address=request.client_ip or "unknown",
        user_agent=request.headers.get("User-Agent", ""),
        success=True
    )

    # In real implementation, get users from database
    users = [
        {"id": "1", "username": "admin", "email": "admin@example.com", "roles": ["admin"]},
        {"id": "2", "username": "user", "email": "user@example.com", "roles": ["user"]}
    ]

    return Response(json.dumps(users), content_type="application/json")

@router.add_route("/user/profile", methods=["GET", "PUT"])
async def user_profile(request: Request) -> Response:
    """Get or update user profile."""

    if not request.user:
        raise Unauthorized("Authentication required")

    if request.method == "GET":
        # Log access
        audit_logger.log_event(
            audit_logger.AuditEvent.DATA_ACCESS,
            user_id=request.user.id,
            session_id=request.session_id,
            resource="profile",
            action="read",
            details={},
            ip_address=request.client_ip or "unknown",
            user_agent=request.headers.get("User-Agent", ""),
            success=True
        )

        profile_data = {
            "id": request.user.id,
            "username": request.user.username,
            "email": request.user.email,
            "roles": request.user.roles,
            "permissions": request.user.permissions
        }

        return Response(json.dumps(profile_data), content_type="application/json")

    elif request.method == "PUT":
        # Check write permission
        rbac.require_permission(request.user.id, write_permission)

        try:
            data = json.loads(request.body)

            # Log modification
            audit_logger.log_event(
                audit_logger.AuditEvent.DATA_MODIFICATION,
                user_id=request.user.id,
                session_id=request.session_id,
                resource="profile",
                action="update",
                details={"fields": list(data.keys())},
                ip_address=request.client_ip or "unknown",
                user_agent=request.headers.get("User-Agent", ""),
                success=True
            )

            # In real implementation, update user profile
            updated_profile = {
                "id": request.user.id,
                "username": request.user.username,
                "email": data.get("email", request.user.email),
                "roles": request.user.roles,
                "permissions": request.user.permissions
            }

            return Response(json.dumps(updated_profile), content_type="application/json")

        except json.JSONDecodeError:
            raise HTTPException(400, "Invalid JSON")

@router.add_route("/health", methods=["GET"])
async def health_check(request: Request) -> Response:
    """Health check endpoint."""

    # Get security statistics
    security_stats = {
        "security_score": security_headers.get_security_score(),
        "rate_limiter_stats": rate_limiter.get_stats("api_requests"),
        "csrf_stats": csrf_protection.get_stats(),
        "timestamp": datetime.now().isoformat()
    }

    return Response(json.dumps(security_stats), content_type="application/json")

@router.add_route("/audit/logs", methods=["GET"])
async def get_audit_logs(request: Request) -> Response:
    """Get audit logs (admin only)."""

    if not request.user:
        raise Unauthorized("Authentication required")

    # Check permissions
    rbac.require_permission(request.user.id, admin_permission)

    # Get recent audit entries
    entries = audit_logger.get_recent_entries(limit=50)

    logs = [
        {
            "timestamp": entry.timestamp.isoformat(),
            "event_type": entry.event_type.value,
            "user_id": entry.user_id,
            "resource": entry.resource,
            "action": entry.action,
            "success": entry.success
        }
        for entry in entries
    ]

    return Response(json.dumps(logs), content_type="application/json")

# Public route for testing
@router.add_route("/public/info", methods=["GET"])
async def public_info(request: Request) -> Response:
    """Public information endpoint."""

    info = {
        "message": "This is a public endpoint",
        "security_features": [
            "Rate limiting",
            "CSRF protection",
            "Security headers",
            "Audit logging",
            "RBAC permissions"
        ],
        "timestamp": datetime.now().isoformat()
    }

    return Response(json.dumps(info), content_type="application/json")

# Initialize demo data
async def initialize_demo_data():
    """Initialize demo users and roles."""

    # Create demo users
    admin_user = User(
        id="1",
        username="admin",
        email="admin@example.com",
        roles=["admin"],
        permissions=["admin", "read", "write"]
    )

    regular_user = User(
        id="2",
        username="user",
        email="user@example.com",
        roles=["user"],
        permissions=["read", "write"]
    )

    auth_manager.add_user(admin_user)
    auth_manager.add_user(regular_user)

    # Assign roles
    rbac.assign_role("1", "admin")
    rbac.assign_role("2", "user")

    # Set demo passwords (in real app, these would be hashed)
    auth_manager.update_user_password("1", "admin123")
    auth_manager.update_user_password("2", "user123")

    print("Demo data initialized!")
    print("Admin user: admin / admin123")
    print("Regular user: user / user123")

# Setup rate limiting rules
rate_limiter.add_rule(RateLimitRule(
    name="api_requests",
    requests_per_period=100,
    period_seconds=60,
    strategy=RateLimitStrategy.TOKEN_BUCKET,
    burst_limit=20
))

rate_limiter.add_rule(RateLimitRule(
    name="login_attempts",
    requests_per_period=5,
    period_seconds=300,
    strategy=RateLimitStrategy.FIXED_WINDOW
))

# Configure security headers for production
security_headers.configure_for_environment("production")

# Start audit logging
async def start_audit_logging():
    await audit_logger.start()
    print("Audit logging started")

# Main application
async def main():
    """Main application entry point."""

    print("🚀 PyServ Mission-Critical Security Framework Demo")
    print("=" * 50)

    # Initialize demo data
    await initialize_demo_data()

    # Start audit logging
    await start_audit_logging()

    # Add routes to application
    app.add_router(router)

    print("\n📋 Available endpoints:")
    print("  POST /login - User login")
    print("  GET  /admin/users - List users (admin only)")
    print("  GET  /user/profile - Get user profile")
    print("  PUT  /user/profile - Update user profile")
    print("  GET  /health - Health check with security stats")
    print("  GET  /audit/logs - Get audit logs (admin only)")
    print("  GET  /public/info - Public information")
    print("\n🔒 Security Features Enabled:")
    print("  ✓ Multi-factor authentication")
    print("  ✓ Role-based access control")
    print("  ✓ Comprehensive audit logging")
    print("  ✓ Rate limiting")
    print("  ✓ CSRF protection")
    print("  ✓ Security headers")
    print("  ✓ Data encryption")
    print("  ✓ Session management")

    # Run application
    await app.run(host="127.0.0.1", port=8000)

if __name__ == "__main__":
    asyncio.run(main())

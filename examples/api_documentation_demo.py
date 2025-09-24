#!/usr/bin/env python3
"""
Pyserv  API Documentation Demo
Demonstrates FastAPI-style API documentation with ReDoc and Swagger UI.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from pyserv.docs import (
    get_api_docs, api_endpoint, APIEndpoint, APISchema
)


# Example API endpoints with documentation
@api_endpoint(
    path="/api/v1/users",
    method="GET",
    summary="List Users",
    description="Retrieve a paginated list of users",
    tags=["users"]
)
def get_users(page: int = 1, limit: int = 10):
    """Get paginated list of users"""
    return {"users": [], "page": page, "limit": limit}


@api_endpoint(
    path="/api/v1/users/{user_id}",
    method="GET",
    summary="Get User",
    description="Retrieve a specific user by ID",
    tags=["users"]
)
def get_user(user_id: int):
    """Get a specific user by ID"""
    return {"user": {"id": user_id, "name": "John Doe"}}


@api_endpoint(
    path="/api/v1/users",
    method="POST",
    summary="Create User",
    description="Create a new user account",
    tags=["users"]
)
def create_user(username: str, email: str, password: str):
    """Create a new user"""
    return {"user": {"username": username, "email": email}, "created": True}


@api_endpoint(
    path="/api/v1/auth/login",
    method="POST",
    summary="User Login",
    description="Authenticate user and return access token",
    tags=["authentication"]
)
def login(username: str, password: str):
    """Authenticate user"""
    return {"access_token": "jwt_token_here", "token_type": "bearer"}


@api_endpoint(
    path="/api/v1/quantum/keypair",
    method="POST",
    summary="Generate Quantum Keypair",
    description="Generate a quantum-resistant cryptographic keypair",
    tags=["quantum"]
)
def generate_quantum_keypair(algorithm: str = "kyber"):
    """Generate quantum-resistant keypair"""
    return {
        "algorithm": algorithm,
        "public_key": "base64_encoded_public_key",
        "private_key": "base64_encoded_private_key"
    }


@api_endpoint(
    path="/api/v1/quantum/authenticate",
    method="POST",
    summary="Quantum Authentication",
    description="Perform quantum-resistant authentication",
    tags=["quantum", "authentication"]
)
def quantum_authenticate(identity: str):
    """Perform quantum authentication"""
    return {
        "identity": identity,
        "authenticated": True,
        "quantum_token": "quantum_auth_token"
    }


@api_endpoint(
    path="/api/v1/system/health",
    method="GET",
    summary="System Health Check",
    description="Check system health and status",
    tags=["system"]
)
def health_check():
    """System health check"""
    return {"status": "healthy", "timestamp": "2025-09-16T23:00:00Z"}


def demo_api_documentation():
    """Demonstrate API documentation generation"""
    print("🚀 Pyserv  API Documentation Demo")
    print("=" * 50)

    # Get the API documentation instance
    docs = get_api_docs(
        title="Pyserv  Quantum-Secure API",
        version="2.0.0",
        description="A quantum-resistant web framework API with advanced security features"
    )

    # Add some custom schemas
    quantum_keypair_schema = APISchema(
        type="object",
        properties={
            "algorithm": {"type": "string", "example": "kyber"},
            "public_key": {"type": "string", "description": "Base64-encoded public key"},
            "private_key": {"type": "string", "description": "Base64-encoded private key"}
        },
        required=["algorithm", "public_key", "private_key"]
    )

    docs.add_schema("QuantumKeypair", quantum_keypair_schema)

    # Add custom security scheme
    docs.add_security_scheme("oauth2", {
        "type": "oauth2",
        "flows": {
            "authorizationCode": {
                "authorizationUrl": "https://example.com/oauth/authorize",
                "tokenUrl": "https://example.com/oauth/token",
                "scopes": {
                    "read": "Read access",
                    "write": "Write access",
                    "admin": "Admin access"
                }
            }
        }
    })

    # Generate OpenAPI specification
    print("\n1. Generating OpenAPI Specification...")
    spec = docs.generate_openapi_spec()

    print(f"   API Title: {spec['info']['title']}")
    print(f"   API Version: {spec['info']['version']}")
    print(f"   Endpoints: {len(spec['paths'])}")
    print(f"   Schemas: {len(spec['components']['schemas'])}")
    print(f"   Security Schemes: {len(spec['components']['securitySchemes'])}")

    # Show some endpoints
    print("\n2. Documented Endpoints:")
    for path, methods in spec['paths'].items():
        for method, details in methods.items():
            print(f"   {method.upper()} {path}")
            print(f"     Summary: {details.get('summary', 'N/A')}")
            print(f"     Tags: {', '.join(details.get('tags', []))}")

    # Generate HTML documentation
    print("\n3. Generating HTML Documentation...")

    # ReDoc
    redoc_html = docs.generate_redoc_html()
    with open("api_docs_redoc.html", "w") as f:
        f.write(redoc_html)
    print("   ✓ ReDoc documentation saved to: api_docs_redoc.html")

    # Swagger UI
    swagger_html = docs.generate_swagger_html()
    with open("api_docs_swagger.html", "w") as f:
        f.write(swagger_html)
    print("   ✓ Swagger UI documentation saved to: api_docs_swagger.html")

    # Save OpenAPI spec as JSON
    import json
    with open("openapi_spec.json", "w") as f:
        json.dump(spec, f, indent=2)
    print("   ✓ OpenAPI specification saved to: openapi_spec.json")

    print("\n4. Key Features Demonstrated:")
    print("   ✅ Automatic endpoint documentation via decorators")
    print("   ✅ Parameter type inference from function signatures")
    print("   ✅ Custom schema definitions")
    print("   ✅ Multiple security schemes (Bearer, API Key, Quantum)")
    print("   ✅ Tag-based endpoint organization")
    print("   ✅ ReDoc and Swagger UI generation")
    print("   ✅ OpenAPI 3.0 specification compliance")

    print("\n5. Security Features:")
    print("   🔐 Bearer token authentication")
    print("   🔑 API key authentication")
    print("   🔒 Quantum-resistant authentication")
    print("   🔑 OAuth2 support")
    print("   🏷️  Endpoint tagging and organization")

    print("\n6. Usage Instructions:")
    print("   📖 Open api_docs_redoc.html in your browser for ReDoc documentation")
    print("   📖 Open api_docs_swagger.html in your browser for Swagger UI")
    print("   📄 Check openapi_spec.json for the raw OpenAPI specification")

    print("\n7. Integration with Pyserv :")
    print("   • Add @api_endpoint decorators to your route handlers")
    print("   • Use get_api_docs() to access the global documentation instance")
    print("   • Generate documentation automatically or on-demand")
    print("   • Serve documentation at /docs (ReDoc) and /docs/swagger (Swagger UI)")

    return spec


def demo_manual_endpoint_addition():
    """Demonstrate manual endpoint addition"""
    print("\n📝 Manual Endpoint Addition Demo")
    print("=" * 40)

    docs = get_api_docs()

    # Manually add an endpoint
    endpoint = APIEndpoint(
        path="/api/v1/admin/system-info",
        method="GET",
        summary="Get System Information",
        description="Retrieve detailed system information (admin only)",
        tags=["system", "admin"],
        security=[{"bearerAuth": ["admin"]}],
        responses={
            "200": {
                "description": "System information retrieved successfully",
                "content": {
                    "application/json": {
                        "schema": {
                            "$ref": "#/components/schemas/SystemInfo"
                        }
                    }
                }
            },
            "403": {
                "description": "Forbidden - Admin access required",
                "content": {
                    "application/json": {
                        "schema": {
                            "$ref": "#/components/schemas/Error"
                        }
                    }
                }
            }
        }
    )

    docs.add_endpoint(endpoint)

    # Add a custom schema for the response
    system_info_schema = APISchema(
        type="object",
        properties={
            "cpu_usage": {"type": "number", "example": 45.2},
            "memory_usage": {"type": "number", "example": 67.8},
            "disk_usage": {"type": "number", "example": 23.1},
            "uptime": {"type": "integer", "example": 3600},
            "active_connections": {"type": "integer", "example": 150}
        },
        required=["cpu_usage", "memory_usage", "disk_usage"]
    )

    docs.add_schema("SystemInfo", system_info_schema)

    print("   ✓ Manually added admin endpoint with custom schema")
    print("   ✓ Added security requirements (admin role)")
    print("   ✓ Defined detailed response schemas")


if __name__ == "__main__":
    try:
        # Run the main demo
        spec = demo_api_documentation()

        # Run the manual addition demo
        demo_manual_endpoint_addition()

        print("\n" + "=" * 60)
        print("🎉 API Documentation Demo Complete!")
        print("📁 Generated files:")
        print("   • api_docs_redoc.html - ReDoc documentation")
        print("   • api_docs_swagger.html - Swagger UI documentation")
        print("   • openapi_spec.json - OpenAPI specification")
        print("\n🔗 Open the HTML files in your browser to explore the documentation!")

    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()





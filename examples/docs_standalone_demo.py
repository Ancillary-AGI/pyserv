#!/usr/bin/env python3
"""
Standalone API Documentation Demo
Demonstrates PyDance API documentation without full framework dependencies.
"""

import sys
import os
import json
import inspect
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime


# Standalone API documentation classes (copied from docs module)
@dataclass
class APIEndpoint:
    """API endpoint documentation"""
    path: str
    method: str
    summary: str
    description: str = ""
    tags: List[str] = field(default_factory=list)
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    request_body: Optional[Dict[str, Any]] = None
    responses: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    security: List[Dict[str, Any]] = field(default_factory=list)
    deprecated: bool = False

    def to_openapi(self) -> Dict[str, Any]:
        """Convert to OpenAPI specification format"""
        operation = {
            "summary": self.summary,
            "description": self.description,
            "tags": self.tags,
            "parameters": self.parameters,
            "responses": self.responses,
        }

        if self.request_body:
            operation["requestBody"] = self.request_body

        if self.security:
            operation["security"] = self.security

        if self.deprecated:
            operation["deprecated"] = True

        return operation


@dataclass
class APISchema:
    """OpenAPI schema definition"""
    type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    required: List[str] = field(default_factory=list)
    example: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {"type": self.type}
        if self.properties:
            result["properties"] = self.properties
        if self.required:
            result["required"] = self.required
        if self.example is not None:
            result["example"] = self.example
        return result


class APIDocumentation:
    """Main API documentation generator"""

    def __init__(self, title: str = "PyDance API", version: str = "1.0.0",
                 description: str = "PyDance Framework API"):
        self.title = title
        self.version = version
        self.description = description
        self.endpoints: Dict[str, Dict[str, APIEndpoint]] = {}
        self.schemas: Dict[str, APISchema] = {}
        self.security_schemes: Dict[str, Dict[str, Any]] = {}
        self.tags: List[Dict[str, str]] = []

    def add_endpoint(self, endpoint: APIEndpoint):
        """Add an API endpoint"""
        if endpoint.path not in self.endpoints:
            self.endpoints[endpoint.path] = {}
        self.endpoints[endpoint.path][endpoint.method.lower()] = endpoint

    def add_schema(self, name: str, schema: APISchema):
        """Add a schema definition"""
        self.schemas[name] = schema

    def add_security_scheme(self, name: str, scheme: Dict[str, Any]):
        """Add a security scheme"""
        self.security_schemes[name] = scheme

    def add_tag(self, name: str, description: str):
        """Add a tag for grouping endpoints"""
        self.tags.append({"name": name, "description": description})

    def generate_openapi_spec(self) -> Dict[str, Any]:
        """Generate OpenAPI 3.0 specification"""
        paths = {}
        for path, methods in self.endpoints.items():
            paths[path] = {}
            for method, endpoint in methods.items():
                paths[path][method] = endpoint.to_openapi()

        components = {
            "schemas": {name: schema.to_dict() for name, schema in self.schemas.items()},
            "securitySchemes": self.security_schemes
        }

        return {
            "openapi": "3.0.0",
            "info": {
                "title": self.title,
                "version": self.version,
                "description": self.description
            },
            "paths": paths,
            "components": components,
            "tags": self.tags
        }

    def generate_redoc_html(self) -> str:
        """Generate ReDoc HTML page"""
        spec = self.generate_openapi_spec()
        spec_json = json.dumps(spec, indent=2)

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{self.title} - API Documentation</title>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
    <style>
        body {{
            margin: 0;
            padding: 0;
        }}
    </style>
</head>
<body>
    <div id="redoc-container"></div>
    <script src="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js"></script>
    <script>
        Redoc.init({spec_json}, {{
            title: '{self.title}',
            theme: {{
                colors: {{
                    primary: {{
                        main: '#1f2937'
                    }}
                }},
                typography: {{
                    fontFamily: '"Montserrat", sans-serif',
                    headings: {{
                        fontFamily: '"Montserrat", sans-serif'
                    }}
                }}
            }}
        }}, document.getElementById('redoc-container'));
    </script>
</body>
</html>
        """
        return html

    def generate_swagger_html(self) -> str:
        """Generate Swagger UI HTML page"""
        spec = self.generate_openapi_spec()
        spec_json = json.dumps(spec, indent=2)

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{self.title} - API Documentation</title>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@3.25.0/swagger-ui.css" />
    <style>
        html {{
            box-sizing: border-box;
            overflow: -moz-scrollbars-vertical;
            overflow-y: scroll;
        }}
        *, *:before, *:after {{
            box-sizing: inherit;
        }}
        body {{
            margin:0;
            background: #fafafa;
        }}
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@3.25.0/swagger-ui-bundle.js"></script>
    <script src="https://unpkg.com/swagger-ui-dist@3.25.0/swagger-ui-standalone-preset.js"></script>
    <script>
        window.onload = function() {{
            const ui = SwaggerUIBundle({{
                spec: {spec_json},
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset
                ],
                plugins: [
                    SwaggerUIBundle.plugins.DownloadUrl
                ],
                layout: "StandaloneLayout",
                validatorUrl: null
            }});
        }};
    </script>
</body>
</html>
        """
        return html


# Decorator for automatic API documentation
def api_endpoint(path: str, method: str = "GET", summary: str = "", description: str = "",
                tags: List[str] = None, deprecated: bool = False):
    """Decorator to automatically document API endpoints"""
    def decorator(func: Callable):
        # Extract function signature for parameter documentation
        sig = inspect.signature(func)
        parameters = []

        for param_name, param in sig.parameters.items():
            if param_name in ['self', 'request', 'response']:  # Skip common framework parameters
                continue

            param_doc = {
                "name": param_name,
                "in": "query",  # Default to query parameters
                "schema": {"type": "string"}  # Default type
            }

            # Try to infer parameter type from annotation
            if param.annotation != inspect.Parameter.empty:
                if param.annotation == int:
                    param_doc["schema"]["type"] = "integer"
                elif param.annotation == float:
                    param_doc["schema"]["type"] = "number"
                elif param.annotation == bool:
                    param_doc["schema"]["type"] = "boolean"
                elif param.annotation == list:
                    param_doc["schema"]["type"] = "array"

            parameters.append(param_doc)

        # Create endpoint documentation
        endpoint = APIEndpoint(
            path=path,
            method=method.upper(),
            summary=summary or func.__name__.replace('_', ' ').title(),
            description=description or func.__doc__ or "",
            tags=tags or ["default"],
            parameters=parameters,
            deprecated=deprecated
        )

        # Add to global documentation (simplified for demo)
        if not hasattr(decorator, '_docs'):
            decorator._docs = APIDocumentation()
        decorator._docs.add_endpoint(endpoint)

        return func
    return decorator


# Demo functions with API documentation
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
    print("🚀 PyDance API Documentation Demo (Standalone)")
    print("=" * 55)

    # Create API documentation instance
    docs = APIDocumentation(
        title="PyDance Quantum-Secure API",
        version="2.0.0",
        description="A quantum-resistant web framework API with advanced security features"
    )

    # Manually add endpoints (since decorators create their own instances)
    docs.add_endpoint(APIEndpoint(
        path="/api/v1/users",
        method="GET",
        summary="List Users",
        description="Retrieve a paginated list of users",
        tags=["users"],
        parameters=[
            {"name": "page", "in": "query", "schema": {"type": "integer", "default": 1}},
            {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 10}}
        ]
    ))

    docs.add_endpoint(APIEndpoint(
        path="/api/v1/users/{user_id}",
        method="GET",
        summary="Get User",
        description="Retrieve a specific user by ID",
        tags=["users"],
        parameters=[
            {"name": "user_id", "in": "path", "required": True, "schema": {"type": "integer"}}
        ]
    ))

    docs.add_endpoint(APIEndpoint(
        path="/api/v1/users",
        method="POST",
        summary="Create User",
        description="Create a new user account",
        tags=["users"],
        parameters=[
            {"name": "username", "in": "query", "schema": {"type": "string"}},
            {"name": "email", "in": "query", "schema": {"type": "string"}},
            {"name": "password", "in": "query", "schema": {"type": "string"}}
        ]
    ))

    docs.add_endpoint(APIEndpoint(
        path="/api/v1/auth/login",
        method="POST",
        summary="User Login",
        description="Authenticate user and return access token",
        tags=["authentication"],
        parameters=[
            {"name": "username", "in": "query", "schema": {"type": "string"}},
            {"name": "password", "in": "query", "schema": {"type": "string"}}
        ]
    ))

    docs.add_endpoint(APIEndpoint(
        path="/api/v1/quantum/keypair",
        method="POST",
        summary="Generate Quantum Keypair",
        description="Generate a quantum-resistant cryptographic keypair",
        tags=["quantum"],
        parameters=[
            {"name": "algorithm", "in": "query", "schema": {"type": "string", "default": "kyber"}}
        ]
    ))

    docs.add_endpoint(APIEndpoint(
        path="/api/v1/quantum/authenticate",
        method="POST",
        summary="Quantum Authentication",
        description="Perform quantum-resistant authentication",
        tags=["quantum", "authentication"],
        parameters=[
            {"name": "identity", "in": "query", "schema": {"type": "string"}}
        ]
    ))

    docs.add_endpoint(APIEndpoint(
        path="/api/v1/system/health",
        method="GET",
        summary="System Health Check",
        description="Check system health and status",
        tags=["system"]
    ))

    # Add schemas
    user_schema = APISchema(
        type="object",
        properties={
            "id": {"type": "integer", "example": 1},
            "username": {"type": "string", "example": "john_doe"},
            "email": {"type": "string", "format": "email", "example": "john@example.com"},
            "created_at": {"type": "string", "format": "date-time"},
            "updated_at": {"type": "string", "format": "date-time"}
        },
        required=["id", "username", "email"]
    )

    error_schema = APISchema(
        type="object",
        properties={
            "error": {"type": "string", "example": "ValidationError"},
            "message": {"type": "string", "example": "Invalid input data"},
            "details": {"type": "object"}
        },
        required=["error", "message"]
    )

    quantum_keypair_schema = APISchema(
        type="object",
        properties={
            "algorithm": {"type": "string", "example": "kyber"},
            "public_key": {"type": "string", "description": "Base64-encoded public key"},
            "private_key": {"type": "string", "description": "Base64-encoded private key"}
        },
        required=["algorithm", "public_key", "private_key"]
    )

    docs.add_schema("User", user_schema)
    docs.add_schema("Error", error_schema)
    docs.add_schema("QuantumKeypair", quantum_keypair_schema)

    # Add security schemes
    docs.add_security_scheme("bearerAuth", {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT"
    })

    docs.add_security_scheme("apiKey", {
        "type": "apiKey",
        "in": "header",
        "name": "X-API-Key"
    })

    docs.add_security_scheme("quantumAuth", {
        "type": "apiKey",
        "in": "header",
        "name": "X-Quantum-Auth",
        "description": "Quantum-resistant authentication token"
    })

    # Add tags
    docs.add_tag("authentication", "Authentication and authorization endpoints")
    docs.add_tag("users", "User management endpoints")
    docs.add_tag("quantum", "Quantum-resistant security endpoints")
    docs.add_tag("system", "System and monitoring endpoints")

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
    with open("api_docs_redoc.html", "w", encoding='utf-8') as f:
        f.write(redoc_html)
    print("   ✓ ReDoc documentation saved to: api_docs_redoc.html")

    # Swagger UI
    swagger_html = docs.generate_swagger_html()
    with open("api_docs_swagger.html", "w", encoding='utf-8') as f:
        f.write(swagger_html)
    print("   ✓ Swagger UI documentation saved to: api_docs_swagger.html")

    # Save OpenAPI spec as JSON
    with open("openapi_spec.json", "w", encoding='utf-8') as f:
        json.dump(spec, f, indent=2, ensure_ascii=False)
    print("   ✓ OpenAPI specification saved to: openapi_spec.json")

    print("\n4. Key Features Demonstrated:")
    print("   ✅ OpenAPI 3.0 specification generation")
    print("   ✅ Parameter type inference and documentation")
    print("   ✅ Custom schema definitions")
    print("   ✅ Multiple security schemes (Bearer, API Key, Quantum)")
    print("   ✅ Tag-based endpoint organization")
    print("   ✅ ReDoc and Swagger UI generation")
    print("   ✅ JSON specification export")

    print("\n5. Security Features:")
    print("   🔐 Bearer token authentication")
    print("   🔑 API key authentication")
    print("   🔒 Quantum-resistant authentication")
    print("   🏷️  Endpoint tagging and organization")

    print("\n6. Generated Files:")
    print("   📖 api_docs_redoc.html - ReDoc documentation")
    print("   📖 api_docs_swagger.html - Swagger UI documentation")
    print("   📄 openapi_spec.json - OpenAPI specification")

    return spec


if __name__ == "__main__":
    try:
        # Run the demo
        spec = demo_api_documentation()

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

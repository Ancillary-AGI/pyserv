"""
PyDance API Documentation Module
Provides FastAPI-style API documentation with ReDoc support.
"""

from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import json
import inspect


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


# Global API documentation instance
_api_docs = None

def get_api_docs(title: str = "PyDance API", version: str = "1.0.0") -> APIDocumentation:
    """Get global API documentation instance"""
    global _api_docs
    if _api_docs is None:
        _api_docs = APIDocumentation(title=title, version=version)
    return _api_docs


# Decorators for automatic API documentation
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

        # Add to global documentation
        docs = get_api_docs()
        docs.add_endpoint(endpoint)

        return func
    return decorator


def api_response(status_code: str, description: str, schema: Optional[Dict[str, Any]] = None):
    """Decorator to document API responses"""
    def decorator(func: Callable):
        # This would modify the endpoint's response documentation
        # Implementation depends on how endpoints are registered
        return func
    return decorator


# Utility functions for common schemas
def create_user_schema() -> APISchema:
    """Create a standard user schema"""
    return APISchema(
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


def create_error_schema() -> APISchema:
    """Create a standard error response schema"""
    return APISchema(
        type="object",
        properties={
            "error": {"type": "string", "example": "ValidationError"},
            "message": {"type": "string", "example": "Invalid input data"},
            "details": {"type": "object"}
        },
        required=["error", "message"]
    )


# Initialize default schemas and security schemes
def initialize_default_docs():
    """Initialize default API documentation"""
    docs = get_api_docs()

    # Add common schemas
    docs.add_schema("User", create_user_schema())
    docs.add_schema("Error", create_error_schema())

    # Add common security schemes
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

    # Add common tags
    docs.add_tag("authentication", "Authentication and authorization endpoints")
    docs.add_tag("users", "User management endpoints")
    docs.add_tag("quantum", "Quantum-resistant security endpoints")
    docs.add_tag("system", "System and monitoring endpoints")


# Initialize on import
initialize_default_docs()

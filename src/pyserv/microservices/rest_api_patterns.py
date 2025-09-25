"""
Enhanced API design patterns for Pyserv  framework.

This module provides:
- HATEOAS (Hypermedia as the Engine of Application State)
- Rate limiting with token bucket algorithm
- Standardized API responses
- API error handling
- Pagination support
"""

import json
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


from pyserv.rate_limiting import RateLimiter, RateLimitConfig, RateLimitAlgorithm
from pyserv.pagination import PaginationParams, Paginator, PaginationResult
from pyserv.exceptions import APIError


class HttpMethod(Enum):
    """HTTP methods enumeration"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


@dataclass
class Link:
    """
    HATEOAS link representation.

    Links provide navigation and action discovery in REST APIs,
    following the HATEOAS principle.
    """
    href: str
    rel: str
    method: HttpMethod = HttpMethod.GET
    type: str = "application/json"
    title: Optional[str] = None
    templated: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert link to dictionary representation"""
        result = {
            "href": self.href,
            "rel": self.rel,
            "method": self.method.value,
            "type": self.type
        }

        if self.title:
            result["title"] = self.title

        if self.templated:
            result["templated"] = True

        return result


class APIResponse:
    """
    Standardized API response with HATEOAS links.

    This class provides a consistent response format across all API endpoints,
    including support for HATEOAS links, metadata, and versioning.
    """

    def __init__(self,
                 data: Any = None,
                 status: int = 200,
                 message: str = "Success",
                 links: Optional[List[Link]] = None,
                 meta: Optional[Dict[str, Any]] = None):
        self.data = data
        self.status = status
        self.message = message
        self.links = links or []
        self.meta = meta or {}
        self.timestamp = datetime.now()
        self.api_version = "v1"
        self.request_id = self._generate_request_id()

    def _generate_request_id(self) -> str:
        """Generate unique request ID"""
        return f"req_{int(time.time() * 1000000)}"

    def add_link(self, link: Link) -> None:
        """Add a HATEOAS link to the response"""
        self.links.append(link)

    def add_links(self, links: List[Link]) -> None:
        """Add multiple HATEOAS links to the response"""
        self.links.extend(links)

    def set_meta(self, key: str, value: Any) -> None:
        """Set metadata key-value pair"""
        self.meta[key] = value

    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary"""
        response = {
            "status": self.status,
            "message": self.message,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "api_version": self.api_version,
            "request_id": self.request_id
        }

        if self.links:
            response["_links"] = {link.rel: link.to_dict() for link in self.links}

        if self.meta:
            response["_meta"] = self.meta

        return response

    def to_json(self) -> str:
        """Convert response to JSON string"""
        return json.dumps(self.to_dict(), default=str, indent=2)

    @classmethod
    def success(cls, data: Any = None, message: str = "Success", links: Optional[List[Link]] = None) -> 'APIResponse':
        """Create a success response"""
        return cls(data=data, status=200, message=message, links=links)

    @classmethod
    def created(cls, data: Any = None, message: str = "Created", links: Optional[List[Link]] = None) -> 'APIResponse':
        """Create a resource created response"""
        return cls(data=data, status=201, message=message, links=links)

    @classmethod
    def no_content(cls, message: str = "No Content") -> 'APIResponse':
        """Create a no content response"""
        return cls(data=None, status=204, message=message)

    @classmethod
    def paginated(cls,
                  items: List[Any],
                  total: int,
                  page: int,
                  per_page: int,
                  links: Optional[List[Link]] = None) -> 'APIResponse':
        """Create a paginated response"""
        response = cls(
            data={
                "items": items,
                "pagination": {
                    "total": total,
                    "page": page,
                    "per_page": per_page,
                    "total_pages": (total + per_page - 1) // per_page
                }
            },
            status=200,
            message="Success",
            links=links
        )

        # Add pagination metadata
        response.set_meta("pagination", {
            "total": total,
            "page": page,
            "per_page": per_page,
            "has_next": page * per_page < total,
            "has_prev": page > 1
        })

        return response





class APIResource(ABC):
    """
    Base class for API resources.

    This abstract class provides a foundation for implementing RESTful API resources
    with built-in support for CRUD operations, HATEOAS links, and rate limiting.
    """

    def __init__(self, rate_limiter: Optional[RateLimiter] = None):
        self.rate_limiter = rate_limiter

    @abstractmethod
    async def get_collection(self, request: Any, pagination: PaginationParams) -> APIResponse:
        """Get collection of resources"""
        pass

    @abstractmethod
    async def get_resource(self, request: Any, resource_id: str) -> APIResponse:
        """Get single resource"""
        pass

    @abstractmethod
    async def create_resource(self, request: Any, data: Dict[str, Any]) -> APIResponse:
        """Create new resource"""
        pass

    @abstractmethod
    async def update_resource(self, request: Any, resource_id: str, data: Dict[str, Any]) -> APIResponse:
        """Update existing resource"""
        pass

    @abstractmethod
    async def delete_resource(self, request: Any, resource_id: str) -> APIResponse:
        """Delete resource"""
        pass

    async def check_rate_limit(self, request: Any) -> None:
        """Check rate limit for the request"""
        if self.rate_limiter:
            if not await self.rate_limiter.acquire():
                raise APIError(
                    "Rate limit exceeded",
                    status=429,
                    error_code="rate_limit_exceeded"
                )

    def get_resource_links(self, resource_id: str, base_url: str) -> List[Link]:
        """Get HATEOAS links for a resource"""
        return [
            Link(
                href=f"{base_url}/{resource_id}",
                rel="self",
                method=HttpMethod.GET,
                title="Get resource"
            ),
            Link(
                href=f"{base_url}/{resource_id}",
                rel="edit",
                method=HttpMethod.PUT,
                title="Update resource"
            ),
            Link(
                href=f"{base_url}/{resource_id}",
                rel="delete",
                method=HttpMethod.DELETE,
                title="Delete resource"
            ),
            Link(
                href=base_url,
                rel="collection",
                method=HttpMethod.GET,
                title="Get collection"
            )
        ]

    def get_collection_links(self, base_url: str) -> List[Link]:
        """Get HATEOAS links for a collection"""
        return [
            Link(
                href=base_url,
                rel="self",
                method=HttpMethod.GET,
                title="Get collection"
            ),
            Link(
                href=base_url,
                rel="create",
                method=HttpMethod.POST,
                title="Create resource"
            )
        ]

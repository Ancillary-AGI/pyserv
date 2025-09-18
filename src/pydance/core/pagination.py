"""
Unified Pagination Module for PyDance Framework.

This module provides a consolidated, production-ready pagination implementation
with support for multiple pagination strategies, HATEOAS links, and metadata.
"""

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Union, TypeVar, Generic, Callable
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class PaginationParams:
    """Parameters for pagination requests"""
    page: int = 1
    per_page: int = 20
    sort_by: Optional[str] = None
    sort_order: str = "asc"
    filters: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate pagination parameters"""
        if self.page < 1:
            self.page = 1
        if self.per_page < 1:
            self.per_page = 20
        if self.per_page > 1000:  # Reasonable upper limit
            self.per_page = 1000
        if self.sort_order not in ["asc", "desc"]:
            self.sort_order = "asc"

    @classmethod
    def from_request(cls, request: Any) -> 'PaginationParams':
        """Create pagination params from request object"""
        params = cls()

        # Extract from query parameters
        if hasattr(request, 'query_params'):
            query_params = request.query_params
        elif hasattr(request, 'args'):
            query_params = request.args
        else:
            query_params = {}

        # Handle both dict and multi-dict formats
        def get_param(key: str, default=None):
            if isinstance(query_params, dict):
                return query_params.get(key, default)
            else:
                return query_params.get(key, [default])[0] if query_params.get(key) else default

        params.page = int(get_param('page', 1))
        params.per_page = int(get_param('per_page', 20))
        params.sort_by = get_param('sort_by')
        params.sort_order = get_param('sort_order', 'asc')

        # Extract filters (all other parameters)
        filter_keys = ['page', 'per_page', 'sort_by', 'sort_order']
        for key, value in query_params.items():
            if key not in filter_keys:
                if isinstance(query_params, dict):
                    params.filters[key] = value
                else:
                    params.filters[key] = value[0] if isinstance(value, list) else value

        return params

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            "page": self.page,
            "per_page": self.per_page,
        }
        if self.sort_by:
            result["sort_by"] = self.sort_by
            result["sort_order"] = self.sort_order
        if self.filters:
            result.update(self.filters)
        return result


@dataclass
class PaginationMetadata:
    """Metadata for paginated responses"""
    total: int
    page: int
    per_page: int
    total_pages: int
    has_next: bool
    has_prev: bool
    next_page: Optional[int]
    prev_page: Optional[int]
    start_index: int
    end_index: int

    @classmethod
    def calculate(cls, total: int, page: int, per_page: int) -> 'PaginationMetadata':
        """Calculate pagination metadata"""
        total_pages = math.ceil(total / per_page) if per_page > 0 else 1
        has_next = page < total_pages
        has_prev = page > 1
        next_page = page + 1 if has_next else None
        prev_page = page - 1 if has_prev else None

        start_index = (page - 1) * per_page
        end_index = min(start_index + per_page, total)

        return cls(
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
            has_next=has_next,
            has_prev=has_prev,
            next_page=next_page,
            prev_page=prev_page,
            start_index=start_index,
            end_index=end_index
        )


@dataclass
class PaginationLink:
    """HATEOAS link for pagination"""
    href: str
    rel: str
    method: str = "GET"
    title: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            "href": self.href,
            "rel": self.rel,
            "method": self.method
        }
        if self.title:
            result["title"] = self.title
        return result


class BasePaginator(ABC, Generic[T]):
    """Abstract base class for paginators"""

    def __init__(self, params: PaginationParams):
        self.params = params

    @abstractmethod
    def paginate(self, queryset: Any, request: Any = None) -> 'PaginationResult[T]':
        """Paginate the queryset"""
        pass

    def get_pagination_links(self, base_url: str, metadata: PaginationMetadata) -> List[PaginationLink]:
        """Generate HATEOAS pagination links"""
        links = []
        params = self.params

        # Self link
        query_params = params.to_dict()
        links.append(PaginationLink(
            href=self._build_url(base_url, query_params),
            rel="self",
            title="Current page"
        ))

        # First page
        if params.page > 1:
            first_params = params.to_dict()
            first_params['page'] = 1
            links.append(PaginationLink(
                href=self._build_url(base_url, first_params),
                rel="first",
                title="First page"
            ))

        # Previous page
        if metadata.has_prev:
            prev_params = params.to_dict()
            prev_params['page'] = metadata.prev_page
            links.append(PaginationLink(
                href=self._build_url(base_url, prev_params),
                rel="prev",
                title="Previous page"
            ))

        # Next page
        if metadata.has_next:
            next_params = params.to_dict()
            next_params['page'] = metadata.next_page
            links.append(PaginationLink(
                href=self._build_url(base_url, next_params),
                rel="next",
                title="Next page"
            ))

        # Last page
        if params.page < metadata.total_pages:
            last_params = params.to_dict()
            last_params['page'] = metadata.total_pages
            links.append(PaginationLink(
                href=self._build_url(base_url, last_params),
                rel="last",
                title="Last page"
            ))

        return links

    def _build_url(self, base_url: str, params: Dict[str, Any]) -> str:
        """Build URL with query parameters"""
        parsed = urlparse(base_url)
        query_dict = parse_qs(parsed.query)
        query_dict.update({k: [str(v)] for k, v in params.items() if v is not None})

        # Remove empty values
        query_dict = {k: v for k, v in query_dict.items() if v and v != ['']}

        new_query = urlencode(query_dict, doseq=True)
        return urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment
        ))


@dataclass
class PaginationResult(Generic[T]):
    """Result of pagination operation"""
    items: List[T]
    metadata: PaginationMetadata
    links: List[PaginationLink] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        result = {
            "items": [item.to_dict() if hasattr(item, 'to_dict') else item for item in self.items],
            "pagination": {
                "total": self.metadata.total,
                "page": self.metadata.page,
                "per_page": self.metadata.per_page,
                "total_pages": self.metadata.total_pages,
                "has_next": self.metadata.has_next,
                "has_prev": self.metadata.has_prev,
                "next_page": self.metadata.next_page,
                "prev_page": self.metadata.prev_page,
                "start_index": self.metadata.start_index,
                "end_index": self.metadata.end_index
            }
        }

        if self.links:
            result["_links"] = {link.rel: link.to_dict() for link in self.links}

        return result


class PageNumberPaginator(BasePaginator[T]):
    """Page number-based pagination"""

    def paginate(self, queryset: Any, request: Any = None) -> PaginationResult[T]:
        """Paginate using page numbers"""
        # Convert queryset to list if needed
        if hasattr(queryset, 'all'):
            items = list(queryset.all())
        elif hasattr(queryset, '__iter__'):
            items = list(queryset)
        else:
            items = queryset if isinstance(queryset, list) else [queryset]

        total = len(items)
        metadata = PaginationMetadata.calculate(total, self.params.page, self.params.per_page)

        # Slice the items
        start = metadata.start_index
        end = metadata.end_index
        paginated_items = items[start:end]

        # Apply sorting if specified
        if self.params.sort_by:
            reverse = self.params.sort_order == "desc"
            try:
                paginated_items.sort(key=lambda x: getattr(x, self.params.sort_by), reverse=reverse)
            except (AttributeError, TypeError):
                logger.warning(f"Could not sort by {self.params.sort_by}")

        result = PaginationResult(
            items=paginated_items,
            metadata=metadata
        )

        # Add links if request provided
        if request and hasattr(request, 'url'):
            base_url = str(request.url)
            result.links = self.get_pagination_links(base_url, metadata)

        return result


class LimitOffsetPaginator(BasePaginator[T]):
    """Limit/offset-based pagination"""

    def __init__(self, params: PaginationParams):
        super().__init__(params)
        # Convert page-based params to limit/offset
        self.limit = params.per_page
        self.offset = (params.page - 1) * params.per_page

    def paginate(self, queryset: Any, request: Any = None) -> PaginationResult[T]:
        """Paginate using limit/offset"""
        # Convert queryset to list if needed
        if hasattr(queryset, 'all'):
            items = list(queryset.all())
        elif hasattr(queryset, '__iter__'):
            items = list(queryset)
        else:
            items = queryset if isinstance(queryset, list) else [queryset]

        total = len(items)

        # Apply limit/offset
        start = self.offset
        end = start + self.limit
        paginated_items = items[start:end]

        # Calculate metadata
        page = (self.offset // self.limit) + 1
        metadata = PaginationMetadata.calculate(total, page, self.limit)

        result = PaginationResult(
            items=paginated_items,
            metadata=metadata
        )

        # Add links if request provided
        if request and hasattr(request, 'url'):
            base_url = str(request.url)
            result.links = self.get_pagination_links(base_url, metadata)

        return result


class CursorPaginator(BasePaginator[T]):
    """Cursor-based pagination for better performance"""

    def __init__(self, params: PaginationParams, cursor_field: str = 'id'):
        super().__init__(params)
        self.cursor_field = cursor_field
        self.cursor = params.filters.get('cursor')
        self.direction = params.filters.get('direction', 'next')  # 'next' or 'prev'

    def paginate(self, queryset: Any, request: Any = None) -> PaginationResult[T]:
        """Paginate using cursor"""
        # This is a simplified implementation
        # In production, this would need database-specific cursor queries

        if hasattr(queryset, 'all'):
            items = list(queryset.all())
        elif hasattr(queryset, '__iter__'):
            items = list(queryset)
        else:
            items = queryset if isinstance(queryset, list) else [queryset]

        # Apply cursor-based filtering (simplified)
        if self.cursor:
            try:
                cursor_value = int(self.cursor)
                if self.direction == 'next':
                    items = [item for item in items if getattr(item, self.cursor_field, 0) > cursor_value]
                else:
                    items = [item for item in items if getattr(item, self.cursor_field, 0) < cursor_value]
                    items.reverse()  # Reverse for previous page
            except (ValueError, AttributeError):
                pass

        # Apply limit
        paginated_items = items[:self.params.per_page]
        total = len(items)  # This is approximate for cursor pagination

        # Create metadata (simplified for cursor pagination)
        metadata = PaginationMetadata(
            total=total,
            page=1,  # Not meaningful for cursor pagination
            per_page=self.params.per_page,
            total_pages=1,  # Not meaningful for cursor pagination
            has_next=len(paginated_items) == self.params.per_page,
            has_prev=bool(self.cursor and self.direction == 'prev'),
            next_page=None,
            prev_page=None,
            start_index=0,
            end_index=len(paginated_items)
        )

        result = PaginationResult(
            items=paginated_items,
            metadata=metadata
        )

        # Add cursor links
        if request and hasattr(request, 'url'):
            result.links = self._get_cursor_links(str(request.url), paginated_items)

        return result

    def _get_cursor_links(self, base_url: str, items: List[T]) -> List[PaginationLink]:
        """Generate cursor-based pagination links"""
        links = []

        if items:
            # Next cursor
            last_item = items[-1]
            if hasattr(last_item, self.cursor_field):
                next_cursor = getattr(last_item, self.cursor_field)
                next_params = self.params.to_dict()
                next_params['cursor'] = str(next_cursor)
                next_params['direction'] = 'next'
                links.append(PaginationLink(
                    href=self._build_url(base_url, next_params),
                    rel="next",
                    title="Next page"
                ))

        # Previous cursor (if we have a cursor)
        if self.cursor and self.direction == 'next':
            prev_params = self.params.to_dict()
            prev_params['cursor'] = self.cursor
            prev_params['direction'] = 'prev'
            links.append(PaginationLink(
                href=self._build_url(base_url, prev_params),
                rel="prev",
                title="Previous page"
            ))

        return links


class PaginatorFactory:
    """Factory for creating paginators"""

    @staticmethod
    def create_paginator(pagination_type: str = "page_number",
                        params: Optional[PaginationParams] = None) -> BasePaginator:
        """Create a paginator instance"""
        if params is None:
            params = PaginationParams()

        if pagination_type == "page_number":
            return PageNumberPaginator(params)
        elif pagination_type == "limit_offset":
            return LimitOffsetPaginator(params)
        elif pagination_type == "cursor":
            return CursorPaginator(params)
        else:
            raise ValueError(f"Unknown pagination type: {pagination_type}")


# Convenience functions
def paginate(queryset: Any,
            request: Any = None,
            pagination_type: str = "page_number",
            params: Optional[PaginationParams] = None) -> PaginationResult:
    """Convenience function for pagination"""
    if params is None and request:
        params = PaginationParams.from_request(request)

    paginator = PaginatorFactory.create_paginator(pagination_type, params)
    return paginator.paginate(queryset, request)


# Default instances
default_paginator = PageNumberPaginator(PaginationParams())

__all__ = [
    'PaginationParams',
    'PaginationMetadata',
    'PaginationLink',
    'BasePaginator',
    'PaginationResult',
    'PageNumberPaginator',
    'LimitOffsetPaginator',
    'CursorPaginator',
    'PaginatorFactory',
    'paginate',
    'default_paginator'
]

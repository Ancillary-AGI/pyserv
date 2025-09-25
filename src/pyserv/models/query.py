"""
Query builder for database operations.
"""

import json
from bson import ObjectId
from pymongo import ASCENDING, DESCENDING
from typing import Dict, List, Optional, Any, Tuple, Union, Type, TypeVar, Generic
from pydantic import BaseModel as PydanticBaseModel, create_model, validator
from datetime import datetime
import asyncio
from contextlib import asynccontextmanager
import math
import inspect

from pyserv.database.database_pool import DatabaseConnection
from pyserv.database.config import DatabaseConfig
from pyserv.database.backends import get_backend
from pyserv.utils.types import Field, Relationship, RelationshipType, OrderDirection, PaginatedResponse, AggregationResult, LazyLoad
from pyserv.utils.collections import Collection

T = TypeVar('T')
M = TypeVar('M', bound=PydanticBaseModel)


class QueryBuilder(Generic[T]):
    """Query builder for constructing database queries"""

    def __init__(self, model_class: Type[T]):
        self.model_class = model_class
        self.db = DatabaseConnection.get_instance(self.model_class._db_config)
        self.backend = self.db.backend
        self.conditions: List[str] = []
        self.params: List[Any] = []
        self._limit: Optional[int] = None
        self._offset: Optional[int] = None
        self._order_by: List[Tuple[str, OrderDirection]] = []
        self._prefetch_relations: List[str] = []
        self._select_fields: List[str] = []
        self._distinct: bool = False
        self._group_by: List[str] = []
        self._having_conditions: List[str] = []
        self._having_params: List[Any] = []
        self._param_counter = 1
        self._lazy_loading_enabled: bool = True
        self._filter_criteria: Dict[str, Any] = {}

    def copy(self) -> 'QueryBuilder[T]':
        """Create a copy of the query builder"""
        new_builder = QueryBuilder(self.model_class)
        new_builder.conditions = self.conditions.copy()
        new_builder.params = self.params.copy()
        new_builder._limit = self._limit
        new_builder._offset = self._offset
        new_builder._order_by = self._order_by.copy()
        new_builder._prefetch_relations = self._prefetch_relations.copy()
        new_builder._select_fields = self._select_fields.copy()
        new_builder._distinct = self._distinct
        new_builder._group_by = self._group_by.copy()
        new_builder._having_conditions = self._having_conditions.copy()
        new_builder._having_params = self._having_params.copy()
        new_builder._param_counter = self._param_counter
        new_builder._lazy_loading_enabled = self._lazy_loading_enabled
        return new_builder

    def disable_lazy_loading(self) -> 'QueryBuilder[T]':
        """Disable lazy loading for this query"""
        self._lazy_loading_enabled = False
        return self

    def _get_next_param_placeholder(self) -> str:
        """Get the next parameter placeholder using backend"""
        placeholder = self.backend.get_param_placeholder(self._param_counter)
        if placeholder == "$":
            # For PostgreSQL-style placeholders
            self._param_counter += 1
            return f"${self._param_counter}"
        return placeholder

    def filter(self, **kwargs) -> 'QueryBuilder[T]':
        """Add filter conditions and return self for chaining"""
        # Use backend-agnostic filtering
        for key, value in kwargs.items():
            if '__' in key:
                field, operator = key.split('__', 1)
                self._add_filter_condition(field, operator, value)
            else:
                self._add_filter_condition(key, 'eq', value)
        return self

    def _add_filter_condition(self, field: str, operator: str, value: Any):
        """Add a filter condition - ALL logic moved to backends"""
        # Build unified filter criteria that works across all backends
        if operator == 'in':
            self._filter_criteria[field] = {'$in': value}
        elif operator == 'gt':
            self._filter_criteria[field] = {'$gt': value}
        elif operator == 'lt':
            self._filter_criteria[field] = {'$lt': value}
        elif operator == 'gte':
            self._filter_criteria[field] = {'$gte': value}
        elif operator == 'lte':
            self._filter_criteria[field] = {'$lte': value}
        elif operator == 'neq':
            self._filter_criteria[field] = {'$ne': value}
        elif operator == 'like':
            self._filter_criteria[field] = {'$regex': f'.*{value}.*', '$options': 'i'}
        elif operator == 'ilike':
            self._filter_criteria[field] = {'$regex': f'.*{value}.*', '$options': 'i'}
        elif operator == 'is_null':
            self._filter_criteria[field] = None
        elif operator == 'is_not_null':
            self._filter_criteria[field] = {'$ne': None}
        else:  # eq
            self._filter_criteria[field] = value

    def limit(self, limit: int) -> 'QueryBuilder[T]':
        """Set query limit and return self"""
        self._limit = limit
        return self

    def offset(self, offset: int) -> 'QueryBuilder[T]':
        """Set query offset and return self"""
        self._offset = offset
        return self

    def order_by(self, field: str, direction: OrderDirection = OrderDirection.ASC) -> 'QueryBuilder[T]':
        """Add order by clause and return self"""
        self._order_by.append((field, direction))
        return self

    def prefetch_related(self, *relations: str) -> 'QueryBuilder[T]':
        """Add relationships to prefetch and return self"""
        self._prefetch_relations.extend(relations)
        return self

    def select_fields(self, *fields: str) -> 'QueryBuilder[T]':
        """Specify fields to select and return self"""
        self._select_fields.extend(fields)
        return self

    def distinct(self) -> 'QueryBuilder[T]':
        """Add DISTINCT clause and return self"""
        self._distinct = True
        return self

    def group_by(self, *fields: str) -> 'QueryBuilder[T]':
        """Add GROUP BY clause and return self"""
        self._group_by.extend(fields)
        return self

    def having(self, condition: str, *params: Any) -> 'QueryBuilder[T]':
        """Add HAVING clause and return self"""
        self._having_conditions.append(condition)
        self._having_params.extend(params)
        return self

    def _build_sql(self) -> Tuple[str, List[Any]]:
        """Build SQL query and parameters"""
        # SELECT clause
        select_clause = "SELECT "
        if self._distinct:
            select_clause += "DISTINCT "
        select_clause += ', '.join(self._select_fields) if self._select_fields else '*'

        # FROM clause
        from_clause = f"FROM {self.model_class.get_table_name()}"

        # WHERE clause
        where_clause = f"WHERE {' AND '.join(self.conditions)}" if self.conditions else ""

        # GROUP BY clause
        group_by_clause = f"GROUP BY {', '.join(self._group_by)}" if self._group_by else ""

        # HAVING clause
        having_clause = f"HAVING {' AND '.join(self._having_conditions)}" if self._having_conditions else ""

        # ORDER BY clause
        order_clause = ""
        if self._order_by:
            order_parts = []
            for field, direction in self._order_by:
                order_parts.append(f"{field} {direction.value}")
            order_clause = f"ORDER BY {', '.join(order_parts)}"

        # LIMIT and OFFSET clauses
        limit_clause = f"LIMIT {self._limit}" if self._limit else ""
        offset_clause = f"OFFSET {self._offset}" if self._offset else ""

        sql = f"{select_clause} {from_clause} {where_clause} {group_by_clause} {having_clause} {order_clause} {limit_clause} {offset_clause}"

        # Combine all parameters
        all_params = self.params + self._having_params

        return sql, all_params

    async def execute(self) -> List[T]:
        """Execute the query and return results using backend abstraction"""
        # Build query parameters for the backend
        query_params = {
            'select_fields': self._select_fields,
            'distinct': self._distinct,
            'filters': self._filter_criteria,
            'limit': self._limit,
            'offset': self._offset,
            'order_by': self._order_by,
            'group_by': self._group_by,
            'having': self._having_conditions
        }

        # Execute using backend's query builder method
        results = await self.backend.execute_query_builder(self.model_class, query_params)

        # Convert results to model instances
        instances = []
        for result in results:
            instance = self.model_class(**result)
            instances.append(instance)

        # Prefetch relationships to prevent N+1 queries
        if self._prefetch_relations:
            await self._prefetch_relationships(instances)

        return instances



    async def _prefetch_relationships(self, instances: List[T]):
        """Prefetch relationships to avoid N+1 queries"""
        tasks = []
        for relation_name in self._prefetch_relations:
            if relation_name in self.model_class._relationships:
                rel = self.model_class._relationships[relation_name]
                tasks.append(self._prefetch_relation(instances, rel, relation_name))

        if tasks:
            await asyncio.gather(*tasks)

    async def _prefetch_relation(self, instances: List[T], rel: Relationship, relation_name: str):
        """Prefetch a specific relationship"""
        if rel.relationship_type == RelationshipType.MANY_TO_ONE:
            # For many-to-one relationships
            foreign_keys = [getattr(instance, rel.foreign_key) for instance in instances
                          if getattr(instance, rel.foreign_key) is not None]

            if foreign_keys:
                related_objects = await rel.model_class.query().filter(**{
                    f"{rel.local_key}__in": list(set(foreign_keys))
                }).execute()

                related_dict = {getattr(obj, rel.local_key): obj for obj in related_objects}

                for instance in instances:
                    fk_value = getattr(instance, rel.foreign_key)
                    if fk_value in related_dict:
                        instance._loaded_relations[relation_name] = related_dict[fk_value]

        elif rel.relationship_type == RelationshipType.ONE_TO_MANY:
            # For one-to-many relationships
            local_keys = [getattr(instance, rel.local_key) for instance in instances]

            if local_keys:
                related_objects = await rel.model_class.query().filter(**{
                    f"{rel.foreign_key}__in": local_keys
                }).execute()

                related_dict = {}
                for obj in related_objects:
                    fk_value = getattr(obj, rel.foreign_key)
                    if fk_value not in related_dict:
                        related_dict[fk_value] = []
                    related_dict[fk_value].append(obj)

                for instance in instances:
                    local_key = getattr(instance, rel.local_key)
                    if local_key in related_dict:
                        instance._loaded_relations[relation_name] = related_dict[local_key]

        elif rel.relationship_type == RelationshipType.MANY_TO_MANY:
            # For many-to-many relationships
            if not rel.through_table:
                raise ValueError("Many-to-many relationship requires through_table")

            local_keys = [getattr(instance, rel.local_key) for instance in instances]

            # Create through model dynamically
            from pyserv.models.base import BaseModel
            through_class = type('ThroughModel', (BaseModel,), {
                '_table_name': rel.through_table,
                '_columns': {
                    'id': Field('INTEGER', primary_key=True),
                    rel.through_local_key: Field('INTEGER'),
                    rel.through_foreign_key: Field('INTEGER')
                }
            })
            through_class.set_db_config(self.model_class._db_config)

            # Get through objects
            through_objects = await through_class.query().filter(**{
                rel.through_local_key: getattr(self, rel.local_key)
            }).execute()

            # Get related objects
            related_ids = [getattr(obj, rel.through_foreign_key) for obj in through_objects]
            result = await rel.model_class.query().filter(**{
                f"{rel.local_key}__in": related_ids
            }).execute()

    async def count(self) -> int:
        """Return count of matching records using backend abstraction"""
        # Build query parameters for the backend
        query_params = {
            'select_fields': [],
            'distinct': False,
            'filters': self._filter_criteria,
            'limit': None,
            'offset': None,
            'order_by': [],
            'group_by': [],
            'having': []
        }

        # Execute using backend's query builder method and count results
        results = await self.backend.execute_query_builder(self.model_class, query_params)
        return len(results)



    async def first(self) -> Optional[T]:
        """Return first matching record"""
        results = await self.copy().limit(1).execute()
        return results[0] if results else None

    async def exists(self) -> bool:
        """Check if any records match the query"""
        return await self.copy().limit(1).count() > 0

    async def paginate(self, page: int = 1, page_size: int = 20) -> PaginatedResponse:
        """Return paginated results"""
        # Create a copy to avoid modifying the original query
        count_builder = self.copy()
        total = await count_builder.count()

        # Execute the query with pagination
        items = await self.copy().offset((page - 1) * page_size).limit(page_size).execute()

        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=math.ceil(total / page_size) if page_size > 0 else 0
        )

    async def to_collection(self) -> Collection[T]:
        """Execute query and return results as Collection"""
        items = await self.execute()
        return Collection(items)

    async def as_collection(self) -> Collection[T]:
        """Alias for to_collection()"""
        return await self.to_collection()

    async def aggregate(self, **aggregations: str) -> AggregationResult:
        """Perform aggregation operations using backend abstraction"""
        # Convert filters to backend format
        filters = self._convert_filters_to_backend()

        # Convert aggregations to backend format
        pipeline = []
        for field, func in aggregations.items():
            if func == 'count':
                pipeline.append({'$group': {'_id': None, f'{field}_count': {'$sum': 1}}})
            elif func == 'sum':
                pipeline.append({'$group': {'_id': None, f'{field}_sum': {'$sum': f'${field}'}}})
            elif func == 'avg':
                pipeline.append({'$group': {'_id': None, f'{field}_avg': {'$avg': f'${field}'}}})
            elif func == 'min':
                pipeline.append({'$group': {'_id': None, f'{field}_min': {'$min': f'${field}'}}})
            elif func == 'max':
                pipeline.append({'$group': {'_id': None, f'{field}_max': {'$max': f'${field}'}}})

        # Use backend aggregate method
        results = await self.backend.aggregate(self.model_class, pipeline)

        # Convert results to AggregationResult
        agg_result = AggregationResult()
        if results:
            result = results[0] if results else {}
            for field, func in aggregations.items():
                value = result.get(f'{field}_{func}')
                if func == 'count':
                    agg_result.count = value or 0
                elif func == 'sum':
                    agg_result.sum = value or 0
                elif func == 'avg':
                    agg_result.avg = value or 0
                elif func == 'min':
                    agg_result.min = value
                elif func == 'max':
                    agg_result.max = value

        return agg_result



    def _convert_filters_to_backend(self) -> Dict[str, Any]:
        """Convert query filters to backend-compatible format"""
        if self.model_class._db_config.is_mongodb:
            # For MongoDB, use the filter criteria directly
            return self._filter_criteria
        else:
            # For SQL databases, build a filter dict from conditions and params
            filters = {}
            if self.conditions:
                # Convert SQL conditions to a simple key-value filter dict
                # This is a simplified approach - complex conditions would need more parsing
                for i, condition in enumerate(self.conditions):
                    # Simple parsing for basic conditions like "field = ?" or "field > ?"
                    if ' = ' in condition:
                        field, _ = condition.split(' = ', 1)
                        filters[field.strip()] = self.params[i] if i < len(self.params) else None
                    elif ' > ' in condition:
                        field, _ = condition.split(' > ', 1)
                        filters[field.strip()] = {'$gt': self.params[i] if i < len(self.params) else None}
                    elif ' < ' in condition:
                        field, _ = condition.split(' < ', 1)
                        filters[field.strip()] = {'$lt': self.params[i] if i < len(self.params) else None}
                    elif ' >= ' in condition:
                        field, _ = condition.split(' >= ', 1)
                        filters[field.strip()] = {'$gte': self.params[i] if i < len(self.params) else None}
                    elif ' <= ' in condition:
                        field, _ = condition.split(' <= ', 1)
                        filters[field.strip()] = {'$lte': self.params[i] if i < len(self.params) else None}
                    elif ' != ' in condition:
                        field, _ = condition.split(' != ', 1)
                        filters[field.strip()] = {'$ne': self.params[i] if i < len(self.params) else None}
                    elif ' LIKE ' in condition:
                        field, _ = condition.split(' LIKE ', 1)
                        value = self.params[i] if i < len(self.params) else ""
                        # Convert SQL LIKE to regex for backend compatibility
                        regex = value.replace('%', '.*')
                        filters[field.strip()] = {'$regex': regex, '$options': 'i'}
                    elif ' IN ' in condition:
                        field, _ = condition.split(' IN ', 1)
                        # For IN clauses, take multiple parameters
                        in_values = []
                        param_count = condition.count('?')
                        start_idx = i
                        for j in range(param_count):
                            if start_idx + j < len(self.params):
                                in_values.append(self.params[start_idx + j])
                        filters[field.strip()] = {'$in': in_values}
            return filters

    def _convert_sort_to_backend(self) -> Optional[List[Tuple[str, int]]]:
        """Convert sort order to backend-compatible format"""
        if not self._order_by:
            return None

        sort_list = []
        for field, direction in self._order_by:
            # Convert OrderDirection to integer (1 for ASC, -1 for DESC)
            sort_direction = 1 if direction == OrderDirection.ASC else -1
            sort_list.append((field, sort_direction))

        return sort_list

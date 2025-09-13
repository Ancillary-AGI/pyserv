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

from ..database.database import DatabaseConnection
from ..database.config import DatabaseConfig
from ..utils.types import Field, Relationship, RelationshipType, OrderDirection, PaginatedResponse, AggregationResult, LazyLoad

T = TypeVar('T')
M = TypeVar('M', bound=PydanticBaseModel)


class QueryBuilder(Generic[T]):
    """Query builder for constructing database queries"""

    def __init__(self, model_class: Type[T]):
        self.model_class = model_class
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
        self._mongo_filter: Dict[str, Any] = {}

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
        """Get the next parameter placeholder based on database type"""
        if self.model_class._db_config.is_sqlite:
            return '?'
        elif self.model_class._db_config.is_mysql:
            return '%s'
        else:
            placeholder = f"${self._param_counter}"
            self._param_counter += 1
            return placeholder

    def filter(self, **kwargs) -> 'QueryBuilder[T]':
        """Add filter conditions and return self for chaining"""
        if self.model_class._db_config.is_mongodb:
            # Handle MongoDB filtering
            for key, value in kwargs.items():
                if '__' in key:
                    field, operator = key.split('__', 1)
                    if operator == 'in':
                        self._mongo_filter[field] = {'$in': value}
                    elif operator == 'gt':
                        self._mongo_filter[field] = {'$gt': value}
                    elif operator == 'lt':
                        self._mongo_filter[field] = {'$lt': value}
                    elif operator == 'gte':
                        self._mongo_filter[field] = {'$gte': value}
                    elif operator == 'lte':
                        self._mongo_filter[field] = {'$lte': value}
                    elif operator == 'neq':
                        self._mongo_filter[field] = {'$ne': value}
                    elif operator == 'like':
                        self._mongo_filter[field] = {'$regex': f'.*{value}.*', '$options': 'i'}
                    elif operator == 'ilike':
                        self._mongo_filter[field] = {'$regex': f'.*{value}.*', '$options': 'i'}
                else:
                    self._mongo_filter[key] = value
        else:
            # SQL databases
            for key, value in kwargs.items():
                if '__' in key:
                    field, operator = key.split('__', 1)
                    if operator == 'in':
                        placeholders = ', '.join([self._get_next_param_placeholder() for _ in range(len(value))])
                        self.conditions.append(f"{field} IN ({placeholders})")
                        self.params.extend(value)
                    elif operator == 'like':
                        placeholder = self._get_next_param_placeholder()
                        self.conditions.append(f"{field} LIKE {placeholder}")
                        self.params.append(f"%{value}%")
                    elif operator == 'ilike':
                        if self.model_class._db_config.is_mysql:
                            # MySQL uses different syntax for case-insensitive search
                            placeholder = self._get_next_param_placeholder()
                            self.conditions.append(f"LOWER({field}) LIKE LOWER({placeholder})")
                            self.params.append(f"%{value}%")
                        else:
                            placeholder = self._get_next_param_placeholder()
                            self.conditions.append(f"{field} ILIKE {placeholder}")
                            self.params.append(f"%{value}%")
                    elif operator == 'gt':
                        placeholder = self._get_next_param_placeholder()
                        self.conditions.append(f"{field} > {placeholder}")
                        self.params.append(value)
                    elif operator == 'lt':
                        placeholder = self._get_next_param_placeholder()
                        self.conditions.append(f"{field} < {placeholder}")
                        self.params.append(value)
                    elif operator == 'gte':
                        placeholder = self._get_next_param_placeholder()
                        self.conditions.append(f"{field} >= {placeholder}")
                        self.params.append(value)
                    elif operator == 'lte':
                        placeholder = self._get_next_param_placeholder()
                        self.conditions.append(f"{field} <= {placeholder}")
                        self.params.append(value)
                    elif operator == 'neq':
                        placeholder = self._get_next_param_placeholder()
                        self.conditions.append(f"{field} != {placeholder}")
                        self.params.append(value)
                    elif operator == 'is_null':
                        self.conditions.append(f"{field} IS NULL")
                    elif operator == 'is_not_null':
                        self.conditions.append(f"{field} IS NOT NULL")
                else:
                    placeholder = self._get_next_param_placeholder()
                    self.conditions.append(f"{key} = {placeholder}")
                    self.params.append(value)
        return self

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
        """Execute the query and return results"""
        db = DatabaseConnection.get_instance(self.model_class._db_config)

        if self.model_class._db_config.is_mongodb:
            # MongoDB execution
            async with db.get_connection() as conn:
                collection = conn[self.model_class.get_table_name()]

                # Build find options
                find_options = {}
                if self._limit:
                    find_options['limit'] = self._limit
                if self._offset:
                    find_options['skip'] = self._offset

                # Build sort
                if self._order_by:
                    sort_list = []
                    for field, direction in self._order_by:
                        sort_list.append((field, ASCENDING if direction == OrderDirection.ASC else DESCENDING))
                    find_options['sort'] = sort_list

                # Execute query
                cursor = collection.find(self._mongo_filter, find_options)
                rows = await cursor.to_list(length=None)

                # Convert MongoDB ObjectId to string for ID field
                for row in rows:
                    if '_id' in row:
                        row['id'] = str(row['_id'])
                        del row['_id']

                instances = [self.model_class(**row) for row in rows]

                # Prefetch relationships to prevent N+1 queries
                if self._prefetch_relations:
                    await self._prefetch_relationships(instances)

                return instances
        else:
            # SQL execution
            sql, params = self._build_sql()

            async with db.get_connection() as conn:
                if hasattr(conn, 'execute'):
                    # SQLite
                    cursor = conn.execute(sql, params)
                    rows = cursor.fetchall()
                else:
                    # PostgreSQL
                    rows = await conn.fetch(sql, *params)

            instances = [self.model_class(**dict(row)) for row in rows]

            # Prefetch relationships to prevent N+1 queries if lazy loading is disabled
            if not self._lazy_loading_enabled and self._prefetch_relations:
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
        """Return count of matching records"""
        db = DatabaseConnection.get_instance(self.model_class._db_config)

        if self.model_class._db_config.is_mongodb:
            # MongoDB count
            async with db.get_connection() as conn:
                collection = conn[self.model_class.get_table_name()]
                return await collection.count_documents(self._mongo_filter)
        else:
            # Build count query
            where_clause = f"WHERE {' AND '.join(self.conditions)}" if self.conditions else ""
            group_by_clause = f"GROUP BY {', '.join(self._group_by)}" if self._group_by else ""

            if self._group_by:
                # For grouped queries, we need to count the groups
                sql = f"SELECT COUNT(*) as count FROM (SELECT 1 FROM {self.model_class.get_table_name()} {where_clause} {group_by_clause}) as subquery"
            else:
                sql = f"SELECT COUNT(*) as count FROM {self.model_class.get_table_name()} {where_clause}"

            async with db.get_connection() as conn:
                if hasattr(conn, 'execute'):
                    cursor = conn.execute(sql, self.params)
                    result = cursor.fetchone()
                    return result['count'] if result else 0
                else:
                    result = await conn.fetchval(sql, *self.params)
                    return result or 0

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

    async def aggregate(self, **aggregations: str) -> AggregationResult:
        """Perform aggregation operations"""
        db = DatabaseConnection.get_instance(self.model_class._db_config)

        agg_functions = []
        for field, func in aggregations.items():
            agg_functions.append(f"{func.upper()}({field}) as {field}_{func}")

        where_clause = f"WHERE {' AND '.join(self.conditions)}" if self.conditions else ""
        group_by_clause = f"GROUP BY {', '.join(self._group_by)}" if self._group_by else ""

        sql = f"SELECT {', '.join(agg_functions)} FROM {self.model_class.get_table_name()} {where_clause} {group_by_clause}"

        async with db.get_connection() as conn:
            if hasattr(conn, 'execute'):
                cursor = conn.execute(sql, self.params)
                result = cursor.fetchone()
            else:
                result = await conn.fetchrow(sql, *self.params)

        agg_result = AggregationResult()
        if result:
            for field, func in aggregations.items():
                value = result.get(f"{field}_{func}")
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

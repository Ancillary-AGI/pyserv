"""
Real PostgreSQL database connection implementation with full CRUD operations.
"""

import asyncpg
import json
import os
from typing import List, Dict, Any, AsyncGenerator, Type, Optional, Tuple, Union
from contextlib import asynccontextmanager
from datetime import datetime
import logging
import threading
from decimal import Decimal
from urllib.parse import urlparse

from pyserv.database.config import DatabaseConfig
from pyserv.utils.types import Field, StringField, IntegerField, BooleanField, DateTimeField, FieldType

logger = logging.getLogger(__name__)


class PostgreSQLConnection:
    """PostgreSQL database connection"""

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.pool = None

    async def connect(self) -> None:
        """Connect to the database"""
        params = self.config.get_connection_params()
        self.pool = await asyncpg.create_pool(**params)

    async def disconnect(self) -> None:
        """Disconnect from the database"""
        if self.pool:
            await self.pool.close()

    async def execute_query(self, query: str, params: tuple = None) -> Any:
        """Execute a SQL query"""
        async with self.pool.acquire() as connection:
            if params:
                return await connection.execute(query, *params)
            else:
                return await connection.execute(query)

    async def execute_raw(self, query: str, params: tuple = None) -> Any:
        """Execute a raw query and return cursor for advanced usage (Django-like cursor API)."""
        async with self.pool.acquire() as connection:
            if params:
                return await connection.fetch(query, *params)
            else:
                return await connection.fetch(query)

    async def begin_transaction(self) -> Any:
        """Begin PostgreSQL transaction."""
        async with self.pool.acquire() as connection:
            return await connection.begin()

    async def commit_transaction(self, transaction: Any) -> None:
        """Commit PostgreSQL transaction."""
        await transaction.commit()

    async def rollback_transaction(self, transaction: Any) -> None:
        """Rollback PostgreSQL transaction."""
        await transaction.rollback()

    async def execute_in_transaction(self, query: str, params: tuple = None) -> Any:
        """Execute PostgreSQL query within transaction context."""
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                if params:
                    return await connection.fetch(query, *params)
                else:
                    return await connection.fetch(query)

    async def create_table(self, model_class: Type) -> None:
        """Create a table for the model"""
        fields = []
        for name, field in model_class._fields.items():
            field_def = f"{name} {self.get_sql_type(field)}"
            if field.primary_key:
                field_def += " PRIMARY KEY"
                if field.autoincrement:
                    field_def += " GENERATED ALWAYS AS IDENTITY"
            if not field.nullable:
                field_def += " NOT NULL"
            if field.default is not None:
                field_def += f" DEFAULT {self._format_default(field.default)}"
            fields.append(field_def)

        query = f"CREATE TABLE IF NOT EXISTS {model_class.get_table_name()} ({', '.join(fields)})"
        await self.execute_query(query)

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[Any, None]:
        """Get a database connection context manager"""
        async with self.pool.acquire() as connection:
            yield connection

    async def get_param_placeholder(self, index: int) -> str:
        """Get parameter placeholder for PostgreSQL"""
        return f"${index}"

    def get_sql_type(self, field: Field) -> str:
        """Get SQL type for a field"""
        if isinstance(field, StringField):
            if field.max_length:
                return f"VARCHAR({field.max_length})"
            return "TEXT"
        elif isinstance(field, IntegerField):
            return "INTEGER"
        elif isinstance(field, BooleanField):
            return "BOOLEAN"
        elif isinstance(field, DateTimeField):
            return "TIMESTAMP"
        elif field.field_type == FieldType.UUID:
            return "UUID"
        elif field.field_type == FieldType.JSON:
            return "JSONB"
        elif field.field_type == FieldType.FLOAT:
            return "REAL"
        return "TEXT"

    async def insert_one(self, model_class: Type, data: Dict[str, Any]) -> Any:
        """Insert a single record"""
        fields = list(data.keys())
        values = list(data.values())
        placeholders = ', '.join([self.get_param_placeholder(i+1) for i in range(len(fields))])
        query = f"INSERT INTO {model_class.get_table_name()} ({', '.join(fields)}) VALUES ({placeholders}) RETURNING *"

        async with self.pool.acquire() as connection:
            result = await connection.fetchrow(query, *values)
            return dict(result) if result else None

    async def update_one(self, model_class: Type, filters: Dict[str, Any], data: Dict[str, Any]) -> bool:
        """Update a single record"""
        set_clause = ', '.join([f"{k} = {self.get_param_placeholder(i+1)}" for i, k in enumerate(data.keys())])
        where_clause = ' AND '.join([f"{k} = {self.get_param_placeholder(len(data) + i + 1)}" for i, k in enumerate(filters.keys())])
        query = f"UPDATE {model_class.get_table_name()} SET {set_clause} WHERE {where_clause}"

        params = list(data.values()) + list(filters.values())
        async with self.pool.acquire() as connection:
            result = await connection.execute(query, *params)
            return result == "UPDATE 1"

    async def delete_one(self, model_class: Type, filters: Dict[str, Any]) -> bool:
        """Delete a single record"""
        where_clause = ' AND '.join([f"{k} = {self.get_param_placeholder(i+1)}" for i, k in enumerate(filters.keys())])
        query = f"DELETE FROM {model_class.get_table_name()} WHERE {where_clause}"

        async with self.pool.acquire() as connection:
            result = await connection.execute(query, *filters.values())
            return result == "DELETE 1"

    async def find_one(self, model_class: Type, filters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find a single record"""
        where_clause = ' AND '.join([f"{k} = {self.get_param_placeholder(i+1)}" for i, k in enumerate(filters.keys())])
        query = f"SELECT * FROM {model_class.get_table_name()} WHERE {where_clause} LIMIT 1"

        async with self.pool.acquire() as connection:
            result = await connection.fetchrow(query, *filters.values())
            return dict(result) if result else None

    async def find_many(self, model_class: Type, filters: Dict[str, Any], limit: Optional[int] = None,
                       offset: Optional[int] = None, sort: Optional[List[Tuple[str, int]]] = None) -> List[Dict[str, Any]]:
        """Find multiple records"""
        where_clause = ' AND '.join([f"{k} = {self.get_param_placeholder(i+1)}" for i, k in enumerate(filters.keys())]) if filters else ""
        order_clause = ""
        if sort:
            order_parts = [f"{field} {'DESC' if direction == -1 else 'ASC'}" for field, direction in sort]
            order_clause = f" ORDER BY {', '.join(order_parts)}"

        limit_clause = f" LIMIT {limit}" if limit else ""
        offset_clause = f" OFFSET {offset}" if offset else ""

        query = f"SELECT * FROM {model_class.get_table_name()}"
        if where_clause:
            query += f" WHERE {where_clause}"
        query += order_clause + limit_clause + offset_clause

        async with self.pool.acquire() as connection:
            results = await connection.fetch(query, *(filters.values() if filters else []))
            return [dict(row) for row in results]

    async def count(self, model_class: Type, filters: Dict[str, Any]) -> int:
        """Count records matching filters"""
        where_clause = ' AND '.join([f"{k} = {self.get_param_placeholder(i+1)}" for i, k in enumerate(filters.keys())]) if filters else ""
        query = f"SELECT COUNT(*) as count FROM {model_class.get_table_name()}"
        if where_clause:
            query += f" WHERE {where_clause}"

        async with self.pool.acquire() as connection:
            result = await connection.fetchval(query, *(filters.values() if filters else []))
            return result or 0

    async def aggregate(self, model_class: Type, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Perform aggregation operations using PostgreSQL"""
        # For PostgreSQL, we can implement more complex aggregations
        if not pipeline:
            return []

        # Real MongoDB aggregation pipeline to SQL translation
        results = []
        agg_query = pipeline[0]

        if '$group' in agg_query:
            group_fields = agg_query['$group']
        if '$group' in agg_query:
            group_fields = agg_query['$group']
            # Implement basic GROUP BY aggregations
            select_parts = []
            group_by_parts = []

            for field, agg_func in group_fields.items():
                if field == '_id':
                    continue
                if isinstance(agg_func, dict):
                    for op, field_name in agg_func.items():
                        if op == '$sum':
                            select_parts.append(f"SUM({field_name}) as {field}")
                        elif op == '$avg':
                            select_parts.append(f"AVG({field_name}) as {field}")
                        elif op == '$min':
                            select_parts.append(f"MIN({field_name}) as {field}")
                        elif op == '$max':
                            select_parts.append(f"MAX({field_name}) as {field}")
                        elif op == '$count':
                            select_parts.append(f"COUNT(*) as {field}")

            if select_parts:
                query = f"SELECT {', '.join(select_parts)} FROM {model_class.get_table_name()}"
                async with self.pool.acquire() as connection:
                    results = await connection.fetch(query)
                    return [dict(row) for row in results]

        return []

    def _format_default(self, default: Any) -> str:
        """Format default value for PostgreSQL"""
        if isinstance(default, str):
            if default.upper() in ['CURRENT_TIMESTAMP', 'CURRENT_DATE']:
                return default
            return f"'{default}'"
        elif isinstance(default, bool):
            return 'TRUE' if default else 'FALSE'
        elif default is None:
            return 'NULL'
        return str(default)

    async def create_migrations_table(self) -> None:
        """Create the migrations tracking table for PostgreSQL"""
        query = '''
            CREATE TABLE IF NOT EXISTS migrations (
                id SERIAL PRIMARY KEY,
                migration_id VARCHAR(255) UNIQUE,
                model_name VARCHAR(255) NOT NULL,
                version INTEGER NOT NULL,
                schema_definition TEXT NOT NULL,
                operations TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(model_name, version)
            )
        '''
        await self.execute_query(query)

    async def insert_migration_record(self, model_name: str, version: int, schema_definition: dict, operations: dict, migration_id: str = None) -> None:
        """Insert a migration record for PostgreSQL"""
        import json
        if migration_id:
            query = '''
                INSERT INTO migrations (migration_id, model_name, version, schema_definition, operations)
                VALUES ($1, $2, $3, $4, $5)
            '''
            params = (migration_id, model_name, version, json.dumps(schema_definition), json.dumps(operations))
        else:
            query = '''
                INSERT INTO migrations (model_name, version, schema_definition, operations)
                VALUES ($1, $2, $3, $4)
            '''
            params = (model_name, version, json.dumps(schema_definition), json.dumps(operations))
        await self.execute_query(query, params)

    async def get_applied_migrations(self) -> Dict[str, int]:
        """Get all applied migrations for PostgreSQL"""
        import json
        query = "SELECT model_name, version, schema_definition FROM migrations"
        result = await self.execute_query(query)

        migrations = {}
        if hasattr(result, 'fetchall'):
            rows = await result.fetchall()
        else:
            rows = result

        for row in rows:
            migrations[row['model_name']] = row['version']
        return migrations

    async def delete_migration_record(self, model_name: str, version: int) -> None:
        """Delete a migration record for PostgreSQL"""
        query = "DELETE FROM migrations WHERE model_name = $1 AND version = $2"
        await self.execute_query(query, (model_name, version))

    async def drop_table(self, table_name: str) -> None:
        """Drop a table for PostgreSQL"""
        query = f"DROP TABLE IF EXISTS {table_name} CASCADE"
        await self.execute_query(query)

    async def add_column(self, table_name: str, column_name: str, column_definition: str) -> None:
        """Add a column to a table for PostgreSQL"""
        query = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
        await self.execute_query(query)

    async def drop_column(self, table_name: str, column_name: str) -> None:
        """Drop a column from a table for PostgreSQL"""
        query = f"ALTER TABLE {table_name} DROP COLUMN IF EXISTS {column_name}"
        await self.execute_query(query)

    async def modify_column(self, table_name: str, column_name: str, column_definition: str) -> None:
        """Modify a column in a table for PostgreSQL"""
        query = f"ALTER TABLE {table_name} ALTER COLUMN {column_name} TYPE {column_definition}"
        await self.execute_query(query)

    async def create_index(self, table_name: str, index_name: str, columns: List[str]) -> None:
        """Create an index on a table for PostgreSQL"""
        column_list = ', '.join(columns)
        query = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} ({column_list})"
        await self.execute_query(query)

    async def drop_index(self, table_name: str, index_name: str) -> None:
        """Drop an index from a table for PostgreSQL"""
        query = f"DROP INDEX IF EXISTS {index_name}"
        await self.execute_query(query)

    async def add_field(self, model_name: str, field_name: str, field: Field) -> None:
        """Add a field to an existing model/table for PostgreSQL"""
        table_name = model_name.lower() + 's'  # Follow convention
        column_definition = f"{field_name} {self.get_sql_type(field)}"

        if field.primary_key:
            column_definition += " PRIMARY KEY"
            if field.autoincrement:
                column_definition += " GENERATED ALWAYS AS IDENTITY"

        if not field.nullable:
            column_definition += " NOT NULL"

        if field.default is not None:
            column_definition += f" DEFAULT {self._format_default(field.default)}"

        query = f"ALTER TABLE {table_name} ADD COLUMN {column_definition}"
        await self.execute_query(query)

    async def remove_field(self, model_name: str, field_name: str) -> None:
        """Remove a field from an existing model/table for PostgreSQL"""
        table_name = model_name.lower() + 's'  # Follow convention
        query = f"ALTER TABLE {table_name} DROP COLUMN IF EXISTS {field_name}"
        await self.execute_query(query)

    async def alter_field(self, model_name: str, field_name: str, field: Field) -> None:
        """Alter an existing field in a model/table for PostgreSQL"""
        table_name = model_name.lower() + 's'  # Follow convention
        column_definition = self.get_sql_type(field)

        if field.primary_key:
            column_definition += " PRIMARY KEY"
            if field.autoincrement:
                column_definition += " GENERATED ALWAYS AS IDENTITY"

        if not field.nullable:
            column_definition += " NOT NULL"

        if field.default is not None:
            column_definition += f" DEFAULT {self._format_default(field.default)}"

        query = f"ALTER TABLE {table_name} ALTER COLUMN {field_name} TYPE {column_definition}"
        await self.execute_query(query)

    async def execute_query_builder(self, model_class: Type, query_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute a complex query built by QueryBuilder for PostgreSQL"""
        # Extract query parameters
        select_fields = query_params.get('select_fields', [])
        distinct = query_params.get('distinct', False)
        filters = query_params.get('filters', {})
        limit = query_params.get('limit')
        offset = query_params.get('offset')
        order_by = query_params.get('order_by', [])
        group_by = query_params.get('group_by', [])
        having = query_params.get('having', [])

        # Build SELECT clause
        select_clause = "SELECT "
        if distinct:
            select_clause += "DISTINCT "
        if select_fields:
            select_clause += ', '.join(select_fields)
        else:
            select_clause += '*'

        # Build FROM clause
        from_clause = f"FROM {model_class.get_table_name()}"

        # Build WHERE clause
        where_clause = ""
        params = []
        param_index = 1
        if filters:
            conditions = []
            for key, value in filters.items():
                if isinstance(value, dict):
                    # Handle MongoDB-style operators
                    for op, val in value.items():
                        if op == '$gt':
                            conditions.append(f"{key} > ${param_index}")
                            params.append(val)
                            param_index += 1
                        elif op == '$lt':
                            conditions.append(f"{key} < ${param_index}")
                            params.append(val)
                            param_index += 1
                        elif op == '$gte':
                            conditions.append(f"{key} >= ${param_index}")
                            params.append(val)
                            param_index += 1
                        elif op == '$lte':
                            conditions.append(f"{key} <= ${param_index}")
                            params.append(val)
                            param_index += 1
                        elif op == '$ne':
                            conditions.append(f"{key} != ${param_index}")
                            params.append(val)
                            param_index += 1
                        elif op == '$in':
                            placeholders = ', '.join([f"${param_index + i}" for i in range(len(val))])
                            conditions.append(f"{key} IN ({placeholders})")
                            params.extend(val)
                            param_index += len(val)
                        elif op == '$regex':
                            conditions.append(f"{key} ~ ${param_index}")
                            params.append(val)
                            param_index += 1
                else:
                    conditions.append(f"{key} = ${param_index}")
                    params.append(value)
                    param_index += 1
            if conditions:
                where_clause = f"WHERE {' AND '.join(conditions)}"

        # Build GROUP BY clause
        group_clause = ""
        if group_by:
            group_clause = f"GROUP BY {', '.join(group_by)}"

        # Build HAVING clause
        having_clause = ""
        if having:
            having_conditions = []
            for condition in having:
                # Simple parsing - in practice, you'd need more sophisticated parsing
                having_conditions.append(condition)
            if having_conditions:
                having_clause = f"HAVING {' AND '.join(having_conditions)}"

        # Build ORDER BY clause
        order_clause = ""
        if order_by:
            order_parts = []
            for field, direction in order_by:
                order_parts.append(f"{field} {'DESC' if direction == -1 else 'ASC'}")
            order_clause = f"ORDER BY {', '.join(order_parts)}"

        # Build LIMIT and OFFSET clauses
        limit_clause = f"LIMIT {limit}" if limit else ""
        offset_clause = f"OFFSET {offset}" if offset else ""

        # Combine all parts
        query = f"{select_clause} {from_clause} {where_clause} {group_clause} {having_clause} {order_clause} {limit_clause} {offset_clause}".strip()

        # Execute query
        async with self.pool.acquire() as connection:
            results = await connection.fetch(query, *params)
            return [dict(row) for row in results]

    async def _create_connection(self) -> Any:
        """Create a new PostgreSQL connection for pooling"""
        import asyncpg
        params = self.config.get_connection_params()
        return await asyncpg.connect(**params)

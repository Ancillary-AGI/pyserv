from typing import List, Dict, Any, AsyncGenerator, Type, Optional, Tuple
import aiomysql
from contextlib import asynccontextmanager
from pyserv.database.config import DatabaseConfig
from pyserv.utils.types import Field, StringField, IntegerField, BooleanField, DateTimeField, FieldType


class MySQLBackend:
    """MySQL database backend"""

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.pool = None

    async def connect(self) -> None:
        """Connect to the database"""
        params = self.config.get_connection_params()
        self.pool = await aiomysql.create_pool(
            host=params['host'],
            port=params['port'],
            user=params['user'],
            password=params['password'],
            db=params['database'],
            autocommit=True
        )

    async def disconnect(self) -> None:
        """Disconnect from the database"""
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()

    async def execute_query(self, query: str, params: tuple = None) -> Any:
        """Execute a SQL query"""
        async with self.pool.acquire() as connection:
            async with connection.cursor(aiomysql.DictCursor) as cursor:
                if params:
                    await cursor.execute(query, params)
                else:
                    await cursor.execute(query)
                return cursor

    async def create_table(self, model_class: Type) -> None:
        """Create a table for the model"""
        fields = []
        for name, field in model_class._fields.items():
            field_def = f"{name} {self.get_sql_type(field)}"
            if field.primary_key:
                field_def += " PRIMARY KEY"
                if field.autoincrement:
                    field_def += " AUTO_INCREMENT"
            if not field.nullable:
                field_def += " NOT NULL"
            if field.default is not None:
                field_def += f" DEFAULT {self._format_default(field.default)}"
            fields.append(field_def)

        query = f"CREATE TABLE IF NOT EXISTS {model_class.get_table_name()} ({', '.join(fields)}) ENGINE=InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        await self.execute_query(query)

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[Any, None]:
        """Get a database connection context manager"""
        async with self.pool.acquire() as connection:
            async with connection.cursor(aiomysql.DictCursor) as cursor:
                yield cursor

    async def get_param_placeholder(self, index: int) -> str:
        """Get parameter placeholder for MySQL"""
        return "%s"

    def get_sql_type(self, field: Field) -> str:
        """Get SQL type for a field"""
        if isinstance(field, StringField):
            if field.max_length:
                return f"VARCHAR({field.max_length})"
            return "TEXT"
        elif isinstance(field, IntegerField):
            return "INT"
        elif isinstance(field, BooleanField):
            return "TINYINT(1)"
        elif isinstance(field, DateTimeField):
            return "DATETIME"
        elif field.field_type == FieldType.UUID:
            return "CHAR(36)"
        elif field.field_type == FieldType.JSON:
            return "JSON"
        elif field.field_type == FieldType.FLOAT:
            return "FLOAT"
        return "TEXT"

    async def insert_one(self, model_class: Type, data: Dict[str, Any]) -> Any:
        """Insert a single record"""
        fields = list(data.keys())
        values = list(data.values())
        placeholders = ', '.join([self.get_param_placeholder(i+1) for i in range(len(fields))])
        query = f"INSERT INTO {model_class.get_table_name()} ({', '.join(fields)}) VALUES ({placeholders})"

        async with self.pool.acquire() as connection:
            async with connection.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, values)
                await connection.commit()
                return cursor.lastrowid

    async def update_one(self, model_class: Type, filters: Dict[str, Any], data: Dict[str, Any]) -> bool:
        """Update a single record"""
        set_clause = ', '.join([f"{k} = {self.get_param_placeholder(i+1)}" for i, k in enumerate(data.keys())])
        where_clause = ' AND '.join([f"{k} = {self.get_param_placeholder(len(data) + i + 1)}" for i, k in enumerate(filters.keys())])
        query = f"UPDATE {model_class.get_table_name()} SET {set_clause} WHERE {where_clause}"

        params = tuple(list(data.values()) + list(filters.values()))
        async with self.pool.acquire() as connection:
            async with connection.cursor(aiomysql.DictCursor) as cursor:
                result = await cursor.execute(query, params)
                await connection.commit()
                return cursor.rowcount > 0

    async def delete_one(self, model_class: Type, filters: Dict[str, Any]) -> bool:
        """Delete a single record"""
        where_clause = ' AND '.join([f"{k} = {self.get_param_placeholder(i+1)}" for i, k in enumerate(filters.keys())])
        query = f"DELETE FROM {model_class.get_table_name()} WHERE {where_clause}"

        async with self.pool.acquire() as connection:
            async with connection.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, tuple(filters.values()))
                await connection.commit()
                return cursor.rowcount > 0

    async def find_one(self, model_class: Type, filters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find a single record"""
        where_clause = ' AND '.join([f"{k} = {self.get_param_placeholder(i+1)}" for i, k in enumerate(filters.keys())])
        query = f"SELECT * FROM {model_class.get_table_name()} WHERE {where_clause} LIMIT 1"

        async with self.pool.acquire() as connection:
            async with connection.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, tuple(filters.values()))
                result = await cursor.fetchone()
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
            async with connection.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, tuple(filters.values()) if filters else None)
                results = await cursor.fetchall()
                return [dict(row) for row in results]

    async def count(self, model_class: Type, filters: Dict[str, Any]) -> int:
        """Count records matching filters"""
        where_clause = ' AND '.join([f"{k} = {self.get_param_placeholder(i+1)}" for i, k in enumerate(filters.keys())]) if filters else ""
        query = f"SELECT COUNT(*) as count FROM {model_class.get_table_name()}"
        if where_clause:
            query += f" WHERE {where_clause}"

        async with self.pool.acquire() as connection:
            async with connection.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, tuple(filters.values()) if filters else None)
                result = await cursor.fetchone()
                return result['count'] if result else 0

    async def aggregate(self, model_class: Type, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Perform aggregation operations using MySQL"""
        # For MySQL, we can implement basic aggregations
        if not pipeline:
            return []

        # This is a simplified implementation
        agg_query = pipeline[0]
        if '$group' in agg_query:
            group_fields = agg_query['$group']
            # Implement basic GROUP BY aggregations
            select_parts = []

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
                    async with connection.cursor(aiomysql.DictCursor) as cursor:
                        await cursor.execute(query)
                        results = await cursor.fetchall()
                        return [dict(row) for row in results]

        return []

    def _format_default(self, default: Any) -> str:
        """Format default value for MySQL"""
        if isinstance(default, str):
            if default.upper() in ['CURRENT_TIMESTAMP', 'CURRENT_DATE']:
                return default
            return f"'{default}'"
        elif isinstance(default, bool):
            return '1' if default else '0'
        elif default is None:
            return 'NULL'
        return str(default)

    async def create_migrations_table(self) -> None:
        """Create the migrations tracking table for MySQL"""
        query = '''
            CREATE TABLE IF NOT EXISTS migrations (
                id INT AUTO_INCREMENT PRIMARY KEY,
                migration_id VARCHAR(255) UNIQUE,
                model_name VARCHAR(255) NOT NULL,
                version INT NOT NULL,
                schema_definition TEXT NOT NULL,
                operations TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(model_name, version)
            ) ENGINE=InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        '''
        await self.execute_query(query)

    async def insert_migration_record(self, model_name: str, version: int, schema_definition: dict, operations: dict, migration_id: str = None) -> None:
        """Insert a migration record for MySQL"""
        import json
        if migration_id:
            query = '''
                INSERT INTO migrations (migration_id, model_name, version, schema_definition, operations)
                VALUES (%s, %s, %s, %s, %s)
            '''
            params = (migration_id, model_name, version, json.dumps(schema_definition), json.dumps(operations))
        else:
            query = '''
                INSERT INTO migrations (model_name, version, schema_definition, operations)
                VALUES (%s, %s, %s, %s)
            '''
            params = (model_name, version, json.dumps(schema_definition), json.dumps(operations))
        await self.execute_query(query, params)

    async def get_applied_migrations(self) -> Dict[str, int]:
        """Get all applied migrations for MySQL"""
        import json
        query = "SELECT model_name, version, schema_definition FROM migrations"
        cursor = await self.execute_query(query)

        migrations = {}
        if hasattr(cursor, 'fetchall'):
            rows = await cursor.fetchall()
        else:
            rows = cursor

        for row in rows:
            migrations[row['model_name']] = row['version']
        return migrations

    async def delete_migration_record(self, model_name: str, version: int) -> None:
        """Delete a migration record for MySQL"""
        query = "DELETE FROM migrations WHERE model_name = %s AND version = %s"
        await self.execute_query(query, (model_name, version))

    async def drop_table(self, table_name: str) -> None:
        """Drop a table for MySQL"""
        query = f"DROP TABLE IF EXISTS {table_name}"
        await self.execute_query(query)

    async def add_column(self, table_name: str, column_name: str, column_definition: str) -> None:
        """Add a column to a table for MySQL"""
        query = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
        await self.execute_query(query)

    async def drop_column(self, table_name: str, column_name: str) -> None:
        """Drop a column from a table for MySQL"""
        query = f"ALTER TABLE {table_name} DROP COLUMN {column_name}"
        await self.execute_query(query)

    async def modify_column(self, table_name: str, column_name: str, column_definition: str) -> None:
        """Modify a column in a table for MySQL"""
        query = f"ALTER TABLE {table_name} MODIFY COLUMN {column_name} {column_definition}"
        await self.execute_query(query)

    async def create_index(self, table_name: str, index_name: str, columns: List[str]) -> None:
        """Create an index on a table for MySQL"""
        column_list = ', '.join(columns)
        query = f"CREATE INDEX {index_name} ON {table_name} ({column_list}) USING BTREE"
        await self.execute_query(query)

    async def drop_index(self, table_name: str, index_name: str) -> None:
        """Drop an index from a table for MySQL"""
        query = f"DROP INDEX {index_name} ON {table_name}"
        await self.execute_query(query)

    async def execute_query_builder(self, model_class: Type, query_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute a complex query built by QueryBuilder for MySQL"""
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
        if filters:
            conditions = []
            for key, value in filters.items():
                if isinstance(value, dict):
                    # Handle MongoDB-style operators
                    for op, val in value.items():
                        if op == '$gt':
                            conditions.append(f"{key} > %s")
                            params.append(val)
                        elif op == '$lt':
                            conditions.append(f"{key} < %s")
                            params.append(val)
                        elif op == '$gte':
                            conditions.append(f"{key} >= %s")
                            params.append(val)
                        elif op == '$lte':
                            conditions.append(f"{key} <= %s")
                            params.append(val)
                        elif op == '$ne':
                            conditions.append(f"{key} != %s")
                            params.append(val)
                        elif op == '$in':
                            placeholders = ', '.join(['%s' for _ in val])
                            conditions.append(f"{key} IN ({placeholders})")
                            params.extend(val)
                        elif op == '$regex':
                            conditions.append(f"{key} LIKE %s")
                            params.append(val.replace('.*', '%'))
                else:
                    conditions.append(f"{key} = %s")
                    params.append(value)
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
            async with connection.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query, tuple(params))
                results = await cursor.fetchall()
                return [dict(row) for row in results]





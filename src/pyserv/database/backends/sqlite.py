from typing import List, Dict, Any, AsyncGenerator, Type, Optional, Tuple
import sqlite3
from contextlib import asynccontextmanager
from pyserv.database.config import DatabaseConfig
from pyserv.utils.types import Field, StringField, IntegerField, BooleanField, DateTimeField, FieldType


class SQLiteBackend:
    """SQLite database backend"""

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.connection = None

    async def connect(self) -> None:
        """Connect to the database"""
        self.connection = sqlite3.connect(self.config.database)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")

    async def disconnect(self) -> None:
        """Disconnect from the database"""
        if self.connection:
            self.connection.close()

    async def execute_query(self, query: str, params: tuple = None) -> Any:
        """Execute a SQL query"""
        cursor = self.connection.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return cursor

    async def create_table(self, model_class: Type) -> None:
        """Create a table for the model"""
        fields = []
        for name, field in model_class._fields.items():
            field_def = f"{name} {self.get_sql_type(field)}"
            if field.primary_key:
                field_def += " PRIMARY KEY"
                if field.autoincrement:
                    field_def += " AUTOINCREMENT"
            if not field.nullable:
                field_def += " NOT NULL"
            if field.default is not None:
                field_def += f" DEFAULT {self._format_default(field.default)}"
            fields.append(field_def)

        query = f"CREATE TABLE IF NOT EXISTS {model_class.get_table_name()} ({', '.join(fields)})"
        await self.execute_query(query)
        self.connection.commit()

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[Any, None]:
        """Get a database connection context manager"""
        if not self.connection:
            await self.connect()
        try:
            yield self.connection
        finally:
            pass  # SQLite connections are not pooled

    async def get_param_placeholder(self, index: int) -> str:
        """Get parameter placeholder for SQLite"""
        return "?"

    def get_sql_type(self, field: Field) -> str:
        """Get SQL type for a field"""
        if isinstance(field, StringField):
            if field.max_length:
                return f"VARCHAR({field.max_length})"
            return "TEXT"
        elif isinstance(field, IntegerField):
            return "INTEGER"
        elif isinstance(field, BooleanField):
            return "INTEGER"  # SQLite uses INTEGER for boolean
        elif isinstance(field, DateTimeField):
            return "DATETIME"
        elif field.field_type == FieldType.UUID:
            return "TEXT"
        elif field.field_type == FieldType.JSON:
            return "TEXT"
        elif field.field_type == FieldType.FLOAT:
            return "REAL"
        return "TEXT"

    async def insert_one(self, model_class: Type, data: Dict[str, Any]) -> Any:
        """Insert a single record"""
        fields = list(data.keys())
        values = list(data.values())
        placeholders = ', '.join([self.get_param_placeholder(i+1) for i in range(len(fields))])
        query = f"INSERT INTO {model_class.get_table_name()} ({', '.join(fields)}) VALUES ({placeholders})"

        cursor = await self.execute_query(query, tuple(values))
        self.connection.commit()
        return cursor.lastrowid

    async def update_one(self, model_class: Type, filters: Dict[str, Any], data: Dict[str, Any]) -> bool:
        """Update a single record"""
        set_clause = ', '.join([f"{k} = {self.get_param_placeholder(i+1)}" for i, k in enumerate(data.keys())])
        where_clause = ' AND '.join([f"{k} = {self.get_param_placeholder(len(data) + i + 1)}" for i, k in enumerate(filters.keys())])
        query = f"UPDATE {model_class.get_table_name()} SET {set_clause} WHERE {where_clause}"

        params = tuple(list(data.values()) + list(filters.values()))
        cursor = await self.execute_query(query, params)
        self.connection.commit()
        return cursor.rowcount > 0

    async def delete_one(self, model_class: Type, filters: Dict[str, Any]) -> bool:
        """Delete a single record"""
        where_clause = ' AND '.join([f"{k} = {self.get_param_placeholder(i+1)}" for i, k in enumerate(filters.keys())])
        query = f"DELETE FROM {model_class.get_table_name()} WHERE {where_clause}"

        cursor = await self.execute_query(query, tuple(filters.values()))
        self.connection.commit()
        return cursor.rowcount > 0

    async def find_one(self, model_class: Type, filters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find a single record"""
        where_clause = ' AND '.join([f"{k} = {self.get_param_placeholder(i+1)}" for i, k in enumerate(filters.keys())])
        query = f"SELECT * FROM {model_class.get_table_name()} WHERE {where_clause} LIMIT 1"

        cursor = await self.execute_query(query, tuple(filters.values()))
        row = cursor.fetchone()
        return dict(row) if row else None

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

        cursor = await self.execute_query(query, tuple(filters.values()) if filters else None)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    async def count(self, model_class: Type, filters: Dict[str, Any]) -> int:
        """Count records matching filters"""
        where_clause = ' AND '.join([f"{k} = {self.get_param_placeholder(i+1)}" for i, k in enumerate(filters.keys())]) if filters else ""
        query = f"SELECT COUNT(*) as count FROM {model_class.get_table_name()}"
        if where_clause:
            query += f" WHERE {where_clause}"

        cursor = await self.execute_query(query, tuple(filters.values()) if filters else None)
        row = cursor.fetchone()
        return row['count'] if row else 0

    async def aggregate(self, model_class: Type, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Perform aggregation operations - SQLite has limited aggregation support"""
        # For SQLite, we'll implement basic aggregation
        if not pipeline:
            return []

        # Simple implementation for basic aggregations
        agg_query = pipeline[0]
        if '$group' in agg_query:
            group_fields = agg_query['$group']
            # This is a simplified implementation
            # In a real implementation, you'd need more complex SQL generation
            return []

        return []

    def _format_default(self, default: Any) -> str:
        """Format default value for SQLite"""
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
        """Create the migrations tracking table for SQLite"""
        query = '''
            CREATE TABLE IF NOT EXISTS migrations (
                id INTEGER PRIMARY KEY,
                migration_id TEXT UNIQUE,
                model_name TEXT NOT NULL,
                version INTEGER NOT NULL,
                schema_definition TEXT NOT NULL,
                operations TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(model_name, version)
            )
        '''
        await self.execute_query(query)
        self.connection.commit()

    async def insert_migration_record(self, model_name: str, version: int, schema_definition: dict, operations: dict, migration_id: str = None) -> None:
        """Insert a migration record for SQLite"""
        import json
        if migration_id:
            query = '''
                INSERT INTO migrations (migration_id, model_name, version, schema_definition, operations)
                VALUES (?, ?, ?, ?, ?)
            '''
            params = (migration_id, model_name, version, json.dumps(schema_definition), json.dumps(operations))
        else:
            query = '''
                INSERT INTO migrations (model_name, version, schema_definition, operations)
                VALUES (?, ?, ?, ?)
            '''
            params = (model_name, version, json.dumps(schema_definition), json.dumps(operations))
        await self.execute_query(query, params)
        self.connection.commit()

    async def get_applied_migrations(self) -> Dict[str, int]:
        """Get all applied migrations for SQLite"""
        import json
        query = "SELECT model_name, version, schema_definition FROM migrations"
        cursor = await self.execute_query(query)
        rows = cursor.fetchall()

        migrations = {}
        for row in rows:
            migrations[row['model_name']] = row['version']
        return migrations

    async def delete_migration_record(self, model_name: str, version: int) -> None:
        """Delete a migration record for SQLite"""
        query = "DELETE FROM migrations WHERE model_name = ? AND version = ?"
        await self.execute_query(query, (model_name, version))
        self.connection.commit()

    async def drop_table(self, table_name: str) -> None:
        """Drop a table for SQLite"""
        query = f"DROP TABLE IF EXISTS {table_name}"
        await self.execute_query(query)
        self.connection.commit()

    async def add_column(self, table_name: str, column_name: str, column_definition: str) -> None:
        """Add a column to a table for SQLite"""
        query = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
        await self.execute_query(query)
        self.connection.commit()

    async def drop_column(self, table_name: str, column_name: str) -> None:
        """Drop a column from a table for SQLite (requires table recreation)"""
        # SQLite doesn't support DROP COLUMN directly, so we need to recreate the table
        # This is a simplified implementation - in practice, you'd need to handle all columns
        temp_table = f"{table_name}_temp"

        # Get current schema
        cursor = await self.execute_query(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()

        # Create new column list without the dropped column
        new_columns = [col for col in columns if col['name'] != column_name]

        if new_columns:
            # Create temporary table
            column_defs = ', '.join([f"{col['name']} {col['type']}" for col in new_columns])
            await self.execute_query(f"CREATE TABLE {temp_table} ({column_defs})")

            # Copy data
            column_names = ', '.join([col['name'] for col in new_columns])
            await self.execute_query(f"INSERT INTO {temp_table} ({column_names}) SELECT {column_names} FROM {table_name}")

            # Drop old table and rename new one
            await self.execute_query(f"DROP TABLE {table_name}")
            await self.execute_query(f"ALTER TABLE {temp_table} RENAME TO {table_name}")

        self.connection.commit()

    async def modify_column(self, table_name: str, column_name: str, column_definition: str) -> None:
        """Modify a column in a table for SQLite (requires table recreation)"""
        # Similar to drop_column, SQLite requires table recreation for column modifications
        temp_table = f"{table_name}_temp"

        # Get current schema
        cursor = await self.execute_query(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()

        # Create new column definitions
        column_defs = []
        for col in columns:
            if col['name'] == column_name:
                column_defs.append(f"{column_name} {column_definition}")
            else:
                column_defs.append(f"{col['name']} {col['type']}")

        # Create temporary table
        await self.execute_query(f"CREATE TABLE {temp_table} ({', '.join(column_defs)})")

        # Copy data
        column_names = ', '.join([col['name'] for col in columns])
        await self.execute_query(f"INSERT INTO {temp_table} ({column_names}) SELECT {column_names} FROM {table_name}")

        # Drop old table and rename new one
        await self.execute_query(f"DROP TABLE {table_name}")
        await self.execute_query(f"ALTER TABLE {temp_table} RENAME TO {table_name}")

        self.connection.commit()

    async def create_index(self, table_name: str, index_name: str, columns: List[str]) -> None:
        """Create an index on a table for SQLite"""
        column_list = ', '.join(columns)
        query = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} ({column_list})"
        await self.execute_query(query)
        self.connection.commit()

    async def drop_index(self, table_name: str, index_name: str) -> None:
        """Drop an index from a table for SQLite"""
        query = f"DROP INDEX IF EXISTS {index_name}"
        await self.execute_query(query)
        self.connection.commit()

    async def add_field(self, model_name: str, field_name: str, field: Field) -> None:
        """Add a field to an existing model/table for SQLite"""
        table_name = model_name.lower() + 's'  # Follow convention
        column_definition = f"{field_name} {self.get_sql_type(field)}"

        if field.primary_key:
            column_definition += " PRIMARY KEY"
            if field.autoincrement:
                column_definition += " AUTOINCREMENT"

        if not field.nullable:
            column_definition += " NOT NULL"

        if field.default is not None:
            column_definition += f" DEFAULT {self._format_default(field.default)}"

        query = f"ALTER TABLE {table_name} ADD COLUMN {column_definition}"
        await self.execute_query(query)
        self.connection.commit()

    async def remove_field(self, model_name: str, field_name: str) -> None:
        """Remove a field from an existing model/table for SQLite"""
        table_name = model_name.lower() + 's'  # Follow convention
        await self.drop_column(table_name, field_name)

    async def alter_field(self, model_name: str, field_name: str, field: Field) -> None:
        """Alter an existing field in a model/table for SQLite"""
        table_name = model_name.lower() + 's'  # Follow convention
        await self.modify_column(table_name, field_name, self.get_sql_type(field))

    def get_type_mappings(self) -> Dict[Any, str]:
        """Get SQLite-specific type mappings"""
        from ...utils.types import FieldType
        return {
            FieldType.BOOLEAN: "INTEGER",
            FieldType.UUID: "TEXT",
            FieldType.JSON: "TEXT",
            FieldType.TIMESTAMPTZ: "TEXT",
            FieldType.BLOB: "BLOB",
            FieldType.BYTEA: "BLOB",
        }

    def format_default_value(self, value: Any) -> str:
        """Format default value for SQLite"""
        from decimal import Decimal
        if isinstance(value, str):
            if value.upper() in ['CURRENT_TIMESTAMP', 'CURRENT_DATE']:
                return value
            return f"'{value}'"
        elif isinstance(value, (int, float, Decimal)):
            return str(value)
        elif isinstance(value, bool):
            return '1' if value else '0'
        elif value is None:
            return 'NULL'
        return f"'{str(value)}'"

    def format_foreign_key(self, foreign_key: str) -> str:
        """Format foreign key constraint for SQLite"""
        ref_table, ref_column = foreign_key.split('.')
        return f"REFERENCES {ref_table}({ref_column})"

    async def execute_query_builder(self, model_class: Type, query_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute a complex query built by QueryBuilder for SQLite"""
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
                            conditions.append(f"{key} > ?")
                            params.append(val)
                        elif op == '$lt':
                            conditions.append(f"{key} < ?")
                            params.append(val)
                        elif op == '$gte':
                            conditions.append(f"{key} >= ?")
                            params.append(val)
                        elif op == '$lte':
                            conditions.append(f"{key} <= ?")
                            params.append(val)
                        elif op == '$ne':
                            conditions.append(f"{key} != ?")
                            params.append(val)
                        elif op == '$in':
                            placeholders = ', '.join(['?' for _ in val])
                            conditions.append(f"{key} IN ({placeholders})")
                            params.extend(val)
                        elif op == '$regex':
                            conditions.append(f"{key} LIKE ?")
                            params.append(val.replace('.*', '%'))
                else:
                    conditions.append(f"{key} = ?")
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
        cursor = await self.execute_query(query, tuple(params) if params else None)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

from typing import List, Dict, Any, AsyncGenerator, Type, Optional, Tuple
from motor.motor_asyncio import AsyncIOMotorClient
from contextlib import asynccontextmanager
from pymongo import ASCENDING, DESCENDING
from bson import ObjectId
from pyserv.database.config import DatabaseConfig
from pyserv.utils.types import Field


class MongoDBBackend:
    """MongoDB database backend"""

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.client = None
        self.db = None

    async def connect(self) -> None:
        """Connect to the database"""
        params = self.config.get_connection_params()
        self.client = AsyncIOMotorClient(
            host=params['host'],
            port=params['port'],
            username=params['username'],
            password=params['password'],
            authSource=params['authSource']
        )
        self.db = self.client[self.config.database]

    async def disconnect(self) -> None:
        """Disconnect from the database"""
        if self.client:
            self.client.close()

    async def execute_query(self, query: str, params: tuple = None) -> Any:
        """Execute a query (not applicable for MongoDB - placeholder)"""
        # MongoDB doesn't use SQL queries, so this is a no-op
        return None

    async def create_table(self, model_class: Type) -> None:
        """Create indexes for the model (MongoDB collections are created automatically)"""
        collection = self.db[model_class.get_table_name()]

        # Create indexes based on field definitions
        indexes = []
        for name, field in model_class._fields.items():
            if field.index or field.primary_key:
                indexes.append((name, ASCENDING))
            if field.unique and not field.primary_key:
                await collection.create_index([(name, ASCENDING)], unique=True)

        # Create compound index for primary keys if multiple
        if indexes:
            await collection.create_index(indexes)

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[Any, None]:
        """Get a database connection context manager"""
        if not self.db:
            await self.connect()
        try:
            yield self.db
        finally:
            pass

    async def get_param_placeholder(self, index: int) -> str:
        """Get parameter placeholder (not applicable for MongoDB)"""
        return ""

    def get_sql_type(self, field: Field) -> str:
        """Get SQL type (not applicable for MongoDB)"""
        return ""

    async def insert_one(self, model_class: Type, data: Dict[str, Any]) -> Any:
        """Insert a single document"""
        collection = self.db[model_class.get_table_name()]

        # Convert data to MongoDB format
        mongo_data = self._convert_to_mongo(data)

        result = await collection.insert_one(mongo_data)
        return str(result.inserted_id)

    async def update_one(self, model_class: Type, filters: Dict[str, Any], data: Dict[str, Any]) -> bool:
        """Update a single document"""
        collection = self.db[model_class.get_table_name()]

        # Convert filters and data to MongoDB format
        mongo_filters = self._convert_to_mongo(filters)
        mongo_data = self._convert_to_mongo(data)

        result = await collection.update_one(mongo_filters, {"$set": mongo_data})
        return result.modified_count > 0

    async def delete_one(self, model_class: Type, filters: Dict[str, Any]) -> bool:
        """Delete a single document"""
        collection = self.db[model_class.get_table_name()]

        # Convert filters to MongoDB format
        mongo_filters = self._convert_to_mongo(filters)

        result = await collection.delete_one(mongo_filters)
        return result.deleted_count > 0

    async def find_one(self, model_class: Type, filters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find a single document"""
        collection = self.db[model_class.get_table_name()]

        # Convert filters to MongoDB format
        mongo_filters = self._convert_to_mongo(filters)

        result = await collection.find_one(mongo_filters)
        if result:
            # Convert ObjectId to string and return
            result['_id'] = str(result['_id'])
            return result
        return None

    async def find_many(self, model_class: Type, filters: Dict[str, Any], limit: Optional[int] = None,
                       offset: Optional[int] = None, sort: Optional[List[Tuple[str, int]]] = None) -> List[Dict[str, Any]]:
        """Find multiple documents"""
        collection = self.db[model_class.get_table_name()]

        # Convert filters to MongoDB format
        mongo_filters = self._convert_to_mongo(filters)

        # Build query
        query = collection.find(mongo_filters)

        # Add sorting
        if sort:
            mongo_sort = [(field, ASCENDING if direction == 1 else DESCENDING) for field, direction in sort]
            query = query.sort(mongo_sort)

        # Add pagination
        if offset:
            query = query.skip(offset)
        if limit:
            query = query.limit(limit)

        results = await query.to_list(length=None)

        # Convert ObjectIds to strings
        for result in results:
            if '_id' in result:
                result['_id'] = str(result['_id'])

        return results

    async def count(self, model_class: Type, filters: Dict[str, Any]) -> int:
        """Count documents matching filters"""
        collection = self.db[model_class.get_table_name()]

        # Convert filters to MongoDB format
        mongo_filters = self._convert_to_mongo(filters)

        return await collection.count_documents(mongo_filters)

    async def aggregate(self, model_class: Type, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Perform aggregation operations using MongoDB"""
        collection = self.db[model_class.get_table_name()]

        # MongoDB aggregation pipeline can be used directly
        results = await collection.aggregate(pipeline).to_list(length=None)

        # Convert ObjectIds to strings
        for result in results:
            if '_id' in result and isinstance(result['_id'], ObjectId):
                result['_id'] = str(result['_id'])

        return results

    def _convert_to_mongo(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert data to MongoDB format"""
        mongo_data = {}

        for key, value in data.items():
            if key == 'id' and isinstance(value, str):
                # Convert string ID to ObjectId for MongoDB
                try:
                    mongo_data['_id'] = ObjectId(value)
                except:
                    mongo_data['_id'] = value
            elif key == 'id':
                mongo_data['_id'] = value
            else:
                mongo_data[key] = value

        return mongo_data

    async def get_collection(self, model_class: Type) -> Any:
        """Get the collection for a model"""
        return self.db[model_class.get_table_name()]

    async def create_index(self, model_class: Type) -> None:
        """Create indexes for the model"""
        collection = await self.get_collection(model_class)
        indexes = []
        for name, field in model_class._fields.items():
            if field.primary_key:
                indexes.append((name, ASCENDING))

        for field_name, direction in indexes:
            await collection.create_index([(field_name, direction)])

    async def create_migrations_table(self) -> None:
        """Create the migrations tracking collection for MongoDB"""
        # MongoDB creates collections automatically on first insert
        # We can create an index for efficient querying
        migrations_collection = self.db.migrations
        await migrations_collection.create_index([("model_name", 1), ("version", 1)], unique=True)

    async def insert_migration_record(self, model_name: str, version: int, schema_definition: dict, operations: dict, migration_id: str = None) -> None:
        """Insert a migration record for MongoDB"""
        from datetime import datetime
        migrations_collection = self.db.migrations
        migration_doc = {
            'model_name': model_name,
            'version': version,
            'schema_definition': schema_definition,
            'operations': operations,
            'applied_at': datetime.now()
        }
        if migration_id:
            migration_doc['migration_id'] = migration_id
        await migrations_collection.insert_one(migration_doc)

    async def get_applied_migrations(self) -> Dict[str, int]:
        """Get all applied migrations for MongoDB"""
        migrations_collection = self.db.migrations
        migrations = {}

        async for doc in migrations_collection.find({}):
            migrations[doc['model_name']] = doc['version']

        return migrations

    async def delete_migration_record(self, model_name: str, version: int) -> None:
        """Delete a migration record for MongoDB"""
        migrations_collection = self.db.migrations
        await migrations_collection.delete_one({"model_name": model_name, "version": version})

    async def drop_table(self, table_name: str) -> None:
        """Drop a collection for MongoDB"""
        await self.db[table_name].drop()

    async def add_column(self, table_name: str, column_name: str, column_definition: str) -> None:
        """Add a field to documents for MongoDB (no-op - MongoDB is schemaless)"""
        # MongoDB is schemaless, so adding a column is a no-op
        # Fields are added dynamically when documents are inserted
        pass

    async def drop_column(self, table_name: str, column_name: str) -> None:
        """Remove a field from all documents for MongoDB"""
        collection = self.db[table_name]
        # Use $unset to remove the field from all documents
        await collection.update_many({}, {"$unset": {column_name: ""}})

    async def modify_column(self, table_name: str, column_name: str, column_definition: str) -> None:
        """Modify a field in documents for MongoDB (limited support)"""
        # MongoDB has limited support for field type changes
        # This is a simplified implementation
        collection = self.db[table_name]
        # For now, we'll just log that this operation is not fully supported
        print(f"Warning: Field modification not fully supported in MongoDB for {table_name}.{column_name}")

    async def create_index(self, table_name: str, index_name: str, columns: List[str]) -> None:
        """Create an index on a collection for MongoDB"""
        collection = self.db[table_name]
        # MongoDB doesn't use named indexes in the same way, but we can create compound indexes
        index_spec = [(col, ASCENDING) for col in columns]
        await collection.create_index(index_spec, name=index_name)

    async def drop_index(self, table_name: str, index_name: str) -> None:
        """Drop an index from a collection for MongoDB"""
        collection = self.db[table_name]
        await collection.drop_index(index_name)

    async def execute_query_builder(self, model_class: Type, query_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute a complex query built by QueryBuilder for MongoDB"""
        collection = self.db[model_class.get_table_name()]

        # Extract query parameters
        select_fields = query_params.get('select_fields', [])
        distinct = query_params.get('distinct', False)
        filters = query_params.get('filters', {})
        limit = query_params.get('limit')
        offset = query_params.get('offset')
        order_by = query_params.get('order_by', [])
        group_by = query_params.get('group_by', [])
        having = query_params.get('having', [])

        # Convert filters to MongoDB format
        mongo_filters = self._convert_filters_to_mongo(filters)

        # Build projection (SELECT fields)
        projection = None
        if select_fields:
            projection = {field: 1 for field in select_fields}
            # Add _id if not explicitly excluded
            if '_id' not in projection and '_id' not in [f for f in select_fields if f.startswith('-')]:
                projection['_id'] = 1

        # Build sort specification
        sort_spec = None
        if order_by:
            sort_spec = [(field, ASCENDING if direction == 1 else DESCENDING) for field, direction in order_by]

        # Build aggregation pipeline if needed
        if group_by or having or distinct:
            pipeline = []

            # Add $match stage for filters
            if mongo_filters:
                pipeline.append({"$match": mongo_filters})

            # Add $group stage for GROUP BY
            if group_by:
                group_spec = {"_id": {field: f"${field}" for field in group_by}}
                # Add accumulators for HAVING-like conditions
                if having:
                    # This is a simplified implementation
                    # In practice, you'd need to parse HAVING conditions
                    pass
                pipeline.append({"$group": group_spec})

            # Add $sort stage
            if sort_spec:
                sort_dict = {field: direction for field, direction in sort_spec}
                pipeline.append({"$sort": sort_dict})

            # Add $skip and $limit stages
            if offset:
                pipeline.append({"$skip": offset})
            if limit:
                pipeline.append({"$limit": limit})

            # Execute aggregation
            results = await collection.aggregate(pipeline).to_list(length=None)

        else:
            # Simple find query
            query = collection.find(mongo_filters, projection)

            if sort_spec:
                query = query.sort(sort_spec)

            if offset:
                query = query.skip(offset)

            if limit:
                query = query.limit(limit)

            results = await query.to_list(length=None)

        # Convert ObjectIds to strings
        for result in results:
            if '_id' in result and isinstance(result['_id'], ObjectId):
                result['_id'] = str(result['_id'])

        return results

    def _convert_filters_to_mongo(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Convert query filters to MongoDB format"""
        mongo_filters = {}

        for key, value in filters.items():
            if isinstance(value, dict):
                # Handle MongoDB-style operators
                mongo_filters[key] = value
            else:
                mongo_filters[key] = value

        return mongo_filters

    async def add_field(self, model_name: str, field_name: str, field: Field) -> None:
        """Add a field to documents for MongoDB (no-op - MongoDB is schemaless)"""
        # MongoDB is schemaless, so adding a field is a no-op
        # Fields are added dynamically when documents are inserted
        pass

    async def remove_field(self, model_name: str, field_name: str) -> None:
        """Remove a field from all documents for MongoDB"""
        collection = self.db[model_name.lower() + 's']  # Follow convention
        # Use $unset to remove the field from all documents
        await collection.update_many({}, {"$unset": {field_name: ""}})

    async def alter_field(self, model_name: str, field_name: str, field: Field) -> None:
        """Alter a field in documents for MongoDB (limited support)"""
        # MongoDB has limited support for field type changes
        # This is a simplified implementation
        collection = self.db[model_name.lower() + 's']  # Follow convention
        # For now, we'll just log that this operation is not fully supported
        print(f"Warning: Field modification not fully supported in MongoDB for {model_name}.{field_name}")

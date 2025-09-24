"""
GraphQL schema definition for Pyserv  framework.
Provides type system, schema construction, and field definitions.
"""

from typing import Dict, Any, Optional, List, Callable, Union, Type
import json


class GraphQLError(Exception):
    """GraphQL execution error"""
    pass


class GraphQLType:
    """Base GraphQL type"""
    def __init__(self, name: str):
        self.name = name

    def __str__(self):
        return self.name


# Scalar types
class String(GraphQLType):
    def __init__(self):
        super().__init__("String")

class Int(GraphQLType):
    def __init__(self):
        super().__init__("Int")

class Float(GraphQLType):
    def __init__(self):
        super().__init__("Float")

class Boolean(GraphQLType):
    def __init__(self):
        super().__init__("Boolean")

class ID(GraphQLType):
    def __init__(self):
        super().__init__("ID")


class List(GraphQLType):
    """List type wrapper"""
    def __init__(self, of_type: GraphQLType):
        self.of_type = of_type
        super().__init__(f"[{of_type.name}]")


class Field:
    """GraphQL field definition"""
    def __init__(self, type_: GraphQLType, resolver: Optional[Callable] = None,
                 args: Optional[Dict[str, GraphQLType]] = None,
                 description: Optional[str] = None):
        self.type = type_
        self.resolver = resolver
        self.args = args or {}
        self.description = description


class ObjectType(GraphQLType):
    """GraphQL object type"""
    def __init__(self, name: str, fields: Optional[Dict[str, Field]] = None):
        super().__init__(name)
        self.fields = fields or {}

    def add_field(self, name: str, field: Field):
        """Add field to object type"""
        self.fields[name] = field

    def get_field(self, name: str) -> Optional[Field]:
        """Get field by name"""
        return self.fields.get(name)


class Query(ObjectType):
    """GraphQL Query type"""
    def __init__(self, fields: Optional[Dict[str, Field]] = None):
        super().__init__("Query", fields)


class Mutation(ObjectType):
    """GraphQL Mutation type"""
    def __init__(self, fields: Optional[Dict[str, Field]] = None):
        super().__init__("Mutation", fields)


class Subscription(ObjectType):
    """GraphQL Subscription type"""
    def __init__(self, fields: Optional[Dict[str, Field]] = None):
        super().__init__("Subscription", fields)


class Schema:
    """GraphQL schema definition"""
    def __init__(self, query: Optional[Query] = None,
                 mutation: Optional[Mutation] = None,
                 subscription: Optional[Subscription] = None):
        self.query = query
        self.mutation = mutation
        self.subscription = subscription
        self.types: Dict[str, ObjectType] = {}

        # Register built-in types
        if query:
            self.types["Query"] = query
        if mutation:
            self.types["Mutation"] = mutation
        if subscription:
            self.types["Subscription"] = subscription

    def add_type(self, type_: ObjectType):
        """Add custom type to schema"""
        self.types[type_.name] = type_

    def get_type(self, name: str) -> Optional[ObjectType]:
        """Get type by name"""
        return self.types.get(name)

    def validate(self) -> List[str]:
        """Validate schema"""
        errors = []

        if not self.query:
            errors.append("Schema must have a Query type")

        # Check for duplicate field names
        for type_name, type_obj in self.types.items():
            field_names = set()
            for field_name in type_obj.fields.keys():
                if field_name in field_names:
                    errors.append(f"Duplicate field '{field_name}' in type '{type_name}'")
                field_names.add(field_name)

        return errors

    def to_graphql(self) -> str:
        """Convert schema to GraphQL SDL"""
        lines = []

        # Add types
        for type_name, type_obj in self.types.items():
            lines.append(f"type {type_name} {{")
            for field_name, field in type_obj.fields.items():
                args_str = ""
                if field.args:
                    args_list = []
                    for arg_name, arg_type in field.args.items():
                        args_list.append(f"{arg_name}: {arg_type.name}")
                    args_str = f"({', '.join(args_list)})"

                lines.append(f"  {field_name}{args_str}: {field.type.name}")
            lines.append("}")

        return "\n".join(lines)


class SelectionSet:
    """GraphQL selection set"""
    def __init__(self, selections: List[Dict[str, Any]]):
        self.selections = selections

    def get_field_names(self) -> List[str]:
        """Get field names in selection set"""
        return [sel['name']['value'] for sel in self.selections if 'name' in sel]


class GraphQLDocument:
    """Parsed GraphQL document"""
    def __init__(self, operations: Dict[str, Any]):
        self.operations = operations

    def get_operation(self, operation_name: Optional[str] = None):
        """Get operation by name"""
        if operation_name:
            return self.operations.get(operation_name)
        elif len(self.operations) == 1:
            return list(self.operations.values())[0]
        else:
            raise GraphQLError("Must specify operation name when multiple operations exist")


class GraphQLParser:
    """Simple GraphQL parser"""

    @staticmethod
    def parse(query: str) -> GraphQLDocument:
        """Parse GraphQL query string"""
        # This is a simplified parser - in production you'd use a proper GraphQL parser
        operations = {}

        # Extract operation definitions
        if 'query' in query.lower():
            operations['query'] = {'type': 'query', 'selection_set': []}
        if 'mutation' in query.lower():
            operations['mutation'] = {'type': 'mutation', 'selection_set': []}
        if 'subscription' in query.lower():
            operations['subscription'] = {'type': 'subscription', 'selection_set': []}

        return GraphQLDocument(operations)


class GraphQLResult:
    """GraphQL execution result"""
    def __init__(self, data: Optional[Dict[str, Any]] = None,
                 errors: Optional[List[Dict[str, Any]]] = None):
        self.data = data
        self.errors = errors or []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {}
        if self.data is not None:
            result['data'] = self.data
        if self.errors:
            result['errors'] = self.errors
        return result

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict())





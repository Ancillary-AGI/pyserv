"""
Model factory for creating model classes dynamically.
"""

from typing import Dict, List, Optional, Any, Type, TypeVar
from pyserv.utils.types import Field, Relationship, LazyLoad

T = TypeVar('T', bound='BaseModel')


class ModelFactory:
    """Factory for creating model classes dynamically"""

    @staticmethod
    def create_model(
        name: str,
        fields: Dict[str, Field],
        table_name: Optional[str] = None,
        base_class: Type[T] = None,
        relationships: Optional[Dict[str, Relationship]] = None
    ) -> Type[T]:
        """
        Create a new model class dynamically

        Args:
            name: Name of the model class
            fields: Dictionary of field definitions
            table_name: Optional table name (defaults to lowercase plural of name)
            base_class: Base class to inherit from (defaults to BaseModel)
            relationships: Dictionary of relationship definitions

        Returns:
            A new model class
        """
        if base_class is None:
            # Import here to avoid circular imports
            from pyserv.models.base import BaseModel
            base_class = BaseModel

        attrs = {
            '_columns': fields,
            '_table_name': table_name or f"{name.lower()}s",
            '_relationships': relationships or {}
        }

        # Create lazy loading descriptors for relationships
        for rel_name in (relationships or {}).keys():
            attrs[rel_name] = LazyLoad(rel_name)

        return type(name, (base_class,), attrs)

    @staticmethod
    def extend_model(
        base_model: Type[T],
        name: str,
        additional_fields: Dict[str, Field],
        additional_relationships: Optional[Dict[str, Relationship]] = None
    ) -> Type[T]:
        """
        Extend an existing model with additional fields and relationships

        Args:
            base_model: The base model class to extend
            name: Name of the new model class
            additional_fields: Additional field definitions
            additional_relationships: Additional relationship definitions

        Returns:
            A new model class that extends the base model
        """
        # Merge fields
        merged_fields = {**base_model._columns, **additional_fields}

        # Merge relationships
        merged_relationships = {**(base_model._relationships or {}), **(additional_relationships or {})}

        # Create lazy loading descriptors for new relationships
        attrs = {
            '_columns': merged_fields,
            '_table_name': base_model.get_table_name(),
            '_relationships': merged_relationships
        }

        # Add lazy loading descriptors for new relationships only
        for rel_name in (additional_relationships or {}).keys():
            attrs[rel_name] = LazyLoad(rel_name)

        return type(name, (base_model,), attrs)





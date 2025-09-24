#!/usr/bin/env python3
"""
Test script to verify MetaModel functionality and ClassVar type annotations.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from pyserv.models.base import BaseModel, ModelMeta
from pyserv.utils.types import Field
from typing import get_type_hints, Dict, ClassVar

class TestModel(BaseModel):
    """Test model to verify MetaModel functionality"""

    _columns: ClassVar[Dict[str, Field]] = {
        'id': Field('INTEGER', primary_key=True),
        'name': Field('TEXT'),
        'email': Field('TEXT')
    }
    _table_name: ClassVar[str] = 'test_models'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

def test_classvar_annotations():
    """Test that ClassVar annotations are correctly applied"""
    print("Testing ClassVar annotations...")

    # Check type hints
    hints = get_type_hints(TestModel)
    print(f"Type hints: {hints}")

    # Check that _columns and _table_name are ClassVar
    assert '_columns' in hints
    assert '_table_name' in hints

    # Check class attributes
    assert hasattr(TestModel, '_columns')
    assert hasattr(TestModel, '_table_name')
    assert TestModel._columns == {
        'id': Field('INTEGER', primary_key=True),
        'name': Field('TEXT'),
        'email': Field('TEXT')
    }
    assert TestModel._table_name == 'test_models'

    print("✓ ClassVar annotations working correctly")

def test_metamodel_protection():
    """Test that MetaModel prevents overshadowing of protected attributes"""
    print("Testing MetaModel protection...")

    # Try to create instance with protected attributes in kwargs
    instance = TestModel(
        name="Test User",
        email="test@example.com",
        _columns="should_be_filtered",  # This should be filtered out
        _table_name="should_be_filtered",  # This should be filtered out
        _db_config="should_be_filtered"  # This should be filtered out
    )

    # Check that instance attributes were set for regular fields
    assert hasattr(instance, 'name')
    assert hasattr(instance, 'email')
    assert instance.name == "Test User"
    assert instance.email == "test@example.com"

    # Check that protected attributes were NOT set as instance attributes
    # (they should still be accessible as class attributes)
    assert not hasattr(instance, '_columns') or getattr(instance, '_columns') != "should_be_filtered"
    assert not hasattr(instance, '_table_name') or getattr(instance, '_table_name') != "should_be_filtered"
    assert not hasattr(instance, '_db_config') or getattr(instance, '_db_config') != "should_be_filtered"

    # Check that class attributes are still accessible
    assert TestModel._columns is not None
    assert TestModel._table_name == 'test_models'

    print("✓ MetaModel protection working correctly")

def test_normal_functionality():
    """Test that normal model functionality still works"""
    print("Testing normal model functionality...")

    # Create instance normally
    instance = TestModel(name="Normal User", email="normal@example.com")

    # Check attributes
    assert instance.name == "Normal User"
    assert instance.email == "normal@example.com"

    # Check to_dict works
    data = instance.to_dict()
    assert data['name'] == "Normal User"
    assert data['email'] == "normal@example.com"

    # Check class methods work
    assert TestModel.get_table_name() == 'test_models'
    primary_key = TestModel.get_primary_key()
    assert primary_key == 'id'

    print("✓ Normal functionality working correctly")

def test_inheritance():
    """Test that inheritance works correctly with MetaModel"""
    print("Testing inheritance...")

    class SubTestModel(TestModel):
        _columns: ClassVar[Dict[str, Field]] = {
            **TestModel._columns,
            'age': Field('INTEGER')
        }

    # Check that subclass has merged columns
    assert 'id' in SubTestModel._columns
    assert 'name' in SubTestModel._columns
    assert 'email' in SubTestModel._columns
    assert 'age' in SubTestModel._columns

    # Create instance of subclass
    sub_instance = SubTestModel(name="Sub User", email="sub@example.com", age=25)

    # Check attributes
    assert sub_instance.name == "Sub User"
    assert sub_instance.email == "sub@example.com"
    assert sub_instance.age == 25

    print("✓ Inheritance working correctly")

if __name__ == "__main__":
    print("Running MetaModel tests...\n")

    try:
        test_classvar_annotations()
        test_metamodel_protection()
        test_normal_functionality()
        test_inheritance()

        print("\n🎉 All tests passed! MetaModel implementation is working correctly.")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)





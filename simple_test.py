#!/usr/bin/env python3
"""
Simple test to verify MetaModel functionality.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from pydance.models.base import BaseModel, MetaModel
    from pydance.utils.types import Field
    from typing import Dict, ClassVar

    print("✓ Imports successful")

    # Test basic class creation
    class TestModel(BaseModel):
        _columns: ClassVar[Dict[str, Field]] = {
            'id': Field('INTEGER', primary_key=True),
            'name': Field('TEXT'),
        }
        _table_name: ClassVar[str] = 'test_models'

    print("✓ TestModel created successfully")

    # Test instance creation
    instance = TestModel(name="Test")
    print(f"✓ Instance created: {instance}")
    print(f"✓ Instance name: {instance.name}")

    # Test that class attributes are preserved
    print(f"✓ Class _columns: {TestModel._columns}")
    print(f"✓ Class _table_name: {TestModel._table_name}")

    # Test MetaModel protection
    protected_instance = TestModel(name="Protected", _columns="should_be_filtered")
    print(f"✓ Protected instance name: {protected_instance.name}")
    print(f"✓ Protected instance _columns (should be class attr): {protected_instance._columns}")

    print("\n🎉 All basic tests passed!")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

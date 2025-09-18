#!/usr/bin/env python3
"""
Unit tests for database migration system.
"""

import pytest
import asyncio
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from src.pydance.migrations.migration import Migration
from src.pydance.migrations.migrator import Migrator
from src.pydance.migrations.framework import MigrationFramework
from src.pydance.database.config import DatabaseConfig
from src.pydance.models.base import BaseModel
from src.pydance.utils.types import Field, StringField, IntegerField


class TestMigration:
    """Test Migration class functionality"""

    def test_migration_creation(self):
        """Test creating a migration object"""
        # Create a mock model class
        class MockModel:
            __name__ = "TestModel"
            get_table_name = Mock(return_value="test_models")

        migration = Migration(
            model_class=MockModel,
            from_version=0,
            to_version=1,
            operations={'added_columns': []},
            schema_definition={'id': {'field_type': 'INTEGER', 'primary_key': True}}
        )

        assert migration.model_name == "TestModel"
        assert migration.from_version == 0
        assert migration.to_version == 1
        assert migration.operations == {'added_columns': []}
        assert migration.is_upgrade() is True
        assert migration.is_downgrade() is False
        assert migration.is_initial() is True

    def test_migration_directions(self):
        """Test migration direction detection"""
        class MockModel:
            __name__ = "TestModel"
            get_table_name = Mock(return_value="test_models")

        # Upgrade migration
        upgrade = Migration(MockModel, 0, 1, {}, {})
        assert upgrade.is_upgrade() is True
        assert upgrade.is_downgrade() is False

        # Downgrade migration
        downgrade = Migration(MockModel, 1, 0, {}, {})
        assert downgrade.is_upgrade() is False
        assert downgrade.is_downgrade() is True

        # Same version (no change)
        no_change = Migration(MockModel, 1, 1, {}, {})
        assert no_change.is_upgrade() is False
        assert no_change.is_downgrade() is False

    def test_migration_operations(self):
        """Test migration operations access"""
        class MockModel:
            __name__ = "TestModel"
            get_table_name = Mock(return_value="test_models")

        operations = {
            'added_columns': [{'name': 'new_field'}],
            'removed_columns': [{'name': 'old_field'}],
            'modified_columns': [{'name': 'changed_field'}],
            'added_indexes': [{'name': 'new_index'}],
            'removed_indexes': [{'name': 'old_index'}]
        }

        migration = Migration(MockModel, 0, 1, operations, {})

        assert migration.get_added_columns() == [{'name': 'new_field'}]
        assert migration.get_removed_columns() == [{'name': 'old_field'}]
        assert migration.get_modified_columns() == [{'name': 'changed_field'}]
        assert migration.get_added_indexes() == [{'name': 'new_index'}]
        assert migration.get_removed_indexes() == [{'name': 'old_index'}]

    def test_migration_serialization(self):
        """Test migration to/from dict conversion"""
        class MockModel:
            __name__ = "TestModel"
            get_table_name = Mock(return_value="test_models")

        original = Migration(
            model_class=MockModel,
            from_version=0,
            to_version=1,
            operations={'test': 'data'},
            schema_definition={'field': 'definition'}
        )

        # Convert to dict
        data = original.to_dict()
        assert data['model_name'] == 'TestModel'
        assert data['from_version'] == 0
        assert data['to_version'] == 1
        assert data['operations'] == {'test': 'data'}
        assert data['is_upgrade'] is True

        # Convert back from dict
        restored = Migration.from_dict(data, MockModel)
        assert restored.model_name == original.model_name
        assert restored.from_version == original.from_version
        assert restored.to_version == original.to_version
        assert restored.operations == original.operations


class TestMigrator:
    """Test Migrator class functionality"""

    @pytest.fixture
    def db_config(self):
        """Create a test database config"""
        return DatabaseConfig('sqlite:///:memory:')

    @pytest.fixture
    def migrator(self, db_config):
        """Create a test migrator instance"""
        return Migrator.get_instance(db_config)

    def test_migrator_initialization(self, migrator):
        """Test migrator initialization"""
        assert migrator.db_config is not None
        assert migrator.applied_migrations == {}
        assert migrator.migration_schemas == {}

    @patch('src.pydance.migrations.migrator.DatabaseConnection')
    async def test_initialize_sqlite(self, mock_db_conn, migrator):
        """Test SQLite initialization"""
        migrator.db_config.is_sqlite = True
        migrator.db_config.is_postgres = False
        migrator.db_config.is_mysql = False
        migrator.db_config.is_mongodb = False

        mock_conn = Mock()
        mock_db_conn.get_instance.return_value.get_connection.return_value.__aenter__ = Mock(return_value=mock_conn)
        mock_db_conn.get_instance.return_value.get_connection.return_value.__aexit__ = Mock(return_value=None)

        await migrator.initialize()

        # Verify SQLite-specific calls were made
        mock_conn.execute.assert_called()

    def test_get_current_version(self, migrator):
        """Test getting current migration version"""
        # Initially should return 0
        assert migrator.get_current_version('TestModel') == 0

        # After setting a version
        migrator.applied_migrations['TestModel'] = 2
        assert migrator.get_current_version('TestModel') == 2

    def test_schema_serialization(self):
        """Test schema serialization/deserialization"""
        fields = {
            'id': Field('INTEGER', primary_key=True),
            'name': StringField(max_length=100),
            'age': IntegerField()
        }

        # Test serialization
        serialized = Migration._serialize_schema(fields)
        assert 'id' in serialized
        assert 'name' in serialized
        assert 'age' in serialized
        assert serialized['id']['primary_key'] is True

        # Test deserialization
        deserialized = Migration._deserialize_field(serialized['id'])
        assert deserialized.primary_key is True
        assert deserialized.field_type == 'INTEGER'


class TestMigrationFramework:
    """Test MigrationFramework functionality"""

    @pytest.fixture
    def db_config(self):
        """Create a test database config"""
        return DatabaseConfig('sqlite:///:memory:')

    @pytest.fixture
    def framework(self, db_config):
        """Create a test framework instance"""
        return MigrationFramework(db_config, 'test_app')

    def test_framework_initialization(self, framework):
        """Test framework initialization"""
        assert framework.db_config is not None
        assert framework.app_package == 'test_app'
        assert framework.discovered_models == []

    @patch('src.pydance.migrations.framework.DatabaseConnection')
    async def test_initialize_framework(self, mock_db_conn, framework):
        """Test framework initialization"""
        mock_conn_instance = Mock()
        mock_db_conn.get_instance.return_value = mock_conn_instance

        await framework.initialize()

        # Verify migrator was initialized
        mock_conn_instance.initialize.assert_called_once()

    def test_schema_serialization(self, framework):
        """Test schema serialization in framework"""
        fields = {
            'id': Field('INTEGER', primary_key=True),
            'name': StringField(max_length=100)
        }

        serialized = framework._serialize_schema(fields)
        assert isinstance(serialized, dict)
        assert 'id' in serialized
        assert 'name' in serialized

    def test_field_serialization(self, framework):
        """Test field serialization in framework"""
        field = Field('TEXT', nullable=False, default='test')
        serialized = framework._serialize_field(field)

        assert serialized['field_type'] == 'TEXT'
        assert serialized['nullable'] is False
        assert serialized['default'] == 'test'


class TestDatabaseConfig:
    """Test DatabaseConfig functionality"""

    def test_sqlite_config(self):
        """Test SQLite database configuration"""
        config = DatabaseConfig('sqlite:///test.db')
        assert config.is_sqlite is True
        assert config.database == 'test.db'
        assert config.get_connection_params() == {'database': 'test.db'}

    def test_postgres_config(self):
        """Test PostgreSQL database configuration"""
        config = DatabaseConfig('postgresql://user:pass@localhost:5432/testdb')
        assert config.is_postgres is True
        assert config.username == 'user'
        assert config.password == 'pass'
        assert config.host == 'localhost'
        assert config.port == 5432
        assert config.database == 'testdb'

    def test_mysql_config(self):
        """Test MySQL database configuration"""
        config = DatabaseConfig('mysql://user:pass@localhost:3306/testdb')
        assert config.is_mysql is True
        assert config.username == 'user'
        assert config.password == 'pass'
        assert config.host == 'localhost'
        assert config.port == 3306
        assert config.database == 'testdb'

    def test_mongodb_config(self):
        """Test MongoDB database configuration"""
        config = DatabaseConfig('mongodb://user:pass@localhost:27017/testdb')
        assert config.is_mongodb is True
        assert config.username == 'user'
        assert config.password == 'pass'
        assert config.host == 'localhost'
        assert config.port == 27017
        assert config.database == 'testdb'


class TestFieldTypes:
    """Test field type functionality"""

    def test_field_creation(self):
        """Test creating different field types"""
        # Integer field
        int_field = IntegerField(primary_key=True, autoincrement=True)
        assert int_field.primary_key is True
        assert int_field.autoincrement is True

        # String field
        str_field = StringField(max_length=255, nullable=False)
        assert str_field.max_length == 255
        assert str_field.nullable is False

        # Boolean field
        bool_field = Field('BOOLEAN', default=True)
        assert bool_field.default is True

    def test_sql_definition_generation(self):
        """Test SQL definition generation for different databases"""
        field = Field('TEXT', nullable=False, default='test')

        # SQLite
        sqlite_config = DatabaseConfig('sqlite:///:memory:')
        sqlite_sql = field.sql_definition('test_field', sqlite_config)
        assert 'NOT NULL' in sqlite_sql
        assert "DEFAULT 'test'" in sqlite_sql

        # PostgreSQL
        pg_config = DatabaseConfig('postgresql://user:pass@localhost/testdb')
        pg_sql = field.sql_definition('test_field', pg_config)
        assert 'NOT NULL' in pg_sql
        assert "DEFAULT 'test'" in pg_sql

        # MySQL
        mysql_config = DatabaseConfig('mysql://user:pass@localhost/testdb')
        mysql_sql = field.sql_definition('test_field', mysql_config)
        assert 'NOT NULL' in mysql_sql
        assert "DEFAULT 'test'" in mysql_sql


# Integration test for the complete migration workflow
class TestMigrationWorkflow:
    """Integration tests for complete migration workflow"""

    @pytest.fixture
    def test_model(self):
        """Create a test model for migration testing"""
        class TestUser(BaseModel):
            _fields = {
                'id': Field('INTEGER', primary_key=True, autoincrement=True),
                'username': StringField(max_length=50, nullable=False),
                'email': StringField(max_length=100, nullable=False),
                'created_at': Field('TIMESTAMP', default='CURRENT_TIMESTAMP')
            }
            _migration_version = 1

        return TestUser

    def test_model_migration_setup(self, test_model):
        """Test that model is properly set up for migrations"""
        assert hasattr(test_model, '_fields')
        assert hasattr(test_model, '_migration_version')
        assert test_model._migration_version == 1
        assert 'id' in test_model._fields
        assert 'username' in test_model._fields
        assert 'email' in test_model._fields

    def test_migration_version_tracking(self, test_model):
        """Test migration version tracking"""
        # Test default version
        assert getattr(test_model, '_migration_version', 1) >= 1

        # Test version comparison
        current_version = 0
        target_version = getattr(test_model, '_migration_version', 1)
        assert target_version > current_version

"""
Unit tests for refactored models
"""
import pytest
import asyncio
from datetime import datetime
from pyserv.models.base import BaseModel
from pyserv.models.user import BaseUser, UserRole, UserStatus
from pyserv.models.factory import ModelFactory
from pyserv.database.config_consolidated import DatabaseConfig
from pyserv.models.base import StringField, IntegerField, BooleanField


class TestModel(BaseModel):
    """Test model for unit tests"""
    _table_name = "test_models"
    
    id = IntegerField(primary_key=True)
    name = StringField(max_length=100)
    active = BooleanField(default=True)


@pytest.fixture
def db_config():
    """Create test database config"""
    return DatabaseConfig(database_url="sqlite:///:memory:")


@pytest.fixture
def setup_model(db_config):
    """Setup test model with database config"""
    TestModel.set_db_config(db_config)
    BaseUser.set_db_config(db_config)


class TestBaseModel:
    """Test BaseModel functionality"""
    
    def test_model_creation(self, setup_model):
        """Test basic model creation"""
        model = TestModel(name="Test", active=True)
        assert model.name == "Test"
        assert model.active is True
    
    def test_model_attributes(self, setup_model):
        """Test model attribute access"""
        model = TestModel(name="Test")
        assert model.name == "Test"
        
        # Test setting attributes
        model.name = "Updated"
        assert model.name == "Updated"
    
    def test_table_name(self, setup_model):
        """Test table name generation"""
        assert TestModel.get_table_name() == "test_models"
    
    def test_to_dict(self, setup_model):
        """Test model to dictionary conversion"""
        model = TestModel(name="Test", active=True)
        data = model.to_dict()
        assert data['name'] == "Test"
        assert data['active'] is True
    
    def test_query_builder(self, setup_model):
        """Test query builder creation"""
        query = TestModel.query()
        assert query.model_class == TestModel


class TestUserModel:
    """Test BaseUser model functionality"""
    
    def test_user_creation(self, setup_model):
        """Test user model creation"""
        user = BaseUser(
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password"
        )
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.role == UserRole.USER
        assert user.status == UserStatus.PENDING
    
    def test_password_hashing(self, setup_model):
        """Test password hashing functionality"""
        password = "test_password123!"
        hashed = BaseUser.hash_password(password)
        assert hashed != password
        assert BaseUser.verify_password_hash(password, hashed)
    
    def test_password_strength_validation(self, setup_model):
        """Test password strength validation"""
        weak_password = "123"
        strong_password = "StrongPass123!"
        
        assert not BaseUser.is_password_strong(weak_password)
        assert BaseUser.is_password_strong(strong_password)
    
    def test_user_methods(self, setup_model):
        """Test user utility methods"""
        user = BaseUser(
            first_name="John",
            last_name="Doe",
            username="johndoe",
            is_active=True,
            status=UserStatus.ACTIVE
        )
        
        assert user.get_full_name() == "John Doe"
        assert user.is_authenticated()
    
    def test_user_permissions(self, setup_model):
        """Test user permission methods"""
        admin_user = BaseUser(is_superuser=True)
        regular_user = BaseUser(is_superuser=False)
        
        assert admin_user.has_permission("any_permission")
        assert not regular_user.has_permission("any_permission")


class TestModelFactory:
    """Test ModelFactory functionality"""
    
    def test_create_dynamic_model(self, setup_model):
        """Test dynamic model creation"""
        fields = {
            'id': IntegerField(primary_key=True),
            'title': StringField(max_length=200),
            'published': BooleanField(default=False)
        }
        
        Article = ModelFactory.create_model(
            name="Article",
            fields=fields,
            table_name="articles"
        )
        
        assert Article._table_name == "articles"
        assert 'title' in Article._fields
        assert 'published' in Article._fields
        
        # Test instance creation
        article = Article(title="Test Article", published=True)
        assert article.title == "Test Article"
        assert article.published is True
    
    def test_extend_model(self, setup_model):
        """Test model extension"""
        additional_fields = {
            'description': StringField(max_length=500),
            'priority': IntegerField(default=1)
        }
        
        ExtendedModel = ModelFactory.extend_model(
            base_model=TestModel,
            name="ExtendedTestModel",
            additional_fields=additional_fields
        )
        
        # Should have original fields
        assert 'name' in ExtendedModel._fields
        assert 'active' in ExtendedModel._fields
        
        # Should have new fields
        assert 'description' in ExtendedModel._fields
        assert 'priority' in ExtendedModel._fields
        
        # Test instance creation
        extended = ExtendedModel(
            name="Test",
            active=True,
            description="Extended model test",
            priority=5
        )
        assert extended.name == "Test"
        assert extended.description == "Extended model test"
        assert extended.priority == 5


@pytest.mark.asyncio
class TestAsyncOperations:
    """Test async database operations (mocked)"""
    
    async def test_query_methods(self, setup_model):
        """Test query method creation"""
        # These would normally interact with database
        # For now, just test that methods exist and return correct types
        query = TestModel.query()
        assert hasattr(query, 'filter')
        assert hasattr(query, 'limit')
        assert hasattr(query, 'offset')
        assert hasattr(query, 'order_by')
        
        # Test method chaining
        chained_query = query.filter(name="test").limit(10).offset(5)
        assert chained_query._limit == 10
        assert chained_query._offset == 5


if __name__ == "__main__":
    pytest.main([__file__])
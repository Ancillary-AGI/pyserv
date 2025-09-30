"""
Integration tests for database-agnostic model operations
"""
import pytest
import asyncio
from pyserv.models.base import BaseModel
from pyserv.models.user import BaseUser, UserRole, UserStatus
from pyserv.database.config_consolidated import DatabaseConfig
from pyserv.models.base import StringField, IntegerField, BooleanField, EmailField


class Product(BaseModel):
    """Test product model"""
    _table_name = "products"
    
    id = IntegerField(primary_key=True)
    name = StringField(max_length=200)
    price = IntegerField()
    in_stock = BooleanField(default=True)


@pytest.fixture(params=[
    "sqlite:///:memory:",
    # Add other database URLs when their connections are implemented
    # "postgresql://user:pass@localhost/test",
    # "mysql://user:pass@localhost/test"
])
def db_config(request):
    """Test with different database backends"""
    return DatabaseConfig(database_url=request.param)


@pytest.fixture
async def setup_models(db_config):
    """Setup models with database configuration"""
    Product.set_db_config(db_config)
    BaseUser.set_db_config(db_config)
    
    # In a real implementation, you would create tables here
    # await Product.get_db_connection().create_table(Product)
    # await BaseUser.get_db_connection().create_table(BaseUser)


@pytest.mark.asyncio
class TestDatabaseAgnosticOperations:
    """Test database operations work across different backends"""
    
    async def test_model_crud_operations(self, setup_models):
        """Test Create, Read, Update, Delete operations"""
        # Test model creation
        product = Product(
            name="Test Product",
            price=1999,
            in_stock=True
        )
        
        # Verify data is set correctly
        assert product.name == "Test Product"
        assert product.price == 1999
        assert product.in_stock is True
        
        # Test to_dict conversion
        data = product.to_dict()
        assert data['name'] == "Test Product"
        assert data['price'] == 1999
        
        # Note: Actual database operations would require
        # implementing the database connection backends
        # await product.save()
        # saved_product = await Product.get(id=product.id)
        # assert saved_product.name == "Test Product"
    
    async def test_user_authentication_flow(self, setup_models):
        """Test user authentication with database operations"""
        # Test user creation with validation
        user_data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'StrongPassword123!',
            'role': UserRole.USER,
            'status': UserStatus.ACTIVE
        }
        
        # This would normally create and save to database
        # user = await BaseUser.create_user(**user_data)
        
        # For now, test the validation logic
        assert BaseUser.is_password_strong(user_data['password'])
        hashed = BaseUser.hash_password(user_data['password'])
        assert BaseUser.verify_password_hash(user_data['password'], hashed)
    
    async def test_query_builder_interface(self, setup_models):
        """Test query builder provides consistent interface"""
        # Test query builder creation
        query = Product.query()
        assert query.model_class == Product
        
        # Test method chaining
        filtered_query = query.filter(in_stock=True).limit(10)
        assert filtered_query._limit == 10
        assert 'in_stock' in filtered_query._filter_criteria
        
        # Test ordering
        ordered_query = query.order_by('name')
        assert len(ordered_query._order_by) == 1
        assert ordered_query._order_by[0][0] == 'name'
    
    async def test_model_relationships(self, setup_models):
        """Test model relationship definitions"""
        # Test that models have field definitions
        assert hasattr(BaseUser, '_fields')
        assert isinstance(BaseUser._fields, dict)
        
        # Test relationship access (would be lazy-loaded in real implementation)
        user = BaseUser(username='testuser')
        # In real implementation: user.sessions would lazy-load related objects
        assert hasattr(user, '_loaded_relations')
    
    async def test_database_config_flexibility(self, setup_models):
        """Test that models work with different database configurations"""
        # Test that models can be configured with different databases
        sqlite_config = DatabaseConfig(database_url="sqlite:///:memory:")
        Product.set_db_config(sqlite_config)
        
        # Test database connection retrieval
        db_connection = Product.get_db_connection()
        assert db_connection is not None
        assert db_connection.config.database_url == "sqlite:///:memory:"
    
    async def test_model_validation(self, setup_models):
        """Test model field validation"""
        # Test email validation in user model
        try:
            from email_validator import validate_email
            # This would be called during user creation
            validate_email("test@example.com")
            valid_email = True
        except:
            valid_email = False
        
        assert valid_email
        
        # Test password strength validation
        weak_passwords = ["123", "password", "abc"]
        strong_passwords = ["StrongPass123!", "MySecure@Pass1"]
        
        for weak in weak_passwords:
            assert not BaseUser.is_password_strong(weak)
        
        for strong in strong_passwords:
            assert BaseUser.is_password_strong(strong)


class TestModelMetaclass:
    """Test model metaclass functionality"""
    
    def test_automatic_table_name_generation(self):
        """Test that table names are generated automatically"""
        class TestModel(BaseModel):
            _columns = {'id': IntegerField(primary_key=True)}
        
        # Should generate table name from class name
        assert TestModel._table_name == "testmodels"
    
    def test_column_inheritance(self):
        """Test that fields are properly inherited"""
        class BaseTestModel(BaseModel):
            id = IntegerField(primary_key=True)
            created_at = StringField()
        
        class ExtendedModel(BaseTestModel):
            name = StringField(max_length=100)
        
        assert 'id' in ExtendedModel._fields
        assert 'created_at' in ExtendedModel._fields
        assert 'name' in ExtendedModel._fields


if __name__ == "__main__":
    pytest.main([__file__])
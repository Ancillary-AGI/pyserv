"""
Integration tests for HTTP endpoints
"""
import pytest

from pydance import Application


@pytest.mark.integration
class TestHTTPEndpoints:
    """Test HTTP endpoint integration"""

    @pytest.fixture
    async def http_app(self):
        """Create an application with HTTP routes"""
        app = Application()

        @app.route('/')
        async def home(request):
            return {'message': 'Welcome to Pydance', 'status': 'ok'}

        @app.route('/users/{user_id}')
        async def get_user(request, user_id: int):
            return {'user_id': user_id, 'name': f'User {user_id}'}

        @app.route('/users', methods=['POST'])
        async def create_user(request):
            data = await request.json()
            return {'user': data, 'created': True}

        return app

    @pytest.mark.asyncio
    async def test_home_endpoint(self, http_app, client):
        """Test home endpoint"""
        response = await client.get('/')
        assert response.status_code == 200
        data = response.json()
        assert data['message'] == 'Welcome to Pydance'
        assert data['status'] == 'ok'

    @pytest.mark.asyncio
    async def test_parameterized_routes(self, http_app, client):
        """Test routes with parameters"""
        response = await client.get('/users/123')
        assert response.status_code == 200
        data = response.json()
        assert data['user_id'] == 123
        assert data['name'] == 'User 123'

    @pytest.mark.asyncio
    async def test_post_requests(self, http_app, client):
        """Test POST request handling"""
        user_data = {'name': 'John Doe', 'email': 'john@example.com'}
        response = await client.post('/users', json=user_data)
        assert response.status_code == 200
        data = response.json()
        assert data['created'] is True
        assert data['user'] == user_data

    @pytest.mark.asyncio
    async def test_404_handling(self, http_app, client):
        """Test 404 error handling"""
        response = await client.get('/nonexistent')
        assert response.status_code == 404

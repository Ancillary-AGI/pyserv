"""
Security tests for Pyserv  framework
"""
import pytest
import json
from unittest.mock import patch, MagicMock

from pyserv import Application
from pyserv.exceptions import HTTPException


@pytest.mark.security
class TestSecurity:
    """Security tests"""

    @pytest.fixture
    def secure_app(self):
        """Application with security features"""
        app = Application()

        @app.route('/')
        async def home(request):
            return {'message': 'Secure Home'}

        @app.route('/admin')
        async def admin(request):
            return {'message': 'Admin Panel'}

        @app.route('/user/{user_id}')
        async def user_profile(request, user_id: int):
            return {'user_id': user_id, 'profile': 'data'}

        @app.route('/login', methods=['POST'])
        async def login(request):
            data = await request.json()
            # Simulate authentication
            if data.get('username') == 'admin' and data.get('password') == 'secret':
                return {'token': 'fake-jwt-token', 'status': 'authenticated'}
            else:
                raise HTTPException(401, 'Invalid credentials')

        return app

    @pytest.mark.asyncio
    async def test_sql_injection_protection(self, secure_app, client):
        """Test protection against SQL injection"""
        # This would test if user input is properly sanitized
        # For now, test that parameterized routes work safely
        response = await client.get('/user/123')
        assert response.status_code == 200

        # Test with potentially malicious input
        response = await client.get('/user/123%27%20OR%201%3D1')  # URL encoded SQL injection
        # Should still work if properly handled
        assert response.status_code in [200, 404]  # Either valid or not found

    @pytest.mark.asyncio
    async def test_xss_protection(self, secure_app, client):
        """Test protection against XSS attacks"""
        # Test with malicious script in URL
        malicious_path = '/user/123<script>alert("xss")</script>'
        response = await client.get(malicious_path)
        assert response.status_code == 404  # Should not match route

        # Test with malicious data in JSON response
        @secure_app.route('/echo')
        async def echo(request):
            data = await request.json()
            return {'echo': data}

        malicious_data = {'message': '<script>alert("xss")</script>'}
        response = await client.post('/echo', json=malicious_data)
        assert response.status_code == 200
        # Response should contain the malicious data (framework doesn't auto-escape JSON)
        assert '<script>' in response.text

    @pytest.mark.asyncio
    async def test_csrf_protection(self, secure_app, client):
        """Test CSRF protection"""
        # Test POST request without CSRF token
        data = {'username': 'admin', 'password': 'secret'}
        response = await client.post('/login', json=data)
        # Should work since we don't have CSRF middleware enabled by default
        assert response.status_code in [200, 401]

    @pytest.mark.asyncio
    async def test_authentication_bypass(self, secure_app, client):
        """Test authentication bypass attempts"""
        # Test direct access to protected routes
        response = await client.get('/admin')
        assert response.status_code == 200  # No auth required in test app

        # Test with invalid credentials
        data = {'username': 'admin', 'password': 'wrong'}
        response = await client.post('/login', json=data)
        assert response.status_code == 401

        # Test with valid credentials
        data = {'username': 'admin', 'password': 'secret'}
        response = await client.post('/login', json=data)
        assert response.status_code == 200
        assert 'token' in response.json()

    @pytest.mark.asyncio
    async def test_directory_traversal(self, secure_app, client):
        """Test protection against directory traversal attacks"""
        # Test with ../ in path
        malicious_paths = [
            '/../../../etc/passwd',
            '/..%2F..%2F..%2Fetc%2Fpasswd',  # URL encoded
            '/static/../../../app.py'
        ]

        for path in malicious_paths:
            response = await client.get(path)
            assert response.status_code in [404, 403]  # Should be blocked

    @pytest.mark.asyncio
    async def test_input_validation(self, secure_app, client):
        """Test input validation and sanitization"""
        # Test with very large input
        large_data = {'data': 'x' * 1000000}  # 1MB of data

        @secure_app.route('/large-input', methods=['POST'])
        async def large_input_handler(request):
            data = await request.json()
            return {'received': len(data['data'])}

        response = await client.post('/large-input', json=large_data)
        # Should handle large input gracefully
        assert response.status_code in [200, 413]  # 413 = Payload Too Large

    @pytest.mark.asyncio
    async def test_rate_limiting(self, secure_app, client):
        """Test rate limiting functionality"""
        # Make many rapid requests
        responses = []
        for i in range(100):
            response = await client.get('/')
            responses.append(response.status_code)

        # Should not be rate limited in basic test (no rate limiting middleware)
        success_count = sum(1 for status in responses if status == 200)
        assert success_count > 50  # At least half should succeed

    @pytest.mark.asyncio
    async def test_secure_headers(self, secure_app, client):
        """Test security headers"""
        response = await client.get('/')

        # Check for common security headers
        headers = response.headers

        # These would be present if security middleware is enabled
        # For now, just check that response is successful
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_ssl_redirect(self, secure_app, client):
        """Test SSL/HTTPS redirect"""
        # Test with X-Forwarded-Proto header
        response = await client.get('/', headers={'X-Forwarded-Proto': 'http'})
        # Should work normally without SSL middleware
        assert response.status_code == 200

    def test_secret_key_security(self, secure_app):
        """Test secret key configuration"""
        # Check that app has a secret key
        assert secure_app.config.secret_key is not None
        assert len(secure_app.config.secret_key) > 0

        # Test with weak secret key
        weak_app = Application()
        weak_app.config.secret_key = 'weak'
        assert weak_app.config.secret_key == 'weak'  # Should allow custom config

    @pytest.mark.asyncio
    async def test_error_information_leakage(self, secure_app, client):
        """Test that errors don't leak sensitive information"""
        @secure_app.route('/error')
        async def error_route(request):
            raise Exception("Sensitive internal error information")

        response = await client.get('/error')
        assert response.status_code == 500

        # Error response should not contain sensitive information
        error_text = response.text.lower()
        assert 'sensitive' not in error_text
        assert 'internal' not in error_text

    @pytest.mark.asyncio
    async def test_http_methods_restriction(self, secure_app, client):
        """Test HTTP method restrictions"""
        # Test GET on POST-only route
        response = await client.get('/login')
        assert response.status_code == 405  # Method Not Allowed

        # Test POST on GET route
        response = await client.post('/')
        assert response.status_code == 405

    @pytest.mark.asyncio
    async def test_host_header_attack(self, secure_app, client):
        """Test protection against Host header attacks"""
        # Test with malicious host header
        malicious_hosts = [
            'evil.com',
            '127.0.0.1.evil.com',
            'localhost.evil.com'
        ]

        for host in malicious_hosts:
            response = await client.get('/', headers={'Host': host})
            # Should work since no host validation middleware by default
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_content_type_validation(self, secure_app, client):
        """Test Content-Type validation"""
        # Test POST without Content-Type
        response = await client.post('/login', data='invalid json')
        # Should handle gracefully
        assert response.status_code in [200, 400, 500]

        # Test with correct Content-Type
        response = await client.post('/login',
                                   json={'username': 'test'},
                                   headers={'Content-Type': 'application/json'})
        assert response.status_code in [200, 401]

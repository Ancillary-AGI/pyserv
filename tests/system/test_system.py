"""
System tests for Pyserv  framework - End-to-end testing
"""
import subprocess
import time
import os
import pytest
import requests
from pathlib import Path


@pytest.mark.system
class TestSystem:
    """System-level tests"""

    @pytest.fixture(scope="class")
    def system_app(self, tmp_path_factory):
        """Create a system test application"""
        app_dir = tmp_path_factory.mktemp("system_app")

        # Create app.py
        app_content = '''
from pyserv import Application

app = Application()

@app.route('/')
async def home(request):
    return {'message': 'System Test App', 'status': 'running'}

@app.route('/health')
async def health(request):
    return {'status': 'healthy'}

@app.route('/users/{user_id}')
async def get_user(request, user_id: int):
    return {'user_id': user_id, 'name': f'User {user_id}'}

@app.route('/data', methods=['POST'])
async def post_data(request):
    data = await request.json()
    return {'received': data, 'method': 'POST'}

@app.websocket_route('/ws')
async def websocket_handler(websocket):
    await websocket.accept()
    await websocket.send_json({'message': 'WebSocket connected'})
    await websocket.close()
'''
        (app_dir / 'app.py').write_text(app_content)

        return app_dir

    def test_end_to_end_functionality(self, system_app):
        """Test complete end-to-end functionality"""
        original_cwd = os.getcwd()
        try:
            os.chdir(system_app)

            # Start server
            server_process = subprocess.Popen([
                'python', 'manage.py', 'start',
                '--host', '127.0.0.1',
                '--port', '8765'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            time.sleep(3)

            try:
                # Test all endpoints work together
                response = requests.get('http://127.0.0.1:8765/')
                assert response.status_code == 200
                assert response.json()['status'] == 'running'

                response = requests.get('http://127.0.0.1:8765/health')
                assert response.status_code == 200
                assert response.json()['status'] == 'healthy'

                response = requests.get('http://127.0.0.1:8765/users/123')
                assert response.status_code == 200
                data = response.json()
                assert data['user_id'] == 123

                # Test POST endpoint
                test_data = {'key': 'value', 'number': 42}
                response = requests.post('http://127.0.0.1:8765/data', json=test_data)
                assert response.status_code == 200
                response_data = response.json()
                assert response_data['received'] == test_data

                # Test 404
                response = requests.get('http://127.0.0.1:8765/nonexistent')
                assert response.status_code == 404

            finally:
                subprocess.run(['python', 'manage.py', 'stop'],
                             capture_output=True)
                time.sleep(2)

                if server_process.poll() is None:
                    server_process.terminate()
                    server_process.wait(timeout=5)

        finally:
            os.chdir(original_cwd)

    def test_system_integration_health(self, system_app):
        """Test overall system health and integration"""
        original_cwd = os.getcwd()
        try:
            os.chdir(system_app)

            # Test that all components can be imported and initialized
            result = subprocess.run([
                'python', '-c', 'from pyserv import Application; app = Application(); print("OK")'
            ], capture_output=True, text=True)

            assert result.returncode == 0
            assert "OK" in result.stdout

            # Test manage.py commands are available
            result = subprocess.run(['python', 'manage.py', '--help'],
                                  capture_output=True, text=True)
            assert result.returncode == 0

        finally:
            os.chdir(original_cwd)





"""
System tests for Pydance framework - End-to-end testing
"""
import subprocess
import time
import signal
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
        # Create a temporary directory for the test app
        app_dir = tmp_path_factory.mktemp("system_app")

        # Create app.py
        app_content = '''
from pydance import Application

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

        # Create config.py
        config_content = '''
from pydance import AppConfig

config = AppConfig(
    debug=True,
    host='127.0.0.1',
    port=8765,  # Use a different port for system tests
)
'''
        (app_dir / 'config.py').write_text(config_content)

        return app_dir

    def test_full_system_startup_shutdown(self, system_app):
        """Test complete system startup and shutdown"""
        # Change to app directory
        original_cwd = os.getcwd()
        try:
            os.chdir(system_app)

            # Start server in background
            server_process = subprocess.Popen([
                'python', 'manage.py', 'start',
                '--host', '127.0.0.1',
                '--port', '8765'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # Wait for server to start
            time.sleep(3)

            try:
                # Test HTTP endpoints
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
                assert data['name'] == 'User 123'

                # Test POST endpoint
                test_data = {'key': 'value', 'number': 42}
                response = requests.post('http://127.0.0.1:8765/data', json=test_data)
                assert response.status_code == 200
                response_data = response.json()
                assert response_data['received'] == test_data
                assert response_data['method'] == 'POST'

                # Test 404
                response = requests.get('http://127.0.0.1:8765/nonexistent')
                assert response.status_code == 404

            finally:
                # Stop server
                subprocess.run(['python', 'manage.py', 'stop'],
                             capture_output=True)

                # Wait for server to stop
                time.sleep(2)

                # Force kill if still running
                if server_process.poll() is None:
                    server_process.terminate()
                    server_process.wait(timeout=5)

        finally:
            os.chdir(original_cwd)

    def test_cli_commands_integration(self, system_app):
        """Test CLI commands work together"""
        original_cwd = os.getcwd()
        try:
            os.chdir(system_app)

            # Test status when server is not running
            result = subprocess.run(['python', 'manage.py', 'status'],
                                  capture_output=True, text=True)
            assert "not running" in result.stdout.lower()

            # Start server
            server_process = subprocess.Popen([
                'python', 'manage.py', 'start',
                '--host', '127.0.0.1',
                '--port', '8766'  # Different port
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            time.sleep(3)

            try:
                # Test status when server is running
                result = subprocess.run(['python', 'manage.py', 'status'],
                                      capture_output=True, text=True)
                assert "running" in result.stdout.lower()

                # Test restart
                result = subprocess.run(['python', 'manage.py', 'restart'],
                                      capture_output=True, text=True)
                time.sleep(3)

                # Verify server is still running after restart
                response = requests.get('http://127.0.0.1:8766/')
                assert response.status_code == 200

            finally:
                subprocess.run(['python', 'manage.py', 'stop'],
                             capture_output=True)
                time.sleep(2)

                if server_process.poll() is None:
                    server_process.terminate()
                    server_process.wait(timeout=5)

        finally:
            os.chdir(original_cwd)

    def test_configuration_loading(self, system_app):
        """Test configuration file loading"""
        original_cwd = os.getcwd()
        try:
            os.chdir(system_app)

            # Test with config file
            server_process = subprocess.Popen([
                'python', 'manage.py', 'start',
                '--config', 'config.py',
                '--host', '127.0.0.1',
                '--port', '8767'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            time.sleep(3)

            try:
                # Server should be running on configured port
                response = requests.get('http://127.0.0.1:8767/')
                assert response.status_code == 200

            finally:
                subprocess.run(['python', 'manage.py', 'stop'],
                             capture_output=True)
                time.sleep(2)

                if server_process.poll() is None:
                    server_process.terminate()
                    server_process.wait(timeout=5)

        finally:
            os.chdir(original_cwd)

    def test_error_handling_system(self, system_app):
        """Test system-level error handling"""
        original_cwd = os.getcwd()
        try:
            os.chdir(system_app)

            # Create app with error-prone routes
            error_app_content = '''
from pydance import Application

app = Application()

@app.route('/error')
async def error_route(request):
    raise ValueError("Test error")

@app.route('/async-error')
async def async_error_route(request):
    await asyncio.sleep(0.1)
    raise RuntimeError("Async test error")
'''
            (system_app / 'error_app.py').write_text(error_app_content)

            server_process = subprocess.Popen([
                'python', 'manage.py', 'start',
                '--app', 'error_app:app',
                '--host', '127.0.0.1',
                '--port', '8768'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            time.sleep(3)

            try:
                # Test error responses
                response = requests.get('http://127.0.0.1:8768/error')
                assert response.status_code == 500

                response = requests.get('http://127.0.0.1:8768/async-error')
                assert response.status_code == 500

                # Test normal route still works
                response = requests.get('http://127.0.0.1:8768/')
                assert response.status_code == 404  # Route not defined in error app

            finally:
                subprocess.run(['python', 'manage.py', 'stop'],
                             capture_output=True)
                time.sleep(2)

                if server_process.poll() is None:
                    server_process.terminate()
                    server_process.wait(timeout=5)

        finally:
            os.chdir(original_cwd)

    def test_concurrent_connections_system(self, system_app):
        """Test system handling of concurrent connections"""
        original_cwd = os.getcwd()
        try:
            os.chdir(system_app)

            server_process = subprocess.Popen([
                'python', 'manage.py', 'start',
                '--host', '127.0.0.1',
                '--port', '8769'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            time.sleep(3)

            try:
                # Make multiple concurrent requests
                import threading
                import queue

                results = queue.Queue()

                def make_request(request_id):
                    try:
                        response = requests.get('http://127.0.0.1:8769/')
                        results.put((request_id, response.status_code))
                    except Exception as e:
                        results.put((request_id, str(e)))

                # Start 20 concurrent requests
                threads = []
                for i in range(20):
                    thread = threading.Thread(target=make_request, args=(i,))
                    threads.append(thread)
                    thread.start()

                # Wait for all threads to complete
                for thread in threads:
                    thread.join()

                # Check results
                successful_requests = 0
                while not results.empty():
                    request_id, result = results.get()
                    if isinstance(result, int) and result == 200:
                        successful_requests += 1

                # At least 80% should succeed
                assert successful_requests >= 16

            finally:
                subprocess.run(['python', 'manage.py', 'stop'],
                             capture_output=True)
                time.sleep(2)

                if server_process.poll() is None:
                    server_process.terminate()
                    server_process.wait(timeout=5)

        finally:
            os.chdir(original_cwd)

    def test_process_management_system(self, system_app):
        """Test system process management"""
        original_cwd = os.getcwd()
        try:
            os.chdir(system_app)

            # Start server
            server_process = subprocess.Popen([
                'python', 'manage.py', 'start',
                '--host', '127.0.0.1',
                '--port', '8770'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            time.sleep(3)

            try:
                # Check PID file exists
                pid_file = Path('.pydance.pid')
                assert pid_file.exists()

                # Check server is responding
                response = requests.get('http://127.0.0.1:8770/')
                assert response.status_code == 200

                # Stop server via CLI
                result = subprocess.run(['python', 'manage.py', 'stop'],
                                      capture_output=True)
                assert result.returncode == 0

                time.sleep(2)

                # Check PID file is removed
                assert not pid_file.exists()

                # Check server is no longer responding
                try:
                    requests.get('http://127.0.0.1:8770/', timeout=2)
                    assert False, "Server should not be responding"
                except requests.exceptions.ConnectionError:
                    pass  # Expected

            finally:
                if server_process.poll() is None:
                    server_process.terminate()
                    server_process.wait(timeout=5)

        finally:
            os.chdir(original_cwd)

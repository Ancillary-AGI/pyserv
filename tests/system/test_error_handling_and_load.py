"""
System tests for error handling and load testing
"""
import subprocess
import time
import os
import pytest
import requests
import threading
import queue


@pytest.mark.system
class TestErrorHandlingAndLoad:
    """System-level error handling and load tests"""

    @pytest.fixture(scope="class")
    def error_app(self, tmp_path_factory):
        """Create an application with error-prone routes"""
        app_dir = tmp_path_factory.mktemp("error_app")

        # Create app.py with error routes
        app_content = '''
from pyserv import Application

app = Application()

@app.route('/')
async def home(request):
    return {'message': 'Home'}

@app.route('/error')
async def error_route(request):
    raise ValueError("Test error")

@app.route('/async-error')
async def async_error_route(request):
    import asyncio
    await asyncio.sleep(0.1)
    raise RuntimeError("Async test error")
'''
        (app_dir / 'app.py').write_text(app_content)

        return app_dir

    def test_error_response_handling(self, error_app):
        """Test system-level error handling"""
        original_cwd = os.getcwd()
        try:
            os.chdir(error_app)

            server_process = subprocess.Popen([
                'python', 'manage.py', 'start',
                '--host', '127.0.0.1',
                '--port', '8770'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            time.sleep(3)

            try:
                # Test error responses
                response = requests.get('http://127.0.0.1:8770/error')
                assert response.status_code == 500

                response = requests.get('http://127.0.0.1:8770/async-error')
                assert response.status_code == 500

                # Test normal route still works
                response = requests.get('http://127.0.0.1:8770/')
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

    def test_concurrent_connections_load(self, error_app):
        """Test system handling of concurrent connections"""
        original_cwd = os.getcwd()
        try:
            os.chdir(error_app)

            server_process = subprocess.Popen([
                'python', 'manage.py', 'start',
                '--host', '127.0.0.1',
                '--port', '8771'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            time.sleep(3)

            try:
                # Make multiple concurrent requests
                results = queue.Queue()

                def make_request(request_id):
                    try:
                        response = requests.get('http://127.0.0.1:8771/')
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

    def test_process_management_robustness(self, error_app):
        """Test process management under various conditions"""
        original_cwd = os.getcwd()
        try:
            os.chdir(error_app)

            # Test multiple start/stop cycles
            for cycle in range(3):
                port = 8772 + cycle

                server_process = subprocess.Popen([
                    'python', 'manage.py', 'start',
                    '--host', '127.0.0.1',
                    f'--port={port}'
                ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                time.sleep(2)

                try:
                    # Verify server is running
                    response = requests.get(f'http://127.0.0.1:{port}/')
                    assert response.status_code == 200

                finally:
                    subprocess.run(['python', 'manage.py', 'stop'],
                                 capture_output=True)
                    time.sleep(1)

                    if server_process.poll() is None:
                        server_process.terminate()
                        server_process.wait(timeout=5)

        finally:
            os.chdir(original_cwd)

    def test_resource_cleanup(self, error_app):
        """Test that system resources are properly cleaned up"""
        original_cwd = os.getcwd()
        try:
            os.chdir(error_app)

            # Start server
            server_process = subprocess.Popen([
                'python', 'manage.py', 'start',
                '--host', '127.0.0.1',
                '--port', '8775'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            time.sleep(3)

            try:
                # Verify server is running and create some activity
                for _ in range(5):
                    response = requests.get('http://127.0.0.1:8775/')
                    assert response.status_code == 200

                # Trigger some errors
                for _ in range(3):
                    try:
                        requests.get('http://127.0.0.1:8775/error', timeout=1)
                    except:
                        pass  # Expected to fail

            finally:
                # Stop server
                subprocess.run(['python', 'manage.py', 'stop'],
                             capture_output=True)
                time.sleep(2)

                # Verify process is actually stopped
                if server_process.poll() is None:
                    server_process.terminate()
                    server_process.wait(timeout=5)

                # Verify server is no longer responding
                try:
                    requests.get('http://127.0.0.1:8775/', timeout=2)
                    assert False, "Server should not be responding after stop"
                except requests.exceptions.ConnectionError:
                    pass  # Expected

        finally:
            os.chdir(original_cwd)





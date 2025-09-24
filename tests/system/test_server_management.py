"""
System tests for server management functionality
"""
import subprocess
import time
import os
import pytest
import requests
from pathlib import Path


@pytest.mark.system
class TestServerManagement:
    """System-level server management tests"""

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
'''
        (app_dir / 'app.py').write_text(app_content)

        # Create config.py
        config_content = '''
from pyserv import AppConfig

config = AppConfig(
    debug=True,
    host='127.0.0.1',
    port=8765,
)
'''
        (app_dir / 'config.py').write_text(config_content)

        return app_dir

    def test_server_startup_shutdown(self, system_app):
        """Test basic server startup and shutdown"""
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
                # Test server is responding
                response = requests.get('http://127.0.0.1:8765/')
                assert response.status_code == 200
                assert response.json()['status'] == 'running'

                response = requests.get('http://127.0.0.1:8765/health')
                assert response.status_code == 200
                assert response.json()['status'] == 'healthy'

            finally:
                subprocess.run(['python', 'manage.py', 'stop'],
                             capture_output=True)
                time.sleep(2)

                if server_process.poll() is None:
                    server_process.terminate()
                    server_process.wait(timeout=5)

        finally:
            os.chdir(original_cwd)

    def test_cli_status_command(self, system_app):
        """Test CLI status command"""
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
                '--port', '8766'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            time.sleep(3)

            try:
                # Test status when server is running
                result = subprocess.run(['python', 'manage.py', 'status'],
                                      capture_output=True, text=True)
                assert "running" in result.stdout.lower()

            finally:
                subprocess.run(['python', 'manage.py', 'stop'],
                             capture_output=True)
                time.sleep(2)

                if server_process.poll() is None:
                    server_process.terminate()
                    server_process.wait(timeout=5)

        finally:
            os.chdir(original_cwd)

    def test_server_restart(self, system_app):
        """Test server restart functionality"""
        original_cwd = os.getcwd()
        try:
            os.chdir(system_app)

            # Start server
            server_process = subprocess.Popen([
                'python', 'manage.py', 'start',
                '--host', '127.0.0.1',
                '--port', '8767'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            time.sleep(3)

            try:
                # Verify server is running
                response = requests.get('http://127.0.0.1:8767/')
                assert response.status_code == 200

                # Test restart
                result = subprocess.run(['python', 'manage.py', 'restart'],
                                      capture_output=True, text=True)
                time.sleep(3)

                # Verify server is still running after restart
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
                '--port', '8768'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            time.sleep(3)

            try:
                # Server should be running on configured port
                response = requests.get('http://127.0.0.1:8768/')
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

    def test_pid_file_management(self, system_app):
        """Test PID file creation and cleanup"""
        original_cwd = os.getcwd()
        try:
            os.chdir(system_app)

            # Start server
            server_process = subprocess.Popen([
                'python', 'manage.py', 'start',
                '--host', '127.0.0.1',
                '--port', '8769'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            time.sleep(3)

            try:
                # Check PID file exists
                pid_file = Path('.pyserv .pid')
                assert pid_file.exists()

                # Check server is responding
                response = requests.get('http://127.0.0.1:8769/')
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
                    requests.get('http://127.0.0.1:8769/', timeout=2)
                    assert False, "Server should not be responding"
                except requests.exceptions.ConnectionError:
                    pass  # Expected

            finally:
                if server_process.poll() is None:
                    server_process.terminate()
                    server_process.wait(timeout=5)

        finally:
            os.chdir(original_cwd)





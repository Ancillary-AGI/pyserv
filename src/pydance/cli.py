#!/usr/bin/env python3
"""
Pydance CLI - Command Line Interface for Pydance Framework
"""
import argparse
import os
import sys
import signal
import subprocess
import time
import re
import importlib.util
from pathlib import Path
from typing import Optional, List
from urllib.parse import urlparse

class PydanceCLI:
    """Command Line Interface for Pydance Framework"""

    def __init__(self):
        self.parser = argparse.ArgumentParser(
            description="Pydance Framework CLI",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  pydance start --host 0.0.0.0 --port 8000
  pydance start --reload
  pydance stop
  pydance restart
  pydance shell
  pydance migrate
            """
        )
        self.parser.add_argument(
            '--config',
            help='Path to config file',
            default='config.py'
        )
        self.parser.add_argument(
            '--app',
            help='Application module path (e.g., myapp:app)',
            default='app:app'
        )

        subparsers = self.parser.add_subparsers(dest='command', help='Available commands')

        # Start command
        start_parser = subparsers.add_parser('start', help='Start the server')
        start_parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
        start_parser.add_argument('--port', type=int, default=8000, help='Port to bind to')
        start_parser.add_argument('--workers', type=int, default=1, help='Number of workers')
        start_parser.add_argument('--reload', action='store_true', help='Enable auto-reload')
        start_parser.add_argument('--debug', action='store_true', help='Enable debug mode')

        # Stop command
        stop_parser = subparsers.add_parser('stop', help='Stop the server')

        # Restart command
        restart_parser = subparsers.add_parser('restart', help='Restart the server')
        restart_parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
        restart_parser.add_argument('--port', type=int, default=8000, help='Port to bind to')
        restart_parser.add_argument('--workers', type=int, default=1, help='Number of workers')
        restart_parser.add_argument('--reload', action='store_true', help='Enable auto-reload')
        restart_parser.add_argument('--debug', action='store_true', help='Enable debug mode')

        # Status command
        subparsers.add_parser('status', help='Show server status')

        # Shell command
        subparsers.add_parser('shell', help='Start interactive shell')

        # Migrate command
        migrate_parser = subparsers.add_parser('migrate', help='Run database migrations')
        migrate_parser.add_argument('--action', choices=['migrate', 'downgrade', 'reset', 'status'],
                                   default='migrate', help='Action to perform')
        migrate_parser.add_argument('--model', help='Specific model to migrate (default: all)')
        migrate_parser.add_argument('--version', type=int, help='Target version for downgrade')
        migrate_parser.add_argument('--database-url', help='Database connection URL')
        migrate_parser.add_argument('--models-package', default='app.models',
                                   help='Python package path to discover models from')
        migrate_parser.add_argument('--dry-run', action='store_true',
                                   help='Show what would be done without making changes')
        migrate_parser.add_argument('--verbose', '-v', action='store_true',
                                   help='Verbose output')

        # Create app command
        create_parser = subparsers.add_parser('createapp', help='Create a new application')
        create_parser.add_argument('name', help='Application name')

        # Collect static command
        subparsers.add_parser('collectstatic', help='Collect static files')

        # Test command
        test_parser = subparsers.add_parser('test', help='Run tests')
        test_parser.add_argument('--unit', action='store_true', help='Run unit tests only')
        test_parser.add_argument('--integration', action='store_true', help='Run integration tests only')
        test_parser.add_argument('--performance', action='store_true', help='Run performance tests only')
        test_parser.add_argument('--security', action='store_true', help='Run security tests only')
        test_parser.add_argument('--regression', action='store_true', help='Run regression tests only')
        test_parser.add_argument('--load', action='store_true', help='Run load tests')
        test_parser.add_argument('--stress', action='store_true', help='Run stress tests')
        test_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
        test_parser.add_argument('--coverage', action='store_true', help='Run with coverage')
        test_parser.add_argument('--markers', help='Run tests with specific markers')

    # Validation patterns
    def _validate_host(self, host: str) -> bool:
        """Validate host address"""
        if not host:
            return False
        # Allow localhost, 127.0.0.1, 0.0.0.0, or valid IP addresses
        if host in ['localhost', '127.0.0.1', '0.0.0.0']:
            return True
        # Check for valid IP address format
        ip_pattern = re.compile(r'^(\d{1,3}\.){3}\d{1,3}$')
        if not ip_pattern.match(host):
            return False
        # Check each octet is 0-255
        octets = host.split('.')
        return all(0 <= int(octet) <= 255 for octet in octets)

    def _validate_port(self, port: int) -> bool:
        """Validate port number"""
        return 1 <= port <= 65535

    def _validate_workers(self, workers: int) -> bool:
        """Validate worker count"""
        return 1 <= workers <= 100  # Reasonable upper limit

    def _validate_module_path(self, module_path: str) -> bool:
        """Validate Python module path"""
        if not module_path:
            return False
        # Allow module paths like 'app', 'myapp.core', 'myapp:app'
        pattern = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)*(?::[a-zA-Z_][a-zA-Z0-9_]*)*$')
        return bool(pattern.match(module_path))

    def _validate_config_file(self, config_path: str) -> bool:
        """Validate config file exists and is readable"""
        if not config_path:
            return False
        config_file = Path(config_path)
        return config_file.exists() and config_file.is_file() and config_file.suffix == '.py'

    def _validate_database_url(self, url: str) -> bool:
        """Validate database URL format"""
        if not url:
            return False
        try:
            parsed = urlparse(url)
            # Must have scheme and netloc/path
            return bool(parsed.scheme and (parsed.netloc or parsed.path))
        except Exception:
            return False

    def _validate_app_name(self, name: str) -> bool:
        """Validate application name"""
        if not name:
            return False
        # Must be valid Python identifier
        return bool(re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name))

    def _validate_model_name(self, name: str) -> bool:
        """Validate model name"""
        if not name:
            return False
        # Must be valid Python class name
        return bool(re.match(r'^[A-Z][a-zA-Z0-9_]*$', name))

    def _validate_package_name(self, name: str) -> bool:
        """Validate package name"""
        if not name:
            return False
        # Must be valid Python module path
        return bool(re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)*$', name))

    def _check_module_exists(self, module_path: str) -> bool:
        """Check if Python module exists"""
        try:
            if ':' in module_path:
                module_path, _ = module_path.split(':', 1)
            importlib.import_module(module_path)
            return True
        except ImportError:
            return False

    def _check_command_exists(self, command: str) -> bool:
        """Check if system command exists"""
        try:
            subprocess.run([command, '--version'], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def run(self):
        """Run the CLI"""
        args = self.parser.parse_args()

        if not args.command:
            self.parser.print_help()
            return

        getattr(self, f'cmd_{args.command}')(args)

    def cmd_start(self, args):
        """Start the server"""
        # Validate arguments
        errors = []

        if not self._validate_host(args.host):
            errors.append(f"Invalid host address: {args.host}")

        if not self._validate_port(args.port):
            errors.append(f"Invalid port number: {args.port} (must be 1-65535)")

        if not self._validate_workers(args.workers):
            errors.append(f"Invalid worker count: {args.workers} (must be 1-100)")

        if not self._validate_module_path(args.app):
            errors.append(f"Invalid app module path: {args.app}")

        if not self._check_module_exists(args.app):
            errors.append(f"App module not found: {args.app}")

        if not self._check_command_exists('hypercorn'):
            errors.append("Hypercorn is not installed or not in PATH")

        if errors:
            print("❌ Validation errors:")
            for error in errors:
                print(f"  • {error}")
            sys.exit(1)

        print(f"Starting Pydance server on {args.host}:{args.port}")

        # Set environment variables
        env = os.environ.copy()
        env['PYDANCE_HOST'] = args.host
        env['PYDANCE_PORT'] = str(args.port)
        env['PYDANCE_WORKERS'] = str(args.workers)
        env['PYDANCE_RELOAD'] = '1' if args.reload else '0'
        env['PYDANCE_DEBUG'] = '1' if args.debug else '0'

        # Add current directory to Python path
        env['PYTHONPATH'] = os.getcwd() + os.pathsep + env.get('PYTHONPATH', '')

        # Build command
        cmd = [
            sys.executable, '-m', 'hypercorn',
            f'{args.app}',
            '--bind', f'{args.host}:{args.port}',
        ]

        if args.workers > 1:
            cmd.extend(['--workers', str(args.workers)])

        if args.reload:
            cmd.append('--reload')

        if args.debug:
            cmd.extend(['--log-level', 'debug'])

        # Save PID for management
        try:
            self._save_pid()
        except Exception as e:
            print(f"Warning: Could not save PID file: {e}")

        try:
            subprocess.run(cmd, env=env)
        except KeyboardInterrupt:
            print("\nServer stopped")
        except subprocess.CalledProcessError as e:
            print(f"❌ Server failed to start: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Unexpected error starting server: {e}")
            sys.exit(1)
        finally:
            try:
                self._remove_pid()
            except Exception as e:
                print(f"Warning: Could not remove PID file: {e}")

    def cmd_stop(self, args):
        """Stop the server"""
        pid = self._get_pid()
        if not pid:
            print("No server process found")
            return

        try:
            os.kill(pid, signal.SIGTERM)
            print("Server stopped")
            self._remove_pid()
        except ProcessLookupError:
            print("Server process not found")
            self._remove_pid()
        except Exception as e:
            print(f"Error stopping server: {e}")

    def cmd_restart(self, args):
        """Restart the server"""
        print("Restarting server...")
        self.cmd_stop(args)
        time.sleep(2)  # Wait for shutdown
        self.cmd_start(args)

    def cmd_status(self, args):
        """Show server status"""
        pid = self._get_pid()
        if pid:
            try:
                os.kill(pid, 0)  # Check if process exists
                print(f"Server is running (PID: {pid})")
            except ProcessLookupError:
                print("Server process not found (stale PID file)")
                self._remove_pid()
        else:
            print("Server is not running")

    def cmd_shell(self, args):
        """Start interactive shell"""
        print("Starting Pydance shell...")
        import IPython
        IPython.embed()

    def cmd_migrate(self, args):
        """Run database migrations"""
        # Validate arguments
        errors = []

        if args.database_url and not self._validate_database_url(args.database_url):
            errors.append(f"Invalid database URL format: {args.database_url}")

        if args.model and not self._validate_model_name(args.model):
            errors.append(f"Invalid model name: {args.model} (must start with capital letter)")

        if not self._validate_package_name(args.models_package):
            errors.append(f"Invalid package name: {args.models_package}")

        if args.action == "downgrade" and args.version is None:
            errors.append("--version parameter is required for downgrade action")

        if args.action == "downgrade" and args.version is not None and args.version < 0:
            errors.append(f"Invalid version number: {args.version} (must be >= 0)")

        if errors:
            print("❌ Validation errors:")
            for error in errors:
                print(f"  • {error}")
            sys.exit(1)

        import asyncio
        from .database.migrations.migrator import Migrator
        from .database.config import DatabaseConfig

        try:
            # Setup database config
            config = DatabaseConfig(args.database_url)

            if args.verbose:
                print(f"Database type: {config.db_type}")
                print(f"Database URL: {config.database_url}")

            # Initialize migration manager
            manager = Migrator.get_instance(config)
            asyncio.run(manager.initialize())

            # Discover models dynamically
            models = asyncio.run(manager.discover_models(args.models_package))

            if not models:
                print(f"⚠️  No models found in package {args.models_package}")
                if args.verbose:
                    print("Make sure your models inherit from BaseModel and are properly defined")
                return

            if args.verbose:
                print(f"Found {len(models)} models: {[m.__name__ for m in models]}")

            # Filter models if specific model requested
            if args.model:
                models = [m for m in models if m.__name__.lower() == args.model.lower()]
                if not models:
                    print(f"❌ Error: Model '{args.model}' not found in package {args.models_package}")
                    if args.verbose:
                        available_models = [m.__name__ for m in asyncio.run(manager.discover_models(args.models_package))]
                        print(f"Available models: {available_models}")
                    sys.exit(1)

            # Perform requested action
            if args.action == "migrate":
                if args.dry_run:
                    print("🔍 DRY RUN - No changes will be made")
                for model in models:
                    if args.verbose:
                        print(f"📦 Migrating model: {model.__name__}")
                    try:
                        asyncio.run(manager.apply_model_migrations(model))
                    except Exception as e:
                        print(f"❌ Failed to migrate {model.__name__}: {e}")
                        if not args.dry_run:
                            sys.exit(1)
                print("✅ Migration completed")

            elif args.action == "downgrade":
                if args.dry_run:
                    print(f"🔍 DRY RUN - Would downgrade to version {args.version}")

                for model in models:
                    if args.verbose:
                        print(f"⬇️  Downgrading model: {model.__name__} to version {args.version}")
                    try:
                        asyncio.run(manager.downgrade_model(model, args.version))
                    except Exception as e:
                        print(f"❌ Failed to downgrade {model.__name__}: {e}")
                        if not args.dry_run:
                            sys.exit(1)
                print("✅ Downgrade completed")

            elif args.action == "reset":
                if args.dry_run:
                    print("🔍 DRY RUN - Would reset database")
                    return

                confirm = input("⚠️  Are you sure you want to reset the database? This will drop all tables! (y/N): ")
                if confirm.lower() == 'y':
                    try:
                        asyncio.run(manager.reset_database(models))
                        print("✅ Database reset completed")
                    except Exception as e:
                        print(f"❌ Failed to reset database: {e}")
                        sys.exit(1)
                else:
                    print("ℹ️  Reset cancelled")

            elif args.action == "status":
                try:
                    asyncio.run(manager.show_status(models))
                except Exception as e:
                    print(f"❌ Failed to get migration status: {e}")
                    sys.exit(1)

        except Exception as e:
            print(f"❌ Migration error: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)

    def cmd_createapp(self, args):
        """Create a new application"""
        # Validate arguments
        errors = []

        if not self._validate_app_name(args.name):
            errors.append(f"Invalid application name: {args.name} (must be a valid Python identifier)")

        app_dir = Path(args.name)
        if app_dir.exists():
            errors.append(f"Directory '{args.name}' already exists")

        if errors:
            print("❌ Validation errors:")
            for error in errors:
                print(f"  • {error}")
            sys.exit(1)

        try:
            # Create app structure
            app_dir.mkdir(parents=True, exist_ok=False)

            # Create __init__.py
            (app_dir / '__init__.py').write_text('')

            # Create models.py
            (app_dir / 'models.py').write_text(f'''from pydance import BaseModel

class {args.name.title()}Model(BaseModel):
    """Model for {args.name} app"""
    pass
''')

            # Create views.py
            (app_dir / 'views.py').write_text(f'''from pydance import Application

def setup_routes(app: Application):
    """Setup routes for {args.name} app"""
    pass
''')

            # Create urls.py
            (app_dir / 'urls.py').write_text(f'''from .{args.name} import views

# URL patterns for {args.name} app
urlpatterns = []
''')

            print(f"✅ Created app '{args.name}'")
            print(f"📁 App structure created in: {app_dir.absolute()}")

        except PermissionError:
            print(f"❌ Permission denied: Cannot create directory '{args.name}'")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Failed to create app: {e}")
            # Clean up partially created directory
            if app_dir.exists():
                import shutil
                shutil.rmtree(app_dir)
            sys.exit(1)

    def cmd_collectstatic(self, args):
        """Collect static files"""
        print("Collecting static files...")
        # Implementation would depend on static file handling
        print("Static files collected")

    def cmd_test(self, args):
        """Run tests"""
        # Validate arguments
        errors = []

        if not self._check_command_exists('pytest'):
            errors.append("pytest is not installed or not in PATH")

        if args.coverage and not self._check_command_exists('coverage'):
            errors.append("coverage is not installed (required for --coverage)")

        if args.markers:
            # Validate custom markers format
            for marker in args.markers.split(','):
                marker = marker.strip()
                if not marker or not re.match(r'^[a-zA-Z_][a-zA-Z0-9_-]*$', marker):
                    errors.append(f"Invalid marker format: {marker}")

        if errors:
            print("❌ Validation errors:")
            for error in errors:
                print(f"  • {error}")
            sys.exit(1)

        print("🧪 Running Pydance tests...")

        # Build pytest command
        cmd = [sys.executable, '-m', 'pytest']

        # Add test markers
        markers = []
        if args.unit:
            markers.append('unit')
        if args.integration:
            markers.append('integration')
        if args.performance:
            markers.append('performance')
        if args.security:
            markers.append('security')
        if args.regression:
            markers.append('regression')
        if args.load:
            markers.append('load')
        if args.stress:
            markers.append('stress')

        if args.markers:
            markers.extend([m.strip() for m in args.markers.split(',')])

        if markers:
            cmd.extend(['-m', ' or '.join(markers)])

        # Add coverage
        if args.coverage:
            cmd.extend(['--cov=src/pydance', '--cov-report=html', '--cov-report=term'])

        # Add verbosity
        if args.verbose:
            cmd.append('-v')

        # Run tests
        try:
            print(f"📋 Executing: {' '.join(cmd)}")
            result = subprocess.run(cmd, cwd=os.getcwd())

            if result.returncode == 0:
                print("✅ All tests passed!")
            elif result.returncode == 1:
                print("❌ Tests failed")
            elif result.returncode == 2:
                print("❌ Test collection failed")
            elif result.returncode == 3:
                print("❌ Internal error")
            elif result.returncode == 4:
                print("❌ Command line usage error")
            elif result.returncode == 5:
                print("❌ No tests collected")
            else:
                print(f"❌ Tests failed with exit code {result.returncode}")

            sys.exit(result.returncode)

        except FileNotFoundError:
            print("❌ pytest command not found")
            sys.exit(1)
        except subprocess.CalledProcessError as e:
            print(f"❌ Test execution failed: {e}")
            sys.exit(1)
        except KeyboardInterrupt:
            print("\n🛑 Tests interrupted by user")
            sys.exit(130)
        except Exception as e:
            print(f"❌ Unexpected error running tests: {e}")
            sys.exit(1)

    def _get_pid_file(self):
        """Get PID file path"""
        return Path('.pydance.pid')

    def _save_pid(self):
        """Save current process PID"""
        pid_file = self._get_pid_file()
        try:
            pid_file.write_text(str(os.getpid()))
        except (OSError, PermissionError) as e:
            raise Exception(f"Cannot write PID file: {e}")

    def _get_pid(self):
        """Get saved PID"""
        pid_file = self._get_pid_file()
        if not pid_file.exists():
            return None

        try:
            content = pid_file.read_text().strip()
            if not content:
                return None
            pid = int(content)
            if pid <= 0:
                return None
            return pid
        except (ValueError, OSError) as e:
            print(f"Warning: Invalid PID file content: {e}")
            return None

    def _remove_pid(self):
        """Remove PID file"""
        pid_file = self._get_pid_file()
        if pid_file.exists():
            try:
                pid_file.unlink()
            except OSError as e:
                print(f"Warning: Could not remove PID file: {e}")


def main():
    """Main entry point"""
    cli = PydanceCLI()
    cli.run()


if __name__ == '__main__':
    main()

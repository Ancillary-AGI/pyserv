#!/usr/bin/env python3
"""
Pyserv CLI - Command Line Interface for Pyserv Framework
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
from typing import Optional, List, Dict, Any, Callable, Tuple
from urllib.parse import urlparse
from datetime import datetime


class CommandRegistry:
    """Registry for CLI commands with validation and execution logic"""
    
    def __init__(self):
        self.commands = {}
    
    def register(self, name: str, validator: Callable = None, executor: Callable = None):
        """Register a command with optional validator and executor"""
        if executor is not None:
            # Direct registration
            self.commands[name] = {
                'function': executor,
                'validator': validator,
                'executor': executor
            }
        else:
            # Decorator pattern
            def decorator(func):
                self.commands[name] = {
                    'function': func,
                    'validator': validator,
                    'executor': func
                }
                return func
            return decorator
    
    def execute(self, name: str, args: Any) -> bool:
        """Execute a command with validation"""
        if name not in self.commands:
            return False

        command = self.commands[name]

        # Run validation if available
        if command['validator']:
            errors = command['validator'](args)
            if errors:
                print("❌ Validation errors:")
                for error in errors:
                    print(f"  • {error}")
                return False

        # Execute the command
        command['executor'](args)
        return True


class PyservCLI:
    """Command Line Interface for Pyserv Framework"""

    def __init__(self):
        self.registry = CommandRegistry()
        self.parser = self._create_parser()
        self._register_commands()

    def _create_parser(self) -> argparse.ArgumentParser:
        """Create and configure the argument parser"""
        parser = argparse.ArgumentParser(
            description="Pyserv Framework CLI",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  pyserv start --host 0.0.0.0 --port 8000
  pyserv start --reload
  pyserv stop
  pyserv restart
  pyserv shell
  pyserv migrate
  pyserv startproject myproject
  pyserv startapp myapp
  pyserv runserver
  pyserv makemigrations
  pyserv test
            """
        )
        
        # Global arguments
        parser.add_argument('--config', help='Path to config file', default='config.py')
        parser.add_argument('--app', help='Application module path (e.g., myapp:app)', default='app:app')
        
        # Subparsers for commands
        subparsers = parser.add_subparsers(dest='command', help='Available commands')
        
        # Server management commands
        self._add_server_commands(subparsers)
        
        # Development commands
        self._add_development_commands(subparsers)
        
        # Database commands
        self._add_database_commands(subparsers)
        
        # Project management commands
        self._add_project_commands(subparsers)

        # Add interactive flag for better UX
        parser.add_argument('--interactive', '-i', action='store_true',
                           help='Run in interactive mode with prompts')
        
        # Testing commands
        self._add_testing_commands(subparsers)
        
        # User management commands
        self._add_user_commands(subparsers)
        
        # System commands
        self._add_system_commands(subparsers)
        
        # Queue and scheduler commands
        self._add_queue_commands(subparsers)
        
        # Help command
        subparsers.add_parser('help', help='Show help')
        
        return parser

    def _add_server_commands(self, subparsers):
        """Add server management commands"""
        start_parser = subparsers.add_parser('start', help='Start the server')
        start_parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
        start_parser.add_argument('--port', type=int, default=8000, help='Port to bind to')
        start_parser.add_argument('--workers', type=int, default=1, help='Number of workers')
        start_parser.add_argument('--reload', action='store_true', help='Enable auto-reload')
        start_parser.add_argument('--debug', action='store_true', help='Enable debug mode')

        subparsers.add_parser('stop', help='Stop the server')

        restart_parser = subparsers.add_parser('restart', help='Restart the server')
        restart_parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
        restart_parser.add_argument('--port', type=int, default=8000, help='Port to bind to')
        restart_parser.add_argument('--workers', type=int, default=1, help='Number of workers')
        restart_parser.add_argument('--reload', action='store_true', help='Enable auto-reload')
        restart_parser.add_argument('--debug', action='store_true', help='Enable debug mode')

        subparsers.add_parser('status', help='Show server status')

    def _add_development_commands(self, subparsers):
        """Add development commands"""
        subparsers.add_parser('shell', help='Start interactive shell')
        
        runserver_parser = subparsers.add_parser('runserver', help='Run development server')
        runserver_parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
        runserver_parser.add_argument('--port', type=int, default=8000, help='Port to bind to')
        runserver_parser.add_argument('--reload', action='store_true', help='Enable auto-reload')

    def _add_database_commands(self, subparsers):
        """Add database commands"""
        migrate_parser = subparsers.add_parser('migrate', help='Run database migrations')
        migrate_parser.add_argument('--action', choices=['migrate', 'downgrade', 'reset', 'status', 'list'],
                                   default='migrate', help='Action to perform')
        migrate_parser.add_argument('--model', help='Specific model to migrate (default: all)')
        migrate_parser.add_argument('--version', type=int, help='Target version for downgrade (e.g., --version 2)')
        migrate_parser.add_argument('--migration-id', help='Specific migration ID to run (e.g., --migration-id 001)')
        migrate_parser.add_argument('--target-version', type=int, help='Target version to migrate to (e.g., --target-version 3)')
        migrate_parser.add_argument('--migration', help='Specific migration file to run')
        migrate_parser.add_argument('--database-url', help='Database connection URL')
        migrate_parser.add_argument('--models-package', default='app.models',
                                   help='Python package path to discover models from')
        migrate_parser.add_argument('--dry-run', action='store_true',
                                   help='Show what would be done without making changes')
        migrate_parser.add_argument('--verbose', '-v', action='store_true',
                                   help='Verbose output')
        migrate_parser.add_argument('--force', action='store_true',
                                   help='Force migration even if it may cause data loss')
        migrate_parser.add_argument('--specific-model', help='Migrate only this specific model (e.g., --specific-model User)')

        makemigrations_parser = subparsers.add_parser('makemigrations', help='Create database migrations')
        makemigrations_parser.add_argument('--app', help='App to create migrations for')
        makemigrations_parser.add_argument('--name', default='auto', help='Migration name')

        showmigrations_parser = subparsers.add_parser('showmigrations', help='Show migration status')
        showmigrations_parser.add_argument('--app', help='App to show migrations for')

        subparsers.add_parser('dbshell', help='Start database shell')

    def _add_project_commands(self, subparsers):
        """Add project management commands"""
        startproject_parser = subparsers.add_parser('startproject', help='Create a new Pyserv project')
        startproject_parser.add_argument('name', help='Project name')
        startproject_parser.add_argument('--template', default='basic',
                                       choices=['minimal', 'basic', 'api', 'full', 'microservice', 'enterprise'],
                                       help='Project template: minimal (simple), basic (standard), api (REST), full (complete), microservice (distributed), enterprise (production-ready)')
        startproject_parser.add_argument('--git-repo', help='Git repository URL to clone as template')
        startproject_parser.add_argument('--git-branch', default='main', help='Git branch to clone')

        startapp_parser = subparsers.add_parser('startapp', help='Create a new Pyserv app')
        startapp_parser.add_argument('name', help='App name')

        createapp_parser = subparsers.add_parser('createapp', help='Create a new application')
        createapp_parser.add_argument('name', help='Application name')

        collectstatic_parser = subparsers.add_parser('collectstatic', help='Collect static files')
        collectstatic_parser.add_argument('--noinput', action='store_true', help='Do not prompt for input')
        collectstatic_parser.add_argument('--clear', action='store_true', help='Clear the existing files before collecting')
        collectstatic_parser.add_argument('--cdn', action='store_true', help='Deploy to CDN after collecting')
        collectstatic_parser.add_argument('--hash', action='store_true', help='Add hash-based versioning')

    def _add_testing_commands(self, subparsers):
        """Add testing commands"""
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
        test_parser.add_argument('--app', help='App to test')
        test_parser.add_argument('--verbosity', type=int, default=1, help='Test verbosity')
        test_parser.add_argument('--keepdb', action='store_true', help='Keep test database')

    def _add_user_commands(self, subparsers):
        """Add user management commands"""
        subparsers.add_parser('createsuperuser', help='Create superuser')

    def _add_system_commands(self, subparsers):
        """Add system commands"""
        subparsers.add_parser('check', help='Check for common problems')
        subparsers.add_parser('version', help='Show Pyserv version')

    def _add_queue_commands(self, subparsers):
        """Add queue and scheduler commands"""
        work_parser = subparsers.add_parser('work', help='Start background workers')
        work_parser.add_argument('--queue', default='default', help='Queue name')
        work_parser.add_argument('--workers', type=int, default=1, help='Number of workers')
        work_parser.add_argument('--concurrency', type=int, default=4, help='Max concurrent jobs per worker')

        enqueue_parser = subparsers.add_parser('enqueue', help='Enqueue a background job')
        enqueue_parser.add_argument('func', help='Function to execute (module.function)')
        enqueue_parser.add_argument('--queue', default='default', help='Queue name')
        enqueue_parser.add_argument('--priority', type=int, default=0, help='Job priority')
        enqueue_parser.add_argument('--args', nargs='*', help='Function arguments')
        enqueue_parser.add_argument('--kwargs', nargs='*', help='Function keyword arguments')

        schedule_parser = subparsers.add_parser('schedule', help='Schedule a cron job')
        schedule_parser.add_argument('func', help='Function to execute (module.function)')
        schedule_parser.add_argument('cron', help='Cron expression (e.g., "0 9 * * 1-5")')
        schedule_parser.add_argument('--args', nargs='*', help='Function arguments')
        schedule_parser.add_argument('--kwargs', nargs='*', help='Function keyword arguments')

        jobs_parser = subparsers.add_parser('jobs', help='List background jobs')
        jobs_parser.add_argument('--queue', default='default', help='Queue name')
        jobs_parser.add_argument('--status', help='Filter by status')

        workers_parser = subparsers.add_parser('workers', help='Manage workers')
        workers_parser.add_argument('action', choices=['start', 'stop', 'status'], help='Action to perform')
        workers_parser.add_argument('--queue', default='default', help='Queue name')
        workers_parser.add_argument('--workers', type=int, default=1, help='Number of workers')
        workers_parser.add_argument('--concurrency', type=int, default=4, help='Max concurrent jobs per worker')

    def _register_commands(self):
        """Register all CLI commands"""
        # Server commands
        self.registry.register('start', self._validate_server_args, self.cmd_start)
        self.registry.register('stop', None, self.cmd_stop)
        self.registry.register('restart', self._validate_server_args, self.cmd_restart)
        self.registry.register('status', None, self.cmd_status)

        # Development commands
        self.registry.register('shell', None, self.cmd_shell)
        self.registry.register('runserver', self._validate_server_args, self.cmd_runserver)

        # Database commands
        self.registry.register('migrate', None, self.cmd_migrate)
        self.registry.register('makemigrations', None, self.cmd_makemigrations)
        self.registry.register('showmigrations', None, self.cmd_showmigrations)
        self.registry.register('dbshell', None, self.cmd_dbshell)

        # Project commands
        self.registry.register('startproject', self._validate_project_name, self.cmd_startproject)
        self.registry.register('startapp', self._validate_app_name, self.cmd_startapp)
        self.registry.register('createapp', self._validate_app_name, self.cmd_createapp)
        self.registry.register('collectstatic', None, self.cmd_collectstatic)

        # Testing commands
        self.registry.register('test', self._validate_test_args, self.cmd_test)

        # User commands
        self.registry.register('createsuperuser', None, self.cmd_createsuperuser)

        # System commands
        self.registry.register('check', None, self.cmd_check)
        self.registry.register('version', None, self.cmd_version)
        self.registry.register('help', None, self.cmd_help)

        # Queue commands
        self.registry.register('work', None, self.cmd_work)
        self.registry.register('enqueue', None, self.cmd_enqueue)
        self.registry.register('schedule', None, self.cmd_schedule)
        self.registry.register('jobs', None, self.cmd_jobs)
        self.registry.register('workers', None, self.cmd_workers)

    # Validation methods
    def _validate_server_args(self, args) -> List[str]:
        """Validate server arguments"""
        errors = []
        
        if not self._validate_host(args.host):
            errors.append(f"Invalid host address: {args.host}")
            
        if not self._validate_port(args.port):
            errors.append(f"Invalid port number: {args.port} (must be 1-65535)")
            
        if hasattr(args, 'workers') and not self._validate_workers(args.workers):
            errors.append(f"Invalid worker count: {args.workers} (must be 1-100)")
            
        if not self._validate_module_path(args.app):
            errors.append(f"Invalid app module path: {args.app}")
            
        if not self._check_module_exists(args.app):
            errors.append(f"App module not found: {args.app}")
            
        if not self._check_command_exists('hypercorn'):
            errors.append("Hypercorn is not installed or not in PATH")
            
        return errors

    def _validate_test_args(self, args) -> List[str]:
        """Validate test arguments"""
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
                    
        return errors

    def _validate_project_name(self, args) -> List[str]:
        """Validate project name"""
        errors = []

        if not self._validate_app_name_str(args.name):
            errors.append(f"Invalid project name: {args.name} (must be a valid Python identifier)")

        if os.path.exists(args.name):
            errors.append(f"Directory '{args.name}' already exists")

        return errors

    def _validate_app_name(self, args) -> List[str]:
        """Validate app name"""
        errors = []

        if not self._validate_app_name_str(args.name):
            errors.append(f"Invalid app name: {args.name} (must be a valid Python identifier)")

        if os.path.exists(args.name):
            errors.append(f"Directory '{args.name}' already exists")

        return errors

    # Utility validation methods
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

    def _validate_app_name_str(self, name: str) -> bool:
        """Validate application name string"""
        if not name:
            return False
        # Must be valid Python identifier
        return bool(re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name))

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

    # Command execution methods
    def run(self):
        """Run the CLI"""
        args = self.parser.parse_args()

        if not hasattr(args, 'command') or not args.command:
            self.parser.print_help()
            return

        if not self.registry.execute(args.command, args):
            print(f"Unknown command: {args.command}")
            self.parser.print_help()
            sys.exit(1)

    def cmd_start(self, args):
        """Start the server"""
        print(f"Starting Pyserv server on {args.host}:{args.port}")

        # Set environment variables
        env = os.environ.copy()
        env['PYSERV _HOST'] = args.host
        env['PYSERV _PORT'] = str(args.port)
        env['PYSERV _WORKERS'] = str(args.workers)
        env['PYSERV _RELOAD'] = '1' if args.reload else '0'
        env['PYSERV _DEBUG'] = '1' if args.debug else '0'

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
        print("Starting Pyserv shell...")
        try:
            import IPython
            IPython.embed()
        except ImportError:
            import code
            code.interact()

    def cmd_dbshell(self, args):
        """Start database shell"""
        print("Database shell not implemented yet")

    def cmd_migrate(self, args):
        """Run database migrations"""
        import asyncio
        from ..migrations.framework import migrate_app, check_migration_status
        from ..database.config import DatabaseConfig

        async def run_migrations():
            try:
                # Get database configuration
                db_config = DatabaseConfig.from_env()
                if not db_config:
                    print("❌ No database configuration found")
                    return

                # Get app package name
                app_package = getattr(args, 'models_package', 'app')

                # Handle different actions
                if args.action == 'status':
                    print(f"🔍 Checking migration status for app: {app_package}")
                    status = await check_migration_status(db_config, app_package)
                    print(f"📊 Migration Status:")
                    print(f"  • Total models: {status['total_models']}")
                    print(f"  • Up to date: {status['up_to_date']}")
                    print(f"  • Needs update: {status['needs_update']}")
                    for model in status['models']:
                        status_icon = "✅" if model['up_to_date'] else "⏳"
                        print(f"    {status_icon} {model['name']}: v{model['current_version']} -> v{model['target_version']}")
                    return

                elif args.action == 'list':
                    print(f"📋 Listing all migrations for app: {app_package}")
                    status = await check_migration_status(db_config, app_package)
                    print("Available Models and Migrations:")
                    for model in status['models']:
                        print(f"  • {model['name']}: Current v{model['current_version']}, Target v{model['target_version']}")
                    return

                elif args.action == 'downgrade':
                    if not args.version and not args.target_version:
                        print("❌ Version required for downgrade action (--version or --target-version)")
                        return
                    target_ver = args.target_version or args.version
                    print(f"⬇️  Downgrading migrations to version {target_ver}")

                    # Handle specific migration ID for downgrade
                    if args.migration_id:
                        print(f"🔍 Downgrading specific migration: {args.migration_id}")

                elif args.action == 'reset':
                    print("🔄 Resetting all migrations")
                    if not getattr(args, 'force', False):
                        confirm = input("⚠️  This will reset all migrations. Continue? (y/N): ").lower().strip()
                        if confirm not in ['y', 'yes']:
                            print("Operation cancelled")
                            return

                print(f"🔄 Running migrations for app: {app_package}")

                # Run migrations
                results = await migrate_app(
                    db_config,
                    app_package=app_package,
                    dry_run=args.dry_run
                )

                if args.dry_run:
                    print("📋 Dry run results:")
                    print(f"  • Models processed: {results['models_processed']}")
                    print(f"  • Migrations would be applied: {len(results['migrations'])}")
                    for migration in results['migrations']:
                        print(f"    - {migration['model']}: v{migration['from_version']} -> v{migration['to_version']}")
                else:
                    print("✅ Migration complete:")
                    print(f"  • Models processed: {results['models_processed']}")
                    print(f"  • Migrations applied: {results['migrations_applied']}")

                if results['errors']:
                    print("❌ Errors encountered:")
                    for error in results['errors']:
                        print(f"  • {error}")

            except Exception as e:
                print(f"❌ Migration failed: {e}")
                import traceback
                traceback.print_exc()

        asyncio.run(run_migrations())

    def cmd_makemigrations(self, args):
        """Create database migrations"""
        print("Create migrations command - implementation depends on database framework")

    def cmd_showmigrations(self, args):
        """Show migration status"""
        print("Show migrations command - implementation depends on database framework")

    def cmd_startproject(self, args):
        """Create a new Pyserv project"""
        project_name = args.name
        template = args.template

        # Interactive mode for template selection
        if getattr(args, 'interactive', False) or template == 'basic':
            print("🚀 Welcome to Pyserv Project Creator!")
            print("Let's set up your new project with the perfect template.\n")

            print("Available templates:")
            templates = {
                'minimal': 'Simple, lightweight setup for small projects',
                'basic': 'Standard web application with common features',
                'api': 'REST API focused with authentication and documentation',
                'full': 'Complete application with all Pyserv features',
                'microservice': 'Microservice architecture with service discovery',
                'enterprise': 'Production-ready with advanced security and monitoring'
            }

            for key, desc in templates.items():
                marker = "→" if key == template else " "
                print(f"  {marker} {key}: {desc}")

            if getattr(args, 'interactive', False):
                print(f"\nCurrent selection: {template}")
                choice = input("Choose a template (or press Enter to keep current): ").strip().lower()
                if choice and choice in templates:
                    template = choice
                    print(f"✅ Selected template: {template}")
                elif choice:
                    print(f"⚠️  Invalid choice '{choice}', keeping current template: {template}")

        print(f"\n📦 Creating Pyserv project '{project_name}' with '{template}' template...")

        # Check if git repo is specified
        if hasattr(args, 'git_repo') and args.git_repo:
            print(f"Cloning template from: {args.git_repo}")
            self._clone_git_template(project_name, args.git_repo, args.git_branch)
        else:
            # Create project structure from template
            self._create_project_from_template(project_name, template)

        print(f"\n✅ Project '{project_name}' created successfully!")
        print("\n🎯 Next steps:")
        print(f"  cd {project_name}")
        print("  pip install -r requirements.txt")
        print("  python manage.py migrate")
        print("  python manage.py createsuperuser")
        print("  python manage.py runserver")
        print("\n📚 For more information, check the README.md file in your project directory")
        print(f"\n🎉 Happy coding with Pyserv!")

    def _clone_git_template(self, project_name: str, git_repo: str, branch: str):
        """Clone a project template from git repository"""
        try:
            # Check if git is available
            if not self._check_command_exists('git'):
                print("❌ Git is not installed or not in PATH")
                print("Falling back to basic template...")
                self._create_project_from_template(project_name, 'basic')
                return

            # Clone the repository
            cmd = ['git', 'clone', '--depth', '1']
            if branch != 'main':
                cmd.extend(['-b', branch])
            cmd.extend([git_repo, project_name])

            print(f"📥 Cloning repository: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                print(f"❌ Failed to clone repository: {result.stderr}")
                print("Falling back to basic template...")
                self._create_project_from_template(project_name, 'basic')
                return

            # Remove .git directory to start fresh
            git_dir = Path(project_name) / '.git'
            if git_dir.exists():
                import shutil
                shutil.rmtree(git_dir)

            print("✅ Template cloned successfully")

        except Exception as e:
            print(f"❌ Error cloning template: {e}")
            print("Falling back to basic template...")
            self._create_project_from_template(project_name, 'basic')

    def _create_project_from_template(self, project_name: str, template: str):
        """Create project structure from built-in template"""
        # Create standard project structure following framework conventions
        project_dirs = [
            project_name,
            f"{project_name}/apps",
            f"{project_name}/static",
            f"{project_name}/static/css",
            f"{project_name}/static/js",
            f"{project_name}/static/images",
            f"{project_name}/templates",
            f"{project_name}/config",
            f"{project_name}/tests",
            f"{project_name}/docs",
        ]

        for dir_path in project_dirs:
            os.makedirs(dir_path, exist_ok=True)

        # Create main application file
        app_content = f'''"""
{project_name} - Pyserv  Application
"""

from pyserv import Application
from pyserv.server.config import Config
from pyserv.core.database import DatabaseConnection
import asyncio

# Create application instance
app = Application()

# Load configuration
config = Config()
config.from_object('config.settings')

# Database setup
db = DatabaseConnection(config.DATABASE_URL)

@app.on_startup
async def startup():
    """Application startup event"""
    await db.connect()
    print("Application started successfully!")

@app.on_shutdown
async def shutdown():
    """Application shutdown event"""
    await db.disconnect()
    print("Application shut down")

# Basic routes
@app.route('/')
async def home(request):
    """Home page"""
    return {{
        'message': f'Welcome to {project_name}!',
        'status': 'running',
        'version': '1.0.0'
    }}

@app.route('/health')
async def health(request):
    """Health check endpoint"""
    return {{
        'status': 'healthy',
        'timestamp': request.headers.get('date', ''),
        'service': '{project_name}'
    }}

@app.route('/api/v1/info')
async def api_info(request):
    """API information"""
    return {{
        'name': '{project_name}',
        'version': '1.0.0',
        'description': 'Pyserv  application',
        'endpoints': [
            '/',
            '/health',
            '/api/v1/info'
        ]
    }}

if __name__ == '__main__':
    # Run directly for development
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8000, reload=True)
'''

        with open(f"{project_name}/app.py", 'w', encoding='utf-8') as f:
            f.write(app_content)

        # Create manage.py for CLI commands
        manage_content = f'''#!/usr/bin/env python3
"""
{project_name} Management Script
"""

import sys
import os
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

def main():
    """Main entry point"""
    from pyserv.cli import main
    main()

if __name__ == '__main__':
    main()
'''

        with open(f"{project_name}/manage.py", 'w', encoding='utf-8') as f:
            f.write(manage_content)

        # Make manage.py executable
        os.chmod(f"{project_name}/manage.py", 0o755)

        # Create configuration file
        config_content = f'''# {project_name} Configuration

# Application settings
DEBUG = True
SECRET_KEY = "{os.urandom(32).hex()}"
APP_NAME = "{project_name}"

# Server settings
HOST = "127.0.0.1"
PORT = 8000
WORKERS = 1

# Database settings
DATABASE_URL = "mongodb://localhost:27017/{project_name.lower()}"

# Security settings
SESSION_SECRET = "{os.urandom(32).hex()}"
JWT_SECRET = "{os.urandom(32).hex()}"

# Logging
LOG_LEVEL = "INFO"
LOG_FILE = "logs/app.log"

# Email settings (optional)
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USER = ""
EMAIL_PASSWORD = ""

# File upload settings
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB
UPLOAD_FOLDER = "uploads"

# API settings
API_PREFIX = "/api/v1"
API_VERSION = "1.0.0"
'''

        with open(f"{project_name}/config/settings.py", 'w', encoding='utf-8') as f:
            f.write(config_content)

        # Create __init__.py for config
        with open(f"{project_name}/config/__init__.py", 'w', encoding='utf-8') as f:
            f.write('')

        # Create requirements file
        requirements_content = '''# Core dependencies
pyserv >=1.0.0
motor>=3.0.0
pymongo>=4.0.0

# Web server
uvicorn[standard]>=0.20.0
hypercorn>=0.14.0

# Templates
jinja2>=3.0.0

# Utilities
python-dotenv>=0.19.0
click>=8.0.0

# Development dependencies
pytest>=7.0.0
pytest-asyncio>=0.21.0
black>=22.0.0
flake8>=4.0.0
'''

        with open(f"{project_name}/requirements.txt", 'w', encoding='utf-8') as f:
            f.write(requirements_content)

        # Create .env.example file
        env_content = f'''# {project_name} Environment Variables

# Database
DATABASE_URL=mongodb://localhost:27017/{project_name.lower()}

# Application
DEBUG=True
SECRET_KEY={os.urandom(32).hex()}

# Server
HOST=127.0.0.1
PORT=8000

# Security
SESSION_SECRET={os.urandom(32).hex()}
JWT_SECRET={os.urandom(32).hex()}

# Email (configure as needed)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
'''

        with open(f"{project_name}/.env.example", 'w', encoding='utf-8') as f:
            f.write(env_content)

        # Create .gitignore
        gitignore_content = '''# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Logs
*.log
logs/

# Database
*.db
*.sqlite3

# Uploads
uploads/
media/

# Node modules (if using frontend)
node_modules/

# Coverage
.coverage
htmlcov/
.pytest_cache/

# Temporary files
*.tmp
*.temp
'''

        with open(f"{project_name}/.gitignore", 'w', encoding='utf-8') as f:
            f.write(gitignore_content)

        # Create README.md
        readme_content = f'''# {project_name}

A Pyserv  web application.

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Copy environment configuration:
```bash
cp .env.example .env
```

4. Run database migrations:
```bash
python manage.py migrate
```

5. Create a superuser:
```bash
python manage.py createsuperuser
```

6. Run the development server:
```bash
python manage.py runserver
```

## Project Structure

```
{project_name}/
├── app.py              # Main application file
├── manage.py           # Management script
├── config/             # Configuration files
│   ├── __init__.py
│   └── settings.py
├── apps/               # Application modules
├── static/             # Static files (CSS, JS, images)
├── templates/          # HTML templates
├── tests/              # Test files
└── docs/               # Documentation
```

## Available Commands

- `python manage.py runserver` - Start development server
- `python manage.py migrate` - Run database migrations
- `python manage.py createsuperuser` - Create admin user
- `python manage.py test` - Run tests
- `python manage.py shell` - Start interactive shell

## API Endpoints

- `GET /` - Home page
- `GET /health` - Health check
- `GET /api/v1/info` - API information

## License

MIT License
'''

        with open(f"{project_name}/README.md", 'w', encoding='utf-8') as f:
            f.write(readme_content)

        # Create basic test file
        test_content = f'''"""
Tests for {project_name}
"""

import pytest
from app import app


def test_home_endpoint():
    """Test home endpoint"""
    # This is a placeholder test
    # Add your actual tests here
    assert True


def test_health_endpoint():
    """Test health endpoint"""
    # This is a placeholder test
    # Add your actual tests here
    assert True


if __name__ == '__main__':
    pytest.main([__file__])
'''

        with open(f"{project_name}/tests/__init__.py", 'w', encoding='utf-8') as f:
            f.write('')

        with open(f"{project_name}/tests/test_app.py", 'w', encoding='utf-8') as f:
            f.write(test_content)

        # Create logs directory
        os.makedirs(f"{project_name}/logs", exist_ok=True)

        print(f"📁 Created project structure with {len(project_dirs)} directories")
        print("📄 Generated configuration and template files")

    def cmd_startapp(self, args):
        """Create a new Pyserv app"""
        app_name = args.name

        print(f"Creating Pyserv app '{app_name}'...")

        # Create app structure
        os.makedirs(f"{app_name}/models")
        os.makedirs(f"{app_name}/views")
        os.makedirs(f"{app_name}/controllers")
        os.makedirs(f"{app_name}/templates/{app_name}")
        os.makedirs(f"{app_name}/static/{app_name}")

        # Create __init__.py
        init_content = f'''"""
{app_name} app for Pyserv 
"""
'''

        with open(f"{app_name}/__init__.py", 'w') as f:
            f.write(init_content)

        # Create models file
        models_content = f'''"""
Models for {app_name} app
"""

from pyserv.models.base import BaseModel, Field
from datetime import datetime

class ExampleModel(BaseModel):
    """Example model"""
    name = Field(str, required=True)
    description = Field(str)
    created_at = Field(datetime, default=datetime.now)

    class Meta:
        table_name = "{app_name}_example"
'''

        with open(f"{app_name}/models/__init__.py", 'w') as f:
            f.write(models_content)

        # Create views file
        views_content = f'''"""
Views for {app_name} app
"""

from pyserv.views.base import TemplateView

class HomeView(TemplateView):
    template_name = "{app_name}/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['app_name'] = '{app_name}'
        return context
'''

        with open(f"{app_name}/views/__init__.py", 'w') as f:
            f.write(views_content)

        # Create controllers file
        controllers_content = f'''"""
Controllers for {app_name} app
"""

from pyserv.controllers.base import BaseController

class {app_name.title()}Controller(BaseController):
    """Controller for {app_name}"""

    def index(self, request):
        """Index action"""
        return self.render_template("{app_name}/index.html", {{
            'title': '{app_name.title()}',
            'message': 'Welcome to {app_name}!'
        }})
'''

        with open(f"{app_name}/controllers/__init__.py", 'w') as f:
            f.write(controllers_content)

        print(f"App '{app_name}' created successfully!")

    def cmd_createapp(self, args):
        """Create a new application"""
        app_dir = Path(args.name)

        try:
            # Create app structure
            app_dir.mkdir(parents=True, exist_ok=False)

            # Create __init__.py
            (app_dir / '__init__.py').write_text('')

            # Create models.py
            (app_dir / 'models.py').write_text(f'''from pyserv import BaseModel

class {args.name.title()}Model(BaseModel):
    """Model for {args.name} app"""
    pass
''')

            # Create views.py
            (app_dir / 'views.py').write_text(f'''from pyserv import Application

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

    def cmd_runserver(self, args):
        """Run development server"""
        print(f"Starting development server at http://{args.host}:{args.port}")

        # Import and run the application
        try:
            # Try to find app.py in current directory
            spec = importlib.util.spec_from_file_location("app", "app.py")
            if spec and spec.loader:
                app_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(app_module)

                if hasattr(app_module, 'app'):
                    app = app_module.app
                    app.run(host=args.host, port=args.port)
                else:
                    print("Error: No 'app' instance found in app.py")
            else:
                print("Error: Could not find app.py")
        except Exception as e:
            print(f"Error starting server: {e}")

    def cmd_collectstatic(self, args):
        """Collect static files"""
        # Import directly to avoid circular imports
        import importlib.util
        spec = importlib.util.spec_from_file_location("staticfiles", "src/pyserv/utils/staticfiles.py")
        staticfiles = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(staticfiles)

        # Parse additional arguments
        clear = getattr(args, 'clear', False)
        deploy_cdn = getattr(args, 'cdn', False)
        add_hashing = getattr(args, 'hash', False)

        # Create mock args object for the staticfiles command
        class MockArgs:
            def __init__(self):
                self.clear = clear
                self.cdn = deploy_cdn
                self.hash = add_hashing

        mock_args = MockArgs()
        staticfiles.cmd_collectstatic(mock_args)

    def cmd_test(self, args):
        """Run tests"""
        print("🧪 Running Pyserv tests...")

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
            cmd.extend(['--cov=src/pyserv', '--cov-report=html', '--cov-report=term'])

        # Add verbosity
        if args.verbose or (hasattr(args, 'verbosity') and args.verbosity > 1):
            cmd.append('-v')

        # Add app filter if specified
        if hasattr(args, 'app') and args.app:
            cmd.append(f"tests/{args.app}")
        elif hasattr(args, 'app') and not args.app:
            cmd.append('tests/')
        else:
            cmd.append('tests/')

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

    def cmd_createsuperuser(self, args):
        """Create superuser"""
        import asyncio
        from ..models.user import BaseUser, UserRole, UserStatus

        async def create_superuser():
            try:
                print("Creating superuser...")

                # Interactive superuser creation
                username = input("Username: ").strip()
                email = input("Email: ").strip()
                password = input("Password: ")
                confirm_password = input("Confirm password: ")

                if not username or not email or not password:
                    print("❌ Username, email, and password are required")
                    return

                if password != confirm_password:
                    print("❌ Error: Passwords do not match")
                    return

                # Create superuser
                user = await BaseUser.create_user(
                    email=email,
                    username=username,
                    password=password,
                    role=UserRole.ADMIN,
                    status=UserStatus.ACTIVE,
                    is_superuser=True,
                    is_staff=True,
                    is_verified=True
                )

                print(f"✅ Superuser '{username}' created successfully!")
                print(f"   Email: {email}")
                print(f"   Role: {user.role}")
                print(f"   Status: {user.status}")

            except Exception as e:
                print(f"❌ Failed to create superuser: {e}")
                import traceback
                traceback.print_exc()

        asyncio.run(create_superuser())

    def cmd_check(self, args):
        """Check for common problems"""
        print("Checking for common problems...")

        issues = []

        # Check for required files
        required_files = ['app.py', 'requirements.txt']
        for file in required_files:
            if not os.path.exists(file):
                issues.append(f"Missing required file: {file}")

        # Check Python version
        if sys.version_info < (3, 8):
            issues.append("Python 3.8+ is required")

        if issues:
            print("Issues found:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("No issues found!")

    def cmd_version(self, args):
        """Show Pyserv version"""
        try:
            from .. import __version__
            print(f"Pyserv {__version__}")
        except ImportError:
            print("Pyserv version unknown")

    def cmd_help(self, args):
        """Show help"""
        self.parser.print_help()

    def cmd_work(self, args):
        """Start background workers"""
        print(f"Starting {args.workers} worker(s) for queue '{args.queue}'...")
        print("Background worker implementation depends on queue framework")

    def cmd_enqueue(self, args):
        """Enqueue a background job"""
        print(f"Enqueueing job: {args.func}")
        print("Background job implementation depends on queue framework")

    def cmd_schedule(self, args):
        """Schedule a cron job"""
        print(f"Scheduling job: {args.func} with cron '{args.cron}'")
        print("Cron job implementation depends on scheduler framework")

    def cmd_jobs(self, args):
        """List background jobs"""
        print(f"Background jobs in queue '{args.queue}':")
        print("Job listing implementation depends on queue framework")

    def cmd_workers(self, args):
        """Manage workers"""
        if args.action == 'start':
            print(f"Starting {args.workers} worker(s) for queue '{args.queue}'...")
        elif args.action == 'stop':
            print(f"Stopping workers for queue '{args.queue}'...")
        elif args.action == 'status':
            print(f"Worker status for queue '{args.queue}':")
        print("Worker management implementation depends on queue framework")

    def _get_pid_file(self):
        """Get PID file path"""
        return Path('.pyserv .pid')

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
    """Main CLI entry point"""
    cli = PyservCLI()
    cli.run()


if __name__ == '__main__':
    main()

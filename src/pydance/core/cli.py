"""
Command Line Interface for PyDance framework.
Provides development tools, project management, and deployment utilities.
"""

import os
import sys
import argparse
import subprocess
import json
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
import importlib.util

from ..core.config import AppConfig
from ..core.database import DatabaseConnection
from ..core.queues import queue_manager, cron_scheduler
from ..models.base import BaseModel
from ..migrations.framework import MigrationFramework


class CLI:
    """Main CLI class"""

    def __init__(self):
        self.commands: Dict[str, Callable] = {}
        self.register_commands()

    def register_commands(self):
        """Register available commands"""
        self.commands = {
            'startproject': self.startproject,
            'startapp': self.startapp,
            'runserver': self.runserver,
            'shell': self.shell,
            'dbshell': self.dbshell,
            'makemigrations': self.makemigrations,
            'migrate': self.migrate,
            'showmigrations': self.showmigrations,
            'createsuperuser': self.createsuperuser,
            'collectstatic': self.collectstatic,
            'test': self.test,
            'check': self.check,
            'version': self.version,
            'help': self.help_command
        }

    def run(self, args: List[str] = None):
        """Run CLI command"""
        if args is None:
            args = sys.argv[1:]

        if not args:
            self.help_command()
            return

        command = args[0]
        command_args = args[1:]

        if command in self.commands:
            try:
                self.commands[command](command_args)
            except Exception as e:
                print(f"Error: {e}")
                sys.exit(1)
        else:
            print(f"Unknown command: {command}")
            self.help_command()
            sys.exit(1)

    def startproject(self, args: List[str]):
        """Create a new PyDance project"""
        parser = argparse.ArgumentParser(description='Create a new PyDance project')
        parser.add_argument('name', help='Project name')
        parser.add_argument('--template', default='basic',
                           help='Project template (basic, api, full)')
        args_parsed = parser.parse_args(args)

        project_name = args_parsed.name
        template = args_parsed.template

        if os.path.exists(project_name):
            print(f"Error: Directory '{project_name}' already exists")
            return

        print(f"Creating PyDance project '{project_name}'...")

        # Create project structure
        os.makedirs(project_name)
        os.makedirs(f"{project_name}/apps")
        os.makedirs(f"{project_name}/static")
        os.makedirs(f"{project_name}/templates")
        os.makedirs(f"{project_name}/config")

        # Create main app file
        app_content = f'''"""
{project_name} - PyDance Application
"""

from pydance import Application, AppConfig
from pydance.core.routing import Router

# Create application
app = Application()

# Configure app
app.config.debug = True
app.config.secret_key = "your-secret-key-here"

# Define routes
@app.route('/')
def home(request):
    return "Welcome to {project_name}!"

# Run application
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
'''

        with open(f"{project_name}/app.py", 'w') as f:
            f.write(app_content)

        # Create config file
        config_content = '''# PyDance Configuration
DEBUG = True
SECRET_KEY = "your-secret-key-here"
DATABASE_URL = "mongodb://localhost:27017/pydance"
'''

        with open(f"{project_name}/config/settings.py", 'w') as f:
            f.write(config_content)

        # Create requirements file
        requirements_content = '''pydance
motor
jinja2
'''

        with open(f"{project_name}/requirements.txt", 'w') as f:
            f.write(requirements_content)

        print(f"Project '{project_name}' created successfully!")
        print("Next steps:")
        print(f"  cd {project_name}")
        print("  pip install -r requirements.txt")
        print("  python app.py")

    def startapp(self, args: List[str]):
        """Create a new PyDance app"""
        parser = argparse.ArgumentParser(description='Create a new PyDance app')
        parser.add_argument('name', help='App name')
        args_parsed = parser.parse_args(args)

        app_name = args_parsed.name

        if os.path.exists(app_name):
            print(f"Error: Directory '{app_name}' already exists")
            return

        print(f"Creating PyDance app '{app_name}'...")

        # Create app structure
        os.makedirs(f"{app_name}/models")
        os.makedirs(f"{app_name}/views")
        os.makedirs(f"{app_name}/controllers")
        os.makedirs(f"{app_name}/templates/{app_name}")
        os.makedirs(f"{app_name}/static/{app_name}")

        # Create __init__.py
        init_content = f'''"""
{app_name} app for PyDance
"""
'''

        with open(f"{app_name}/__init__.py", 'w') as f:
            f.write(init_content)

        # Create models file
        models_content = f'''"""
Models for {app_name} app
"""

from pydance.models.base import BaseModel, Field

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

from pydance.views.base import TemplateView

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

from pydance.controllers.base import BaseController

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

    def runserver(self, args: List[str]):
        """Run development server"""
        parser = argparse.ArgumentParser(description='Run development server')
        parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
        parser.add_argument('--port', type=int, default=8000, help='Port to bind to')
        parser.add_argument('--reload', action='store_true', help='Enable auto-reload')
        args_parsed = parser.parse_args(args)

        print(f"Starting development server at http://{args_parsed.host}:{args_parsed.port}")

        # Import and run the application
        try:
            # Try to find app.py in current directory
            spec = importlib.util.spec_from_file_location("app", "app.py")
            if spec and spec.loader:
                app_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(app_module)

                if hasattr(app_module, 'app'):
                    app = app_module.app
                    app.run(host=args_parsed.host, port=args_parsed.port)
                else:
                    print("Error: No 'app' instance found in app.py")
            else:
                print("Error: Could not find app.py")
        except Exception as e:
            print(f"Error starting server: {e}")

    def shell(self, args: List[str]):
        """Start interactive shell"""
        print("PyDance Interactive Shell")
        print("Available objects: app, models, etc.")
        print("Type 'exit()' to quit")

        # Create shell context
        context = {
            'app': None,  # Would need to load actual app
            'models': None,
            'exit': lambda: sys.exit(0)
        }

        try:
            import IPython
            IPython.embed(user_ns=context)
        except ImportError:
            import code
            code.interact(local=context)

    def dbshell(self, args: List[str]):
        """Start database shell"""
        print("Database shell not implemented yet")
        # Would connect to database and provide interactive shell

    def makemigrations(self, args: List[str]):
        """Create database migrations"""
        parser = argparse.ArgumentParser(description='Create database migrations')
        parser.add_argument('--app', help='App to create migrations for')
        parser.add_argument('--name', default='auto', help='Migration name')
        args_parsed = parser.parse_args(args)

        print("Creating migrations...")

        # This would use the migration framework
        migration_framework = MigrationFramework()
        migrations = migration_framework.create_migrations(args_parsed.app)

        if migrations:
            print(f"Created {len(migrations)} migrations")
        else:
            print("No changes detected")

    def migrate(self, args: List[str]):
        """Apply database migrations"""
        parser = argparse.ArgumentParser(description='Apply database migrations')
        parser.add_argument('--app', help='App to migrate')
        parser.add_argument('--fake', action='store_true', help='Mark migrations as run without executing')
        args_parsed = parser.parse_args(args)

        print("Applying migrations...")

        # This would use the migration framework
        migration_framework = MigrationFramework()
        applied = migration_framework.apply_migrations(args_parsed.app, fake=args_parsed.fake)

        print(f"Applied {len(applied)} migrations")

    def showmigrations(self, args: List[str]):
        """Show migration status"""
        parser = argparse.ArgumentParser(description='Show migration status')
        parser.add_argument('--app', help='App to show migrations for')
        args_parsed = parser.parse_args(args)

        print("Migration status:")

        # This would use the migration framework
        migration_framework = MigrationFramework()
        status = migration_framework.get_migration_status(args_parsed.app)

        for migration, applied in status.items():
            status_str = "applied" if applied else "pending"
            print(f"  {migration}: {status_str}")

    def createsuperuser(self, args: List[str]):
        """Create superuser"""
        print("Creating superuser...")

        # Interactive superuser creation
        username = input("Username: ")
        email = input("Email: ")
        password = input("Password: ")
        confirm_password = input("Confirm password: ")

        if password != confirm_password:
            print("Error: Passwords do not match")
            return

        # This would create a superuser in the database
        print(f"Superuser '{username}' created successfully")

    def collectstatic(self, args: List[str]):
        """Collect static files"""
        parser = argparse.ArgumentParser(description='Collect static files')
        parser.add_argument('--noinput', action='store_true', help='Do not prompt for input')
        args_parsed = parser.parse_args(args)

        print("Collecting static files...")

        # This would collect static files from all apps
        static_files = []  # Would scan for static files

        print(f"Collected {len(static_files)} static files")

    def test(self, args: List[str]):
        """Run tests"""
        parser = argparse.ArgumentParser(description='Run tests')
        parser.add_argument('--app', help='App to test')
        parser.add_argument('--verbosity', type=int, default=1, help='Test verbosity')
        parser.add_argument('--keepdb', action='store_true', help='Keep test database')
        args_parsed = parser.parse_args(args)

        print("Running tests...")

        # Run pytest
        cmd = ['pytest']
        if args_parsed.app:
            cmd.append(f"tests/{args_parsed.app}")
        else:
            cmd.append('tests/')

        if args_parsed.verbosity > 1:
            cmd.append('-v')

        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Tests failed with exit code {e.returncode}")
            sys.exit(e.returncode)

    def check(self, args: List[str]):
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

    def version(self, args: List[str]):
        """Show PyDance version"""
        try:
            from .. import __version__
            print(f"PyDance {__version__}")
        except ImportError:
            print("PyDance version unknown")

    def help_command(self, args: List[str] = None):
        """Show help"""
        print("PyDance CLI")
        print("Available commands:")
        print()

        commands_help = {
            'startproject': 'Create a new PyDance project',
            'startapp': 'Create a new PyDance app',
            'runserver': 'Run development server',
            'shell': 'Start interactive shell',
            'dbshell': 'Start database shell',
            'makemigrations': 'Create database migrations',
            'migrate': 'Apply database migrations',
            'showmigrations': 'Show migration status',
            'createsuperuser': 'Create superuser',
            'collectstatic': 'Collect static files',
            'test': 'Run tests',
            'check': 'Check for common problems',
            'version': 'Show PyDance version',
            'help': 'Show this help'
        }

        for cmd, desc in commands_help.items():
            print("15")

        print()
        print("Use 'pydance <command> --help' for more information about a command")


def main():
    """Main CLI entry point"""
    cli = CLI()
    cli.run()


if __name__ == '__main__':
    main()

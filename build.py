#!/usr/bin/env python3
"""
Build script for Pyserv  framework.
Handles building, testing, and publishing the package.
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd, cwd=None):
    """Run a command and return the result."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {cmd}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        sys.exit(1)


def main():
    """Main build function."""
    if len(sys.argv) < 2:
        print("Usage: python build.py [clean|build|test|publish|all]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "clean":
        print("Cleaning build artifacts...")
        run_command("rm -rf build/ dist/ *.egg-info/ .tox/ htmlcov/ .coverage .pytest_cache/ .mypy_cache/")

    elif command == "build":
        print("Building package...")
        run_command("python -m build")

    elif command == "test":
        print("Running tests...")
        run_command("python -m pytest --cov=pyserv  --cov-report=term-missing")

    elif command == "lint":
        print("Running linting...")
        run_command("python -m flake8 src/pyserv tests")
        run_command("python -m black --check --diff src/pyserv tests")
        run_command("python -m isort --check-only --diff src/pyserv tests")

    elif command == "typecheck":
        print("Running type checking...")
        run_command("python -m mypy src/pyserv")

    elif command == "security":
        print("Running security checks...")
        run_command("python -m bandit -r src/pyserv -c .bandit.yml")

    elif command == "publish":
        print("Publishing to PyPI...")
        run_command("python -m twine upload dist/*")

    elif command == "check":
        print("Checking package...")
        run_command("python -m twine check dist/*")

    elif command == "install":
        print("Installing package...")
        run_command("pip install -e .")

    elif command == "all":
        print("Running full build pipeline...")
        main_with_args(["clean"])
        main_with_args(["build"])
        main_with_args(["test"])
        main_with_args(["lint"])
        main_with_args(["typecheck"])
        main_with_args(["security"])
        main_with_args(["check"])
        print("All checks passed! Ready for publishing.")

    else:
        print(f"Unknown command: {command}")
        print("Available commands: clean, build, test, lint, typecheck, security, publish, check, install, all")
        sys.exit(1)


def main_with_args(args):
    """Run main with specific arguments."""
    old_argv = sys.argv
    sys.argv = ["build.py"] + args
    try:
        main()
    finally:
        sys.argv = old_argv


if __name__ == "__main__":
    main()





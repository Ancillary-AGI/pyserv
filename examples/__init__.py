"""
PyDance Examples Package

Common utilities and setup for examples.
"""
import os
import sys
from pathlib import Path


def setup_path():
    """Set up the Python path to include the src directory."""
    # Get the examples directory
    examples_dir = Path(__file__).parent
    # Get the project root (parent of examples)
    project_root = examples_dir.parent
    # Add src to path
    src_dir = project_root / 'src'
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))


def print_header(title: str, description: str = ""):
    """Print a formatted header for examples."""
    print(f"🚀 {title}")
    if description:
        print(description)
    print("=" * 50)
    print()


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n📍 {title}")
    print("-" * 30)


def print_success(message: str):
    """Print a success message."""
    print(f"✅ {message}")


def print_error(message: str):
    """Print an error message."""
    print(f"❌ {message}")


def print_info(message: str):
    """Print an info message."""
    print(f"ℹ️  {message}")


def handle_example_error(func):
    """Decorator to handle errors in examples gracefully."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print_error(f"Error running example: {e}")
            import traceback
            traceback.print_exc()
            return None
    return wrapper

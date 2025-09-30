#!/usr/bin/env python3
"""
Pyserv Framework Setup
Enterprise-grade web framework with optional C/C++ extensions
"""

from setuptools import setup, find_packages, Extension
from pathlib import Path
import sys
import os
import subprocess

def get_version():
    """Get version from __init__.py"""
    version_file = Path(__file__).parent / "src" / "pyserv" / "__init__.py"
    if version_file.exists():
        with open(version_file, 'r') as f:
            for line in f:
                if line.startswith("__version__"):
                    return line.split("=")[1].strip().strip('"\'')
    return "0.1.0"

def read_readme():
    """Read README file"""
    readme_path = Path(__file__).parent / "README.md"
    if readme_path.exists():
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return ""

def check_c_compiler():
    """Check if C compiler is available"""
    try:
        if sys.platform == "win32":
            subprocess.run(['cl'], capture_output=True, check=True)
        else:
            subprocess.run(['gcc', '--version'], capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False

def get_compile_args():
    """Get compiler arguments for performance"""
    if sys.platform == "win32":
        return ["/O2", "/DNDEBUG"]
    else:
        return ["-O3", "-DNDEBUG"]

def should_build_extensions():
    """Determine if C extensions should be built"""
    # Skip C extensions if explicitly disabled
    if os.environ.get('PYSERV_DISABLE_CEXT', '').lower() in ('1', 'true', 'yes'):
        return False
    
    # Check if compiler is available
    if not check_c_compiler():
        print("Warning: C compiler not found. Skipping C extensions.")
        return False
    
    return True

# Core dependencies - minimal for basic functionality
install_requires = [
    # No required dependencies - framework works with stdlib only
]

# Optional dependencies for enhanced features
extras_require = {
    # Security enhancements
    "security": [
        "bcrypt>=3.2.0",           # Password hashing
        "cryptography>=3.4.0",    # Advanced cryptography
        "pyclamd>=0.4.0",         # ClamAV integration (optional)
        "python-magic>=0.4.24",   # File type detection (optional)
    ],
    
    # Validation enhancements
    "validation": [
        "email-validator>=1.1.0", # Email validation
        "phonenumbers>=8.12.0",   # International phone validation
    ],
    
    # Template engine
    "templates": [
        "jinja2>=3.0.0",          # Advanced templating
    ],
    
    # Internationalization
    "i18n": [
        "babel>=2.9.0",           # Locale formatting
        "pytz>=2021.3",           # Timezone support
    ],
    
    # Mathematical operations
    "math": [
        "numpy>=1.21.0",          # Advanced mathematical operations
    ],
    
    # Database support
    "database": [
        "sqlalchemy>=1.4.0",     # SQL ORM
        "asyncpg>=0.24.0",       # PostgreSQL async driver
        "aiomysql>=0.0.21",      # MySQL async driver
        "aiosqlite>=0.17.0",     # SQLite async driver
        "pymongo>=4.0.0",        # MongoDB driver
        "motor>=2.5.0",          # MongoDB async driver
        "redis>=4.0.0",          # Redis support
    ],
    
    # Performance optimizations
    "performance": [
        "uvloop>=0.16.0; sys_platform != 'win32'",  # Fast event loop (Unix only)
        "httptools>=0.4.0",      # Fast HTTP parsing
        "cython>=0.29.0",        # C extensions compilation
    ],
    
    # Web3 and blockchain
    "web3": [
        "web3>=5.24.0",          # Ethereum integration
        "eth-account>=0.5.6",    # Ethereum accounts
    ],
    
    # Monitoring and observability
    "monitoring": [
        "prometheus-client>=0.12.0",  # Metrics collection
        "structlog>=21.2.0",          # Structured logging
        "psutil>=5.8.0",              # System monitoring
    ],
    
    # Development tools
    "dev": [
        "pytest>=6.0.0",
        "pytest-asyncio>=0.18.0",
        "pytest-cov>=3.0.0",
        "black>=21.0.0",
        "isort>=5.0.0",
        "flake8>=3.9.0",
        "mypy>=0.910",
    ],
}

# All optional dependencies
extras_require["all"] = [
    dep for deps in extras_require.values() for dep in deps
]

# Define C extensions for performance
extensions = []
if should_build_extensions():
    # HTTP parser extension
    http_parser_ext = Extension(
        'pyserv.core.http_parser',
        sources=['src/pyserv/core/http_parser.c'] if os.path.exists('src/pyserv/core/http_parser.c') else [],
        extra_compile_args=get_compile_args(),
        language='c'
    )
    
    # Only add if source file exists
    if os.path.exists('src/pyserv/core/http_parser.c'):
        extensions.append(http_parser_ext)
    
    if not extensions:
        print("Note: C extension source files not found. Framework will use Python implementations.")

setup(
    name="pyserv",
    version=get_version(),
    author="Pyserv Team",
    author_email="team@pyserv.dev",
    description="Enterprise-grade Python web framework with optional high-performance extensions",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/pyserv/pyserv",
    project_urls={
        "Documentation": "https://docs.pyserv.dev",
        "Source Code": "https://github.com/pyserv/pyserv",
        "Bug Tracker": "https://github.com/pyserv/pyserv/issues",
        "Changelog": "https://github.com/pyserv/pyserv/blob/main/CHANGELOG.md",
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "Topic :: Security",
        "Framework :: AsyncIO",
    ],
    keywords="web framework http server enterprise security async",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    package_data={
        "pyserv": [
            "static/css/*.css",
            "static/js/*.js", 
            "translations/*.json",
            "locale/*/LC_MESSAGES/*.mo",
        ]
    },
    include_package_data=True,
    python_requires=">=3.8",
    install_requires=install_requires,
    extras_require=extras_require,
    ext_modules=extensions,
    entry_points={
        "console_scripts": [
            "pyserv=pyserv.cli:main",
        ],
    },
    zip_safe=False,
)
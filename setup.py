"""
Pyserv  Framework Setup
High-performance web framework with C/C++ extensions
"""

from setuptools import setup, Extension, find_packages
import os
import sys
import subprocess
from pathlib import Path


def get_version():
    """Get version from version file"""
    version_file = Path(__file__).parent / "src" / "pyserv" / "__init__.py"
    if version_file.exists():
        with open(version_file, 'r') as f:
            for line in f:
                if line.startswith("__version__"):
                    return line.split("=")[1].strip().strip('"\'')
    return "1.0.0"


def has_ssl():
    """Check if OpenSSL is available"""
    import ssl
    return True


def get_compile_args():
    """Get compiler arguments based on platform"""
    if sys.platform == "win32":
        return [
            "/O2",  # Optimize for speed
            "/MT",  # Static linking
            "/DNDEBUG",  # No debug
        ]
    else:
        return [
            "-O3",  # Maximum optimization
            "-march=native",  # CPU-specific optimizations
            "-flto",  # Link-time optimization
            "-fomit-frame-pointer",  # Reduce stack usage
            "-DNDEBUG",  # No debug
        ]


def get_link_args():
    """Get linker arguments"""
    if sys.platform == "win32":
        return []
    else:
        return [
            "-flto",  # Link-time optimization
            "-Wl,--strip-all",  # Strip symbols
        ]


def find_openssl():
    """Find OpenSSL installation"""
    if sys.platform == "win32":
        # Check common locations
        locations = [
            "C:\\OpenSSL-Win64",
            "C:\\OpenSSL-Win32",
            "C:\\Program Files\\OpenSSL",
            "C:\\Program Files (x86)\\OpenSSL"
        ]
        for location in locations:
            if os.path.exists(location):
                return location
        return None
    else:
        # Use pkg-config on Unix-like systems
        try:
            result = subprocess.run(['pkg-config', '--exists', 'openssl'],
                                  capture_output=True, text=True)
            if result.returncode == 0:
                return "pkg-config"
        except FileNotFoundError:
            pass

        # Check common locations
        locations = [
            "/usr/include/openssl",
            "/usr/local/include/openssl",
            "/opt/homebrew/include/openssl"
        ]
        for location in locations:
            if os.path.exists(location):
                return location
        return None


def get_ssl_includes():
    """Get SSL include directories"""
    openssl_path = find_openssl()
    if not openssl_path:
        return []

    if sys.platform == "win32":
        return [os.path.join(openssl_path, "include")]
    elif openssl_path == "pkg-config":
        try:
            result = subprocess.run(['pkg-config', '--cflags', 'openssl'],
                                  capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip().split()
        except FileNotFoundError:
            pass
        return []
    else:
        return [openssl_path]


def get_ssl_libraries():
    """Get SSL library directories and names"""
    openssl_path = find_openssl()
    if not openssl_path:
        return [], []

    if sys.platform == "win32":
        lib_path = os.path.join(openssl_path, "lib")
        return [lib_path], ["libssl", "libcrypto"]
    elif openssl_path == "pkg-config":
        try:
            cflags_result = subprocess.run(['pkg-config', '--libs', 'openssl'],
                                         capture_output=True, text=True)
            if cflags_result.returncode == 0:
                libs = cflags_result.stdout.strip().split()
                lib_dirs = []
                lib_names = []
                for lib in libs:
                    if lib.startswith('-L'):
                        lib_dirs.append(lib[2:])
                    elif lib.startswith('-l'):
                        lib_names.append(lib[2:])
                return lib_dirs, lib_names
        except FileNotFoundError:
            pass
        return [], []
    else:
        return [], ["ssl", "crypto"]


# Check for required dependencies
def check_dependencies():
    """Check for build dependencies"""
    missing = []

    # Check for OpenSSL
    if not has_ssl():
        print("Warning: OpenSSL not available. SSL support will be disabled.")

    # Check for C compiler
    try:
        if sys.platform == "win32":
            subprocess.run(['cl'], capture_output=True)
        else:
            subprocess.run(['gcc', '--version'], capture_output=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        missing.append("C compiler (gcc/cl)")

    if missing:
        print(f"Warning: Missing dependencies: {', '.join(missing)}")
        print("C extensions will not be built. Using Python fallback.")

    return len(missing) == 0


# Define C extension
server_core_extension = Extension(
    'pyserv.core.pyserv_server_core',
    sources=['src/pyserv/core/server_core.c'],
    include_dirs=[
        'src/pyserv/core',
        '/usr/include',
        '/usr/local/include',
    ] + get_ssl_includes(),
    library_dirs=[
        '/usr/lib',
        '/usr/local/lib',
        '/usr/lib64',
        '/usr/local/lib64',
    ] + get_ssl_libraries()[0],
    libraries=[
        'pthread',
        'm',  # math library
    ] + get_ssl_libraries()[1],
    extra_compile_args=get_compile_args(),
    extra_link_args=get_link_args(),
    define_macros=[
        ('HAVE_SSL', '1' if has_ssl() else '0'),
        ('PYSERV_VERSION', f'"{get_version()}"'),
    ],
    language='c',
)

# Check if we should build the extension
build_extensions = check_dependencies()

if not build_extensions:
    extensions = []
else:
    extensions = [server_core_extension]

# Read README
def read_readme():
    """Read README file"""
    readme_path = Path(__file__).parent / "README.md"
    if readme_path.exists():
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return ""


# Read requirements
def read_requirements():
    """Read requirements file"""
    req_path = Path(__file__).parent / "requirements.txt"
    if req_path.exists():
        with open(req_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return []


setup(
    name="pyserv",
    version=get_version(),
    author="Pyserv  Team",
    author_email="team@pyserv.dev",
    description="High-Performance Web Framework with C/C++ Core",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/pyserv/pyserv",
    project_urls={
        "Documentation": "https://pyserv.dev/docs",
        "Source": "https://github.com/pyserv/pyserv",
        "Tracker": "https://github.com/pyserv/pyserv/issues",
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
        "Programming Language :: C",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
        "Topic :: Security",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
    ],
    keywords="web framework http server high-performance c-extensions security",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    package_data={
        "pyserv": [
            "static/css/*.css",
            "static/js/*.js",
            "translations/*.json",
            "security/cryptography.py",
            "security/iam.py",
            "security/zero_trust.py",
            "security/web3.py",
            "security/defense_in_depth.py",
            "security/key_management.py",
            "security/siem_integration.py",
            "security/compliance.py",
            "security/webassembly.py",
            "security/backup_recovery.py",
            "security/performance_optimization.py",
        ]
    },
    include_package_data=True,
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-asyncio>=0.15",
            "pytest-cov>=2.0",
            "black>=21.0",
            "isort>=5.0",
            "flake8>=3.9",
            "mypy>=0.800",
            "sphinx>=4.0",
            "sphinx-rtd-theme>=1.0",
        ],
        "security": [
            "cryptography>=3.4",
            "bcrypt>=3.2",
            "pyjwt>=2.0",
            "oauthlib>=3.1",
            "python-jose>=3.3",
        ],
        "performance": [
            "uvloop>=0.15",
            "httptools>=0.3",
            "gunicorn>=20.1",
        ],
        "database": [
            "sqlalchemy>=1.4",
            "alembic>=1.7",
            "redis>=4.0",
            "pymongo>=4.0",
        ],
        "web3": [
            "web3>=5.25",
            "eth-account>=0.5",
            "ipfshttpclient>=0.8",
        ],
        "monitoring": [
            "prometheus-client>=0.12",
            "sentry-sdk>=1.3",
            "structlog>=21.1",
        ],
    },
    ext_modules=extensions if build_extensions else [],
    entry_points={
        "console_scripts": [
            "pyserv=pyserv.cli:main",
            "pyserv-admin=pyserv.cli:admin",
        ],
    },
    zip_safe=False,
    cmdclass={
        # Custom build commands can be added here
    },
)

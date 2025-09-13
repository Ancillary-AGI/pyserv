import os
from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="pydance",
    version="0.1.0",
    package_dir={'': 'src'},
    packages=find_packages(where='src'),
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'pydance=pydance.cli:main',
        ],
    },
    author="Your Name",
    author_email="your.email@example.com",
    description="A comprehensive web framework with MVC architecture",
    long_description="",
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/pydance",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.8",
)

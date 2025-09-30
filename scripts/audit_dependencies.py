#!/usr/bin/env python3
"""
Dependency audit script for Pyserv framework
Scans all Python files to find actual external dependencies being used
"""

import os
import re
import ast
from pathlib import Path
from collections import defaultdict

# Standard library modules (don't count as external dependencies)
STDLIB_MODULES = {
    'abc', 'asyncio', 'base64', 'binascii', 'collections', 'contextlib', 'copy', 
    'csv', 'dataclasses', 'datetime', 'decimal', 'email', 'enum', 'functools',
    'gc', 'glob', 'hashlib', 'heapq', 'hmac', 'html', 'http', 'inspect', 'io',
    'itertools', 'json', 'logging', 'math', 'mimetypes', 'multiprocessing',
    'operator', 'os', 'pathlib', 'pickle', 'platform', 'queue', 'random', 're',
    'secrets', 'shutil', 'signal', 'socket', 'ssl', 'statistics', 'string',
    'struct', 'subprocess', 'sys', 'tempfile', 'threading', 'time', 'traceback',
    'typing', 'urllib', 'uuid', 'warnings', 'weakref', 'xml', 'zlib', 'gzip',
    'sqlite3', 'stat', 'fnmatch', 'array', 'bisect', 'concurrent', 'atexit',
    '__future__', 'cmath'
}

class ImportVisitor(ast.NodeVisitor):
    def __init__(self):
        self.imports = []
        
    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append(alias.name.split('.')[0])
            
    def visit_ImportFrom(self, node):
        if node.module:
            self.imports.append(node.module.split('.')[0])

def find_imports_in_file(file_path):
    """Find all imports in a Python file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse AST
        try:
            tree = ast.parse(content)
            visitor = ImportVisitor()
            visitor.visit(tree)
            return visitor.imports
        except SyntaxError:
            # Fallback to regex for files with syntax issues
            imports = []
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith('import '):
                    module = line.replace('import ', '').split()[0].split('.')[0]
                    imports.append(module)
                elif line.startswith('from ') and ' import ' in line:
                    module = line.split(' import ')[0].replace('from ', '').split('.')[0]
                    imports.append(module)
            return imports
            
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return []

def scan_directory(directory):
    """Scan directory for Python files and extract imports"""
    external_deps = defaultdict(list)
    
    for root, dirs, files in os.walk(directory):
        # Skip certain directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules']]
        
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, directory)
                
                imports = find_imports_in_file(file_path)
                
                for imp in imports:
                    # Skip internal pyserv imports
                    if imp.startswith('pyserv'):
                        continue
                    # Skip standard library
                    if imp in STDLIB_MODULES:
                        continue
                    # Skip relative imports
                    if imp.startswith('.'):
                        continue
                        
                    external_deps[imp].append(rel_path)
    
    return external_deps

def main():
    src_dir = Path(__file__).parent / "src" / "pyserv"
    
    print("Scanning Pyserv framework for external dependencies...\n")
    
    external_deps = scan_directory(src_dir)
    
    if not external_deps:
        print("No external dependencies found!")
        return
    
    print("External dependencies found:\n")
    
    # Group by dependency type
    security_deps = []
    template_deps = []
    crypto_deps = []
    validation_deps = []
    math_deps = []
    i18n_deps = []
    other_deps = []
    
    for dep, files in sorted(external_deps.items()):
        print(f"* {dep}")
        for file in sorted(set(files)):
            print(f"   - {file}")
        print()
        
        # Categorize dependencies
        if dep in ['bcrypt', 'cryptography', 'pyclamd', 'boto3', 'magic']:
            security_deps.append(dep)
        elif dep in ['jinja2']:
            template_deps.append(dep)
        elif dep in ['email_validator', 'phonenumbers']:
            validation_deps.append(dep)
        elif dep in ['numpy']:
            math_deps.append(dep)
        elif dep in ['babel', 'pytz']:
            i18n_deps.append(dep)
        else:
            other_deps.append(dep)
    
    print("\nDependency Categories:")
    if security_deps:
        print(f"Security: {', '.join(security_deps)}")
    if template_deps:
        print(f"Templates: {', '.join(template_deps)}")
    if validation_deps:
        print(f"Validation: {', '.join(validation_deps)}")
    if math_deps:
        print(f"Math: {', '.join(math_deps)}")
    if i18n_deps:
        print(f"Internationalization: {', '.join(i18n_deps)}")
    if other_deps:
        print(f"Other: {', '.join(other_deps)}")
    
    print(f"\nTotal external dependencies: {len(external_deps)}")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Pyserv  Development Management Script
"""
import os
import sys
from pathlib import Path

# Add src to Python path for development
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

# Import and run CLI
from pyserv.cli import main

if __name__ == '__main__':
    main()





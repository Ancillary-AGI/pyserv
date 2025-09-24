#!/usr/bin/env python3
"""
Build script for Pyserv  Template Engine C++ extensions
"""

import os
import sys
import subprocess
import platform
from pathlib import Path
from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext


class CMakeExtension(Extension):
    def __init__(self, name, sourcedir=''):
        Extension.__init__(self, name, sources=[])
        self.sourcedir = os.path.abspath(sourcedir)


class CMakeBuild(build_ext):
    def run(self):
        try:
            subprocess.check_output(['cmake', '--version'])
        except OSError:
            raise RuntimeError("CMake must be installed to build the following extensions: " +
                             ", ".join(e.name for e in self.extensions))

        for ext in self.extensions:
            self.build_extension(ext)

    def build_extension(self, ext):
        extdir = os.path.abspath(os.path.dirname(self.get_ext_fullpath(ext.name)))
        cmake_args = ['-DCMAKE_LIBRARY_OUTPUT_DIRECTORY=' + extdir,
                      '-DPYTHON_EXECUTABLE=' + sys.executable]

        cfg = 'Debug' if self.debug else 'Release'
        build_args = ['--config', cfg]

        if platform.system() == "Windows":
            cmake_args += ['-DCMAKE_LIBRARY_OUTPUT_DIRECTORY_{}={}'.format(cfg.upper(), extdir)]
            if sys.maxsize > 2**32:
                cmake_args += ['-A', 'x64']
            build_args += ['--', '/m']
        else:
            cmake_args += ['-DCMAKE_BUILD_TYPE=' + cfg]
            build_args += ['--', '-j2']

        env = os.environ.copy()
        env['CXXFLAGS'] = '{} -DVERSION_INFO=\\"{}\\"'.format(env.get('CXXFLAGS', ''),
                                                              self.distribution.get_version())
        if not os.path.exists(self.build_temp):
            os.makedirs(self.build_temp)
        subprocess.check_call(['cmake', ext.sourcedir] + cmake_args, cwd=self.build_temp, env=env)
        subprocess.check_call(['cmake', '--build', '.'] + build_args, cwd=self.build_temp)


def main():
    """Main build function"""
    template_dir = Path(__file__).parent / 'src' / 'pyserv ' / 'core' / 'templating'

    # Create CMakeLists.txt for template engine
    cmake_content = f'''cmake_minimum_required(VERSION 3.15)
project(pyserv _template_engine VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find Python
find_package(Python3 REQUIRED COMPONENTS Interpreter Development)

# Include directories
include_directories(${{Python3_INCLUDE_DIRS}})
include_directories("{template_dir}")

# Source files
set(SOURCES
    template_core.cpp
)

# Create shared library
add_library(pyserv _template_core SHARED ${{SOURCES}})

# Set library properties
set_target_properties(pyserv _template_core PROPERTIES
    PREFIX ""
    SUFFIX ".so"
)

if(WIN32)
    set_target_properties(pyserv _template_core PROPERTIES
        SUFFIX ".dll"
    )
endif()

# Link libraries
target_link_libraries(pyserv _template_core ${{Python3_LIBRARIES}})

# Compiler flags
if(MSVC)
    target_compile_options(pyserv _template_core PRIVATE /W4 /O2)
else()
    target_compile_options(pyserv _template_core PRIVATE -Wall -Wextra -O3 -fPIC)
endif()

# Install
install(TARGETS pyserv _template_core
    LIBRARY DESTINATION ${{CMAKE_INSTALL_LIBDIR}}
    ARCHIVE DESTINATION ${{CMAKE_INSTALL_LIBDIR}}
)
'''

    cmake_file = template_dir / 'CMakeLists.txt'
    with open(cmake_file, 'w') as f:
        f.write(cmake_content)

    print(f"Created CMakeLists.txt at {cmake_file}")

    # Setup configuration
    setup(
        name='pyserv -template-engine',
        version='1.0.0',
        description='Ultra-fast C++ template engine for Pyserv ',
        author='Pyserv  Team',
        ext_modules=[CMakeExtension('pyserv _template_core', sourcedir=str(template_dir))],
        cmdclass=dict(build_ext=CMakeBuild),
        zip_safe=False,
    )


if __name__ == '__main__':
    main()





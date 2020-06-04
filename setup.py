#! /usr/bin/env python3

from setuptools import setup
from cmakecommands import generate_cmdclass
from cmakebuilder import CMakeBuilder

# CMakeBuilder builds the ENTIRE python package and place it at dist_dir
# - this includes copying all the py files in the project
cmake = CMakeBuilder(
    package_name="mypkg",  # name of the distribution package (also the root package)
    src_dir="src",  # where all the source files are located (both PY and EXT)
    test_dir="tests",  # if this dir is missing...
    test_submodules=["lib/catch2"],  # these submodules won't be loaded in pip
    # ext_module_dirs=["example_module"], # explicitly define ext_modules OR...
    ext_module_hint=r"pybind11_add_module",  # define regex pattern to search in each CMakeLists.txt
    # has_package_data = False, # set False to allow sdist to skip running cmake (uncomment only if no package_data or manually setting it)
    
    ### DEVLEOPMENT OPTIONS: below options should be commented out for deployment ###
    # skip_configure=True, # skip CMake configuration stage and uses existing config
    # config="Debug",    # specify build type (configuration), default="Release"
    # generator="Ninja", # use build_ext generator option
    # toolset=,    # toolset spec for selected generator
    # platform=, # target platform
)

setup(
    name=cmake.package_name,
    version="0.5",
    author="Takeshi (Kesh) Ikuma",
    author_email="tikuma@gmail.com",
    description="Boilerplate for CMake-based project",
    long_description="Auto-configuration of a package containing pybind11-based binary module",
    url="https://github.com/hokiedsp/python_cmake_boilerplate",
    package_dir=cmake.get_package_dir(),
    packages=cmake.find_packages(),
    # package_data= # filled automatically with non-.py files installed by CMake (PY component)
    ext_modules=cmake.find_ext_modules(),
    cmdclass=generate_cmdclass(cmake),
    data_files=cmake.get_setup_data_files(),
    zip_safe=False,
)

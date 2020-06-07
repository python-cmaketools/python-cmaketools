import warnings

from .cmakebuilder import CMakeBuilder
from .cmakecommands import generate_cmdclass
from setuptools import setup as _setup
from . import cmakeutil
from . import gitutil


def setup(**kwargs):
    """Run setuptools.setup() after setting up its commands for CMake build

    It accepts most of setuptools.setup() arguments with additional arguments
    to configure CMake build. Also, it may overwrite user-provided setuptools
    arguments in order to integrate CMake.

    CMake Keyward Arguments
    -----------------------
    cmake_path : str
        path to cmake command (default auto-detected)
    src_dir : str
        Source directory (default "src")
    ext_module_dirs : str[]
        List of source directories defining external modules
    ext_module_hint : str 
        Regex pattern to auto-detect external module directories
    test_dir : str
        Unit test directory (default "tests")
    test_submodules : str[]
        List of git submodules only used for testing
    has_package_data : bool
        Set False if project has no package_data (default True)
    skip_configure : bool
        Set True to configure cmake externally (default False)
    config : str
        Default CMake build type (default "Release")
    generator : str
        Default CMake --G argument
    platform : str
        Default CMake --platform argument
    toolset : str
        Default CMake --toolset argument
    parallel : int > 0
        Default CMake --parallel argument
    configure_opts : str[]
        List of other default option arguments for CMake configure 
    build_opts : str[]
        List of other default option arguments for CMake build
    install_opts : str[]
        List of other default option arguments for CMake install

    Overriden setuptools arguments
    ------------------------------
    cmdclass (partial override, affecting egg_info, build_py, 
              build_ext, sdist, and install_data commands)
    data_files
    ext_modules
    package_dir
    package_data
    packages

    """

    # supported keyword arguments to CMakeBuilder constructor
    cmake_keys = (
        "src_dir",
        "test_dir",
        "test_submodules",
        "ext_module_dirs",
        "ext_module_hint",
        "has_package_data",
        "skip_configure",
        "config",
        "generator",
        "toolset",
        "platform",
        "configure_opts",
        "build_opts",
        "install_opts",
    )

    # split kwargs into CMakeBuilder arguments and setup arguments
    given_keys = kwargs.keys()
    cmake_args = {key: kwargs[key] for key in given_keys & cmake_keys}
    setup_args = {key: kwargs[key] for key in given_keys - cmake_keys}

    # instantiate CMakeBuilder using its option arguments
    cmake = CMakeBuilder(**cmake_args)

    # create
    setup_args["packages"] = cmake.find_packages()
    setup_args["ext_modules"] = cmake.find_ext_modules()
    setup_args["data_files"] = cmake.get_setup_data_files()
    setup_args["cmdclass"] = {
        **(setup_args["cmdclass"] if "cmdclass" in setup_args else {}),
        **generate_cmdclass(cmake),
    }
    _setup(**setup_args)

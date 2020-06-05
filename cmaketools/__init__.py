import warnings

from .cmakebuilder import CMakeBuilder
from .cmakecommands import generate_cmdclass
from setuptools import setup as _setup
from . import cmakeutil
from . import gitutil


def setup(**kwargs):

    # supported keyword arguments to CMakeBuilder constructor
    cmake_keys = (
        "package_name",
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
    )

    # split kwargs into CMakeBuilder arguments and setup arguments
    given_keys = kwargs.keys()
    cmake_args = {key: kwargs[key] for key in given_keys & cmake_keys}
    setup_args = {key: kwargs[key] for key in given_keys - cmake_keys}

    # instantiate CMakeBuilder using its option arguments
    cmake = CMakeBuilder(**cmake_args)

    # create
    setup_args["package_dir"] = cmake.get_package_dir()
    setup_args["packages"] = cmake.find_packages()
    setup_args["ext_modules"] = cmake.find_ext_modules()
    setup_args["data_files"] = cmake.get_setup_data_files()
    setup_args["cmdclass"] = {
        **(setup_args["cmdclass"] if "cmdclass" in setup_args else {}),
        **generate_cmdclass(cmake),
    }
    _setup(**setup_args)

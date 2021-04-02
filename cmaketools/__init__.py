from distutils.errors import DistutilsSetupError
from setuptools import (
    Command,
    Extension,
    Require,
    find_packages,
    find_namespace_packages,
)
from .dist import Distribution

from setuptools import setup as _setup
from . import cmakeutil as _cmakeutil

# export identical variables as setuptools
__all__ = [
    "setup",
    "Distribution",
    "Command",
    "Extension",
    "Require",
    "find_packages",
    "find_namespace_packages",
]


def setup(**kwargs):

    # Some of the conventional distutils options are automatically filled by cmaketools
    # https://docs.python.org/3/distutils/setupscript.html
    #
    # `package_dir` - auto-filled as {'',`build_ext.src_dir`}
    # `packages` - auto-filled by cmakeutil.find_packages()
    # `py_modules` - ignored?
    # `ext_modules` - auto-filled by cmakeutil.find_ext_modules() with options:
    #                 `build_ext.ext_module_dirs` or `build_ext.ext_module_hint`
    # `data_files` - auto-appends .submodule and .submodule_status

    # must be in a CMake project directory
    if not _cmakeutil.is_cmake_build():
        raise DistutilsSetupError(
            "This project is not a CMake project. Use setuptools to package. (Missing CMakeLists.txt)"
        )

    # run the setuptools.setup
    # with custom distribution class & cmake-infused commands (append custom commands if specified)
    _setup(
        **{"distclass": Distribution, **kwargs,}
    )


# same docstring as setuptools'
setup.__doc__ = _setup.__doc__

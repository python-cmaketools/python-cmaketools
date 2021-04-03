from .build import build
from .build_py import build_py
from .build_ext import build_ext
from .sdist import sdist
from .develop import develop
from .manage_cmake import manage_cmake


CMake_Commands = dict(
    sdist=sdist,
    build=build,
    build_py=build_py,
    build_ext=build_ext,
    develop=develop,
    manage_cmake=manage_cmake,
)

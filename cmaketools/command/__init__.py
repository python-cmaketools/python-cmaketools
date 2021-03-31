from .build_py import build_py
from .build_ext import build_ext
from .sdist import sdist
from .develop import develop


CMake_Commands = dict(
    sdist=sdist, build_py=build_py, build_ext=build_ext, develop=develop
)

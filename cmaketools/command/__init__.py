from .build_py import build_py as build_py
from .build_ext import build_ext as build_ext
from .sdist import sdist as sdist


CMake_Commands = dict(sdist=sdist, build_py=build_py, build_ext=build_ext)

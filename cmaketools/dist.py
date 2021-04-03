from setuptools import Distribution as _Distribution, Extension
import os, logging, re
from distutils.errors import DistutilsOptionError

from .command import CMake_Commands
from . import cmakeutil
from . import cmakeoptions

# list of main options relevant to cmaketools
cmake_opts = (
    "package_dir",
    "ext_modules",
    "ext_package",
    "src_dir",
    "ext_module_targets",
    "ext_module_dirs",
    "ext_module_hint",
)


def dir_to_pkg(pkg_dir, root_pkg=None, root_pkg_dir=None):
    """Convert relative directory to package name

    Args:
        pkg_dir (str): [description]
        root_pkg (str, optional): [description]. Defaults to "".

    Returns:
        str: [description]
    """

    if root_pkg_dir:
        pkg_dir = pkg_dir[len(root_pkg_dir) + 1]
    pkg = "" if pkg_dir == "." else re.sub(r"/", ".", pkg_dir)
    return f"{root_pkg}.{pkg}" if root_pkg else pkg


class Distribution(_Distribution):
    """
    Add custom option attributes to setuptools Distribution class.
    """

    def __init__(self, attrs):
        self.cmake = None  # CMakeBuilder instance
        self.cmakelists = None  # dict of all CMakeLists.txt file contents
        self.src_dir = None
        self.ext_module_dirs = None
        self.ext_module_hint = None

        # setup_requires
        _Distribution.__init__(self, attrs)

        # register cmaketools commands: let user defined commands to override them if so desired
        self.cmdclass = {**CMake_Commands, **self.cmdclass}

    def finalize_options(self):

        # build CMakeLists.txt tree
        self.cmakelists = cmakeutil.parse_cmakelists()

        return super().finalize_options()

    def run_commands(self):
        """Before running setuptools.run_commands', process cmaketools
        main options to finalize `package_dir` and `ext_modules` dist
        attributes.
        """

        # convert cmaketools convenience options to setuptools options
        if not self.package_dir:
            self._use_src_dir()
        elif self.src_dir:
            raise DistutilsOptionError(
                "Both `package_dir` and `src_dir` options are set. "
                + "Only one can be set for a cmaketools distribution package."
            )

        # convert cmaketools ext_module_dirs and ext_module_hint to ext_modules
        self._add_ext_modules_from_dirs(self.ext_module_dirs)
        self._add_ext_modules_with_hint()

        # All set. Run the commands (under cmake running context to stop it when done/fail)
        (manage_cmake := self.get_command_obj("manage_cmake")).ensure_finalized()
        with manage_cmake.cmake_running():
            return _Distribution.run_commands(self)

    def cmakelists_filter(self, command, args=None):

        return cmakeutil.cmakelists_filter(self.cmakelists,command, args)


    def _use_src_dir(self):
        if not self.src_dir and os.path.isdir("src"):
            # if neither set but 'src' folder exists, use 'src' by default
            self.src_dir = "src"
        if self.src_dir:
            self.package_dir = {"": self.src_dir}

    def _get_extension(self, name):
        """check if the extension name is already taken"""
        return (
            next((ext for ext in self.ext_modules if ext.name == name), None)
            if self.ext_modules
            else None
        )

    def _add_ext_modules_from_dirs(self, dirs, only_warn=None):
        """append ext_modules specified via ext_module_dirs"""
        if not dirs:
            return

        package_dirs = self.package_dir if self.package_dir else {"": ""}

        for dir in dirs:
            pkg = next(
                (pkg for pkg in package_dirs.items() if dir.startswith(pkg[1])),
                None,
            )
            if pkg is None:
                msg = f"Extension module dir '{dir}' does not belong to a root package directory."
                if only_warn:
                    logging.warning(msg)
                else:
                    raise DistutilsOptionError(msg)

            name = dir_to_pkg(dir, *pkg)
            if self._get_extension(name) is not None:
                msg = f"Extension module name '{name}' already taken."
                if only_warn:
                    logging.warning(msg)
                else:
                    raise DistutilsOptionError(msg)

            if self.ext_modules:
                self.ext_modules.append(Extension(name, []))
            else:
                self.ext_modules = [Extension(name, [])]
                return

    def _add_ext_modules_with_hint(self):
        """[legacy] append ext_modules specified via ext_module_hint"""

        print("finalize_options", self.ext_module_hint)

        if hint := self.ext_module_hint:
            print(hint)
            # now add modules to ext_modules by each base packages
            new_dirs = [
                dir
                for dir, _ in cmakeutil.search_cmakelists(self.cmakelists.keys(), hint)
            ]
            self._add_ext_modules_from_dirs(new_dirs, only_warn=True)

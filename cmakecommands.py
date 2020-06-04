import os
import re

from setuptools.command.egg_info import (
    egg_info as _egg_info_orig,
    manifest_maker as _manifest_maker_orig,
)
from setuptools.command.build_ext import build_ext as _build_ext_orig
from setuptools.command.build_py import build_py as _build_py_orig
from setuptools.command.sdist import sdist as _sdist_orig
from distutils.command.install_data import install_data as _install_data_orig
from wheel import bdist_wheel as _bdist_wheel_orig

from cmakebuilder import CMakeBuilder
import cmakeutil


class manifest_maker(_manifest_maker_orig):
    def _add_defaults_python(self):
        # Python files in self.distribution.package_dir are copies from the
        # CMake source directory. Hence, no files need to be copied by this
        # function. All the original python files in theCMake source
        # directory are added to the manifest via  _add_defaults_ext()
        # build_py is used to get:
        #  - python modules
        #  - files defined in package_data
        # build_py = self.get_finalized_command("build_py")
        return


class _egg_info(_egg_info_orig):
    def __init__(self, cmake, dist):
        print("egg_info (cmake)")
        _egg_info_orig.__init__(self, dist)
        self.cmake = cmake

    def finalize_options(self):
        _egg_info_orig.finalize_options(self)

        # use the same output directries in CMake
        build_dir = self.get_finalized_command("build").build_base
        dist_dir = self.get_finalized_command("sdist").dist_dir
        self.cmake.dist_dir = dist_dir
        self.cmake.build_dir = build_dir

    def find_sources(self):
        """Generate SOURCES.txt manifest file using custom manifest_maker"""
        manifest_filename = os.path.join(self.egg_info, "SOURCES.txt")
        mm = manifest_maker(self.distribution)
        mm.manifest = manifest_filename
        mm.run()
        self.filelist = mm.filelist


class _build_py(_build_py_orig):
    def __init__(self, cmake, dist):
        _build_py_orig.__init__(self, dist)
        self.cmake = cmake

    def finalize_options(self):
        # build_py command depends on build_ext
        build_ext = self.distribution.get_command_obj("build_ext")
        build_ext.ensure_finalized()

        # run the regular finalize_options
        _build_py_orig.finalize_options(self)

    def _run_cmake(self):
        """run cmake to copy .py files and files to be included in package_data"""
        self.cmake.run(
            component="PY", pkg_version=self.distribution.get_version(),
        )

    def run(self):

        print("\nrunning build_py (cmake)\n")
        self._run_cmake()

        _build_py_orig.run(self)

    def _get_data_files(self):
        print("build_py::_get_data_files (cmake)\n")

        # gather package_data from cmake builder
        # - if data exists, egg_info command must run again to update source file list
        if not self.package_data and self.cmake.has_package_data:

            # must run cmake to make the data available in dist_dir
            # copy .py files and files to be included in package_data
            self._run_cmake()

            # get the package_data from cmake
            package_data = self.cmake.get_package_data()
            if package_data:
                self.distribution.package_data = package_data
                self.package_data = package_data

        return _build_py_orig._get_data_files(self)


class _build_ext(_build_ext_orig):

    description = "build C/C++ extensions with CMake (compile/link to build directory)"
    user_options = [
        (
            "cmake-path=",
            None,
            "Name/path of the CMake executable to use, overriding default auto-detection.",
        ),
        ("build-lib=", "b", "directory for compiled extension modules"),
        (
            "inplace",
            "i",
            "ignore build-lib and put compiled extensions into the source "
            + "directory alongside your pure Python modules",
        ),
        ("force", "f", "forcibly build everything (delete existing CMakeCache.txt)"),
        # -C <initial-cache>
        ("cache=", "C", "Pre-load a CMake script to populate the cache."),
        # -D=<var>:<type>=<value>,<var>=<value>,...
        (
            "define=",
            "D",
            "Create or update a CMake CACHE entry" + _build_ext_orig.sep_by,
        ),
        # -U <globbing_expr>
        ("undef=", "U", "Remove matching entries from CMake CACHE."),
        # -G <generator-name>
        ("generator=", "G", "Specify a build system generator."),
        # -T <toolset-spec>
        ("toolset=", "T", "Toolset specification for the generator, if supported."),
        # -A <platform-name>
        ("platform=", "A", "Specify platform name if supported by generator."),
        # -Wno-dev
        ("Wno-dev", None, "Suppress developer warnings."),
        # -Wdev
        ("Wdev", None, "Enable developer warnings."),
        # -Werror=[dev|deprecated]
        ("Werror=", None, "Make specified warnings into errors: dev or deprecated."),
        # -Wno-error=
        ("Wno-error=", None, "Make specified warnings not errors."),
        # -Wdeprecated
        ("Wdeprecated", None, "Enable deprecated functionality warnings."),
        # -Wno-deprecated
        ("Wno-deprecated", None, "Suppress deprecated functionality warnings."),
        # --log-level=<ERROR|WARNING|NOTICE|STATUS|VERBOSE|DEBUG|TRACE>
        (
            "log-level=",
            None,
            "Set the log level to one of: ERROR, WARNING, NOTICE, STATUS, VERBOSE, DEBUG, TRACE",
        ),
        # --log-context
        (
            "log-context",
            None,
            "Enable the message() command outputting context attached to each message.",
        ),
        # --debug-trycompile
        (
            "debug-trycompile=",
            None,
            "Do not delete the try_compile() build tree. Only useful on one try_compile() at a time.",
        ),
        # --debug-output
        ("debug-output", None, "Put cmake in a debug mode."),
        # --debug-find
        ("debug-find", None, "Put cmake find commands in a debug mode."),
        # --trace
        ("trace", None, "Put cmake in trace mode."),
        # --trace-expand
        ("trace-expand", None, "Put cmake in trace mode with variables expanded."),
        # --trace-format=<human|json>
        (
            "trace-format=",
            None,
            "Put cmake in trace mode and sets the trace output format.",
        ),
        # --trace-source=<file>
        (
            "trace-source=",
            None,
            "Put cmake in trace mode, but output only lines of a specified file.",
        ),
        # --trace-redirect=<file>
        (
            "trace-redirect=",
            None,
            "Put cmake in trace mode and redirect trace output to a file instead of stderr.",
        ),
        # --warn-uninitialized
        ("warn-uninitialized", None, "Specify a build system generator."),
        # --warn-unused-vars
        ("warn-unused-vars", None, "Warn about unused variables."),
        # --no-warn-unused-cli
        ("no-warn-unused-cli", None, "Don’t warn about command line options."),
        # --check-system-vars
        (
            "check-system-vars",
            None,
            "Find problems with variable usage in system files.",
        ),
        # build <dir>
        # --parallel [<jobs>], -j [<jobs>]
        (
            "parallel=",
            "j",
            "The maximum number of concurrent processes to use when building.",
        ),
        # --config <cfg>
        ("config=", None, "For multi-configuration tools, choose this configuration."),
        # --clean-first
        ("clean-first", None, "Build target clean first, then build."),
        # --verbose, -v
        (
            "verbose",
            "v",
            "Enable verbose output - if supported - including the build commands to be executed.",
        ),
        # install <dir>
        # --strip
        ("strip", None, "Strip before installing."),
    ]

    boolean_options = [
        "inplace",
        "debug",
        "force",
        "Wno-dev",
        "Wdev",
        "Wdeprecated",
        "Wno-deprecated",
        "log-context",
        "debug-trycompile=",
        "debug-output",
        "debug-find",
        "trace",
        "trace-expand",
        "warn-uninitialized",
        "warn-unused-vars",
        "no-warn-unused-cli",
        "check-system-vars",
        "clean-first",
        "strip",
        "verbose",
    ]

    help_options = [
        (
            "help-generator",
            None,
            "list available compilers",
            CMakeBuilder.get_generators,
        )
    ]

    negative_opt = {}

    def __init__(self, cmake, dist):
        """Instantiate with a link to a CMakeBuilder instance

        Parameter:
        ---------
        cmake CMakeBuilder: instance to run CMake commands
        """

        self.cmake = cmake
        _build_ext_orig.__init__(self, dist)

    def initialize_options(self):
        self.build_lib = None
        self.inplace = None
        self.define = None
        self.cmake_path = None
        self.build_lib = None
        self.cache = None
        self.undef = None
        self.generator = None
        self.toolset = None
        self.platform = None
        self.Wno_dev = None
        self.Wdev = None
        self.Werror = None
        self.Wno_error = None
        self.Wdeprecated = None
        self.Wno_deprecated = None
        self.log_level = None
        self.log_context = None
        self.debug_trycompile = None
        self.debug_output = None
        self.debug_find = None
        self.trace = None
        self.trace_expand = None
        self.trace_format = None
        self.trace_source = None
        self.trace_redirect = None
        self.warn_uninitialized = None
        self.warn_unused_vars = None
        self.no_warn_unused_cli = None
        self.check_system_vars = None
        self.parallel = None
        self.config = None
        self.clean_first = None
        self.strip = None

        self.cmake.revert()

    def finalize_options(self):
        # self.set_undefined_options('build',
        #                            ('build_lib', 'build_lib'),
        #                            ('force', 'force'),
        #                            ('parallel', 'parallel'),
        #                            )

        self.set_undefined_options(
            "build", ("build_lib", "build_lib"),
        )

        self.verbose = None

        if self.cmake_path:
            # validate the path before assign
            cmakeutil.validate(self.cmake_path)
            self.cmake.path = self.cmake_path

        cmake_settings = {}

        if self.parallel:
            try:
                val = int(self.parallel)
                assert self.cmake.parallel > 0
            except:
                raise ValueError(
                    f'"parallel" option must be a positive integer (given "{self.parallel}")'
                )
            cmake_settings["parallel"] = val

        cmake_settings["generator"] = dict(
            generator=self.generator, toolset=self.toolset, platform=self.platform
        )

        if self.config:
            config_values = (
                "Debug",
                "Release",
                "RelWithDebInfo",
                "MinSizeRel",
            )
            if self.config not in config_values:
                raise ValueError(
                    f'"{self.config}" must be one of {", ".join(config_values)}'
                )
            cmake_settings["config"] = self.config

        configure_args = []
        if self.define:
            for d in re.finditer(
                r"([A-Za-z0-9_./\-+]+)(?:\:([A-Z]+))?=([^" + os.pathsep + r"]+)",
                self.define,
            ):
                val = f'"{d[3]}"' if re.search(r"\s", d[3]) else d[3]
                configure_args.append(
                    f"-D{d[1]}:{d[2]}={val}" if d[2] else f"-D{d[1]}={val}"
                )

        # some CMake options are in short form
        for opt in (
            ("cache", "C",),
            ("undef", "U",),
        ):
            val = getattr(self, opt[0])
            if val:
                configure_args.append(f"-{opt[1]}")
                configure_args.append(val)

        def set_args(args, opts):
            for attr in opts:
                val = getattr(self, attr)
                opt = re.sub("_", "-", attr)
                if val == 1:
                    args.append(f"--{opt}")
                elif val:
                    args.append(f"--{opt}={val}")
            return args

        set_args(
            configure_args,
            (
                "toolset",
                "platform",
                "Wno_dev",
                "Wdev",
                "Werror",
                "Wno_error",
                "Wdeprecated",
                "Wno_deprecated",
                "log_level",
                "log_context",
                "debug_trycompile",
                "debug_output",
                "debug_find",
                "trace",
                "trace_expand",
                "trace_format",
                "trace_source",
                "trace_redirect",
                "warn_uninitialized",
                "warn_unused_vars",
                "no_warn_unused_cli",
            ),
        )
        cmake_settings["configure_args"] = configure_args
        cmake_settings["build_args"] = set_args([], ("clean_first", "verbose",))
        cmake_settings["install_args"] = set_args([], ("strip", "verbose",))
        self.cmake.configure(**cmake_settings)

    def get_source_files(self):
        """List all the source files
        
        - All files in src folder
        - All CMakeLists.txt from cmake_srcdir down to the root"""
        return self.cmake.get_source_files()

    def run(self):
        print(
            f'running build_ext (cmake) -> {"<inplace>" if self.inplace else self.build_lib}\n'
        )
        self.cmake.run(
            component=None if self.inplace else "EXT",
            prefix=None if self.inplace else self.build_lib,
            pkg_version=self.distribution.get_version(),
        )


class _sdist(_sdist_orig):
    def __init__(self, cmake, dist):
        _sdist_orig.__init__(self, dist)
        self.cmake = cmake

    def run(self):
        """Create the source distribution(s). The list of archive files created is
        stored so it can be retrieved later by 'get_archive_files()'.

        Before creating the distributions, pin git submodule commit so installing
        from sdist at any point in the future will use the same commit  
        """

        print("running sdist (cmake)\n")

        self.cmake.pin_gitmodules()  # save current submodule sha1
        _sdist_orig.run(self)


class _install_data(_install_data_orig):
    def __init__(self, cmake, dist):
        _sdist_orig.__init__(self, dist)
        # self.cmake = cmake

    def run(self):
        return


###############################################################################


def _create_constructor(superclass, cmake):
    def constructor(self, dist):
        superclass.__init__(self, cmake, dist)

    return constructor


def generate_cmdclass(cmake):
    """Generate setup()'s cmdclass keyword argument
    
    Parameter:
    ----------
    cmake :class:CMakeBuilder : the cmake project builder to link commands to
    """
    return {
        "egg_info": type(
            "egg_info",
            (_egg_info,),
            {"__init__": _create_constructor(_egg_info, cmake)},
        ),
        "build_py": type(
            "build_py",
            (_build_py,),
            {"__init__": _create_constructor(_build_py, cmake)},
        ),
        "build_ext": type(
            "build_ext",
            (_build_ext,),
            {"__init__": _create_constructor(_build_ext, cmake)},
        ),
        "sdist": type(
            "sdist", (_sdist,), {"__init__": _create_constructor(_sdist, cmake)},
        ),
        "install_data": type(
            "install_data",
            (_install_data,),
            {"__init__": _create_constructor(_install_data, cmake)},
        ),
    }

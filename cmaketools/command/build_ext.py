from distutils.errors import DistutilsExecError
from setuptools.command.build_ext import build_ext as _build_ext_orig
from setuptools.dist import DistutilsOptionError
from distutils.fancy_getopt import FancyGetopt
import re

from .. import cmakeutil


class build_ext(_build_ext_orig):

    description = "build C/C++ extensions with CMake (compile/link to build directory)"
    cmake_config_options = [
        # -C <initial-cache>
        ("cache=", "C", "Pre-load a CMake script to populate the cache."),
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
    ]
    cmake_build_options = [
        # --parallel [<have_started>], -j [<have_started>]
        (
            "parallel=",
            "j",
            "The maximum number of concurrent processes to use when building.",
        ),
        # --clean-first
        ("clean-first", None, "Build target clean first, then build."),
        # --verbose, -v
        (
            "verbose",
            "v",
            "Enable verbose output - if supported - including the build commands to be executed.",
        ),
    ]
    cmake_install_options = [
        # install <dir>
        # --strip
        ("strip", None, "Strip before installing."),
        # --verbose, -v
        (
            "verbose",
            "v",
            "Enable verbose output - if supported - including the build commands to be executed.",
        ),
    ]

    user_options = (
        [
            # -G <generator-name>
            ("generator=", "G", "Specify a build system generator."),
            # -T <toolset-spec>
            ("toolset=", "T", "Toolset specification for the generator, if supported."),
            # -A <platform-name>
            ("platform=", "A", "Specify platform name if supported by generator."),
            # build <dir>
            ("build-dir=", "b", "directory for compiled extension modules"),
            (
                "inplace",
                "i",
                "ignore build-lib and put compiled extensions into the source "
                + "directory alongside your pure Python modules",
            ),
            (
                "skip-configure",
                None,
                "Set to configure cmake externally (default False)",
            ),
            (
                "force",
                "f",
                "forcibly build everything (delete existing CMakeCache.txt)",
            ),
            # --config <cfg>
            (
                "config=",
                None,
                "CMAKE_BUILD_TYPE: Debug, Release, RelWithDebInfo, MinSizeRel.",
            ),
            # -D=<var>:<type>:<value>,<var>:<value>,...
            (
                "defines=",
                "D",
                "list of CMake CACHE entries: name=value or name:type=value"
                + _build_ext_orig.sep_by,
            ),
            # -U <globbing_expr>
            (
                "undefs=",
                "U",
                "list of entries to remove from CMake CACHE." + _build_ext_orig.sep_by,
            ),
        ]
        + cmake_config_options
        + cmake_build_options
        + cmake_install_options
    )

    boolean_options = [
        "inplace",
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
        "skip-configure",
    ]

    help_options = []
    #     (
    #         "help-generator",
    #         None,
    #         "list available compilers",
    #         CMakeBuilder.get_generators,
    #     )
    # ]

    negative_opt = {}

    def __init__(self, dist):
        """Instantiate with a link to a CMakeBuilder instance

        Parameter:
        ---------
        cmake CMakeBuilder: instance to run CMake commands
        """

        super().__init__(dist)

        self.options_sorted = None
        self.config_options = None
        self.build_options = None
        self.install_options = None
        self.have_started = {}
        self.have_completed = {}

    def initialize_options(self):
        self.options_sorted = False
        self.have_started = {}
        self.have_completed = {}

        self.build_dir = None
        self.dist_dir = None
        self.inplace = None
        self.debug = None

        self.skip_configure = None

        self.generator = None
        self.toolset = None
        self.platform = None

        self.defines = None
        self.undefs = None

        self.config = None
        self.verbose = None

        self.cache = None
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
        self.clean_first = None
        self.strip = None

        self.package = None
        self.extensions = None
        self.ext_map = {}
        self.build_lib = None

    def _sort_options(self):
        # only perform once
        if self.options_sorted:
            return

        self.set_undefined_options(
            "build",
            ("plat_name", "platform"),
            ("build_base", "build_dir"),
            ("debug", "debug"),
            ("force", "force"),
            ("parallel", "parallel"),
        )

        self.set_undefined_options(
            "build_py", ("build_lib", "build_lib"),
        )

        self.dist_dir = "." if self.inplace else self.build_lib

        if self.verbose:
            self.verbose = True

        def picker(opts):
            parser = FancyGetopt(opts)
            optvals = {}
            for opt in opts:
                arg = opt[0]
                name = parser.get_attr_name(re.sub(r"=$", "", arg))
                val = getattr(self, name)
                if val:
                    optvals["--" + arg] = val
            return optvals

        self.config_options = picker(self.cmake_config_options)
        self.build_options = picker(self.cmake_build_options)
        self.install_options = picker(self.cmake_install_options)
        self.options_sorted = True

    def configure(self):

        # sort options (if not done so already)
        self._sort_options()

        defines = self.defines
        if defines:
            if isinstance(defines, str):
                defines = defines.split(_build_ext_orig.sep_by)

            def parse_d(dstr):
                if isinstance(dstr, str):
                    m = re.match(r"([^:=\n]+)(?:\:([^:\n]+))?[:=]([^\n]+)$", dstr)
                    if not m:
                        raise DistutilsOptionError(
                            f"Invalid `defines` (-D in cmake) option: {dstr}"
                        )
                    return m[1:] if m[2] else (m[1], m[3])
                return dstr

            defines = tuple((parse_d(d) for d in defines))

        undefs = self.undefs
        if undefs and isinstance(undefs, str):
            undefs = undefs.split(_build_ext_orig.sep_by)

        # set build config preference: develop.debug -> self.config -> "Release"

        develop = self.get_finalized_command("develop", False)
        config = "Debug" if develop and develop.debug else self.config or "Release"

        self.have_started["config"] = self.distribution.cmake.configure(
            self.build_dir,
            config=config,
            defines=defines,
            undefines=undefs,
            options=self.config_options,
        )

    def ensure_cmake_configured(self):
        if "config" not in self.have_started:
            self.configure()

    def ensure_cmake_started(self):

        # sort options (if not done so already)
        self._sort_options()

        # queue configure CMake command (if not already done so)
        self.ensure_cmake_configured()

        # queue
        cmake = self.distribution.cmake
        if "build" not in self.have_started:
            self.have_started["build"] = cmake.build(options=self.build_options)
        if "install" not in self.have_started:
            self.have_started["install"] = cmake.install(
                self.dist_dir, options=self.install_options
            )

    def finalize_options(self):

        # super().finalize_options()
        if self.package is None:
            self.package = self.distribution.ext_package
        self.extensions = self.distribution.ext_modules or []
        self.check_extensions_list(self.extensions)
        for ext in self.extensions:
            ext._full_name = self.get_ext_fullname(ext.name)
        for ext in self.extensions:
            fullname = ext._full_name
            self.ext_map[fullname] = ext

            self.ext_map[fullname.split(".")[-1]] = ext

            ext._links_to_dynamic = False
            ext._needs_stub = False

        # sort options (if not done so already)
        self._sort_options()

    def run(self):

        self.ensure_cmake_started()
        failed_job = self.distribution.cmake.wait(self.have_started["install"])
        if failed_job is not None:
            job = next(
                (key for key, val in self.have_started.items() if val == failed_job),
                "internal",
            )
            raise DistutilsExecError(f"CMake {job} failed.")

    def get_source_files(self):
        """Override it to retun empty list as sdist takes care of this via MANIFEST processing"""
        return []

    def develop_pre_run(self, uninstall):
        if uninstall:
            cmakeutil.uninstall()

    def develop_post_run(self, uninstall):
        self.ensure_finalized()
        if not uninstall:
            cmakeutil.log_install(self.build_dir)

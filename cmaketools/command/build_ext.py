from distutils.errors import DistutilsExecError
from setuptools.command.build_ext import build_ext as _build_ext_orig

from .. import cmakeutil
from .. import cmakeoptions


class build_ext(_build_ext_orig):

    description = "build C/C++ extensions with CMake (compile/link to build directory)"
    user_options = [
        *cmakeoptions.to_distutils("config"),
        *cmakeoptions.to_distutils("build"),
        *cmakeoptions.to_distutils("install"),
        # fmt:off
        ("debug", "g", "compile/link with debugging information"),
        ("inplace", "i", "ignore build-lib and put compiled extensions into the source "
                          + "directory alongside your pure Python modules"),
        ("force", "f", "forcibly build everything (delete existing CMakeCache.txt)")
        # fmt:on
    ]

    boolean_options = [
        *cmakeoptions.to_distutils_bools("config"),
        *cmakeoptions.to_distutils_bools("build"),
        *cmakeoptions.to_distutils_bools("install"),
        # fmt:off
        "debug", "inplace", "force",
        # fmt:on
    ]

    def initialize_options(self):
        self.extensions = None
        self.ext_map = {}

        self.build_base = None
        self.build_lib = None
        # self.plat_name = None
        # self.build_job_temp = None
        self.inplace = 0
        self.package = None

        self.debug = None
        self.force = None

        # started job ids
        self.config_job = None
        self.build_job = None
        self.install_job = None

        for o in cmakeoptions.config_options.keys():
            setattr(self, o, None)

        for o in cmakeoptions.build_options.keys():
            setattr(self, o, None)

        for o in cmakeoptions.install_options.keys():
            setattr(self, o, None)

    def finalize_options(self):
        self.set_undefined_options(
            "build",
            ("build_base", "build_base"),
            ("build_lib", "build_lib"),
            ("debug", "debug"),
            ("force", "force"),
        )

        # if build command has any assigned options, overwrite existing options
        build = self.get_finalized_command("build")
        for opts in cmakeoptions.option_dict.values():
            for name in opts.keys():
                val = getattr(build, name, None)
                if val is not None:
                    setattr(self, name, val)

        # as a subcommand of develop command
        if self.inplace:
            # make sure build_py does not need to build/install modules
            # Once finalized, it whether cmake build is necessary. If it is
            # then build_Py must be deployed as subsubcommand
            self.get_finalized_command("build_py")

            develop = self.get_finalized_command("develop")
            for opts in cmakeoptions.option_dict.values():
                for name in opts.keys():
                    val = getattr(develop, name, None)
                    if val is not None:
                        setattr(self, name, val)

        if self.config is None:
            self.config = "Debug" if self.debug is True else "Release"

        if self.package is None:
            self.package = self.distribution.ext_package

        self.extensions = self.distribution.ext_modules

        self.check_extensions_list(self.extensions)
        for ext in self.extensions:
            ext._full_name = self.get_ext_fullname(ext.name)
        for ext in self.extensions:
            fullname = ext._full_name
            self.ext_map[fullname] = self.ext_map[fullname.split(".")[-1]] = ext
            ext._links_to_dynamic = False
            ext._needs_stub = False

    def configure(self):
        """Queue configure command

        Raises:
            DistutilsOptionError: [description]

        Returns:
            [type]: [description]
        """

        # only run once
        if self.config_job is None:

            # set build config preference: develop.debug -> self.config_job -> "Release"
            try:
                develop = self.get_finalized_command("develop", False)
                self.config = (
                    "Debug"
                    if develop and develop.debug
                    else self.config_job or "Release"
                )
            except:
                pass

            manage_cmake = self.get_finalized_command("manage_cmake")
            manage_cmake.restart(self)
            self.config_job = manage_cmake.enqueue_config(self)

        return self.config_job

    ensure_cmake_configured = configure

    def ensure_cmake_built(self):

        # queue configure CMake command (if not already done so)
        self.ensure_cmake_configured()

        # queue
        manage_cmake = self.get_finalized_command("manage_cmake")
        if self.build_job is None:
            self.build_job = manage_cmake.enqueue_build(self)

        return self.build_job

    def ensure_cmake_started(self):

        # queue configure CMake command (if not already done so)
        self.ensure_cmake_built()

        # queue
        manage_cmake = self.get_finalized_command("manage_cmake")
        if self.install_job is None:
            self.install_job = manage_cmake.enqueue_install(
                self, "." if self.inplace else self.build_lib
            )

        return self.install_job

    def run(self):

        if (
            self.inplace
            and (build_py := self.get_finalized_command("build_py")).use_cmake
        ):
            build_py.ensure_cmake_started()

        self.ensure_cmake_started()

        manage_cmake = self.get_finalized_command("manage_cmake")
        failed_job = manage_cmake.waitfor(self.install_job)
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
            cmakeutil.log_install(self.build_base)

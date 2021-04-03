from setuptools.command.build_py import build_py as _build_py_orig
from distutils import log
from .. import cmakeutil
from os import path


class build_py(_build_py_orig):
    user_options = [
        ("inplace", "i", "ignore build-lib and put compiled extensions into the source "
                          + "directory alongside other pure Python modules"),
        ("use-cmake", None, "use CMake's PY install COMPONENT to perform the build",),
        (
            "use-setuptools",
            None,
            "do not use CMake's PY install COMPONENT to perform the build",
        ),
        (
            "cmake-nobuild",
            None,
            "do not need CMake to build its project, only install needed",
        ),
        (
            "cmake-build",
            None,
            "CMake needs to build its project, before install py files",
        ),
        (
            "cmake-component",
            None,
            f"CMake install component dedicated for installing py files",
        ),
    ] + _build_py_orig.user_options
    boolean_options = ["use-cmake",] + _build_py_orig.boolean_options
    negative_opt = {
        "use-setuptools": "use-cmake",
        "cmake-build": "cmake-nobuild",
        **_build_py_orig.negative_opt,
    }

    def __init__(self, dist):
        self.use_cmake = None
        self.cmake_job = None
        self.cmake_nobuild = None
        self.cmake_component = None
        self.cmake_modules = {}  # list of modules not present in source
        return super().__init__(dist)

    def initialize_options(self):
        self.inplace = 0
        self.use_cmake = None
        self.build_lib = None
        self.build_base = None
        return super().initialize_options()

    def check_module(self, module, module_file):
        found = super().check_module(module, module_file)
        if not found:
            if module in self.cmake_modules:
                # post cmake-run, module file should already be there
                print(f"post-cmake checking {self.build_lib + '/' + module_file}")
                found = path.isfile(path.join(self.build_lib, module_file))
            else:
                # pre cmake-run, add missing module file to cmake_modules
                self.cmake_modules[module] = module_file
                found = True
        return found

    def find_modules(self):
        """exclude cmake-installed modules from the module list"""
        modules = super().find_modules()
        return [
            m
            for m in modules
            if f"{'.'.join(m[:2]) if m[0] else m[1]}" not in self.cmake_modules
        ]

    def finalize_options(self):
        super().finalize_options()

        if self.use_cmake is None and self.cmake_component is None:
            self.set_undefined_options(
                "build", ("build_lib", "build_lib"), ("build_base", "build_base")
            )
            # automatically identify whether CMake must run to complete build_py

            # analyze the py_modules option
            self.find_modules()

            # if self.use_cmake is None or self.cmake_nobuild is None:
            if len(self.cmake_modules) and self.use_cmake is None:
                # TODO check if the module is being installed by cmake
                # installs = self.distribution.finditer_cmake_install()
                # for dir, args in installs:
                #     match, comp, exclude_from_all = cmakeutil.find_installed_py_modules(
                #         self.cmake_modules
                #     )

                # backward compatible mode
                self.use_cmake = True
                log.info("one or more pure Python modules are missing. build_py will run CMake to build missing modules.")

            # if nobuild flag is not set, look for PY install component to set the flag
            if self.use_cmake and self.cmake_nobuild is None:

                # if PY install component is found, install PY w/out build
                def install_PY_finditer():
                    for _, cmds in self.distribution.cmakelists_filter(
                        "install", ["FILES"]
                    ).items():
                        for _, args in cmds:
                            try:
                                i = args.index("COMPONENT")
                                assert args[i + 1] == "PY"
                            except:
                                yield False

                PY_found = next(install_PY_finditer(), True)
                if PY_found:
                    self.cmake_component = "PY"
                    log.info(
                        "install COMPONENT PY found: only installs CMake PY component."
                    )
                else:
                    log.info(
                        "install COMPONENT PY not found: build the full CMake project"
                    )
                self.cmake_nobuild = PY_found

    def ensure_cmake_started(self):
        # if already started, nothing to do
        if not self.cmake_job and self.use_cmake:
            build_ext = self.get_finalized_command("build_ext")
            manage_cmake = self.get_finalized_command("manage_cmake")

            # make sure configure has/will run
            config_job = build_ext.ensure_cmake_configured()
            if not self.cmake_nobuild:
                build_ext.ensure_cmake_built()

            # after cmake finished configuring
            manage_cmake.waitfor(config_job)
            self.cmake_job = manage_cmake.enqueue_install(
                self, self.build_lib, component=self.cmake_component
            )

        return self.cmake_job

    def run(self):

        if self.use_cmake:
            self.ensure_cmake_started()
            manage_cmake = self.get_finalized_command("manage_cmake")
            manage_cmake.waitfor(self.cmake_job)

        _build_py_orig.run(self)

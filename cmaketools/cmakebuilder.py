import logging

from . import cmakeutil, cmakecontrol as runner


class CMakeBuilder:
    """
    A class used to bridge CMake Runner and Setuptools build steps

    ...

    Attributes
    ----------
    cmake_path : str
        CMake binary path
    generator : str
        Default CMake --G argument
    platform : str
        Default CMake --platform argument
    toolset : str
        Default CMake --toolset argument
    parallel : int > 0
        CMake --parallel argument
    configure_opts : str[]
        List of other option arguments for CMake configure
    build_opts : str[]
        List of other option arguments for CMake build
    install_opts : str[]
        List of other option arguments for CMake install

    Methods
    -------
    clear()
        Clear build directory

    Internal Methods to Generate Arguments of setuptools.setup
    ----------------------------------------------------------
    get_package_dir()
        Returns package_dir argument for setuptools.setup()
    get_setup_data_files()
        Returns data_files argument for setuptools.setup()
    get_package_data(prefix=None):
        Returns package_data argument for setuptools.setup()
    find_packages()
        Returns packages argument for setuptools.setup()
    find_ext_modules()
        Returns ext_modules argument for setuptools.setup()

    Internal Methods Invoked by setuptools.setup commands
    -----------------------------------------------------
    get_source_files()
        Returns a list of all the files in src_dir
    pin_gitmodules()
        Save status of submodules to be included in the sdist
    save_cmake_config()
        Save current CMake configurations
    configure(build_dir, generator=None, config=None, parallel=None,
              configure_opts=[]):
        Configure CMake project
    run(prefix=None, component=None, pkg_version=None, build_opts=[], install_opts=[]):
        Run CMake build & install
    revert()
        Revert the builder configuration to the initial state
    """

    def __init__(self, cmake_path=None, generator=None, toolset=None, platform=None):
        """
        Parameters
        ----------
        cmake_path : str
            path to cmake command (default auto-detected)
        generator : str
            Default CMake --G argument
        platform : str
            Default CMake --platform argument
        toolset : str
            Default CMake --toolset argument
        """

        self.path = cmake_path

        # CMake configurations
        self.generator = generator or "Ninja"
        self.platform = platform
        self.toolset = toolset

        # Start the CMake Runner
        logging.info("starting CMake runner subprocess")
        runner.start(self.generator, self.platform, self.toolset)

        # Make package version available as C++ Preprocessor Define
        # env = cmakeutil.set_environ_cxxflags(self.build_dir, VERSION_INFO=pkg_version)

    def stop(self):
        """Stop Cmake Runner subprocess
        """
        logging.info("stopping CMake runner subprocess")
        runner.stop()

    def configure(
        self, build_dir, config, force=None, defines=None, undefines=None, options={}
    ):
        """configure CMake project"""

        config_values = (
            "Debug",
            "Release",
            "RelWithDebInfo",
            "MinSizeRel",
        )
        if config not in config_values:
            raise ValueError(f'"{config}" must be one of {", ".join(config_values)}')

        print("\n[cmake] configuring CMake project...\n")

        arg = f'-S . -B "{build_dir}" -DCMAKE_BUILD_TYPE={config}'
        cache = options.pop("cache", None)
        if cache:
            arg += f' -C "{cache}"'
        if defines:
            for d in defines:
                arg += (
                    f' -D{d[0]}:{d[1]}="{d[2]}"' if len(d) > 2 else f'-D{d[0]}="{d[1]}"'
                )
        if undefines:
            for u in undefines:
                arg += f' -U "{u}"'
        if self.generator:
            arg += f' -G "{self.generator}"'
        if self.toolset:
            arg += f' -T "{self.toolset}"'
        if self.platform:
            arg += f' -A "{self.platform}"'

        if options:
            arg += " " + cmakeutil.dict_to_arg(options)

        if force:
            self.clear()

        self.last_job = runner.enqueue(arg)
        self.build_dir = build_dir
        self.config = config
        return self.last_job

    def build(
        self, targets=None, options=None, build_dir=None, config=None,
    ):
        print(f"[cmake] building CMake project -> {self.build_dir}\n")

        if build_dir:
            self.build_dir = build_dir
        elif not self.build_dir:
            raise Exception("CMakeBuilder.build:unknown build_dir")

        arg = f'--build "{self.build_dir}"'

        if not config:
            config = self.config
        if config:
             arg += f' --config {config}'

        if targets:
            arg += " --target"
            for tgt in targets:
                arg += " " + tgt

        if options:
            arg += " " + cmakeutil.dict_to_arg(options)

        self.last_job = runner.enqueue(arg)
        return self.last_job

    def install(
        self, prefix, component=None, options=None, config=None,
    ):
        if not self.build_dir:
            raise Exception("CMakeBuilder.build:unknown build_dir")

        print(
            f'\n[cmake] installing CMake project component: {component if component else "ALL"} to {prefix}...\n'
        )

        arg = f'--install "{self.build_dir}" --prefix "{prefix}"'

        if not config:
            config = self.config
        if config:
             arg += f' --config {config}'

        if component:
            arg += f" --component {component}"

        if options:
            arg += " " + cmakeutil.dict_to_arg(options)

        self.last_job = runner.enqueue(arg)
        return self.last_job

    def wait(self, job=None):
        ret = runner.get_failed_job() if runner.wait(job) else None
        self.last_job = runner.get_last_job()
        return ret


    def clear(self):
        """Clear build directory"""
        if self.build_dir:
            cmakeutil.clear(self.build_dir)
        self.revert()

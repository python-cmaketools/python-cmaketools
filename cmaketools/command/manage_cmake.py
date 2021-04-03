import re, contextlib
from distutils import log
from distutils.errors import DistutilsError, DistutilsSetupError
from cmaketools import Command

from .. import cmakecontroller
from .. import cmakeutil
from .. import cmakeoptions

# CMake build system could be used by `build_ext` or `build_py` commands. While build_ext
# always run it, build_py uses it only conditionally (generally not). This command
# is defined as a subcommand to build_ext and build_py to unify the command execution
# path. Also, it allows `build`/`develop` command to directly set CMake options.
#
# super-command's `finalize_options()`
#    - use `self.get_finalized_commands('manage_cmake')` to retrieve the instance of `manage_cmake` command
#    - set CMake configuration options via `manage_cmake.set_cmake_options()`.
#      - can overwrite previous option set by another command
#      - options set directly on `manage_cmake` have the lowest priority
#    - schedule CMake jobs via `manage_cmake.schedule_build()` for all targets or for a specific target
#    - schedule CMake jobs via `manage_cmake.schedule_install()` for all components or for a specific component
# super-command's `run()`
#    - run `Distribution.ensure_cmake_started()` to make sure the cmake has started processing its jobs
#    - use `self.get_finalized_commands('manage_cmake)` to retrieve the instance of `manage_cmake` command
#    - run `manage_cmake.get_cmake_job_id()` to retrieve the CMake job id to wait for
#    - wait for the completion of CMake job via `manage_cmake.waitfor_job()`


class manage_cmake(Command):

    description = "build C/C++ extensions with CMake (compile/link to build directory)"

    def __init__(self, dist):
        """Instantiate with a link to a CMakeBuilder instance

        Parameter:
        ---------
        cmake CMakeBuilder: instance to run CMake commands
        """

        super().__init__(dist)

    def initialize_options(self):
        self.generator = "Ninja"
        self.platform = None
        self.toolset = None

    def finalize_options(self):
        pass

    def run(self):
        # see _running_cmake() contextmanager
        raise DistutilsError(
            "User cannot run `manage_cmake` command (internal use only)."
        )

    @contextlib.contextmanager
    def cmake_running(self):
        """Create a context during which self.cmake is valid. This guarantees
        the runner subprocess to be terminated when done.

        This replaces the default run() method for manage_cmake command
        """

        try:
            yield
        finally:
            if cmakecontroller.is_running():
                log.debug("terminating CMake runner subprocess...")
                cmakecontroller.stop()
                log.info("terminated CMake runner subprocess")

    def restart(self, config):

        attrs = ("generator", "platform", "toolset")
        is_running = cmakecontroller.is_running()

        # if already running and no change in sensitive attributes, nothing to do
        if is_running and not next(
            (
                getattr(self, attr, None) != getattr(config, attr, None)
                for attr in attrs
            ),
            False,
        ):
            return

        # if already running, stop the current cmake runner
        if is_running:
            cmakecontroller.stop()
            log.info("terminated CMake runner subprocess")

        # Start the CMake Runner
        log.info("starting new CMake runner subprocess")
        cmakecontroller.start(self.generator, self.platform, self.toolset)

    def waitfor(self, job=None):
        return cmakecontroller.get_failed_job() if cmakecontroller.wait(job) else None

    def enqueue_config(self, command):
        """[summary]

        Args:
            command (Command): source command object
            build_dir (str): build directory

        Raises:
            DistutilsSetupError: [description]
        """

        log.info(f"configuring CMake project...")

        # if CMakeCache.txt exists and its build type is different, delete the cache
        m = re.search(
            r"CMAKE_BUILD_TYPE:STRING=(.+?)\n",
            cmakeutil.read_cache(command.build_base) or "",
        )
        if m and m[1] != command.config:
            log.info("deleting CMakeCache.txt")
            cmakeutil.delete_cache(command.build_base)

        arg = f'-S . -B "{command.build_base}" ' + cmakeoptions.generate_arg_for(
            "config", command
        )

        log.info(f" arg: {arg}")

        # queue configure CMake project
        return cmakecontroller.enqueue(arg)

    def enqueue_build(self, command, targets=None):
        """add a build job possibly with build targets

        Args:
            target (str, optional): CMake target name. Defaults to None or all targets.
            targets (seq, optional): A list of CMake target names. Defaults to None.
            build_opts (dict, optional): a dict of build options. Defaults to None.

        Returns
        -------
            int: job ID of the scheduled build
        """

        log.info(
            f'building CMake project targets: {targets if targets else "ALL"} in {command.build_base}...'
        )

        arg = f'--build "{command.build_base}" --config {command.config} '

        if targets:
            arg += f" --target {' '.join(targets)}"

        arg += cmakeoptions.generate_arg_for("build", command)

        log.info(f" arg: {arg}")
        return cmakecontroller.enqueue(arg)

    def enqueue_install(self, command, prefix, component=None):
        """add an install job possibly with install components

        Args:
            dist_dir (str): CMake installation prefix
            component (str, optional): CMake install component name. Defaults to None or all components.
            install_opts (dict, optional): a dict of build options. Defaults to None.

        Returns
        -------
            int: job ID of the scheduled install
        """

        log.info(
            f'installing CMake project component: {component if component else "ALL"} to {prefix}...'
        )

        # find config from cache if found
        if hasattr(command, "config") and command.config:
            config = command.config
        else:
            # if CMakeCache.txt exists and its build type is different, delete the cache
            m = re.search(
                r"CMAKE_BUILD_TYPE:STRING=(.+?)\n",
                cmakeutil.read_cache(command.build_base) or "",
            )
            if m:
                config = m[1]
            else:
                raise DistutilsError("cmake build config not resolved")

        arg = f'--install "{command.build_base}" --prefix "{prefix}" --config {config} '

        if component:
            arg += f"--component {component} "

        arg += cmakeoptions.generate_arg_for("install", command)

        log.info(f" arg: {arg}")
        return cmakecontroller.enqueue(arg)

    def cleanup(self, next_cmd, conditional=None, deep=None):
        """clean up build directory for the next cmaketools command

        If conditional, cleanup is only performed if
        - next_cmd.build_base is the same as

        Args:
            conditional (bool, optional): True to clean up if only needed. Defaults to None.
            next_cmd (bool, optional): Next command to be executed. Defaults to None.
            deep (bool, optional): True to delete the entire build directory

        Returns
        -------
            bool : True if build setup
        """

        build_dir = getattr(next_cmd, "build_base", None)

        if not build_dir:
            return

        if conditional and (
            build_dir == self.build_dir or cmakeutil.configured(build_dir)
        ):
            ["generator", "toolset", "platform", "config"]
            cmakeoptions.config_options
        # generator=('-G',' ',"Specify a build system generator."),
        # toolset=('-T',' ',"Toolset specification for the generator, if supported."),
        # platform=('-A',' ',"Specify platform name if supported by generator."),
        # config=("--config",reformat_config,"CMAKE_BUILD_TYPE: Debug, Release, RelWithDebInfo, or MinSizeRel."),

        cmakeutil.clear(build_dir, deep)

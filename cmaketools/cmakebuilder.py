import os
import re
from operator import itemgetter
from setuptools import Extension
from pathlib import Path as _Path, PurePath as _PurePath
from distutils import sysconfig

from . import cmakeutil
from . import gitutil


class CMakeBuilder:
    """
    A class used to manage CMake build process

    ...

    Attributes
    ----------
    path : str
        (static) Path to cmake executable. Auto-initialized
    src_dir : str
        Source directory (default "src")
    ext_module_dirs : str[]
        List of source directories defining external modules
    ext_module_hint : str 
        Regex pattern to auto-detect external module directories
    test_dir : str
        Unit test directory (default "tests")
    test_submodules : str[]
        List of git submodules only used for testing
    has_package_data : bool
        Set False IF project has no package_data (default True)
    skip_configure : bool
        Set True to configure cmake externally (default False)
    config : str
        Default CMake build type (default "Release")
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

    Static Methods
    --------------
    get_generators(as_list=False)
        Get available CMake generators
    get_generator_names()
        Get names of available CMake generators

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

    path = cmakeutil.findexe("cmake")

    @staticmethod
    def get_generators(as_list=False):
        """get available CMake generators
        
        Parameter:
        as_list str: True to return a list of dict of all generators. Each entry
                     consists of 'name', 'desc', and 'default'
        
        Returns: str if as_list==False else dict[]
        """

        return cmakeutil.get_generators(CMakeBuilder.path, as_list)

    @staticmethod
    def get_generator_names():
        """get names of available CMake generators
        
        Parameter:
        generator str: Generator name to validate
        """

        return cmakeutil.get_generator_names(CMakeBuilder.path)

    def __init__(self, **kwargs):
        """
        Parameters
        ----------
        cmake_path : str
            path to cmake command (default auto-detected)
        src_dir : str
            Source directory (default "src")
        ext_module_dirs : str[]
            List of source directories defining external modules
        ext_module_hint : str 
            Regex pattern to auto-detect external module directories
        test_dir : str
            Unit test directory (default "tests")
        test_submodules : str[]
            List of git submodules only used for testing
        has_package_data : bool
            Set False IF project has no package_data (default True)
        skip_configure : bool
            Set True to configure cmake externally (default False)
        config : str
            Default CMake build type (default "Release")
        generator : str
            Default CMake --G argument
        platform : str
            Default CMake --platform argument
        toolset : str
            Default CMake --toolset argument
        parallel : int > 0
            Default CMake --parallel argument
        configure_opts : str[]
            List of other default option arguments for CMake configure 
        build_opts : str[]
            List of other default option arguments for CMake build
        install_opts : str[]
            List of other default option arguments for CMake install
        """

        def opt_value(attr, default):
            return kwargs[attr] if attr in kwargs and kwargs[attr] else default

        if "cmake_path" in kwargs:
            self.path = kwargs["cmake_path"]

        # project configurations
        self.src_dir = opt_value("src_dir", "src")
        self.ext_module_dirs = opt_value("ext_module_dirs", None)
        self.ext_module_hint = opt_value("ext_module_hint", None)
        self.test_dir = opt_value("test_dir", "tests")
        self.test_submodules = opt_value("dist_dir", [])
        self.has_package_data = opt_value("has_package_data", True)

        # CMake configurations
        self.skip_configure = opt_value("skip_configure", False)
        self.build_dir = opt_value("build_dir", "")
        self.config = opt_value("config", "Release")
        self.generator = opt_value("generator", None)
        self.platform = opt_value("platform", None)
        self.toolset = opt_value("toolset", None)
        self.parallel = opt_value("parallel", None)
        self.configure_opts = opt_value("configure_opts", [])
        self.build_opts = opt_value("build_opts", [])
        self.install_opts = opt_value("install_opts", [])

        self.gitmodules_status = None
        self.dist_dir = "dist"

        self._init_config = None
        self._built = False
        self._installed = dict(PY=False, EXT=False)

    def clear(self):
        """Clear build directory"""
        if self.build_dir:
            cmakeutil.clear(self.build_dir)
        self.revert()

    def get_setup_data_files(self):
        """Returns data_files argument for setuptools.setup()"""
        data_files = []
        if gitutil.has_submodules():
            data_files.append(".gitmodules")
            data_files.append(
                os.path.join(self.dist_dir, gitutil.gitmodules_status_name)
            )
        return [("", data_files)]

    def get_source_files(self):
        """Get all the source files"""

        return [
            path.as_posix()
            for path in _Path(self.src_dir).rglob("*")
            if not path.is_dir()
        ] + [
            (path / "CMakeLists.txt").as_posix()
            for path in _PurePath(self.src_dir).parents
        ]

    def pin_gitmodules(self):
        """Save status of submodules to be included in the sdist"""
        self.gitmodules_status = gitutil.get_submodule_status()

    def save_gitmodules_status(self, dst_dir):
        """Save previously pinned submodules status to a file"""

        if self.gitmodules_status:
            with open(os.path.join(dst_dir, gitutil.gitmodules_status_name), "w") as f:
                f.write(self.gitmodules_status)

    def save_cmake_config(self):
        """Save current CMake configurations"""
        # backup the original configuration set in setup.py
        self._init_config = dict(
            config=self.config,
            generator=self.generator,
            parallel=self.parallel,
            configure_opts=self.configure_opts,
            build_opts=self.build_opts,
            install_opts=self.install_opts,
        )

    def configure(
        self,
        build_dir,
        generator_config=None,
        config=None,
        parallel=None,
        configure_opts=[],
    ):
        """configure CMake project"""

        # if skip_configure
        if self.skip_configure:
            return

        # if initial state has not been saved, do so now
        if not self._init_config:
            self.save_cmake_config()

        # check in major changes, requiring removal of the cache file
        if cmakeutil.generator_changed(generator_config, build_dir, self.path):
            print("\n[cmake] switching generator. Deleting CMakeCache.txt")
            cmakeutil.delete_cache(self.build_dir)

        # resolve the new generator config
        if config:
            self.config = config
        else:
            config = self.config
        if generator_config:
            generator, toolset, platform = itemgetter(
                "generator", "toolset", "platform"
            )(generator_config)
            if generator not in generator_config:
                generator = self.generator
            if not toolset:
                toolset = self.toolset
            if not platform:
                platform = self.platform
        else:
            generator = self.generator
            toolset = self.toolset
            platform = self.platform

        if not parallel:
            parallel = self.parallel
        if self.configure_opts:
            configure_opts = [*self.configure_opts, *configure_opts]

        # Make sure git submodules are installed
        # - If not, clone individually
        # - This is critical for source distribution of a project with submodules as
        #   the package would not contain submodules (unless they are included in the
        #   source folder, which is a bad practice)
        gitutil.clone_submodules(
            self.gitmodules_status,
            self.test_submodules if os.path.isdir(self.test_dir) else [],
        )

        print("\n[cmake] configuring CMake project...\n")
        args = configure_opts
        kwargs = dict(build_type=config, cmakePath=self.path,)

        def set_option(opt, val):
            args.append(opt)
            args.append(val)

        def set_generator(val):
            set_option("-G", val)
            if os.name == "nt" and val.startswith("Ninja"):
                kwargs["need_msvc"] = True

        if generator:
            set_generator(generator)
        if toolset:
            set_option("-T", toolset)
        if platform:
            set_option("-A", platform)

        # run cmake configure
        cmakeutil.configure(".", build_dir, *args, **kwargs)

        # store the build directory for later use
        self.build_dir = build_dir

    def run(
        self, prefix, pkg_version=None, component=None, build_opts=[], install_opts=[],
    ):

        if not (self.build_dir and self.config):
            raise RuntimeError(
                "Run configure() first. No build directory has been recorded."
            )

        if not self._built:
            print(f"[cmake] building CMake project -> {self.build_dir}\n")

            # Make package version available as C++ Preprocessor Define
            env = cmakeutil.set_environ_cxxflags(self.build_dir,VERSION_INFO=pkg_version)
            
            if self.build_opts:
                build_opts = [*self.build_opts, *build_opts]

            cmakeutil.build(
                self.build_dir,
                *build_opts,
                build_type=self.config,
                cmakePath=self.path,
                env=env,
            )
            self._built = True

        if (component and not self._installed[component]) or (
            not (component and self._installed["PY"] and self._installed["EXT"])
        ):
            print(
                f'\n[cmake] installing CMake project component: {component if component else "ALL"} to {prefix}...\n'
            )
            if self.install_opts:
                install_opts = [*self.install_opts, *install_opts]
            cmakeutil.install(
                self.build_dir,
                os.path.join(os.getcwd(), prefix),
                *install_opts,
                component=component,
                build_type=self.config,
                cmakePath=self.path,
            )

            if component:
                self._installed[component] = True
            else:
                self._installed["PY"] = True
                self._installed["EXT"] = True

        print()  # Add an empty line for cleaner output

    def find_package_data(self, prefix):
        """Returns package_data argument for setuptools.setup()

        get setup package_data dict (expected to run only post-install)"""

        # glob all the files in dist_dir then filter out py & ext files
        root = _Path(prefix)
        excludes = [".py", sysconfig.get_config_var("EXT_SUFFIX")]
        files = [
            f
            for f in root.rglob("**/*")
            if f.is_file() and not any(f.name.endswith(e) for e in excludes)
        ]

        # find the parent package of each file and add to the package_data
        package_data = {}
        for f in files:
            try:
                pkg_dir = next(d for d in f.parents if (d / "__init__.py").is_file())
            except:
                continue
            pkg_name = _dir_to_pkg(pkg_dir.relative_to(root).as_posix())
            pkg_path = f.relative_to(pkg_dir).as_posix()
            if pkg_name in package_data:
                package_data[pkg_name].append(pkg_path)
            else:
                package_data[pkg_name] = [pkg_path]

        return package_data

    def revert(self):
        """Revert the builder configuration to the initial state it was before its 
        attributes were set by user via cli arguments.
        """
        if self._init_config:
            for key, value in self._init_config.items():
                setattr(self, key, value)
        self._built = False
        self._installed = dict(PY=False, EXT=False)

    def find_packages(self):
        """Returns packages argument for setuptools.setup()
        
        package directories must meet the following conditions:

        * Must reside inside self.src_dir directory, counting itself        
        * Must have __init__.py
        * Any directories w/out any *.py files as namespace package IF one of its
          descendent contains __init__.py (NOTE: I'm not yet clear whether we can 
          have a namespace package as subpackage to another package)
        """

        # scan src_dir for __init__.py
        root = _Path(self.src_dir)
        reg_paths = set(
            [d.parent.relative_to(root) for d in root.rglob("**/__init__.py")]
        )

        # convert path to str
        pkg_dirs = [path.as_posix() for path in reg_paths]

        # convert dir to package notation
        return [_dir_to_pkg(dir) for dir in pkg_dirs]

    def find_ext_modules(self):
        """Returns ext_modules argument for setuptools.setup()
    Return the ext_modules argument for setuptools.setup() filled with
           all the CMake target directories within the src directory. The ext_modules
           are selected either explicitly vis self.ext_module_dirs or implicitly via
           self.ext_module_hint. 

           For explicit specification, self.ext_module_dirs shall contain a list of
           ext_module directory relative to self.src_dir. 

           On the other hand, the implicit method scans all CMakeLists.txt files in
           self.src_dir for text that matches the regular expression given in 
           self.ext_module_hint

           The explicit method always takes precedence over the implicit method: 
           self.ext_module_hint would be ignored if self.ext_module_dirs is given.

           Under both methods, the function returns 
            
        """
        return (
            _create_extensions(self.ext_module_dirs)
            if self.ext_module_dirs
            else self._find_ext_modules_from_hint()
            if self.ext_module_hint
            else None
        )

    def _find_ext_modules_from_hint(self):
        def find_hint(file, hint):
            with open(file) as f:
                txt = f.read()
            return re.search(hint, txt)

        root = _Path(self.src_dir)
        matched_dirs = [
            file.parent.relative_to(root).as_posix()
            for file in root.rglob("**/CMakeLists.txt")
            if find_hint(file, self.ext_module_hint)
        ]
        return _create_extensions(matched_dirs)


def _create_extensions(dirs):
    return [Extension(_dir_to_pkg(mod), []) for mod in dirs]


def _dir_to_pkg(pkg_dir):
    return "" if pkg_dir == "." else re.sub(r"/", ".", pkg_dir)

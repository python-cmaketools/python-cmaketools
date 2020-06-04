import os
import re

import cmakeutil
import gitutil
from setuptools import Extension
from pathlib import Path as _Path, PurePath as _PurePath
from distutils import sysconfig


class CMakeBuilder:
    path = cmakeutil.findexe("cmake")
    default_setup_data_files = [
        "cmakecommands.py",
        "cmakebuilder.py",
        "cmakeutil.py",
        "gitutil.py",
    ]

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
        """validate generator is among the available CMake generators
        
        Parameter:
        generator str: Generator name to validate
        """

        return cmakeutil.get_generator_names(CMakeBuilder.path)

    def __init__(self, **kwargs):
        self.gitmodules_status = None

        def opt_value(attr, default):
            return kwargs[attr] if attr in kwargs and kwargs[attr] else default

        # project configurations
        self.package_name = opt_value("package_name", "")
        self.src_dir = opt_value("src_dir", "src")
        self.build_dir = opt_value("build_dir", "build")
        self.dist_dir = opt_value("dist_dir", "dist")
        self.ext_module_dirs = opt_value("ext_module_dirs", None)
        self.ext_module_hint = opt_value("ext_module_hint", None)
        self.test_dir = opt_value("test_dir", "tests")
        self.test_submodules = opt_value("dist_dir", [])
        self.has_package_data = opt_value("has_package_data", True)

        # CMake configurations
        self.skip_configure = opt_value("skip_configure", False) 
        self.config = opt_value("config", "Release")
        self.generator = opt_value("generator", None)
        self.platform = opt_value("platform", None)
        self.toolset = opt_value("toolset", None)
        self.parallel = opt_value("parallel", None)
        self.configure_args = opt_value("configure_args", [])
        self.build_args = opt_value("build_args", [])
        self.install_args = opt_value("install_args", [])

        self._init_config = None
        self._built = False
        self._installed = dict(PY=False, EXT=False)

    def clear(self):
        """Clear build directory"""
        cmakeutil.clear(self.build_dir)
        self.revert()

    def get_package_dir(self):
        return {self.package_name: self._get_dist_dir(self.dist_dir)}

    def get_setup_data_files(self):
        """Returns setup's data_files argument, listing all the aux files needed to install from sdist"""
        data_files = CMakeBuilder.default_setup_data_files
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
        self.gitmodules_status = gitutil.save_submodule_status(self.dist_dir)

    def save_cmake_config(self):
        """Save current CMake configurations"""
        # backup the original configuration set in setup.py
        self._init_config = dict(
            config=self.config,
            generator=self.generator,
            parallel=self.parallel,
            configure_args=self.configure_args,
            build_args=self.build_args,
            install_args=self.install_args,
        )

    def configure(
        self,
        generator,
        config=None,
        parallel=None,
        configure_args=[],
        build_args=[],
        install_args=[],
    ):
        """configure CMake project"""

        # if skip_configure
        if self.skip_configure:
            return

        # if initial state has not been saved, do so now
        if not self._init_config:
            self.save_cmake_config()

        # check in major changes, requiring removal of the cache file
        if cmakeutil.generator_changed(generator, self.build_dir, self.path):
            print("\n[cmake] switching generator. Deleting CMakeCache.txt")
            cmakeutil.delete_cache(self.build_dir)

        # store the new config
        if config:
            self.config = config
        if generator:
            self.generator
        if parallel:
            self.parallel = parallel
        if configure_args:
            self.configure_args = configure_args
        if build_args:
            self.build_args = build_args
        if install_args:
            self.install_args = install_args

        # Make sure git submodules are installed
        # - If not, clone individually
        # - This is critical for source distribution of a project with submodules as
        #   the package would not contain submodules (unless they are included in the
        #   source folder, which is a bad practice)
        gitutil.clone_submodules(
            self.dist_dir, self.test_submodules if os.path.isdir(self.test_dir) else []
        )

        print("\n[cmake] configuring CMake project...\n")
        args = configure_args
        kwargs = dict(build_type=self.config, cmakePath=self.path,)

        def set_option(opt, val):
            args.append(opt)
            args.append(val)

        def set_generator(val):
            set_option("-G", val)
            if os.name == "nt" and val.startswith("Ninja"):
                kwargs["need_msvc"] = True

        g = self.generator
        if type(g) is dict:
            if "generator" in g and g["generator"]:
                set_generator(g["generator"])
            if "toolset" in g and g["toolset"]:
                set_option("-T", g["toolset"])
            if "platform" in g and g["platform"]:
                set_option("-A", g["platform"])
        else:
            if g:
                set_generator(g)
            if self.toolset:
                set_option("-T", self.toolset)
            if self.platform:
                set_option("-A", self.platform)

        # run cmake configure
        cmakeutil.configure(".", self.build_dir, *args, **kwargs)

    def run(self, pkg_version, prefix=None, component=None):

        if not self._built:
            print(f"[cmake] building CMake project -> {prefix}\n")

            # Make package version available as C++ Preprocessor Define
            env = os.environ.copy()
            if pkg_version:
                env[
                    "CXXFLAGS"
                ] = f'{env.get("CXXFLAGS", "")} -DVERSION_INFO="{pkg_version}"'

            cmakeutil.build(
                self.build_dir,
                *self.build_args,
                build_type=self.config,
                cmakePath=self.path,
                env=env,
            )
            self._built = True

        if (component and not self._installed[component]) or (
            not (component and self._installed["PY"] and self._installed["EXT"])
        ):
            print(
                f'\n[cmake] installing CMake project component: {component if component else "ALL"}...\n'
            )
            cmakeutil.install(
                self.build_dir,
                self._get_dist_dir(prefix),
                *self.install_args,
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

    def _get_dist_dir(self, prefix):
        return os.path.join(prefix if prefix else self.dist_dir, self.package_name)

    def get_package_data(self, prefix=None):
        """get setup package_data dict (expected to run only post-install)"""

        # glob all the files in dist_dir then filter out py & ext files
        root = _Path(self._get_dist_dir(prefix))
        excludes = [".py", sysconfig.get_config_var("EXT_SUFFIX")]
        files = [
            f
            for f in root.rglob("**/*")
            if f.is_file() and not any(f.name.endswith(e) for e in excludes)
        ]

        # find the parent package of each file and add to the package_data
        package_data = {}
        for f in files:
            pkg_dir = next(d for d in f.parents if (d / "__init__.py").is_file())
            pkg_name = _dir_to_pkg(
                self.package_name, pkg_dir.relative_to(root).as_posix()
            )
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
        """Return a list all Python packages found within self.src_dir directory

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

        # add all namespace packages that houses regular packages
        pkg_paths = set(reg_paths)
        for dir in reg_paths:
            pkg_paths |= set(dir.parents)

        # convert path to str
        pkg_dirs = [path.as_posix() for path in pkg_paths]

        # convert dir to package notation
        return [_dir_to_pkg(self.package_name, dir) for dir in pkg_dirs]

    def find_ext_modules(self):
        """Return the ext_modules argument for setuptools.setup() filled with
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
            _create_extensions(self.package_name, self.ext_module_dirs)
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
        return _create_extensions(self.package_name, matched_dirs)


def _create_extensions(root, dirs):
    return [Extension(_dir_to_pkg(root, mod), []) for mod in dirs]


def _dir_to_pkg(root_pkg, pkg_dir):
    return root_pkg + ("" if pkg_dir == "." else "." + re.sub(r"/", ".", pkg_dir))

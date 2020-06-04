# python_cmake_boilerplate

## Boilerplate for Python packages with CMake-based binary extensions

This repository provides a powerful boilerplate (GitHub Template) for Python packages with binary extension modules. Specifically, it includes a set of Python setup modules to create a `sdist` tarball from a [CMake](https://cmake.org/) project with minimal `setup.py` scripting.

### Features

- **Source Distributable**: This boilerplate let you create a `pip`-installable source distribution via Setuptools' `sdist` command. This enables the use of `tox` or Continuous Integration servers to perform multi-environment testing.
- **Automatic Source Content Detection**: By taking advantage of the source directory structure imposed by CMake project, `setup.py`'s critical keywords: `package_dir`, `packages`, `package_data`, and `ext_modules`.
- **Source File Protection**: Neither CMake nor Python setuptools modify the content of the source subdirectory under any command.
- **Git Submodule Aware**: If a project contains git submodules, the submodules will be automatically cloned during `pip` installation and the pinned commit of each submodule will be checked out before build.
- **Support for CMake Command-Line Options**: The most of [the CMake command line options](https://cmake.org/cmake/help/v3.17/manual/cmake.1.html) are made available as options to the `build_ext` command of `setuptools`. For example, `python setup.py build_ext -GNinja` will build the CMake project with Ninja build system.
- **Integaration of Native Code Tests**: CMake ships with a test driver program, called [ctest](https://cmake.org/cmake/help/latest/manual/ctest.1.html). With it, this boilerplate enables simultaneous testing of both the native and Python codes of the package all in Python.

### About Included Example Project

The included example uses [`pybind11`](http://pybind11.readthedocs.io/en/stable/index.html) to bind C++ code to Python. It is loosely based on @benjaminjack's [`python_cpp_example`](https://github.com/benjaminjack/python_cpp_example), which on itself is derived form [`pybind11's` CMake example](https://github.com/pybind/cmake_example).

#### Installation/Exploration

To explore the boilerplate function, first clone the repo with submodules:

```bash
git clone https://github.com/hokiedsp/python_cmake_boilerplate.git --recurse-submodules
```

Then navigate to the project root directory and create the distribution packages. For example,

```bash
python setup.py sdist bdist_wheel
```

creates both source and wheel distributions. They will be found in `dist` subdirectory, and to install them, run

```bash
pip install dist/mypkg-0.5.tar.gz # from source distribution OR
pip install dist/mypkg-0.5-cp37-cp37m-win_amd64.whl # from wheel distribution (file suffix may vary)
```

Now, to build purely from CMake, delete both `dist` and `build` subdirectories under the root, then type:

```bash
cmake . # to configure
cd build
cmake --build . # build the binary extensions
cmake --install . # install the complete Python package in dist directory
ctest . # runs test on pure c++ code
```

The resulting package is found in `dist/mypkg`. If you compare the content of this directory vs. after `python setup.py sdist bdist_wheel`, you may notice that the binary extension file is missing from `dist/mypkg`. This is by design of `setuptools`/`distutils`.

Now, to run the test in Python, return to the root directory and type:

```bash
pip install -e .    # install package using setup.py in editable mode
pytest tests        # run all the test scripts in tests subdirectory
pip uninstall mypkg # uninstall the package
```

Finally,

```bash
tox
```

tests the package in controlled environments

#### Files

1. `src/example_module`: Python binding module of simple C++ functions
2. `src/hello.py`: Python module
3. `src/subpackage/subsubpackage/bye.py`: demo subpackge resolution
4. `lib/catch2` & `lib/pybind11`: git submodules
5. `tests/*.cpp`: Unit tests for C++ code using [`catch2`](https://github.com/catchorg/Catch2.git)
6. `tests/*.py`: Unit tests for Python code (using `pytest`)
7. `tox.ini`: `Tox` configuration file

### Source Directory Structure

The structure of the source directory and placements of `CMakeLists.txt` are vital to minimize potential packaging complications. Here are some key tips in sturcturing the source directory:

- **Source Directory** (`src`) is the base of the Python package structure as you expect from authoring pure Python packages. Treat the `src_dir` as the base package. It could be named arbitrarily so long as it is assigned to `src_dir` attribute of `CMakeBuilder`.
- **Package Directory** Source directory and any directries therein must contain `__init__.py` to be regarded as Python package. The Python modules (both pure and binary) will not be recognized in Python.
- **Pure Python Modules** Place all `.py` files where they belong within the package structure.
- **Binary Module** To define a binary module, create a subdirectory under a package folder it belongs to. In the example, `src/example_module` is one such directory, and it defines `mypkg.example_module` binary module. Each binary module directory should contain `CMakeLists.txt` file which define the library target. For example, the `CMakeLists.txt` file in module directory shall call `pybind11_add_module` to include a `pybind11`-based module to the build project. While this is not a mandatory requirement, this structure is used to auto-detect `ext_modules` by `CMakeBuilder`.
- **Additional Files** Any "owned" additional files needed to build the binary modules or to be used by the package shall be placed somewhere in the source directory as it is the directory packaged in `sdist` (other than setup files).
- **3rd-Pary Files** Script CMake to install them to their final in-package location to keep your package platform agnostic. This can be done via [git submodules](https://git-scm.com/book/en/v2/Git-Tools-Submodules) or CMake [`file(DOWNLOAD <url> <file> ...)`](https://cmake.org/cmake/help/latest/command/file.html#download) command, then build it if necessary and install the files relative to `CMAKE_INSTALL_PREFIX`.

### `CMakeLists.txt` Authoring Tips

First, to learn how to author CMake scripts, visit [Official CMake Tutorial](https://cmake.org/cmake/help/latest/guide/tutorial/index.html).

The automation realized in this Python/CMake package boilerplate relies on CMake's ability to traverse directory hierarchies, i.e., to encapsulate the build process of each directory via its `CMakeLists.txt` script and traverse directries. Some script snippets are repetitive and reusable as described below.

Here are general tips:

- In general, `CMakeLists.txt` is expected in the source directory and its (sub)directories (possibly excluding resource/asset directories). Parent `CMakeLists.txt` must call `add_subdirectory()` for each of its subdirectories.
- **Base Source Directory** shall define `SRC_DIR` variable by

  ```cmake
  set(SRC_DIR ${CMAKE_CURRENT_SOURCE_DIR})
  ```

  so relative paths of subdirectories can be evaluated later.

- **Python Package Directories** with pure Python modules must contain [`install(FILES <file>...)`](https://cmake.org/cmake/help/latest/command/install.html#files) command to copy all `.py` files:

  ```cmake
  file(RELATIVE_PATH DST_DIR ${SRC_DIR} ${CMAKE_CURRENT_SOURCE_DIR})
  file(GLOB PYFILES LIST_DIRECTORIES false RELATIVE ${CMAKE_CURRENT_SOURCE_DIR} "*.py")
  install(FILES ${PYFILES} DESTINATION ${DST_DIR} COMPONENT "PY")
  ```

  The base package (i.e., source directory) takes a bit different form to copy Python files:

  ```cmake
  file(GLOB PYFILES LIST_DIRECTORIES false RELATIVE ${CMAKE_CURRENT_SOURCE_DIR} "*.py")
  install(FILES ${PYFILES} DESTINATION "." COMPONENT "PY")
  ```

  Note `COMPONENT "PY"` designation in `install`. This lets `setuptools`'s `build_py` to install only pure Python files (and `package_data` files).

- **External Module Directories** runs [`add_library(<name> SHARED | MODULE ...)`](https://cmake.org/cmake/help/latest/command/add_library.html#normal-libraries) command either directly or indirectly. Here, it is imperative to set `name` of the library target to match its directory name. Then the target is copied to the final destination with [`install(TARGETS <target>...)`](https://cmake.org/cmake/help/latest/command/install.html#targets) command.

  ```cmake
  # match target name to folder name
  get_filename_component(TARGET ${CMAKE_CURRENT_SOURCE_DIR} NAME)

  # build commands
  add_library(${TARGET} ...)
  set_target_properties(${TARGET} PROPERTIES PREFIX "${PYTHON_MODULE_PREFIX}")
  set_target_properties(${TARGET} PROPERTIES SUFFIX "${PYTHON_MODULE_EXTENSION}")
  # ... more build commands to follow

  # install commands
  get_filename_component(CURRENT_SRC_DIR ${CMAKE_CURRENT_SOURCE_DIR} DIRECTORY)
  if(${SRC_DIR} STREQUAL ${CURRENT_SRC_DIR})
    set(DST_DIR ".") # if parent is the base source folder
  else()
    file(RELATIVE_PATH DST_DIR ${SRC_DIR} ${CURRENT_SRC_DIR})
  endif()
  install(TARGETS ${TARGET} DESTINATION ${DST_DIR} COMPONENT "EXT")
  ```

  Here we register the install as `EXT` component so `build_ext` will only copy external modules to their final locations.

- **Own Package Data Files** are handled in a similar fashion as the pure Python modules with [`install(FILES <file>...)`](https://cmake.org/cmake/help/latest/command/install.html#files) command as `PY` component.

  ```cmake
  # to install a package data file 'data.txt'
  file(RELATIVE_PATH DST_DIR ${SRC_DIR} ${CMAKE_CURRENT_SOURCE_DIR})
  install(FILES "data.txt" DESTINATION ${DST_DIR} COMPONENT "PY")
  ```

- **3rd-party Package Data Files** is a bit trickier. The most intuitive way perhaps to call the `install` command from the source folder, which matches the folder where the 3rd-party file is placed in the package. For example, suppose this skeltal directory model:

  ```bash
  # After 'cmake --install build'
  project-root/
  ├── build/
  |   └── lib/
  |       └── 3rd-party-tool/
  |           └── libtool.dll # <=original
  ├── dist/
  |   └── mypkg/
  |       └── lib/
  |           └── libtool.dll # <=copied distro-ready file
  ├── lib/
  |   └── 3rd-party-tool/ # lib source files in here
  └── src/
      └── lib/
          └── CMakeLists.txt # <=issues install command
  ```

  The source files of a 3rd-party library is included to the project via git submodule in `lib/3rd-party-tool/` and when built its DLL (assuming Windows) file will be found at `build/lib/3rd-party-tool/libtool.dll`. We want this DLL file to be placed in `lib` folder of the Python package, which means CMake must install (copy) `libtool.dll` to `dist/mypkg/lib/libtool.dll`. The install command shall be issued by `src/lib/CMakeLists.txt` even if `src/lib/` would otherwise be empty.

  ```cmake
  # to install a package data file
  SET(DLL_NAME "libtool.dll")
  SET(DLL_PATH "${CMAKE_BINARY_DIR}/lib/3rd-party-tool/${DLL_NAME}")
  file(RELATIVE_PATH DST_DIR ${SRC_DIR} ${CMAKE_CURRENT_SOURCE_DIR})
  install(FILES ${DLL_PATH} DESTINATION ${DST_DIR} COMPONENT "PY")
  ```

- **Project Root** `CMakeLists.txt` defines general configurations (such as finding dependent libraries and setting up tests) of the build project. There are a couple things could be configured here to improve the CMake/Setuptools co-operation.

  - Set the CMake project name to be the Python package name:

    ```cmake
    project(mypkg)
    ```

  - Set default install path to be `dist/<package_name>` so CMake by default installs to the same `dist` directory location:

    ```cmake
    if (CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT)
        set (CMAKE_INSTALL_PREFIX "${CMAKE_SOURCE_DIR}/dist/${PROJECT_NAME}" CACHE PATH "default install path" FORCE )
    endif()
    ```

### Explanation of `setup.py`

```python
#! /usr/bin/env python3
from setuptools import setup
from cmakebuilder import CMakeBuilder
from cmakecommands import generate_cmdclass
```

Aside from the obvious `setup` function, you need:

- `CMakeBuilder` class to oversee the CMake project and
- `generate_cmdclass` function to override several default commands of `setuptools`: `egg_info`, `build_py`, `build_ext`, `sdist`, and `install_data`.

```python
# CMakeBuilder builds the ENTIRE python package and place it at dist_dir
# - this includes copying all the py files in the project
cmake = CMakeBuilder(
    package_name="mypkg",  # name of the distribution package (also the root package)
    src_dir="src",  # where all the source files are located (both PY and EXT)
    test_dir="tests",  # if this dir is missing...
    test_submodules=["lib/catch2"],  # these submodules won't be loaded in pip
    # ext_module_dirs=["example_module"], # explicitly define ext_modules OR...
    ext_module_hint=r"pybind11_add_module",  # define regex pattern to search in each CMakeLists.txt
    # has_package_data = False, # set False to allow sdist to skip running cmake (uncomment only if no package_data or manually setting it)

    ### DEVLEOPMENT OPTIONS: below options should be commented out for deployment ###
    # skip_configure=True, # skip CMake configuration stage and uses existing config
    # config="Debug",    # specify build type (configuration), default="Release"
    # generator="Ninja", # use build_ext generator option
    # toolset=,    # toolset spec for selected generator
    # platform=, # target platform
)
```

To instantiate CMakeBuilder, at the minimum, specify `package_name` and `src_dir`. **_TIP:_ Name `package_name` differently from the project directory if running `tox` test.**

If the project contains unittest test, which is not a part of source distribution (i.e., test files are located outside of `src_dir`) _and_ uses some submodules only for the purpose of testing, set `test_dir` and `test_submodules` to eliminate install-time downloading of unnecessary submodules.

Use `ext_module_hint` to auto-detect source subdirectories which house CMake build targets. To detect external modules, `CMakeBuilder` recursively scans texts of all the `CMakeLists.txt` files in `src_dir`, looking for the regex pattern given in `ext_module_hint`. In the example, we key on the CMake `pybind11_add_module` function as it is used to add `pybind11` CMake target to the project. If no common regex pattern could be derived, utilize `ext_module_dirs` to indicate which source directories morph into external modules once CMake project is built and installed.

For a project without any `package_data` files (i.e., CMake only installs `.py` and extension module `.pyd/.so` files) `ext_module_hint` keyword may be set `False` to speed up `sdist` command execution. Note that it only affects the `setup` performance if only `sdist` command is executed.

There are several options for development purpose: `skip_configure`, `config`, `generator`, `toolset`, and `platform`.

- `skip_configure` is a useful feature if you use another tool to manage CMake development (e.g., Visual Studio Code with CMake Tools Extension). With this option `True`, `setup.py` will not configure CMake project and use existing CMake configuration (i.e., `CMakeCache.txt`).
- `config`, `generator` (`-G`), `toolset` (`-T`), and `platform` (`-A`) directly corresponds to `buld_ext` options of those names and CMake options in the parentheses. `config` option sets CMake's build/install `config` options as well as `CMAKE_BUILD_TYPE` definition in the CMake configure phase

```python
setup(
    name=cmake.package_name,
    # ... metadata arguments snipped ...
    package_dir=cmake.get_package_dir(),
    packages=cmake.find_packages(),
    # package_data= # filled automatically with non-.py files installed by CMake (PY component)
    ext_modules=cmake.find_ext_modules(),
    cmdclass=generate_cmdclass(cmake),
    data_files=cmake.get_setup_data_files(),
    zip_safe=False,
)
```

The `cmake` instance of `CMakeBuilder` provides the values for the `package_name`, `package_dir`, `packages`, `ext_modules`, and `data_files` keyword arguments of `setup`. Note that `data_files` contains a list of root-level supplementary `.py` files, which are only needed to run `setup`.

Traditionally, `package_data` must be specified to indicate additional files to be deployed. This is completely automated as CMake is expected to install all necessary files in `dist_dir/<package_name>`, and `setup`'s `build_py` command auto-generates `package_data` internally by scanning the files in `dist_dir`.

The `cmdclass` argument must be set to use the custom setup commands, and `generate_cmdclass(cmake)` provides the new command classes which are pre-linked to `cmake`.

### Create a new repo from this boilerplate

1. Create a new remote repo via "Use this template" green button at the top of this page or follow [this link](https://github.com/hokiedsp/python_cpp_boilerplate/generate).
2. Clone the newly created repo:

```bash
git clone https://github.com/<your_account>/<new_repo>
```

3. The cloned repo does not have the submodules used in the example. To grab them, run the following from within the repository:

```bash
git submodule add https://github.com/pybind/pybind11.git lib/pybind11
git submodule add https://github.com/catchorg/Catch2.git lib/catch2
```

### `build_ext` Command Options

The `build_ext` command options are completely changed to accomodate CMake command-line options. Here is the output of `python setup.py --help build_ext`

```bash
Common commands: (see '--help-commands' for more)

  setup.py build      will build the package underneath 'build/'
  setup.py install    will install the package

Global options:
  --verbose (-v)  run verbosely (default)
  --quiet (-q)    run quietly (turns verbosity off)
  --dry-run (-n)  don't actually do anything
  --help (-h)     show detailed help message
  --no-user-cfg   ignore pydistutils.cfg in your home directory

Options for 'build_ext' command:
  --cmake-path          Name/path of the CMake executable to use, overriding
                        default auto-detection.
  --build-lib (-b)      directory for compiled extension modules
  --inplace (-i)        ignore build-lib and put compiled extensions into the
                        source directory alongside your pure Python modules
  --force (-f)          forcibly build everything (delete existing
                        CMakeCache.txt)
  --cache (-C)          Pre-load a CMake script to populate the cache.
  --define (-D)         Create or update a CMake CACHE entry (separated by
                        ';')
  --undef (-U)          Remove matching entries from CMake CACHE.
  --generator (-G)      Specify a build system generator.
  --toolset (-T)        Toolset specification for the generator, if supported.
  --platform (-A)       Specify platform name if supported by generator.
  --Wno-dev             Suppress developer warnings.
  --Wdev                Enable developer warnings.
  --Werror              Make specified warnings into errors: dev or
                        deprecated.
  --Wno-error           Make specified warnings not errors.
  --Wdeprecated         Enable deprecated functionality warnings.
  --Wno-deprecated      Suppress deprecated functionality warnings.
  --log-level           Set the log level to one of: ERROR, WARNING, NOTICE,
                        STATUS, VERBOSE, DEBUG, TRACE
  --log-context         Enable the message() command outputting context
                        attached to each message.
  --debug-trycompile    Do not delete the try_compile() build tree. Only
                        useful on one try_compile() at a time.
  --debug-output        Put cmake in a debug mode.
  --debug-find          Put cmake find commands in a debug mode.
  --trace               Put cmake in trace mode.
  --trace-expand        Put cmake in trace mode with variables expanded.
  --trace-format        Put cmake in trace mode and sets the trace output
                        format.
  --trace-source        Put cmake in trace mode, but output only lines of a
                        specified file.
  --trace-redirect      Put cmake in trace mode and redirect trace output to a
                        file instead of stderr.
  --warn-uninitialized  Specify a build system generator.
  --warn-unused-vars    Warn about unused variables.
  --no-warn-unused-cli  Don’t warn about command line options.
  --check-system-vars   Find problems with variable usage in system files.
  --parallel (-j)       The maximum number of concurrent processes to use when
                        building.
  --config              For multi-configuration tools, choose this
                        configuration.
  --clean-first         Build target clean first, then build.
  --verbose (-v)        Enable verbose output - if supported - including the
                        build commands to be executed.
  --strip               Strip before installing.
  --help-generator      list available compilers

usage: setup.py [global_opts] cmd1 [cmd1_opts] [cmd2 [cmd2_opts] ...]
   or: setup.py --help [cmd1 cmd2 ...]
   or: setup.py --help-commands
   or: setup.py cmd --help
```

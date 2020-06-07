# Setuptools extensions for CMake: Seamless integration of Cmake build system to setuptools

This Python package provides an extension to setuptools to integrate CMake into setuptools workflow. CMake build tool is tasked to build/install a complete Python distribution package with binary extensions and necessary data files. Then, setuptools follows to package up the bundled files for binary distribution (`bdist_wheel`/`bdist_egg`/etc.) or the CMake source directory for source distribution (`sdist`).

## Features

- **setup() Wrapper**: `cmaketools.setup()` wraps `setuptools.setup()` to provide one-stop `setup()` call for both CMake and setupstools.
- **Source Distributable**: `cmaketools` let you create a `pip`-installable source distribution via Setuptools' `sdist` command. This enables the use of `tox` to perform multi-environment testing.
- **Automatic Source Content Detection**: By taking advantage of the source directory structure imposed by CMake project, `setup.py`'s critical keywords: `package_dir`, `packages`, `package_data`, `ext_modules`, and `cmdclass`.
- **Source File Protection**: Neither CMake nor Python setuptools will modify any content of the source directory under any command. It will not be cluttered by `__pycache__` or other runtime artifacts.
- **Git Submodule Aware**: If a project contains git submodules, the submodules will be automatically cloned during `pip` installation, and the pinned commit of each submodule will be checked out before build.
- **Support for CMake Command-Line Options**: The most of [the CMake command line options](https://cmake.org/cmake/help/v3.17/manual/cmake.1.html) are made available as the `build_ext` command options. For example, `python setup.py build_ext -GNinja` will build the CMake project with Ninja build system.
- **Integaration of Native Code Tests**: CMake ships with a test driver program, called [ctest](https://cmake.org/cmake/help/latest/manual/ctest.1.html). It could be called to run the CMake build tests from Python via `cmaketools.cmakeutil.ctest()`.

## Usage Examples

You can experiment `cmaketools` with different Python/native interfaces availeble from following GitHub templates:

- [CPython: https://github.com/python-cmaketools/cpython-example](https://github.com/python-cmaketools/cpython-example)
- [Pybind11: https://github.com/python-cmaketools/pybind-example](https://github.com/python-cmaketools/pybind-example)
- [Boost-Python: https://github.com/python-cmaketools/boost-python-example](https://github.com/python-cmaketools/boost-python-example)

## Package Authoring Guide

### Source Directory Structure

The structure of the source directory and placements of `CMakeLists.txt` must adhere to the requirements below for `cmaketools` to detect the package structure correctly. Here are some key tips in structuring the source directory:

- **Source Directory** (`src`) corresponds to the root package (or `Lib\site-packages` in Python directory). It could be named arbitrarily so long as it is assigned to `src_dir` attribute of `CMakeBuilder`.
- **Package Directory** Source subdirectories with `__init__.py` file are included in `packages` `setup` argument.
- **Pure Python Modules** Place all `.py` module files where they belong within the package structure.
- **Binary Extension Module** To define a binary module, create a directory under a package directory it belongs to. In the example, `src/mypkg/example_module` is one such directory then we expect `mypkg.example_module` binary module. **Make sure the directory name matches the module name defined in C/C++ source file.** Each binary module directory should contain `CMakeLists.txt` file which defines the library target. For example, the `CMakeLists.txt` file in module directory shall call `pybind11_add_module` to include a `pybind11`-based module to the build project. This is a requirement for the auto-configuration of `ext_modules` `setup` argument.
- **Additional Files** Any "owned" additional data files needed to build the binary modules or to be used by the package shall be placed somewhere in `src` as it is the directory packaged by `sdist`.
- **3rd-Pary Files** If downloadable or git-clonable, place them outside of `src` to keep `sdist` package small. Script CMake to install them to their final in-package location to keep your package platform agnostic. This can be done via [git submodules](https://git-scm.com/book/en/v2/Git-Tools-Submodules) or CMake [`file(DOWNLOAD <url> <file> ...)`](https://cmake.org/cmake/help/latest/command/file.html#download) command, then build it if necessary and install the files relative to `CMAKE_INSTALL_PREFIX`. Only if they must be distributed in `sdist` package, place them inside `src`.

### `CMakeLists.txt` Authoring Tips

First, to learn how to author CMake scripts, visit [Official CMake Tutorial](https://cmake.org/cmake/help/latest/guide/tutorial/index.html).

The CMake integration relies on CMake's ability to traverse directory hierarchies, i.e., to encapsulate the build process of each directory via its `CMakeLists.txt` script and traverse directries. Some script snippets are repetitive and reusable as described below.

Here are general tips:

- In general, `CMakeLists.txt` is expected in the source directory and its (sub)directories (possibly excluding resource/asset directories). Parent `CMakeLists.txt` must call `add_subdirectory()` for each of its subdirectories.
- **Base Source Directory** shall define a `SRC_DIR` variable by

  ```cmake
  set(SRC_DIR ${CMAKE_CURRENT_SOURCE_DIR})
  ```

  so relative paths of subdirectories can be evaluated later.

- **Package Directories** with pure Python modules must contain [`install(FILES <file>...)`](https://cmake.org/cmake/help/latest/command/install.html#files) command to copy all `.py` files to the install target folder (typically `dist/<package_name>`):

  ```cmake
  file(RELATIVE_PATH DST_DIR ${SRC_DIR} ${CMAKE_CURRENT_SOURCE_DIR})
  file(GLOB PYFILES LIST_DIRECTORIES false RELATIVE ${CMAKE_CURRENT_SOURCE_DIR} "*.py")
  install(FILES ${PYFILES} DESTINATION ${DST_DIR} COMPONENT "PY")
  ```

  Note `COMPONENT "PY"` designation in `install`. This lets `setuptools`'s `build_py` to run CMake to install these files (and `package_data` files).

- **External Module Directories** runs [`add_library(<name> SHARED | MODULE ...)`](https://cmake.org/cmake/help/latest/command/add_library.html#normal-libraries) command either directly or indirectly. Here, it is imperative to set `name` of the library target to match its directory name. Then the target is copied to the final destination with [`install(TARGETS <target>...)`](https://cmake.org/cmake/help/latest/command/install.html#targets) command.

  ```cmake
  # match target name to folder name
  get_filename_component(TARGET ${CMAKE_CURRENT_SOURCE_DIR} NAME)

  # build commands
  add_library(${TARGET} ...) # typically Python3_add_library or pybind11_add_module
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

- **3rd-Party Package Data Files** are a bit trickier. The most intuitive way perhaps is to call the `install` command from the source folder, which matches the folder where the 3rd-party file is placed in the package. For example, suppose this skeletal directory model:

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
  |           └── libtool.dll # <=distro-ready file (the install destination)
  ├── lib/
  |   └── 3rd-party-tool/ # lib source files in here to be built
  └── src/
      └── mypkg/
          └── lib/
              └── CMakeLists.txt # <=issue install command in this file
  ```

  The source files of a 3rd-party library is included to the project via git submodule in `lib/3rd-party-tool/` and when built let's assume its DLL (assuming Windows) file will be found at `build/lib/3rd-party-tool/libtool.dll`. We want this DLL file to be placed in `lib` folder of the Python package, which means CMake must install (copy) `libtool.dll` to `dist/mypkg/lib/libtool.dll`. The install command shall be issued by `src/mypkg/lib/CMakeLists.txt` even if `src/mypkg/lib/` would otherwise be empty.

  ```cmake
  # to install a package data file
  SET(DLL_NAME "libtool.dll")
  SET(DLL_PATH "${CMAKE_BINARY_DIR}/lib/3rd-party-tool/${DLL_NAME}")
  file(RELATIVE_PATH DST_DIR ${SRC_DIR} ${CMAKE_CURRENT_SOURCE_DIR})
  install(FILES ${DLL_PATH} DESTINATION ${DST_DIR} COMPONENT "PY")
  ```

  Note: Typically you can construct CMake variable via libarary's CMake variables rather than hard-coding the `DLL_PATH` as done above.

- **Project Root** `CMakeLists.txt` defines general configurations (such as finding dependent libraries and setting up tests) of the build project. There are a couple things could be configured here to improve the CMake/Setuptools co-operation.
- Set default install path to be `dist` so CMake by default installs to the same `dist` directory location as setuptools:

  ```cmake
  if (CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT)
    set (CMAKE_INSTALL_PREFIX "${CMAKE_SOURCE_DIR}/dist" CACHE PATH "default install path" FORCE )
  endif()
  ```

## `setup()` Arguments

`cmaketools.setup()` call wraps `setuptools.setup()` so to initialize `CMakeBuilder` and auto-generate `setuptools.setup()` arguments. As such, it accepts most of setuptools.setup() arguments with additional arguments to configure CMake build. Also, it may overwrite user-provided setuptools arguments in order to integrate CMake.

### List of New Arguments for CMake

| Keyword            | Type    | Description                                                |
| ------------------ | ------- | ---------------------------------------------------------- |
| `cmake_path`       | str     | path to cmake command (default auto-detected)              |
| `src_dir`          | str     | Source directory (default "src")                           |
| `ext_module_dirs`  | str[]   | List of source directories defining external modules       |
| `ext_module_hint`  | str     | Regex pattern to auto-detect external module directories   |
| `test_dir`         | str     | Unit test directory (default "tests")                      |
| `test_submodules`  | str[]   | List of git submodules only used for testing               |
| `has_package_data` | bool    | Set False if project has no package_data (default True)    |
| `skip_configure`   | bool    | Set True to configure cmake externally (default False)     |
| `config`           | str     | Default CMake build type (default "Release")               |
| `generator`        | str     | Default CMake `--G` argument                               |
| `platform`         | str     | Default CMake `--platform` argument                        |
| `toolset`          | str     | Default CMake `--toolset` argument                         |
| `parallel`         | int > 0 | Default CMake `--parallel` argument                        |
| `configure_opts`   | str[]   | List of other default option arguments for CMake configure |
| `build_opts`       | str[]   | List of other default option arguments for CMake build     |
| `install_opts`     | str[]   | List of other default option arguments for CMake install   |

### Overriden setuptools arguments

- `cmdclass` (partial override, overrides `egg_info`, `build_py`, `build_ext`, `sdist`, and `install_data` commands)
- `data_files`
- `ext_modules`
- `package_dir`
- `package_data`
- `packages`

## `build_ext` Command Options for `cmaketools`-based `setup.py`

The `build_ext` command options are completely changed to accomodate CMake command-line options. Here is the output of `python setup.py --help build_ext`

```bash
Common commands: (see '--help-commands'  for more)
setup.py build will build the package underneath 'build/'
setup.py install will install the package

Global options:
--verbose (-v) run verbosely (default)
--quiet (-q) run quietly (turns verbosity off)
--dry-run (-n) don't actually do anything
--help (-h) show detailed help message
--no-user-cfg ignore pydistutils.cfg in your home directory

Options for 'build_ext' command:
--cmake-path Name/path of the CMake executable to use, overriding
default auto-detection.
--build-lib (-b) directory for compiled extension modules
--inplace (-i) ignore build-lib and put compiled extensions into the
source directory alongside your pure Python modules
--force (-f) forcibly build everything (delete existing
CMakeCache.txt)
--cache (-C) Pre-load a CMake script to populate the cache.
--define (-D) Create or update a CMake CACHE entry (separated by
';')
--undef (-U) Remove matching entries from CMake CACHE.
--generator (-G) Specify a build system generator.
--toolset (-T) Toolset specification for the generator, if supported.
--platform (-A) Specify platform name if supported by generator.
--Wno-dev Suppress developer warnings.
--Wdev Enable developer warnings.
--Werror Make specified warnings into errors: dev or
deprecated.
--Wno-error Make specified warnings not errors.
--Wdeprecated Enable deprecated functionality warnings.
--Wno-deprecated Suppress deprecated functionality warnings.
--log-level Set the log level to one of: ERROR, WARNING, NOTICE,
STATUS, VERBOSE, DEBUG, TRACE
--log-context Enable the message() command outputting context
attached to each message.
--debug-trycompile Do not delete the try_compile() build tree. Only
useful on one try_compile() at a time.
--debug-output Put cmake in a debug mode.
--debug-find Put cmake find commands in a debug mode.
--trace Put cmake in trace mode.
--trace-expand Put cmake in trace mode with variables expanded.
--trace-format Put cmake in trace mode and sets the trace output
format.
--trace-source Put cmake in trace mode, but output only lines of a
specified file.
--trace-redirect Put cmake in trace mode and redirect trace output to a
file instead of stderr.
--warn-uninitialized Specify a build system generator.
--warn-unused-vars Warn about unused variables.
--no-warn-unused-cli Don’t warn about command line options.
--check-system-vars Find problems with variable usage in system files.
--parallel (-j) The maximum number of concurrent processes to use when
building.
--config For multi-configuration tools, choose this
configuration.
--clean-first Build target clean first, then build.
--verbose (-v) Enable verbose output - if supported - including the
build commands to be executed.
--strip Strip before installing.
--help-generator list available compilers

usage: setup.py [global_opts] cmd1 [cmd1_opts] [cmd2 [cmd2_opts] ...]
or: setup.py --help [cmd1 cmd2 ...]
or: setup.py --help-commands
or: setup.py cmd --help
```

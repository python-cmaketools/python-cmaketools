import sys
import multiprocessing
import re
from os import environ, path, name, chdir, makedirs, getcwd, walk, remove
from shutil import which, rmtree
import subprocess as sp
from distutils.version import LooseVersion


def findexe(cmd):
    """Find a CMake executable """
    if which(cmd) is None and name == "nt":
        cmd += ".exe"
        candidates = [
            path.join(environ[var], "CMake", "bin", cmd)
            for var in ("PROGRAMFILES", "PROGRAMFILES(X86)", "APPDATA", "LOCALAPPDATA",)
            if var in environ
        ]
        cmd = next((path for path in candidates if which(path)), None)
    return cmd


def run(*args, path=findexe("cmake"), **runargs):
    """generic cmake execution with its cli arguments in *args and subprocess.run options in **runargs
    
    Returns: subprocess.CompletedProcess.stdout if stderr=False (default) else a tuple
    (subprocess.CompletedProcess.stdout, subprocess.CompletedProcess.stderr,) 
    """
    runargs = {
        "stdout": sp.PIPE,
        "stderr": False,
        "text": True,
        **runargs,
    }
    out = sp.run([path, *args], **runargs)
    return (out.stdout, out.stderr,) if runargs["stderr"] else out.stdout


def validate(cmakePath=findexe("cmake")):
    """Raises FileNotFoundError if cmakePath does not specify a valid cmake executable"""
    min_version = "3.5.0"
    out = sp.run([cmakePath, "--version"], capture_output=True, text=True)
    if not out.check_returncode():
        FileNotFoundError(
            f"CMake file ({cmakePath}) failed to execute with --version argument."
        )
    match = re.match(r"cmake version ([\d.]+)", out.stdout)
    if not match:
        FileNotFoundError(
            f"CMake file ({cmakePath}) failed to provide valid version information."
        )
    cmake_version = LooseVersion(match.group(1))
    if cmake_version < min_version:
        raise FileNotFoundError(f"CMake >= {min_version} is required")


def configured(buildDir):
    """True if CMake project has been configured"""
    return path.isfile(path.join(getcwd(), buildDir, "CMakeCache.txt"))


def clear(buildDir):
    """Clear CMake build directory"""
    for root, dirs, files in walk(buildDir):
        for name in files:
            remove(path.join(root, name))
        for name in dirs:
            rmtree(path.join(root, name))


def configure(
    root_dir,
    build_dir,
    *args,
    build_type="Release",
    cmakePath=findexe("cmake"),
    need_msvc=False,
    **kwargs,
):
    """run cmake to generate a project buildsystem

    Parameters:
    -----------
       root_dir str: Path to root directory of the CMake project to build.
       build_dir str: Path to directory which CMake will use as the root of build directory.

    Arbitrary Args: 
    ---------------
        *args string[]: Additional arguments to be passed onto cmake call 

    Keyword Args:
    ----------
       build_type str: "Debug", {"Release"}, "RelWithDebInfo" and "MinSizeRel"
       cmakePath str: path of cmake executable
       env dict: A mapping that defines the environment variables for the new process
       need_msvc bool: True to create a batch file in Windows to make MSVC compiler available to CMake
    """

    # build cmake arguments
    args = [
        cmakePath,
        *args,
        "-S",
        root_dir,
        "-B",
        build_dir,
        "-D",
        f"CMAKE_BUILD_TYPE:STRING={build_type}",
    ]

    # retrieve env if assigned
    env = kwargs["env"] if "env" in kwargs else None

    # if Windows and G option is specified and its value is "Ninja*", need a BAT file
    if need_msvc:
        # to run Ninja in Windows, cmake must first setup vsvc
        msvc_path = _getvspath()
        if not msvc_path:
            raise FileNotFoundError("Cannot use Ninja because MSVC is not found.")
        args = [_createNinjaBatch(build_dir, msvc_path, args, env)]

    sp.run(args, env=env, check=True).check_returncode()


def _getWorkerCount():
    return max(multiprocessing.cpu_count() - 1, 1)


def build(
    build_dir,
    *args,
    build_type=None,
    parallel=None,
    cmakePath=findexe("cmake"),
    **kwargs,
):
    """run cmake to generate a project buildsystem

    Parameters:
    -----------
       build_dir str: Path to directory which CMake will use as the root of build directory.

    Arbitrary Args: 
    ---------------
        *args string[]: Additional arguments to be passed onto cmake call 

    Keyword Args:
    ----------
       build_type str: "Debug", {"Release"}, "RelWithDebInfo" and "MinSizeRel"
       parallel int: The maximum number of concurrent processes to use when building. Default: 1 less than 
                     the number of available logical cores.
       cmakePath str: path of cmake executable
       env: A mapping that defines the environment variables for the new process
    """

    # build cmake arguments
    args = [
        cmakePath,
        "--build",
        build_dir,
        "-j",
        str(parallel if parallel else _getWorkerCount()),
        *args,
        "--config",
        build_type if build_type else "Release",
    ]

    # retrieve env if assigned
    env = kwargs["env"] if "env" in kwargs else None

    return sp.run(args, env=env).check_returncode()


def install(
    build_dir,
    install_dir,
    *args,
    build_type=None,
    cmakePath=findexe("cmake"),
    **kwargs,
):
    """run cmake to install an already-generated project binary tree

    Parameters:
    ----------
       build_dir str: Path to directory which CMake will use as the root of build directory.
       install_dir str: Override the installation prefix, CMAKE_INSTALL_PREFIX.

    Arbitrary Args: 
    ---------------
        *args string[]: Additional arguments to be passed onto cmake call 

    Keyword Args:
    ----------
       build_type str: "Debug", {"Release"}, "RelWithDebInfo" and "MinSizeRel"
       cmakePath str: path of cmake executable
       env: A mapping that defines the environment variables for the new process

    Keyword Args:
    ----------
       component str: Only install specified component  
       env: A mapping that defines the environment variables for the new process
    """

    # build cmake arguments
    args = [
        cmakePath,
        "--install",
        build_dir,
        "--prefix",
        install_dir if install_dir else "dist",
        *args,
        "--config",
        build_type if build_type else "Release",
    ]

    # add defaults if not specified
    if "component" in kwargs and kwargs["component"]:
        args.append("--component")
        args.append(kwargs["component"])

    # retrieve env if assigned
    env = kwargs["env"] if "env" in kwargs else None

    return sp.run(args, env=env).check_returncode()


def ctest(build_dir, ctestPath=findexe("ctest"), **kwargs):
    """run cmake to generate a project buildsystem

    Parameters:
    ----------
    build_dir str: Location of the CMake build directory

    Keyword Args:
    ----------
       parallel int: The maximum number of concurrent processes to use when building. Default: 1 less than 
                     the number of available logical cores.
       build-config str: Choose configuration to test.
       options seq(str): Sequence of generic arguments. Include preceding dash(es).
       env: A mapping that defines the environment variables for the new process
    """

    # make sure it's a valid path
    if not (ctestPath and which(ctestPath)):
        raise FileNotFoundError("ctest is not found on the local system")

    # prune empty entries
    kwargs = {key: value for key, value in kwargs.items() if value}

    # add defaults if not specified
    if not "parallel" in kwargs:
        kwargs["parallel"] = _getWorkerCount()

    args = [ctestPath]
    env = None
    for key, value in kwargs.items():
        if key in ("parallel", "build-config"):
            args.append(f"--{key}")
            args.append(f"{value}")
        elif key == "options":
            for f in value:
                args.append(f)
        elif key == "env":
            env = value
        else:
            raise KeyError

    return sp.run(args, cwd=build_dir, env=env).check_returncode()


def _getvspath():
    """Use vswhere to obtain VisualStudio path (Windows only)"""
    import vswhere
    return vswhere.find_first(latest=True, products=["*"], prop="installationPath")


def _createNinjaBatch(buildDir, vsPath, cmakeArgs, env):
    """Create Windows batch file for Ninja"""
    if not path.exists(buildDir):
        makedirs(buildDir)
    batpath = path.join(buildDir, "cmake_config.bat")

    is_64bits = sys.maxsize > 2 ** 32
    vsdevcmd_args = [
        f'"{path.join(vsPath,"Common7","Tools","VsDevCmd.bat")}"',
        f"-arch={'amd64' if is_64bits else 'x86'}",
        f"-host_arch={'amd64' if is_64bits else 'x86'}",
    ]

    # put arguments with spaces in double quotes
    cmakeArgs = [(f'"{arg}"' if re.search(r"\s", arg) else arg) for arg in cmakeArgs]

    batfile = open(batpath, "w")
    batfile.write(f'CALL {" ".join(vsdevcmd_args)}\n')
    batfile.write(f'CALL {" ".join(cmakeArgs)}\n')
    batfile.close()
    return batpath


def read_cache(build_dir, vars=None):
    """read CMakeCache.txt file in build_dir"""
    try:
        with open(path.join(build_dir, "CMakeCache.txt")) as f:
            cache = f.read()
        cache_dict = {}
        for line in re.finditer(r"(?!#)(.+?):(.+?)=(.*)", cache):
            v = line[3].upper()
            value = (
                v == "TRUE" or v == "ON" or v == "YES" if line[2] == "BOOL" else line[3]
            )
            if not vars or line[1] in vars:
                cache_dict[line[1]] = value if value else None
        return cache_dict
    except:
        return None


def delete_cache(build_dir):
    """delete CMakeCache.txt file from build_dir"""
    file = path.join(build_dir, "CMakeCache.txt")
    if path.exists(file):
        remove(file)


def get_generators(cmakePath=findexe("cmake"), as_list=False):
    """get available CMake generators
    
    Parameter:
    as_list str: True to return a list of dict of all generators. Each entry
                    consists of 'name', 'desc', and 'default'
    
    Returns: str if as_list==False else dict[]
    """
    match = re.search(r"Generators[\S\s]*", run("--help", path=cmakePath))
    if match:
        result = match[0]
        if as_list:
            result = [
                {
                    "name": re.sub(r"\s+", " ", gen[2].strip()),
                    "default": gen[1] == "*",
                    "multi-arch": gen[2].endswith("[arch]"),
                    "desc": re.sub(r"\s+", " ", gen[3].strip()),
                }
                for gen in re.finditer(
                    r"\n([* ]) (\S.+?) = ([\s\S]+?)(?=\n([* ]) \S)", result
                )
            ]
        else:
            result = "CMake " + result
    else:
        result = [] if as_list else ""

    return result


def get_generator_names(cmakePath=findexe("cmake")):
    """validate generator is among the available CMake generators
    
    Parameter:
    generator str: Generator name to validate
    """

    names = []
    for g in get_generators(cmakePath, True):
        if g["multi-arch"]:
            for m in re.finditer(r'"([^"]+)"', g["desc"]):
                names.append(re.sub(r"\[arch\]", m[1], g["name"]))
        else:
            names.append(g["name"])
    return names


def generator_changed(generator, build_dir="build", cmakePath=findexe("cmake")):
    """Returns True if given generator configurations are different from cache"""

    cfg = read_cache(
        build_dir,
        ["CMAKE_GENERATOR", "CMAKE_GENERATOR_TOOLSET", "CMAKE_GENERATOR_PLATFORM",],
    )

    default = next(g for g in get_generators(cmakePath, True) if g["default"])
    if default["multi-arch"]:
        default["name"] = re.sub(r"\s*\[arch\]\s*", "", default["name"])

    # selected = generator["generator"] if generator["generator"] else

    return cfg and (
        (
            (generator["generator"] if generator["generator"] else default["name"])
            != cfg["CMAKE_GENERATOR"]
        )
        or generator["toolset"] != cfg["CMAKE_GENERATOR_TOOLSET"]
        or generator["platform"] != cfg["CMAKE_GENERATOR_PLATFORM"]
    )

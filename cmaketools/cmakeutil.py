import multiprocessing as mp
import re, logging, subprocess as sp
from os import environ, path, getcwd, walk, remove, name
from shutil import rmtree, which
from setuptools import Extension
from pathlib import Path as _Path

from . import cmakecontrol as runner

_is_win_ = name == "nt"


def find_cmake(cmd=None):
    """Find a CMake executable

    Sets custom cmake path.

    Parameter
    ---------
    cmd : str or None, default=None
        cmake command candidate

    Returns
    -------
    str : Resolved cmake path or None if not found

    """

    if cmd is None:
        cmd = "cmake"

    ok = which(cmd)
    if not ok and _is_win_:
        candidates = [
            path.join(environ[var], "CMake", "bin", "cmake.exe")
            for var in ("PROGRAMFILES", "PROGRAMFILES(X86)", "APPDATA", "LOCALAPPDATA",)
            if var in environ
        ]
        cmd = next((path for path in candidates if which(path)), None)
        if cmd:
            ok = True

    return cmd if ok else None


def is_cmake_build():
    return path.isfile("CMakeLists.txt")


def traverse_cmakelists(root_dir=None, ignore_dirs=None, leaf_pattern=None):
    """Return an iterator yielding subdirectory containing CMakeLists.txt.

    Args:
        root_dir (str, optional): Starting directory for traversal. Defaults to None.
        ignore_dirs (seq<str>, optional): Directories to be excluded from the traversal. Defaults to None.
        leaf_pattern (str, optional): Stop the traversal if matching pattern regexp expression is found in CMakeList.txt. Defaults to None.

    Yields:
        tuple<3>: Contains the name of the current directory and the content of the CMakeLists.txt.
                  If leaf_pattern is specified, 3rd item indicating if the pattern was hit
    """
    if not ignore_dirs:
        ignore_dirs = ()

    dirs = [(root_dir[:-1] if root_dir.endswith("/") else root_dir) if root_dir else ""]
    while True:

        # pop until no more
        try:
            dir = dirs.pop()
        except IndexError:
            break

        logging.debug(f'cmakeutil:traverse_cmakelists:analyzing directory "{dir}"')

        # if on the ignore list, skip
        if dir in ignore_dirs:
            logging.debug(f"cmakeutil:traverse_cmakelists:skipped (in ignore_dirs")
            continue

        # try opening the cmake file
        try:
            with open(f"{dir+'/' if dir else ''}CMakeLists.txt", "r") as f:
                txt = f.read()
        except OSError as err:  # not found, move on
            logging.debug(f"cmakeutil:traverse_cmakelists:no file [{err}]")
            continue

        # remove comments and empty lines
        txt = _remove_comments_and_emptylines(txt)

        # if leaf, stop the traversal on this subtree
        is_leaf = re.match(leaf_pattern, txt) if leaf_pattern else None

        # iteratively output tuple of dir name and its full CMakeLists.txt text
        yield (dir, txt, is_leaf)

        if not is_leaf:
            # look for subdirectories
            for subdir in subdir_iter(txt):
                if dir:
                    subdir = dir + "/" + subdir
                dirs.append(subdir)


def _remove_comments_and_emptylines(txt):
    txt = re.sub(
        r"(?:#\[(?P<equals>=*)\[.*?\](?P=equals)\])|(?:#[^\[].*?(?=\n))", "", txt
    )
    return re.sub(r"^$\n", "", txt, flags=re.MULTILINE)


def subdir_iter(txt):
    for m in re.finditer(
        r'[ \t]*add_subdirectory[ \t]*\("?(.+?)"?[ \t\n\)]', txt, flags=re.IGNORECASE
    ):
        yield m[1]


def subdir_remove(txt, subdir):
    """Scan given CMakeLists.txt text for add_subdirectory command adding subdir

    Args:
        txt (str): Text extracted from CMakeLists.txt
        subdir (str): target subdir

    Returns:
        tuple: 1st element=True if found, 2nd element=possibly modified txt
    """
    pattern = r'[ \t]*add_subdirectory[ \t]*\("?(' + subdir + r')"?[ \t\n\)]'
    matched = next((m for m in re.finditer(pattern, txt, flags=re.IGNORECASE)), None)
    if matched:
        txt = txt[matched.end() :]
        txt = txt[: matched.start()]
    return bool(matched), txt


def dict_to_arg(d):
    """create cmake command argument string from list of arguments

    Each input argument may be a str (non-optional argument), sequence (name-only optional arguments),
    or dict (name-value otpional arugments).

    - Non-optional arguments and option values are checked for space and quoted if space found.
    - Option names receive leading hyphen(s): '-' if one character else '--'

    Attributes:
        str: non-optional argument (will not be modified)
        sequence<str>: name-only option arguments (dashes will be prepended)
        dict<str: str>: name-value option arguments (dashes will be prepended to the names)

    Retruns:
        str : str containing all the arguments separated by space
    """

    def process_one(name, value):
        if not isinstance(value, bool):
            if re.search(r"\s", str(value)):
                value = f'"{value}"'
            return f"{name}={value}"
        elif value:
            return f"{name}"

    return " ".join([process_one(*o) for o in d.items() if o[1] is not None])


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


def _getWorkerCount(reserve=1):
    return max(mp.cpu_count() - reserve, 1)


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


def set_environ_cxxflags(build_dir, **defs):
    """Set CXXFLAGS/CL environmental variable for extra C++ macro definitions"""

    generator = read_cache(build_dir, ["CMAKE_GENERATOR"])["CMAKE_GENERATOR"]
    if not generator:
        raise RuntimeError("{build_dir}{os.sep}CMakeCache.txt not found.")

    envvar = "CL" if generator.startswith("Visual Studio") else "CXXFLAGS"
    env = environ.copy()
    env[envvar] = (
        " ".join(
            [
                f"-D{key}={value}"
                for key, value in [
                    (key, f"{value}" if type(value) == str else value,)
                    for key, value in defs.items()
                ]
            ]
        )
        + " "
        + env.get(envvar, "")
    )

    return env


def _create_extensions(dirs):
    return tuple((Extension(_dir_to_pkg(mod), []) for mod in dirs))


def _dir_to_pkg(pkg_dir, root_pkg=None):
    """Convert relative directory to package name

    Args:
        pkg_dir (str): [description]
        root_pkg (str, optional): [description]. Defaults to "".

    Returns:
        str: [description]
    """
    pkg = "" if pkg_dir == "." else re.sub(r"/", ".", pkg_dir)
    return f"{root_pkg}.{pkg}" if root_pkg else pkg

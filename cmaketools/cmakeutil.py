import re
from distutils import log
from os import environ, mkdir, path, getcwd, walk, remove, name
from shutil import rmtree, which, copyfile

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


def parse_cmakelists(root_dir=None, ignore_dirs=None, leaf_pattern=None):
    """Return an iterator yielding subdirectory containing CMakeLists.txt.

    Args:
        root_dir (str, optional): Starting directory for traversal. Defaults to None.
        ignore_dirs (seq<str>, optional): Directories to be excluded from the traversal. Defaults to None.
        leaf_pattern (str, optional): Stop the traversal if matching pattern regexp expression is found in CMakeList.txt. Defaults to None.

    Yields:
        dict: keys: direcotry path 
              values: the sequence of commands of its CMakeLists.txt
    """
    if not ignore_dirs:
        ignore_dirs = ()

    dirs = [(root_dir[:-1] if root_dir.endswith("/") else root_dir) if root_dir else ""]
    info = {}
    while True:

        # pop until no more
        try:
            dir = dirs.pop()
        except IndexError:
            break

        log.debug(f'cmakeutil:parse_cmakelists:analyzing directory "{dir}"')

        # if on the ignore list, skip
        if dir in ignore_dirs:
            log.debug(f"cmakeutil:parse_cmakelists:skipped (in ignore_dirs")
            continue

        # try opening the cmake file
        try:
            with open(f"{dir+'/' if dir else ''}CMakeLists.txt", "r") as f:
                txt = f.read()
        except OSError as err:  # not found, move on
            log.info(f"cmakeutil:parse_cmakelists:no file [{err}]")
            continue

        # parse the CMake script
        commands = [cmd for cmd in cmakelists_iter(txt)]

        # iteratively output tuple of dir name and its full CMakeLists.txt text
        info[dir] = commands

        if re.match(leaf_pattern, txt) if leaf_pattern else None:
            # if leaf, stop the traversal on this subtree
            log.info(f"cmakeutil:parse_cmakelists:leaf found={dir}")
        else:
            # look for subdirectories
            dirs.extend([cmd[1][0] for cmd in commands if cmd[0] == "add_subdirectory"])

    return info


def search_cmakelists(dirs, pattern):
    """search directories for regexp pattern match in their CMakeList.txt

    Args:
        dirs (seq<str>): list of directories with CMakeList.txt
        pattern (str or re.Pattern): regexp pattern (for re.search())

    Yields:
        (str,re.Match): directory in which the match was found and Match object
    """
    for dir in dirs:
        try:
            with open(f"{dir+'/' if dir else ''}CMakeLists.txt", "r") as f:
                txt = f.read()
        except:
            continue
        if isinstance(pattern, str):
            pattern = re.compile(pattern)
        if m := pattern.search(txt):
            yield (dir, m)


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


def configured(buildDir):
    """True if CMake project has been configured"""
    return path.isfile(path.join(getcwd(), buildDir, "CMakeCache.txt"))


def clear(build_dir, deep=None):
    """Clear CMake build data

    Args:
        build_dir (str): directory where CMake build process take place
        deep (bool, optional): True to delete the entire build directory. Default or False
                               to only remove CMakeCache.txt
    """

    if deep:
        rmtree(build_dir)
        mkdir(build_dir)
    else:
        delete_cache(build_dir)


def read_cache(build_dir, vars=None):
    """read CMakeCache.txt file in build_dir"""
    try:
        with open(path.join(build_dir, "CMakeCache.txt")) as f:
            return f.read()
        # cache_dict = {}
        # for line in re.finditer(r"(?!#)(.+?):(.+?)=(.*)", cache):
        #     v = line[3].upper()
        #     value = (
        #         v == "TRUE" or v == "ON" or v == "YES" if line[2] == "BOOL" else line[3]
        #     )
        #     if not vars or line[1] in vars:
        #         cache_dict[line[1]] = value if value else None
        # return cache_dict
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


install_manifest_filename = "install_manifest.txt"


def log_install(build_dir, dst_dir="."):
    """Save cmake install manifest as .install_manifest.txt

    Args:
        build_dir (str): CMake build directory.
        dst_dir (str, optional): To save the manifest file (.install_manifest.txt) to this directory. Defaults to ".".

    Returns
    -------
        bool : True if saved
    """

    srcfile = path.join(build_dir, install_manifest_filename)
    dstfile = path.join(dst_dir, "." + install_manifest_filename)

    # if the file already exists, append
    if path.isfile(dstfile):
        with open(srcfile, "rt") as f:
            list = f.read()
        with open(dstfile, "at") as f:
            f.write("\n")
            f.write(list)
    else:
        copyfile(srcfile, dstfile)


def uninstall(manifest_path=None):
    """Uninstall CMake installed files and the manifest file

    Args:
        manifest_path (str, optional): File path to the CMake install_manifest.txt. Default path is
        "./.install_manifest.txt". This file gets deleted upon successful completion.
    """

    # default manifest file
    if not manifest_path:
        manifest_path = "." + install_manifest_filename

    try:
        with open(manifest_path, "rt") as f:
            txt = f.read()
    except OSError:
        return  # nothing to do

    try:
        for file in set(txt.splitlines()):
            remove(file)
        remove(manifest_path)
    except:
        raise RuntimeError(
            f"Failed to uninstall the CMake installed files listed in {manifest_path}. "
            + f"Please manually delete the installed files as well as {manifest_path} if exists."
        )


_quote_cont_pattern = re.compile(r"(([\\]){2})*\\\n")
_comment_pattern = re.compile(
    r"[ \t\n\)]*(?:#\[(?P<equals>=*)\[.*?\](?P=equals)\])|^[ \t\n\)]*(?:#[^\[].*?(?=\n))"
)
_cmd_id_pattern = re.compile(r"[ \t\n]*([A-Za-z_][A-Za-z0-9_]*)[ \t]*\([ \t\n]*")
_cmd_barg_pattern = re.compile(r"\[(?P<equals>=*)\[\n?(.*?)\](?P=equals)\][ \t\n^\#]*")
_cmd_qarg_pattern = re.compile(r"\"(.*?)(?:(?:[\\]){2})*(?<![\\])\"[ \t\n^\#]*")
_cmd_args_pattern = re.compile(r"([^\[\"\)\#]+)")
_space_pattern = re.compile(r"[ \t\n]+")


def cmakelists_iter(text):
    """CMakeLists.txt parser

    Args:
        text (str): CMake script

    Yields:
        (str,seq of str): tuple of CMake command identifier str and a sequence of
                   its argument strs
    """
    while text:
        # if comment exists, remove
        if m := _comment_pattern.match(text):
            text = text[m.end() :]

        m = _cmd_id_pattern.match(text)
        if not m:
            return
        identifier = m[1].lower()
        text = text[m.end() :]
        arguments = []
        while text and text[0] != ")":
            if m := _cmd_barg_pattern.match(text):
                # if bracket argument
                arguments.append(m[1])
            elif m := _cmd_qarg_pattern.match(text):
                # if quoted, remove quoted_continuing backslash and subsequent newlines
                arguments.append(_quote_cont_pattern.sub("", m[1]))
            else:
                # get all regular arguments at once
                m = _cmd_args_pattern.match(text)
                arguments.extend(_space_pattern.split(m[1].strip()))
            text = text[m.end() :]

        yield identifier, arguments

        # if comment exists, remove
        if m := _comment_pattern.match(text):
            text = text[m.end() :]

        # trim the closing parenthesis
        if text[0] == ")":
            text = text[1:]


def cmakelists_filter(info, command, args=None):
    out = {}
    for dir, cmd in cmakelists_finditer(info, command, args):
        if dir in out:
            out[dir].append(cmd)
        else:
            out[dir] = [cmd]
    return out

def cmakelists_finditer(info, command, args=None):
    def test_args(this, start):
        if len(this) >= len(start):
            for arg in start:
                if arg not in this:
                    return False
        return True

    for dir, cmds in info.items():
        for cmd in cmds:
            if cmd[0] == command:
                if not args or test_args(cmd[1], args):
                    yield dir, cmd


def find_installed_py_module(info, modules=None, component=None, form="FILES"):
    """Fine py_module to be installed via CMake

    Use modules and component to narrow the search.

    Args:
        info (dict): parsed cmake command blob returned by parse_cmakelists()
        modules (seq of str, optional): names of the module to match
        component (str, optional): specify CMake install component name. Defaults to None.
        form (str, optional): change install form to look. Defaults to "FILES".

    Returns:
        seq: list containing the outcomes for each module. For the i-th module, seq[i] is
        None if no match found or tuple of its component and whether excluded from all or not
    """

    def each_dir(args):
        # match the form is specifed,
        f, *args = args
        if f != form:
            return False

        # find file
        keywords = (
            "TYPE",
            "DESTINATION",
            "PERMISSIONS",
            "CONFIGURATIONS",
            "COMPONENT",
            "RENAME",
            "OPTIONAL",
            "EXCLUDE_FROM_ALL",
        )
        i = next((i for i in range(len(args)) if args[i] in keywords))
        files = args[:i]
        args = args[i:]

        opts = {}
        o = None
        for a in args:
            if a == "PERMISSIONS":
                opts[o] = []
            elif a in keywords:
                o = a
                opts[o] = None
            else:
                opts[o] = a

        # check components
        this_comp = opts.get("COMPONENT", None)
        if component and this_comp != component:
            return False

        # TODO resolve variables in files and destination
        def get_module_match(module):
            mod_parts = module.split(".")
            mod_file = mod_parts[-1] + ".py"
            mod_path = "/".join(mod_parts[1:]) if len(mod_parts) > 1 else "."
            return opts.get("DESTINATION", None) == mod_path and mod_file in files

        return (
            [get_module_match(module) for module in modules],
            this_comp,
            "EXCLUDE_FROM_ALL" in opts,
        )

    return {
        dir: each_dir(cmds[1]) for dir, cmds in cmakelists_filter(info, "install", [form])
    }


def show_generators():
    cmake = find_cmake()
    import subprocess as sp
    out = sp.run((cmake,"--help"),universal_newlines=True,capture_output=True)
    m = re.search(r"\nGenerators\s+",out.stdout)
    if m:
        msg = out.stdout[m.end():]
        msg = re.sub('\n\*([^\n]+)',"\n \g<1>", msg)
        msg = re.sub('\n  Ninja(\s+=)',"\n* Ninja\g<1>", msg)
        print(msg)
    else:
        print("cmake is not available on this computer")


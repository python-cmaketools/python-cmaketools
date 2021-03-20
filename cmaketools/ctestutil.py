import re, subprocess as sp
from shutil import which
from . import cmakerunner as runner
from .cmakeutil import _to_arg_str, _getWorkerCount


def find_ctest(cmd=None):
    ok = which(cmd)
    if not ok:
        cmake = runner.find_cmake(re.sub(r"ctest(\.exe)?$", "cmake", cmd))
        if cmake:
            cmd = re.sub(r"cmake(\.exe)?$", "ctest", cmd)
            ok = which(cmd)
    return cmd if ok else None


def ctest(build_dir, *args, ctest_path=None, **kwargs):
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
    ctest_path = find_ctest(ctest_path)
    if not ctest_path:
        raise FileNotFoundError("ctest is not found on the local system")

    # prune empty entries
    kwargs = {key: value for key, value in kwargs.items() if value}

    # add defaults if not specified
    if not "parallel" in kwargs:
        kwargs["parallel"] = _getWorkerCount()

    args = [ctest_path]
    for key, value in kwargs.items():
        if key in ("parallel", "build-config"):
            args.append(f"--{key}")
            args.append(f"{value}")
        elif key == "options":
            for f in value:
                args.append(f)
        else:
            raise KeyError

    return sp.run(args, cwd=build_dir).check_returncode()

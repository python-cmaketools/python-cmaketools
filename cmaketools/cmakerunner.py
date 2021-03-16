"""
Independent program to run CMake commands entered via stdin

Input Arguments [sys.argv]
--------------------------
[1] cmake_path : str, default=None
        path of the cmake binary. None to auto-detect.

[2] platform : {'Win32','x64','ARM','ARM64'} or None
        Specify target platform if different from the host. Only relevant if using Ninja
        in Windows. Note thet cmake configure run must set the same platform value.
    
[3] git_submodule_status : str or None
        Output of `git submodule status` to checkout specific submodule commits

[4] git_submodule_excludes : sequence of str
        If some git submodules are not needed to build (e.g., used for testing purpose only)
        specify them in this list to save time by not cloning it

"""

import abc
import logging

import os
import sys
import signal
import subprocess as sp
from shutil import which
import re
from collections.abc import Sequence

from . import gitutil

_is_win_ = os.name == "nt"


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
        cmd = "cmake-runner"

    ok = which(cmd)
    if not ok and _is_win_:
        candidates = [
            os.path.join(os.environ[var], "CMake", "bin", "cmake.exe")
            for var in (
                "PROGRAMFILES",
                "PROGRAMFILES(X86)",
                "APPDATA",
                "LOCALAPPDATA",
            )
            if var in os.environ
        ]
        cmd = next((path for path in candidates if which(path)), None)
        if cmd:
            ok = True

    return cmd if ok else None


_cmake_proc_ = _cmake_interrupt_ = None
_cmake_jobs_status_ = (
    []
)  # job0=parse, job1=init, job2+=user; None-incomplete, 0-success, else-fail
_cmake_jobs_completed_ = 0


def start(
    platform=None,
    git_submodule_status=None,
    git_submodule_excludes=tuple(),
    restart=False,
    loglevel="INFO",
):
    """Start the CMake runner process in background

    Parameters
    ----------
    platform : {'Win32','x64','ARM','ARM64'} or None, default=None
        Specify target platform if different from the host. Only relevant if using Ninja
        in Windows. Note thet cmake configure run must set the same platform value.

    git_submodule_status : str or None, default=None
        Output of `git submodule status` to checkout specific submodule commits

    git_submodule_excludes : sequence of str, default=tuple()
        If some git submodules are not needed to build (e.g., used for testing purpose only)
        specify them in this list to save time by not cloning it

    restart : bool, default=False
        Set true to terminate existing CMake runner process first and start a new process.
        Default behavior (`restart=False`) is to raise an Exception

    """

    global _cmake_proc_, _cmake_interrupt_

    if _cmake_proc_:
        if restart:
            logging.info("[cmake] Restarting CMake Runner process...")
            stop()
        else:
            raise RuntimeError("CMake Runner process is already running.")
    else:
        logging.info("[cmake] Starting CMake Runner process...")

    opts = ["--kill-on-error"]
    if platform:
        opts += ("--platform", platform)
    if git_submodule_status:
        opts += ("--git-submodule-status", git_submodule_status)
    if git_submodule_excludes:
        opts += ("--git-submodule-excludes", *git_submodule_status)
    if loglevel:
        opts += ("--log-level", loglevel)

    logging.info(sys.executable)

    _cmake_proc_ = sp.Popen(
        ("python", "-m", "cmaketools.cmakerunner", *opts),
        stdin=sp.PIPE,
        stdout=sp.PIPE,
        bufsize=1,
        encoding="utf-8",
        universal_newlines=True,
        env=os.environ,
        shell=True,
    )

    # first 2 fixed jobs are parse args & initialize
    clear_job_status()  # clear the job status buffer
    _cmake_jobs_status_.append(None)
    _cmake_jobs_status_.append(None)

    # set up the interrupt handler if not already done so
    # def interrupt_handler(sig, frame):
    #     logging.info("Ctrl-C pressed")
    #     if _cmake_proc_:
    #         _cmake_proc_.send_signal(signal.SIGINT)

    # if not _cmake_interrupt_:
    #     _cmake_interrupt_ = signal.signal(signal.SIGINT, interrupt_handler)

    # block
    # if wait(0) != "0\n":
    #     raise RuntimeError("Failed to start CMake Runner process (see the log above)")
    # else:
    #     # wait until it has parsed its arguments
    #     logging.info("[cmake] CMake Runner process started")


def is_running():
    """
    Returns True if CMake runner is currently active
    """

    return _cmake_proc_ is not None and _cmake_proc_.poll() is None


def stop(timeout=5.0):
    """
    Stop the CMake worker process

    Parameter
    ---------
    timeout : float or None
        Timeout for joining the CMake worker process

    """
    global _cmake_proc_, _cmake_jobs_completed_

    # run only if process running
    if _cmake_proc_:
        if not _cmake_proc_.poll():
            # if all jobs were completed, do gentle termination
            _cmake_proc_.terminate()
            try:
                _cmake_proc_.wait(timeout)
            except sp.TimeoutExpired:
                logging.debug(
                    "CMake Runner didn't respond to terminate() trying kill()"
                )
                _cmake_proc_.kill()
                _cmake_proc_.wait()

        # clear the process & job counters
        _cmake_proc_ = None


def enqueue(arg_str):
    """Queue a CMake job

    The job is sent directly to the stdin of the CMake Runner subprocess.

    Parameter
    ---------
    arg_str : str
        CMake command line arguments as a single-line str. Do not include cmake command.

    Returns
    -------
    int : id assigned to the job (unique for a given CMake Runner subprocess)
    """

    if not is_running():
        raise RuntimeError("CMake Runner is not running.")

    id = len(_cmake_jobs_status_)
    if not arg_str.endswith("\n"):
        arg_str += "\n"
    _cmake_proc_.stdin.write(arg_str)
    _cmake_proc_.stdin.flush()

    logging.debug(f"Enqueued Job #{id} to CMake Runner: {arg_str[:-1]}")

    _cmake_jobs_status_.append(None)
    return id


def get_last_job():
    return _cmake_jobs_completed_ - 1 if _cmake_jobs_completed_ > 0 else None


def get_current_job():
    return (
        _cmake_jobs_completed_
        if _cmake_jobs_completed_ < len(_cmake_jobs_status_)
        else None
    )


def get_number_of_jobs(type="all"):
    nall = len(_cmake_jobs_status_)
    return dict(
        all=nall,
        completed=_cmake_jobs_completed_,
        remaining=nall - _cmake_jobs_completed_,
    )[type]


def get_job_status(id=None):
    try:
        return _cmake_jobs_status_[id if id is not None else -1]
    except:
        raise ValueError("Invalid job id")


def clear_job_status():
    global _cmake_jobs_completed_
    _cmake_jobs_status_.clear()
    _cmake_jobs_completed_ = 0


def wait(id=None, timeout=None):
    """Wait till CMake jobs in the queue are processed

    Parameters
    ----------
    id : int or None, default=None
        Wait until the job specified by id is completed OR any job is
        failed. If `id=None` the function blocks until all the job is
        completed

    Returns
    -------
    int : =0 if completed successfully, or !=0 if failed.
    None : if CMake Runner is no longer running and the outcomes of the
           previous run has been cleared
    """

    global _cmake_jobs_completed_

    # validate id
    if id is None:
        id = [len(_cmake_jobs_status_) - 1]  # last job
    elif id < 0 and id >= len(_cmake_jobs_status_):
        raise ValueError(f"Specified job id ({id}) is not valid.")

    # if already completed (or quit) return the status
    if not is_running() or id < _cmake_jobs_completed_:
        return _cmake_jobs_status_[id]

    # wait till all the jobs up to the requested are completed
    ret = 0
    for i in range(_cmake_jobs_completed_, id + 1):
        logging.debug(f"waiting for JOB#{i}")
        rc = _cmake_proc_.stdout.readline()
        _cmake_jobs_completed_ += 1
        ret = _cmake_jobs_status_[i] = int(rc.strip())
        if ret:
            break

    return ret


def runsync(arg_str):
    """Queue a CMake job and wait till its completion

    Parameter
    ---------
    arg_str : str
        CMake command line arguments as a single-line str. Do not include cmake command.
    """

    # queue the job
    id = enqueue(arg_str)

    return wait(id)


###############################################################################

# CMAKE RUNNER MAIN PROCESS
if __name__ == "__main__":

    # def interrupt_handler(sig, frame):
    #     logging.info("Ctrl-C pressed")

    # signal.signal(signal.SIGINT, interrupt_handler)

    if _is_win_:
        from . import vcvarsall

    try:

        import argparse

        class ArgumentParser(argparse.ArgumentParser):
            def error(self, message):
                raise RuntimeError(message)

        class ExtendAction(argparse._AppendAction):
            def __call__(self, parser, namespace, values, option_string=None):
                items = getattr(namespace, self.dest, None)
                items = argparse._copy_items(items)
                items.extend(values)
                setattr(namespace, self.dest, items)

        parser = ArgumentParser(description="CMake Runner")
        parser.add_argument(
            "--cmake-path",
            dest="cmake_path",
            action="store",
            default=None,
            help=f"Path to the CMake executable (only required if not found in the system path or in non-default location)",
        )
        parser.add_argument(
            "--platform",
            dest="platform",
            action="store",
            choices=("Win32", "x64", "ARM", "ARM64"),
            default=None,
            help=f"Specify target platform if different from the host. Only relevant if building with MSVC in Windows. Note thet cmake configure run must set the same platform value.",
        )
        parser.add_argument(
            "--git-submodule-status",
            dest="git_submodule_status",
            action="store",
            default=None,
            help=f"Output of `git submodule status` to checkout specific submodule commits.",
        )
        parser.add_argument(
            "--git-submodule-excludes",
            dest="git_submodule_excludes",
            action=ExtendAction,
            default=[],
            help=f"If some git submodules are not needed to build (e.g., only used for testing) specify them in this list to save time by not cloning it.",
        )
        parser.add_argument(
            "--log-level",
            dest="loglevel",
            action="store",
            default="INFO",
            choices=("CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"),
            help=f"Set the logging level",
        )
        parser.add_argument(
            "--quiet",
            "-q",
            dest="loglevel",
            action="store_const",
            const="NOTSET",
            help=f"no output to screen",
        )
        parser.add_argument(
            "--kill-on-error",
            dest="kill_on_err",
            action="store_true",
            default=False,
            help=f"terminate runner when a CMake call errors out",
        )

        try:
            args = parser.parse_args()
        except Exception as err:
            logging.critical(err)
            sys.stdout.write("-1\n")
            exit()

        # signal successful argument parsing
        sys.stdout.write("0\n")
        sys.stdout.flush()

        cmake_path = args.cmake_path
        platform = args.platform
        git_submodule_status = args.git_submodule_status
        git_submodule_excludes = args.git_submodule_excludes
        kill_on_err = args.kill_on_err

        logging.basicConfig(
            stream=sys.stderr,
            level=args.loglevel,
            format="[%(levelname)8s][cmake-runner] %(message)s",
        )

        logging.info(f"Initializing")

        # resolve/find the cmake path
        cmd = find_cmake(cmake_path)
        assert cmd is not None
        # if cmd!='cmake':
        logging.info(f"CMake found at {cmd}")
        if " " in cmd:
            cmd = f'"{cmd}"'

        # set up os.environ for MSVC
        if _is_win_:
            vcvarsall.run(platform)

        # notify the parent successful initialization
        logging.info(f"Ready to process for CMake jobs")

        # Clone submodule if needed and checkout the commits specified by
        # git_submodule_status (if provided, otherwise checks out the latest)
        gitutil.clone_submodules(git_submodule_status, git_submodule_excludes)

        # done initializing
        sys.stdout.write("0\n")
        sys.stdout.flush()

        while True:
            line = sys.stdin.readline()
            if not line or line == "--quit\n":
                break

            next_args = line.rstrip("\n")

            # run cmake with the given arguments
            logging.info(f"[cmake] {next_args}")

            runargs = {
                "stdout": sys.stderr,
                # "stderr": sp.PIPE,
                # "universal_newlines": True,
                "env": os.environ,
            }

            # put arguments with spaces in double quotes
            rc = sp.run(f"{cmd} {next_args}", **runargs).returncode
            logging.debug(f"CMake returned {rc}")
            sys.stdout.write(f"{rc}\n")
            sys.stdout.flush()

            # kill the loop if started with --kill-on-error option
            if kill_on_err and rc:
                logging.info(f"CMake error encountered...")
                break

        logging.info(f"Terminating")
    except Exception as err:
        logging.error(err)
        sys.stdout.write("-1\n")
        sys.stdout.flush()
    finally:
        pass

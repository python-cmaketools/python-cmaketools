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

import logging

import os
import sys

# import signal
import subprocess as sp

_cmake_proc_ = None
_cmake_jobs_status_ = (
    []
)  # job0=parse, job1=init, job2+=user; None-incomplete, 0-success, else-fail
_cmake_jobs_completed_ = 0

_CMAKE_FIRST_USER_JOB_ = 2


def start(
    restart=False,
    loglevel="INFO",
    generator=None,
    platform=None,
    toolset=None,
    msvc_only_if_no_cl=True,
):
    """Start the CMake runner process in background

    Parameters
    ----------
    git_submodule_excludes : sequence of str, default=tuple()
        If some git submodules are not needed to build (e.g., used for testing purpose only)
        specify them in this list to save time by not cloning it

    restart : bool, default=False
        Set True to terminate existing CMake runner process first and start a new process.
        Default behavior (`restart=False`) is to raise an Exception

    msvc_only_if_no_cl : bool, default=True
        (Windows only) Set True to only run vcvarsall only if "cl" is not recognized command

    generator : str or None, default=None
        Reserved. Currently not used

    platform : {'Win32','x64','ARM','ARM64'} or None, default=None
        (Windows only) Specify target platform if different from the host. Only relevant if
        using Ninja in Windows. Note thet cmake configure run must set the same platform value.

    toolset : str or None, default=None
        Reserved. Currently not used

    """

    global _cmake_proc_

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
    if msvc_only_if_no_cl:
        opts += ("--msvc-only-if-no-cl",)

    opts += ("--log-level", loglevel or logging.getLevelName(logging.root.level))

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

    logging.info("started CMake Runner subprocess")


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
            if (id := get_current_job()) == None or id < _CMAKE_FIRST_USER_JOB_:
                enqueue("--quit")
            else:
                # if all jobs were completed, do gentle termination
                _cmake_proc_.stdin.close()
                _cmake_proc_.terminate()
                try:
                    _cmake_proc_.wait(timeout)
                except sp.TimeoutExpired:
                    logging.debug(
                        "CMake Runner didn't respond to terminate() trying kill()"
                    )
                    _cmake_proc_.kill()
            _cmake_proc_.wait()

        # flush whatever is remaining in stdout buffer
        _cmake_proc_.stdout.flush()

        # clear the process & job counters
        _cmake_proc_ = None

        logging.info("stopped CMake Runner subprocess")


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
    return id - _CMAKE_FIRST_USER_JOB_


def get_last_job():
    return (
        _cmake_jobs_completed_ - _CMAKE_FIRST_USER_JOB_
        if _cmake_jobs_completed_ > 0
        else None
    )


def get_failed_job():
    return next(
        (
            id - _CMAKE_FIRST_USER_JOB_
            for id in range(_cmake_jobs_completed_)
            if _cmake_jobs_status_[id] is not None and _cmake_jobs_status_[id] > 0
        ),
        None,
    )


def get_current_job():
    return (
        _cmake_jobs_completed_ - _CMAKE_FIRST_USER_JOB_
        if _cmake_jobs_completed_ < len(_cmake_jobs_status_)
        else None
    )


def is_idle():
    return bool(get_current_job() == None)


def get_number_of_jobs(type="all"):
    nall = len(_cmake_jobs_status_)
    return max(
        dict(
            all=nall,
            completed=_cmake_jobs_completed_,
            remaining=nall - _cmake_jobs_completed_,
        )[type]
        - _CMAKE_FIRST_USER_JOB_,
        0,
    )


def get_job_status(id=None):
    try:
        return _cmake_jobs_status_[
            id + _CMAKE_FIRST_USER_JOB_ if id is not None else -1
        ]
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
    else:
        id += _CMAKE_FIRST_USER_JOB_
        if id < 0 and id >= len(_cmake_jobs_status_):
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

import cmaketools.cmakerunner as runner
import os
import time
import logging
import sys

logging.basicConfig(stream=sys.stderr, level="DEBUG")


def test_get_cmakebin():
    assert runner.find_cmake() is not None


def test_run_vcvarsall():
    if os.name == "nt":
        keys = (
            "include",
            "lib",
            "libpath",
            "path",
            "VSCMD_ARG_HOST_ARCH",
            "VSCMD_ARG_TGT_ARCH",
        )
        originals = {key: os.environ.get(key, None) for key in keys}

        def check_changed(key):
            assert originals[key] != os.environ[key]

        runner.run_vcvarsall()
        assert os.environ[keys[-2]] == os.environ[keys[-1]]
        (check_changed(key) for key in keys)

        targets = dict(Win32="x86", x64="amd64", ARM="arm", ARM64="arm64")
        for platform in targets.keys():
            runner.run_vcvarsall(platform)
            assert os.environ[keys[-1]] == os.environ[keys[-1]]
            (check_changed(key) for key in keys)


# runner.start(platform='bogus')
runner.start(loglevel = "DEBUG")
logging.info(f"runner is {'running' if runner.is_running() else 'stopped'}")
id = runner.enqueue('--version')
runner.enqueue('--help')

logging.info(f"total number of jobs: {runner.get_number_of_jobs('all')}")

while runner.get_number_of_jobs('remaining'): # last job has not run
    id = runner.get_current_job()
    logging.info(f'runner is running the Job #{id}')

    # Wait for the current job to be completed
    rc = runner.wait(id)

    id = runner.get_last_job()
    logging.info(f'runner completed Job #{id} with exit code: {runner.get_job_status(id)} ({rc})')


runner.stop()

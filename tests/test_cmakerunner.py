import cmaketools.cmakecontrol as runner
import os
import time
import logging
import sys

logging.basicConfig(stream=sys.stderr, level="DEBUG")


def test_run():
    # runner.start(platform='bogus')
    runner.start(platform="Win32",loglevel="DEBUG",git_submodule_excludes=('tests/example',))
    logging.info(f"runner is {'running' if runner.is_running() else 'stopped'}")
    id = runner.enqueue("--version")
    runner.enqueue("--help")

    logging.info(f"total number of jobs: {runner.get_number_of_jobs('all')}")

    while runner.get_number_of_jobs("remaining"):  # last job has not run
        id = runner.get_current_job()
        logging.info(f"runner is running the Job #{id}")

        # Wait for the current job to be completed
        rc = runner.wait(id)

        id = runner.get_last_job()
        logging.info(
            f"runner completed Job #{id} with exit code: {runner.get_job_status(id)} ({rc})"
        )


    runner.stop()

from . import gitutil, cmakeutil

import os, sys, logging, argparse, shutil, shlex
import subprocess as sp

_is_win_ = os.name == "nt"

# CMAKE RUNNER MAIN PROCESS
if __name__ == "__main__":

    # def interrupt_handler(sig, frame):
    #     logging.info("Ctrl-C pressed")

    # signal.signal(signal.SIGINT, interrupt_handler)

    if _is_win_:
        from . import vcvarsall

    try:

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
            "--msvc-only-if-no-cl",
            dest="msvc_only_if_no_cl",
            action="store_true",
            default=False,
            help=f"call vcvarsall only if cl.exe is NOT found.",
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
            logging.critical(f"Parsing failed: {sys.argv} ({err})")
            sys.stdout.write("-1\n")
            exit()

        # signal successful argument parsing
        sys.stdout.write("0\n")
        sys.stdout.flush()

        cmake_path = args.cmake_path
        platform = args.platform
        kill_on_err = args.kill_on_err
        msvc_only_if_no_cl = args.msvc_only_if_no_cl

        logging.basicConfig(
            stream=sys.stderr,
            level=args.loglevel,
            format="[%(levelname)8s][cmake-runner] %(message)s",
        )

        logging.info(f"initializing")

        # resolve/find the cmake path
        cmd = cmakeutil.find_cmake(cmake_path)
        assert cmd is not None
        logging.info(f"CMake found at {cmd}")

        # set up os.environ for MSVC if needed
        if _is_win_ and not (msvc_only_if_no_cl and shutil.which("cl")):
            vcvarsall.run(platform)

        # notify the parent successful initialization
        logging.info(f"Ready to process for CMake jobs")

        # Clone submodule if .gitmodules_status. No action if file not present
        gitutil.clone_submodules()

        # done initializing
        sys.stdout.write("0\n")
        sys.stdout.flush()

        # fixed argument for cmake subprocess.run call
        runargs = {
            "stdout": sys.stderr,
            # "stderr": sp.PIPE,
            # "universal_newlines": True,
            "env": os.environ,
        }

        while True:

            line = sys.stdin.readline()
            if not line or line == "--quit\n":
                break

            next_args = line.rstrip("\n")

            # run cmake with the given arguments
            logging.info(f"[cmake] {next_args}")

            next_args = shlex.split(next_args)
            logging.info(f"next_args:{next_args}")

            # put arguments with spaces in double quotes
            rc = sp.run((cmd, *next_args), **runargs).returncode
            logging.debug(f"CMake returned {rc}")
            sys.stdout.write(f"{rc}\n")
            sys.stdout.flush()

            # kill the loop if started with --kill-on-error option
            if kill_on_err and rc:
                logging.info(f"CMake error encountered...")
                break

        logging.info(f"terminating")
    except Exception as err:
        logging.error(err)
        sys.stdout.write("-1\n")
        sys.stdout.flush()
        
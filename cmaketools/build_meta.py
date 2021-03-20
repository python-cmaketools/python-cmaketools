"""A PEP 517 interface to cmaketools

Previously, when a user or a command line tool (let's call it a "frontend")
needed to make a request of cmaketools to take a certain action, for
example, generating a list of installation requirements, the frontend would
would call "setup.py egg_info" or "setup.py bdist_wheel" on the command line.

PEP 517 defines a different method of interfacing with cmaketools. Rather
than calling "setup.py" directly, the frontend should:

  1. Set the current directory to the directory with a setup.py file
  2. Import this module into a safe python interpreter (one in which
     cmaketools can potentially set global variables or crash hard).
  3. Call one of the functions defined in PEP 517.

What each function does is defined in PEP 517. However, here is a "casual"
definition of the functions (this definition should not be relied on for
bug reports or API stability):

  - `build_wheel`: build a wheel in the folder and return the basename
  - `get_requires_for_build_wheel`: get the `setup_requires` to build
  - `prepare_metadata_for_build_wheel`: get the `install_requires`
  - `build_sdist`: build an sdist in the folder and return the basename
  - `get_requires_for_build_sdist`: get the `setup_requires` to build

Again, this is not a formal definition! Just a "taste" of the module.
"""

import setuptools.build_meta as _build_meta

import io
import os
import tokenize

__all__ = [
    "get_requires_for_build_sdist",
    "get_requires_for_build_wheel",
    "prepare_metadata_for_build_wheel",
    "build_wheel",
    "build_sdist",
    "SetupRequirementsError",
]


SetupRequirementsError = _build_meta.SetupRequirementsError


def _open_setup_script(setup_script):
    if not os.path.exists(setup_script):
        # Supply a default setup.py
        return io.StringIO(u"from cmaketools import setup; setup()")

    return getattr(tokenize, "open", open)(setup_script)


class _BuildMetaBackend(_build_meta._BuildMetaBackend):
    def run_setup(self, setup_script="setup.py"):
        # Note that we can reuse our build directory between calls
        # Correctness comes first, then optimization later
        __file__ = setup_script
        __name__ = "__main__"

        with _open_setup_script(__file__) as f:
            code = f.read().replace(r"\r\n", r"\n")

        exec(compile(code, __file__, "exec"), locals())


# The primary backend
_BACKEND = _BuildMetaBackend()

get_requires_for_build_wheel = _BACKEND.get_requires_for_build_wheel
get_requires_for_build_sdist = _BACKEND.get_requires_for_build_sdist
prepare_metadata_for_build_wheel = _BACKEND.prepare_metadata_for_build_wheel
build_wheel = _BACKEND.build_wheel
build_sdist = _BACKEND.build_sdist

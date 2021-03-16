import cmaketools.vcvarsall as vcvarsall
import os
import time
import logging
import sys

logging.basicConfig(stream=sys.stderr, level="INFO")

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

    vcvarsall.run()
    assert os.environ[keys[-2]] == os.environ[keys[-1]]
    (check_changed(key) for key in keys)

    targets = dict(Win32="x86", x64="amd64", ARM="arm", ARM64="arm64")
    for platform in targets.keys():
        vcvarsall.run(platform)
        assert os.environ[keys[-1]] == os.environ[keys[-1]]
        (check_changed(key) for key in keys)



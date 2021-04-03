import pytest
from cmaketools import cmakeutil
import os
from os import path
from distutils import log

log.set_verbosity(2)# debug


def test_get_cmakebin():
    assert cmakeutil.find_cmake() is not None


root = os.getcwd()

hello_cpp = path.join("tests", "samples", "hello-cpp")


def test_regexps():
    with open(path.join(hello_cpp, "CMakeLists.txt"), "r") as f:
        txt = cmakeutil._remove_comments_and_emptylines(f.read())
        print(txt)
        for subdir in cmakeutil._subdir_iter(txt):
            print(subdir)


@pytest.fixture(scope="function")
def hello_cpp_cwd():
    os.chdir(path.join(root, hello_cpp))
    yield
    os.chdir(root)


# def test_traversal():
os.chdir(path.join(root, hello_cpp))
info = cmakeutil.parse_cmakelists()
print(info)
install_info = cmakeutil.cmakelists_filter(info,'install',['FILES'])
print(install_info)


# with open(path.join(hello_cpp, "CMakeLists.txt"), "r") as f:
#     txt = f.read()

# print(txt)
# for command in cmakeutil.cmakelists_iter(txt):
#     id, args = command
#     print(f"id={id} args={args}")

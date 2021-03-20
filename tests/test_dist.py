from cmaketools.dist import Distribution
import re, os, sys
import pytest


@pytest.fixture(scope="function")
def hello_cpp():
    os.chdir("tests/samples/hello-cpp")
    yield
    os.chdir("../../..")

os.chdir("tests/example")
dist = Distribution({})
dist.parse_config_files()
print("src_dir:", dist.src_dir)
print("ext_module_hint:", dist.ext_module_hint)
print("package_dir:", dist.package_dir)
print("ext_modules:",dist.ext_modules)
dist.run_commands()

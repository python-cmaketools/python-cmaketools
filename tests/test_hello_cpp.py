import cmaketools 
import pytest
import os, logging


@pytest.fixture(scope="function")
def hello_cpp():
    os.chdir("tests/samples/hello-cpp")
    yield
    os.chdir("../../..")

logging.basicConfig(level="INFO")

os.chdir("tests/samples/hello-cpp")
cmaketools.setup()

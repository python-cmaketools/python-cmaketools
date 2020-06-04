import pytest
from os import path, getcwd
import cmakeutil

def test_cpp():
    print("\n\nTesting C++ code...")
    cmakeutil.ctest("build")
    print("\nResuming Python tests...\n")

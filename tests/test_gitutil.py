import pytest
from cmaketools import gitutil
import os
from os import path
import logging

logging.basicConfig(level='DEBUG')

# print(gitutil.find_git())
# print(gitutil.read_config('.gitmodules'))
print(gitutil.capture_submodule_status(['tests/example']))
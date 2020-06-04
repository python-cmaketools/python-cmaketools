import pytest
from mypkg import example_module


class TestClass:
    def test_add(self):
        assert example_module.add(1, 1) == 2

    def test_subtract(self):
        assert example_module.subtract(1, 1) == 0

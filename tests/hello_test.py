import pytest
from mypkg import hello
from mypkg.subpackage.subsubpackage import bye

def test_hello():
    hello.say_hello()

def test_bye():
    bye.say_bye()

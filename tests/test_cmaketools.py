# import pytest

# def test_perform():

    # delete build & dist folders
    # url = 'https://github.com/python-cmaketools/pybind-example.git'

def test_run(virtualenv):
    python_exe_path  = virtualenv.python
    runtime_exe = virtualenv.run("python -c 'import sys; print sys.executable'", capture=True)
    assert runtime_exe == python_exe_path


    setup.py sdist
    setup.py bdist

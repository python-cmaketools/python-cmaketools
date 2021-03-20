import pytest
import pytest_virtualenv

import os, sys
import shutil
import cmaketools
import distutils.debug

distutils.debug.DEBUG = True

print(distutils.debug.DEBUG)

# def test_perform():

# delete build & dist folders
# url = 'https://github.com/python-cmaketools/pybind-example.git'


@pytest.fixture
def pybind_project_venv(virtualenv):
    proj_dir = os.path.join("tests", "example")
    virtualenv.run(("cd", proj_dir))
    yield virtualenv
    shutil.rmtree(os.path.join(proj_dir, "build"), ignore_errors=True)
    shutil.rmtree(os.path.join(proj_dir, "dist"), ignore_errors=True)


# def test_peak_build_ext_opts(pybind_project_venv):
#     opts = cmaketools._peak_build_ext_opts(
#         dict(options=dict(build_ext=dict(test="test")))
#     )
#     expects = {
#         "test": "test",
#         "src_dir": "src",
#         "ext_module_hint": "pybind11_add_module",
#         "has_package_data": "False",
#     }
#     assert (opts[name] == value for name, value in expects.items())


def test_installing(pybind_project_venv):
    print(os.getcwd(), os.path.exists("pyproject.toml"))

    # virtualenv.install_package('pybind_example', installer='pip')
    pybind_project_venv.run("pip install .", capture=True)

    # installed_packages() will return a list of `PackageEntry` objects.
    # assert 'pybind_example' in [i.name for i in virtualenv.installed_packages()]


#     python_exe_path  = virtualenv.python
#     runtime_exe = virtualenv.run("python -c 'import sys; print sys.executable'", capture=True)
#     assert runtime_exe == python_exe_path


# setup.py sdist
# setup.py bdist

# code = 'import cmaketools\ncmaketools.setup()\n'
# exec(compile(code, 'setup.py', 'exec'), locals())

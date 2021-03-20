#! /usr/bin/env python3

from setuptools import setup


with open("README.md", "rt") as f:
    long_description = f.read()

setup(
    name="cmaketools",
    version="0.2.0",
    author="Takeshi (Kesh) Ikuma",
    author_email="tikuma@gmail.com",
    description="Seamless integration of Cmake build system to setuptools/distutils",
    long_description_content_type="text/markdown",
    long_description=long_description,
    license="MIT",
    url="https://github.com/python-cmaketools/python-cmaketools",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Build Tools",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Archiving :: Packaging",
        "Topic :: Utilities",
    ],
    packages=["cmaketools"],
    install_requires=("setuptools>=40.8.0", "wheel", "ninja", 'vswhere; platform_system=="Windows"'),
    test_requires=("pytest", "pytest-virtualenv", "virtualenv"),
)

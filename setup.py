#! /usr/bin/env python3

from setuptools import setup


# read the contents of your README file
from os import path

with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="cmaketools",
    version="0.1.2",
    author="Takeshi (Kesh) Ikuma",
    author_email="tikuma@gmail.com",
    description="Seamless integration of Cmake build system to setuptools/distutils",
    long_description_content_type="text/markdown",
    long_description=long_description,
    license="MIT License",
    url="https://github.com/python-cmaketools/python-cmaketools",
    packages=["cmaketools"],
)

#! /usr/bin/env python

"""CityPY
"""

from setuptools import find_packages, setup
import os


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name="CityPY",
    version="v0.0.1",
    author="RWTH e3d",
    author_email="TODO@e3d.rwth-aachen.de",
    description="Python class for handling CityGML and CityJSON data",
    url="https://gitlab.e3d.rwth-aachen.de/",
    namespace_package=["CityPY"],
    long_description=read("README.md"),
    packages=find_packages(),
    package_dir={"CityPY": "CityPY"},
    install_requires=[
        "numpy",
        "lxml",
        "scipy",
        "shapley"
        ],
)
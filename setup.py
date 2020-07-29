"""
Setup script containing package information such as its name, version, and dependencies.
The 'requirements.txt' file relies on this script to find dependencies.
This scipt makes the project installable although installing it is neither needed nor tested.
"""
from setuptools import find_packages, setup

setup(
    name="imagenet-browser",
    version="0.0.1",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        "flask",
        "flask-restful",
        "flask-sqlalchemy",
        "sqlalchemy",
        "jsonschema",
        "requests",
        "pytest",
        "pytest-cov"
    ]
)

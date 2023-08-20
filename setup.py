# -*- coding: utf-8 -*-

"""
The MIT License (MIT)

Copyright (c) 2023-present Lee-matod

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""
import re

from setuptools import setup

with open("vimanager/__init__.py") as file:
    version = re.search(r"__version__ = \"(\d+\.\d+\.\d(a|b|rc)?)\"", file.read())
    if version is None:
        raise RuntimeError("version is not set")
    version = version.group(1)

if version.endswith(("a", "b", "rc")):
    try:
        import subprocess

        count, _ = subprocess.Popen(
            ["git", "rev-list", "--count", "HEAD"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        ).communicate()
        commit, _ = subprocess.Popen(
            ["git", "rev-parse", "--short", "HEAD"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        ).communicate()
        if count:
            version += count.decode("utf-8").strip()
        if commit:
            version += f"+g{commit.decode('utf-8')}".strip()
    except Exception:
        pass


with open("requirements.txt") as file:
    requirements = file.readlines()

with open("README.md", "r") as file:
    readme = file.read()


setup(
    name="vimanager",
    author="Lee-matod",
    version=version,
    license="MIT",
    description="An unofficial ViMusic CLI that enhances playlist management.",
    long_description=readme,
    long_description_content_type="text/markdown",
    include_package_data=True,
    install_requires=requirements,
    extras_require={"spotify": ["spotdl"]},
    python_requires=">=3.8.0",
    py_modules=["vimanager"],
    packages=["vimanager"],
    entry_points={"console_scripts": ["vimanager = vimanager.main:entrypoint"]},
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Database",
        "Topic :: Terminals",
        "Topic :: Utilities",
        "Typing :: Typed",
    ],
)

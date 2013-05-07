#!/usr/bin/env python

from distutils.core import setup

setup(
    name="python-apt-repo",
    description="Tool for creating and updating apt repositories.",
    author="David Boddie",
    author_email="david.boddie@met.no",
    url="http://www.met.no/",
    version="0.1.0",
    scripts=["python-apt-repo-setup.py"]
    )

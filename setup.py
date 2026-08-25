#!/usr/bin/env python
import os
from setuptools import setup

if os.getenv("PYTDX_CYTHON"):
    from Cython.Build import cythonize
    setup(ext_modules=cythonize(["pytdx/reader/c_gbbq_reader.pyx"]))
else:
    setup()

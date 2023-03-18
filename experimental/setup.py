# -*- coding: utf-8 -*-
from setuptools import setup
from Cython.Build import cythonize

setup(ext_modules=cythonize(sources=["test1.pyx"], libraries=["m"], annotate=True))

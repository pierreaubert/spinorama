# -*- coding: utf-8 -*-
from setuptools import setup
from Cython.Build import cythonize

setup(
    name="c_compute_scores",
    ext_modules=cythonize("c_compute_scores.pyx"),
    zip_safe=False,
)

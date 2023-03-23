# -*- coding: utf-8 -*-
from setuptools import Extension, setup
from Cython.Build import cythonize

extensions = [
    Extension(
        "c_compute_scores",
        ["./c_compute_scores.pyx"],
        define_macros=[("NPY_NO_DEPRECATED_API", "NPY_1_7_API_VERSION")],
    ),
]

setup(
    name="c_compute_scores",
    ext_modules=cythonize(
        extensions,
        compiler_directives={
            "language_level": 3,
            "boundscheck": False,
        },
    ),
    zip_safe=False,
)

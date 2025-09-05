# -*- coding: utf-8 -*-
from setuptools import Extension, setup
from Cython.Build import cythonize
import numpy

extensions = [
    Extension(
        "compute_scores_cython",
        ["./compute_scores_cython.pyx"],
        define_macros=[("NPY_NO_DEPRECATED_API", "NPY_1_7_API_VERSION")],
        include_dirs=[numpy.get_include()],
    ),
]

setup(
    name="compute_scores_cython",
    ext_modules=cythonize(
        extensions,
        compiler_directives={
            "language_level": 3,
            "boundscheck": False,
        },
    ),
    zip_safe=False,
)

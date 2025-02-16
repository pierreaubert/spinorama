# -*- coding: utf-8 -*-
from .noop import remote, init, wait, get, shutdown, is_initialized

__all__ = [
    "get",
    "init",
    "is_initialized",
    "remote",
    "shutdown",
    "wait",
]

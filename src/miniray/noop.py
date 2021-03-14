from functools import wraps
from typing import List, Tuple, Any


def wait(ids: dict, num_returns: int):
    """Emulate ray.wait"""
    print("miniray: wait called")
    return {}, {}


def get(id: int) -> Any:
    """Emulate ray.get"""
    print("miniray: get called")
    return None


class RemoteFunction:
    def __init__(self, function):
        print("miniray: self.__init__  called")
        self._function = function
        self._function_name = self._function.__module__ + "." + self._function.__name__

        @wraps(function)
        def _remote_proxy(*args, **kwargs):
            print("miniray: _remote_proxy called")
            return self._remote(args=args, kwargs=kwargs)

        self.remote = _remote_proxy

    def __call__(self, *args, **kwargs):
        raise TypeError(
            "Remote functions cannot be called directly. Instead "
            f"of running '{self._function_name}()', "
            f"try '{self._function_name}.remote()'."
        )

    def remote(func, num_cpus=1):
        @wraps(func)
        def wrapper(func, *args, **kwargs):
            return func(args=args, kwargs=kwargs)

        return wrapper

    def _remote(self, args=None, kwargs=None):
        print("_remote")


def remote(*args, **kwargs):
    def decorator(function):
        return RemoteFunction(function)

    print("miniray: remote called")
    return decorator


def init():
    return None


def shutdown():
    return None

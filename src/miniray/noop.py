# -*- coding: utf-8 -*-
import inspect
import logging
import random
import string
from functools import wraps

is_initialized: bool = False


# put all the tasks in a queue
global_worker = {"queue": {}, "results": {}}


def flatten_args(signature_parameters, args, kwargs):
    reconstructed_signature = inspect.Signature(parameters=signature_parameters)
    try:
        reconstructed_signature.bind(*args, **kwargs)
    except TypeError as exc:  # capture a friendlier stacktrace
        raise TypeError(str(exc)) from None
    list_args = args
    for keyword, arg in kwargs.items():
        list_args += [keyword, arg]
    return list_args


class RemoteFunction:
    def __init__(self, function):
        self._function = function
        self._function_name = self._function.__module__ + "." + self._function.__name__
        self._function_signature = list(inspect.signature(self._function).parameters.values())

        @wraps(function)
        def _remote_proxy(*args, **kwargs):
            return self._remote(args=args, kwargs=kwargs)

        self.remote = _remote_proxy

    def __call__(self, *args, **kwargs):
        msg = f"Remote functions cannot be called directly. Instead of running '{self._function_name}()', try '{self._function_name}.remote()'."
        raise TypeError(msg)

    def _remote(self, args=None, kwargs=None):
        kwargs = {} if kwargs is None else kwargs
        args = [] if args is None else args
        # unused
        # list_args = flatten_args(self._function_signature, args, kwargs)

        def invocation(function, args, kwargs):
            ref = "".join(
                random.SystemRandom().choice(string.ascii_uppercase + string.digits)
                for _ in range(16)
            )

            global_worker["queue"][ref] = (self._function, args, kwargs)
            return ref

        local_ref = invocation(self._function, args, kwargs)
        return local_ref


def make_decorator():
    def decorator(func):
        if inspect.isfunction(func):
            return RemoteFunction(function=func)
        if inspect.isclass(func):
            raise NotImplementedError
        msg = "remote must be apply to a function or a class."
        raise TypeError(msg)

    return decorator


def remote(*args, **kwargs):
    if len(args) == 1 and len(kwargs) == 0 and callable(args[0]):
        return make_decorator()(args[0])
    return make_decorator()


def wait(ids: dict, num_returns: int):
    """Emulate ray.wait"""

    # for ref, fun_args in global_worker['queue'].items():
    #    print("{} fun_args {}".format(ref, fun_args))

    ready_ids = []
    remaining_ids = []
    for returns, (ref, fun_args) in enumerate(global_worker["queue"].items()):
        func = fun_args[0]
        args = fun_args[1]
        # unused
        # kwargs = fun_args[2]
        results = func(*args)
        global_worker["results"][ref] = results
        ready_ids.append(ref)
        if returns >= num_returns:
            break

    for ref in ready_ids:
        del global_worker["queue"][ref]
    remaining_ids = global_worker["queue"].keys()

    return ready_ids, remaining_ids


def get(id):
    """Emulate ray.get"""
    return global_worker["results"][id]


def init(
    address="172.0.01",
    include_dashboard=True,
    dashboard_host="127.0.0.1",
    dashboard_port=8080,
    local_mode=True,
    configure_logging=True,
    logging_level=logging.INFO,
    log_to_driver=True,
):
    return None


def shutdown():
    return None

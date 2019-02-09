from typing import Callable


class classproperty:
    def __init__(self, func):
        self._func = func

    def __get__(self, obj, owner):
        return self._func(owner)


class CallableWrapper:
    def __init__(self, func: Callable) -> None:
        self.func = func

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

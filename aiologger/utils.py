import sys
from typing import Callable


if sys.version_info >= (3, 7):
    from asyncio import get_running_loop
    from asyncio import create_task
else:
    from asyncio import _get_running_loop

    def get_running_loop():
        loop = _get_running_loop()
        if loop is None:
            raise RuntimeError("no running event loop")
        return loop

    def create_task(coro):
        loop = get_running_loop()
        return loop.create_task(coro)


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


if hasattr(sys, "_getframe"):
    get_current_frame = lambda: sys._getframe(3)
else:  # pragma: no cover

    def get_current_frame():
        """Return the frame object for the caller's stack frame."""
        try:
            raise Exception
        except Exception:
            return sys.exc_info()[2].tb_frame.f_back

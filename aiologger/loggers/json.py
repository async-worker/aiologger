import json
import logging
from datetime import timezone
from asyncio import AbstractEventLoop
from typing import Dict, Iterable, Callable, Tuple, Any, Optional, Awaitable

from aiologger import Logger
from aiologger.formatters.json import ExtendedJsonFormatter
from aiologger.logger import _Caller


class LogRecord(logging.LogRecord):
    def __init__(
        self,
        name,
        level,
        pathname,
        lineno,
        msg,
        args,
        exc_info,
        func=None,
        sinfo=None,
        **kwargs,
    ):
        super().__init__(
            name, level, pathname, lineno, msg, args, exc_info, func, sinfo
        )
        self.extra = kwargs["extra"]
        self.flatten = kwargs["flatten"]
        self.serializer_kwargs = kwargs["serializer_kwargs"]


class JsonLogger(Logger):
    def __init__(
        self,
        name: str = "aiologger-json",
        level: int = logging.DEBUG,
        flatten: bool = False,
        serializer_kwargs: Dict = None,
        extra: Dict = None,
        loop: AbstractEventLoop = None,
    ) -> None:
        super().__init__(name=name, level=level, loop=loop)

        self.flatten = flatten

        if serializer_kwargs is None:
            serializer_kwargs = {}
        self.serializer_kwargs = serializer_kwargs

        if extra is None:
            extra = {}
        self.extra = extra

    @classmethod
    def with_default_handlers(  # type: ignore
        cls,
        *,
        name: str = "aiologger-json",
        level: int = logging.NOTSET,
        serializer: Callable[..., str] = json.dumps,
        flatten: bool = False,
        serializer_kwargs: Dict = None,
        extra: Dict = None,
        exclude_fields: Iterable[str] = None,
        loop: AbstractEventLoop = None,
        tz: timezone = None,
        formatter: Optional[logging.Formatter] = None,
    ):
        if formatter is None:
            formatter = ExtendedJsonFormatter(
                serializer=serializer, exclude_fields=exclude_fields, tz=tz
            )
        return super(JsonLogger, cls).with_default_handlers(
            name=name,
            level=level,
            loop=loop,
            flatten=flatten,
            serializer_kwargs=serializer_kwargs,
            extra=extra,
            formatter=formatter,
        )

    async def _log(  # type: ignore
        self,
        level: int,
        msg: Any,
        args: Tuple,
        exc_info=None,
        extra: Dict = None,
        stack_info=False,
        flatten: bool = False,
        serializer_kwargs: Dict = None,
        caller: _Caller = None,
    ):
        """
        Low-level logging routine which creates a LogRecord and then calls
        all the handlers of this logger to handle the record.

        Overwritten to properly handle log methods kwargs
        """
        sinfo = None
        if caller:
            fn, lno, func, sinfo = caller
        else:  # pragma: no cover
            fn, lno, func = "(unknown file)", 0, "(unknown function)"
        if exc_info and isinstance(exc_info, BaseException):
            exc_info = (type(exc_info), exc_info, exc_info.__traceback__)

        joined_extra = {}
        joined_extra.update(self.extra)

        if extra:
            joined_extra.update(extra)

        record = LogRecord(
            name=self.name,
            level=level,
            pathname=fn,
            lineno=lno,
            msg=msg,
            args=args,
            exc_info=exc_info,
            func=func,
            sinfo=sinfo,
            extra=joined_extra,
            flatten=flatten or self.flatten,
            serializer_kwargs=serializer_kwargs or self.serializer_kwargs,
        )
        await self.handle(record)

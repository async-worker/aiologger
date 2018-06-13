import json
import logging
import sys

from aiologger import Logger
from aiologger.formatters.json import ExtendedJsonFormatter


class LogRecord(logging.LogRecord):
    def __init__(self, name, level, pathname, lineno,
                 msg, args, exc_info, func=None, sinfo=None, **kwargs):
        super().__init__(name, level, pathname, lineno, msg,
                         args, exc_info, func, sinfo)
        self.extra = kwargs['extra']
        self.flatten = kwargs['flatten']
        self.serializer_kwargs = kwargs['serializer_kwargs']


class JsonLogger(Logger):
    def __init__(self,
                 name='aiologger-json',
                 level=logging.DEBUG,
                 serializer=json.dumps,
                 flatten=False,
                 serializer_kwargs=None,
                 extra=None,
                 exclude_fields=None,
                 loop=None):

        super().__init__(name=name, level=level, loop=loop)
        self.serializer = serializer
        self.flatten = flatten
        self.formatter = ExtendedJsonFormatter(self.serializer, exclude_fields)

        if serializer_kwargs is None:
            serializer_kwargs = {}
        self.serializer_kwargs = serializer_kwargs

        if extra is None:
            extra = {}
        self.extra = extra

    @classmethod
    async def with_default_handlers(cls, *,
                                    name='aiologger-json',
                                    level=logging.NOTSET,
                                    loop=None,
                                    serializer=json.dumps,
                                    flatten=False,
                                    serializer_kwargs=None,
                                    extra=None,
                                    exclude_fields=None):
        return await super(JsonLogger, cls).with_default_handlers(
            name='aiologger-json',
            level=level,
            loop=loop,
            serializer=serializer,
            flatten=flatten,
            serializer_kwargs=serializer_kwargs,
            extra=extra,
            exclude_fields=exclude_fields
        )

    def make_log_record(self,
                        level,
                        msg,
                        args,
                        exc_info=None,
                        extra=None,
                        stack_info=False,
                        flatten=False,
                        serializer_kwargs={}):
        sinfo = None
        if logging._srcfile:
            # IronPython doesn't track Python frames, so findCaller raises an
            # exception on some versions of IronPython. We trap it here so that
            # IronPython can use logging.
            try:
                fn, lno, func, sinfo = self.findCaller(stack_info)
            except ValueError:  # pragma: no cover
                fn, lno, func = "(unknown file)", 0, "(unknown function)"
        else:  # pragma: no cover
            fn, lno, func = "(unknown file)", 0, "(unknown function)"
        if exc_info:
            if isinstance(exc_info, BaseException):
                exc_info = (type(exc_info), exc_info, exc_info.__traceback__)
            elif not isinstance(exc_info, tuple):
                exc_info = sys.exc_info()

        joined_extra = {}
        joined_extra.update(self.extra)

        if extra:
            joined_extra.update(extra)

        return LogRecord(
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
            serializer_kwargs=serializer_kwargs or self.serializer_kwargs
        )

    async def _log(self,
                   level,
                   msg,
                   args,
                   exc_info=None,
                   extra=None,
                   stack_info=False,
                   flatten=False,
                   serializer_kwargs={}):
        """
        Low-level logging routine which creates a LogRecord and then calls
        all the handlers of this logger to handle the record.

        Overwritten to properly handle log methods kwargs
        """
        record = self.make_log_record(level, msg, args, exc_info, extra,
                                      stack_info, flatten, serializer_kwargs)
        await self.handle(record)

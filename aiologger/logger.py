import logging
import sys
from aiologger.filters import StdoutFilter
from aiologger.handlers import AsyncStreamHandler
from aiologger.protocols import AiologgerProtocol


class Logger(logging.Logger):
    def __init__(self, *,
                 name='aiologger',
                 level=logging.NOTSET,
                 loop=None):
        super(Logger, self).__init__(name, level)
        self.loop = loop

    @classmethod
    async def with_default_handlers(cls, *,
                                    name='aiologger',
                                    level=logging.NOTSET,
                                    formatter: logging.Formatter=None,
                                    loop=None,
                                    **kwargs):
        self = cls(name=name, level=level, **kwargs)

        formatter = formatter or getattr(self, 'formatter', logging.Formatter())

        stdout_handler = await AsyncStreamHandler.init_from_pipe(
            pipe=sys.stdout,
            level=logging.DEBUG,
            protocol_factory=AiologgerProtocol,
            formatter=formatter,
            filter=StdoutFilter(),
            loop=loop)

        stderr_handler = await AsyncStreamHandler.init_from_pipe(
            pipe=sys.stderr,
            level=logging.WARNING,
            protocol_factory=AiologgerProtocol,
            formatter=formatter,
            loop=loop)

        self.addHandler(stdout_handler)
        self.addHandler(stderr_handler)

        return self

    async def callHandlers(self, record):
        """
        Pass a record to all relevant handlers.

        Loop through all handlers for this logger and its parents in the
        logger hierarchy. If no handler was found, raises an error. Stop
        searching up the hierarchy whenever a logger with the "propagate"
        attribute set to zero is found - that will be the last logger
        whose handlers are called.
        """
        c = self
        found = 0
        while c:
            for handler in c.handlers:
                found = found + 1
                if record.levelno >= handler.level:
                    await handler.handle(record)
            if not c.propagate:
                c = None  # break out
            else:
                c = c.parent
        if found == 0:
            raise Exception("No handlers could be found for logger")

    async def handle(self, record):
        """
        Call the handlers for the specified record.

        This method is used for unpickled records received from a socket, as
        well as those created locally. Logger-level filtering is applied.
        """
        if (not self.disabled) and self.filter(record):
            await self.callHandlers(record)

    def make_log_record(self,
                        level,
                        msg,
                        args,
                        exc_info=None,
                        extra=None,
                        stack_info=False):
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

        return logging.LogRecord(
            name=self.name,
            level=level,
            pathname=fn,
            lineno=lno,
            msg=msg,
            args=args,
            exc_info=exc_info,
            func=func,
            sinfo=sinfo,
            extra=extra
        )

    async def _log(self,
                   level,
                   msg,
                   args,
                   exc_info=None,
                   extra=None,
                   stack_info=False):
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

        record = logging.LogRecord(
            name=self.name,
            level=level,
            pathname=fn,
            lineno=lno,
            msg=msg,
            args=args,
            exc_info=exc_info,
            func=func,
            sinfo=sinfo,
            extra=extra
        )
        await self.handle(record)

    async def debug(self, msg, *args, **kwargs):
        """
        Log msg with severity 'DEBUG'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        await logger.debug("Houston, we have a %s", "thorny problem", exc_info=1)
        """
        if self.isEnabledFor(logging.DEBUG):
            await self._log(logging.DEBUG, msg, args, **kwargs)

    async def info(self, msg, *args, **kwargs):
        """
        Log msg with severity 'INFO'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        await logger.info("Houston, we have an interesting problem", exc_info=1)
        """
        if self.isEnabledFor(logging.INFO):
            await self._log(logging.INFO, msg, args, **kwargs)

    async def warning(self, msg, *args, **kwargs):
        """
        Log msg with severity 'WARNING'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        await logger.warning("Houston, we have a bit of a problem", exc_info=1)
        """
        if self.isEnabledFor(logging.WARNING):
            await self._log(logging.WARNING, msg, args, **kwargs)

    async def error(self, msg, *args, **kwargs):
        """
        Log msg with severity 'ERROR'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        await logger.error("Houston, we have a major problem", exc_info=1)
        """
        if self.isEnabledFor(logging.ERROR):
            await self._log(logging.ERROR, msg, args, **kwargs)

    async def critical(self, msg, *args, **kwargs):
        """
        Log msg with severity 'CRITICAL'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        await logger.critical("Houston, we have a major disaster", exc_info=1)
        """
        if self.isEnabledFor(logging.CRITICAL):
            await self._log(logging.CRITICAL, msg, args, **kwargs)

    async def exception(self, msg, *args, exc_info=True, **kwargs):
        """
        Convenience method for logging an ERROR with exception information.
        """
        await self.error(msg, *args, exc_info=exc_info, **kwargs)

    async def shutdown(self):
        """
        Perform any cleanup actions in the logging system (e.g. flushing
        buffers).

        Should be called at application exit.
        """
        for handler in reversed(self.handlers):
            if not handler:
                continue
            try:
                await handler.flush()
                handler.close()
            except Exception as e :
                """
                Ignore errors which might be caused
                because handlers have been closed but
                references to them are still around at
                application exit. Basically ignore everything, 
                as we're shutting down
                """
                pass

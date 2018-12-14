import asyncio
import logging
import sys
from asyncio import Lock, AbstractEventLoop, Task
from typing import Iterable, Optional, Callable, Awaitable, Tuple

from aiologger.filters import StdoutFilter
from aiologger.handlers import AsyncStreamHandler
from aiologger.protocols import AiologgerProtocol


_Caller = Tuple[str, int, str, Optional[str]]
_HandlerFactory = Callable[[], Awaitable[Iterable[logging.Handler]]]


class Logger(logging.Logger):
    def __init__(self, *,
                 name='aiologger',
                 level=logging.NOTSET,
                 loop=None,
                 formatter: Optional[logging.Formatter] = logging.Formatter,
                 handler_factory: Optional[_HandlerFactory] = None):
        super(Logger, self).__init__(name, level)
        self.loop: AbstractEventLoop = loop or asyncio.get_event_loop()
        self._handler_factory = handler_factory or (lambda: Logger._create_default_handlers(formatter, loop))
        self.initialized = False
        self._initializing = Lock()
        self._initialized = False
        self._was_shutdown = False

        async def _dummy(*args, **kwargs): return
        self.__dummy_task = self.loop.create_task(_dummy())

    @classmethod
    def with_default_handlers(cls, *, name='aiologger',
                              level=logging.NOTSET,
                              formatter: Optional[logging.Formatter] = None,
                              loop=None,
                              **kwargs):
        self = cls(name=name, level=level, loop=loop, formatter=formatter, **kwargs)

        return self

    @classmethod
    async def _create_default_handlers(cls,
                                       formatter: logging.Formatter = None,
                                       loop=None) -> Iterable[logging.Handler]:

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
        return [stdout_handler, stderr_handler]

    async def _initialize(self):
        if not self._initialized:
            async with self._initializing:
                if self._initialized:
                    return
                for handler in await self._handler_factory():
                    self.addHandler(handler)
                self._initialized = True

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
        await self._initialize()

        if (not self.disabled) and self.filter(record):
            await self.callHandlers(record)

    async def _log(self,
                   level,
                   msg,
                   args,
                   exc_info=None,
                   extra=None,
                   stack_info=False,
                   caller: _Caller = None):

        sinfo = None
        if logging._srcfile and caller is None:
            # IronPython doesn't track Python frames, so findCaller raises an
            # exception on some versions of IronPython. We trap it here so that
            # IronPython can use logging.
            try:
                fn, lno, func, sinfo = self.findCaller(stack_info)
            except ValueError:  # pragma: no cover
                fn, lno, func = "(unknown file)", 0, "(unknown function)"
        elif caller:
            fn, lno, func, sinfo = caller
        else:  # pragma: no cover
            fn, lno, func = "(unknown file)", 0, "(unknown function)"
        if exc_info and isinstance(exc_info, BaseException):
            exc_info = (type(exc_info), exc_info, exc_info.__traceback__)

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

    def _make_log_task(self, level, msg, *args, **kwargs) -> Task:
        """
        Creates an asyncio.Task for a msg if logging is enabled for level.
        Returns a dummy task otherwise.
        """
        if not self.isEnabledFor(level):
            return self.__dummy_task

        if kwargs.get('exc_info', False):
            if not isinstance(kwargs['exc_info'], BaseException):
                kwargs['exc_info'] = sys.exc_info()

        coro = self._log(level, msg, *args,
                         caller=self.findCaller(False),
                         **kwargs)
        return self.loop.create_task(coro)

    def debug(self, msg, *args, **kwargs) -> Task:
        """
        Log msg with severity 'DEBUG'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        await logger.debug("Houston, we have a %s", "thorny problem", exc_info=1)
        """
        return self._make_log_task(logging.DEBUG, msg, args, **kwargs)

    def info(self, msg, *args, **kwargs) -> Task:
        """
        Log msg with severity 'INFO'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        await logger.info("Houston, we have an interesting problem", exc_info=1)
        """
        return self._make_log_task(logging.INFO, msg, args, **kwargs)

    def warning(self, msg, *args, **kwargs) -> Task:
        """
        Log msg with severity 'WARNING'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        await logger.warning("Houston, we have a bit of a problem", exc_info=1)
        """
        return self._make_log_task(logging.WARNING, msg, args, **kwargs)

    def error(self, msg, *args, **kwargs) -> Task:
        """
        Log msg with severity 'ERROR'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        await logger.error("Houston, we have a major problem", exc_info=1)
        """
        return self._make_log_task(logging.ERROR, msg, args, **kwargs)

    def critical(self, msg, *args, **kwargs) -> Task:
        """
        Log msg with severity 'CRITICAL'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        await logger.critical("Houston, we have a major disaster", exc_info=1)
        """
        return self._make_log_task(logging.CRITICAL, msg, args, **kwargs)

    def exception(self, msg, *args, exc_info=True, **kwargs) -> Task:
        """
        Convenience method for logging an ERROR with exception information.
        """
        return self.error(msg, *args, exc_info=exc_info, **kwargs)

    async def shutdown(self):
        """
        Perform any cleanup actions in the logging system (e.g. flushing
        buffers).

        Should be called at application exit.
        """
        if self._was_shutdown:
            return
        self._was_shutdown = True

        for handler in reversed(self.handlers):
            if not handler:
                continue
            try:
                if self._initialized:
                    await handler.flush()
                    handler.close()

            except Exception:
                """
                Ignore errors which might be caused
                because handlers have been closed but
                references to them are still around at
                application exit. Basically ignore everything, 
                as we're shutting down
                """
                pass

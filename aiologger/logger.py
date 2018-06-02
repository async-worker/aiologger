import asyncio
import logging
import sys
from asyncio.streams import StreamWriter
from asyncio.unix_events import _set_nonblocking
from io import TextIOBase
from typing import Type, Union

from aiologger.filters import StdoutFilter
from aiologger.protocols import StdoutProtocol, StderrProtocol


class AsyncStreamHandler(logging.StreamHandler):
    @classmethod
    def make(cls,
             level: Union[int, str],
             stream: StreamWriter,
             formatter: logging.Formatter,
             filter: logging.Filter=None) -> 'AsyncStreamHandler':
        self = cls(stream)
        self.setLevel(level)
        self.setFormatter(formatter)

        if filter:
            self.addFilter(filter)

        return self

    async def handleError(self, record: logging.LogRecord):
        """
        Handle errors which occur during an emit() call.

        This method should be called from handlers when an exception is
        encountered during an emit() call. If raiseExceptions is false,
        exceptions get silently ignored. This is what is mostly wanted
        for a logging system - most users will not care about errors in
        the logging system, they are more interested in application errors.
        You could, however, replace this with a custom handler if you wish.
        The record which was being processed is passed in to this method.
        """
        pass  # pragma: no cover

    async def handle(self, record: logging.LogRecord) -> bool:
        """
        Conditionally emit the specified logging record.
        Emission depends on filters which may have been added to the handler.
        """
        rv = self.filter(record)
        if rv:
            await self.emit(record)
        return rv

    async def emit(self, record: logging.LogRecord):
        """
        Actually log the specified logging record to the stream.
        """
        try:
            msg = self.format(record) + self.terminator

            await self.stream.write(msg.encode())
            await self.stream.drain()
        except Exception:
            await self.handleError(record)

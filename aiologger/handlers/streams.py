import asyncio
from asyncio import StreamWriter
from logging import StreamHandler, NOTSET, Formatter, Filter, LogRecord
from typing import Union, Optional

from aiologger.protocols import AiologgerProtocol


class AsyncStreamHandler(StreamHandler):
    def __init__(
        self,
        stream=None,
        level: Union[int, str] = NOTSET,
        formatter: Formatter = None,
        filter: Filter = None,
    ) -> None:
        super().__init__(stream)
        self.setLevel(level)
        if formatter is None:
            formatter = Formatter()
        self.formatter = formatter
        if filter:
            self.addFilter(filter)
        self.protocol_class = AiologgerProtocol
        self._initialization_lock = asyncio.Lock()
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.writer: Optional[StreamWriter] = None

    @property
    def initialized(self):
        return self.writer is not None

    def createLock(self) -> None:
        """
        Does nothing. There's aiologger does not intend to be threadsafe
        """
        self.lock = None

    async def _init_writer(self) -> StreamWriter:
        async with self._initialization_lock:
            if self.writer is not None:
                return self.writer

            self.loop = asyncio.get_event_loop()
            transport, protocol = await self.loop.connect_write_pipe(
                self.protocol_class, self.stream
            )

            self.writer = StreamWriter(  # type: ignore # https://github.com/python/typeshed/pull/2719
                transport=transport,
                protocol=protocol,
                reader=None,
                loop=self.loop,
            )
            return self.writer

    async def handleError(self, record: LogRecord):  # type: ignore
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

    async def handle(self, record: LogRecord) -> bool:  # type: ignore
        """
        Conditionally emit the specified logging record.
        Emission depends on filters which may have been added to the handler.
        """
        rv = self.filter(record)
        if rv:
            await self.emit(record)
        return rv

    async def flush(self):
        await self.writer.drain()

    async def emit(self, record: LogRecord):  # type: ignore
        """
        Actually log the specified logging record to the stream.
        """
        if self.writer is None:
            self.writer = await self._init_writer()

        try:
            msg = self.format(record) + self.terminator

            self.writer.write(msg.encode())
            await self.writer.drain()
        except Exception:
            await self.handleError(record)

    async def close(self):
        """
        Tidy up any resources used by the handler.

        This version removes the handler from an internal map of handlers,
        should ensure that this gets called from overridden close()
        methods.
        """
        if self.writer is None:
            return
        await self.flush()
        self.writer.close()

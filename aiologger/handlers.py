import asyncio
from logging import StreamHandler, Filter, Formatter, LogRecord
from asyncio import StreamWriter
from io import TextIOBase
from typing import Union, Type

from aiologger.protocols import AiologgerProtocol


class AsyncStreamHandler(StreamHandler):
    def __init__(self,
                 stream: StreamWriter,
                 level: Union[int, str],
                 formatter: Formatter,
                 filter: Filter = None):
        super().__init__(stream)
        self.setLevel(level)
        self.setFormatter(formatter)

        if filter:
            self.addFilter(filter)

    @classmethod
    async def init_from_pipe(cls, *,
                             pipe: TextIOBase,
                             level: Union[int, str],
                             formatter: Formatter,
                             filter: Filter = None,
                             protocol_factory: Type[asyncio.Protocol] = None,
                             loop=None) -> 'AsyncStreamHandler':
        if loop is None:
            loop = asyncio.get_event_loop()

        if protocol_factory is None:
            protocol_factory = AiologgerProtocol

        transport, protocol = await loop.connect_write_pipe(protocol_factory,
                                                            pipe)
        stream_writer = StreamWriter(transport=transport,
                                     protocol=protocol,
                                     reader=None,
                                     loop=loop)

        return AsyncStreamHandler(level=level,
                                  stream=stream_writer,
                                  formatter=formatter,
                                  filter=filter)

    async def handleError(self, record: LogRecord):
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

    async def handle(self, record: LogRecord) -> bool:
        """
        Conditionally emit the specified logging record.
        Emission depends on filters which may have been added to the handler.
        """
        rv = self.filter(record)
        if rv:
            await self.emit(record)
        return rv

    async def flush(self):
        await self.stream.drain()

    async def emit(self, record: LogRecord):
        """
        Actually log the specified logging record to the stream.
        """
        try:
            msg = self.format(record) + self.terminator

            await self.stream.write(msg.encode())
            await self.stream.drain()
        except Exception:
            await self.handleError(record)

    def close(self):
        """
        Tidy up any resources used by the handler.

        This version removes the handler from an internal map of handlers,
        _handlers, which is used for handler lookup by name. Subclasses
        should ensure that this gets called from overridden close()
        methods.
        """
        self.stream.close()

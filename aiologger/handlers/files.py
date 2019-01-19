import abc
import asyncio
import os
from logging import Handler, LogRecord

import aiofiles
from aiofiles.threadpool import AsyncTextIOWrapper

from aiologger.handlers.streams import AsyncStreamHandler
from aiologger.utils import classproperty


class AsyncFileHandler(AsyncStreamHandler):
    def __init__(
        self, filename: str, mode: str = "a", encoding: str = None
    ) -> None:
        filename = os.fspath(filename)
        self.absolute_file_path = os.path.abspath(filename)
        self.mode = mode
        self.encoding = encoding
        self.stream: AsyncTextIOWrapper = None
        self._intialization_lock = asyncio.Lock()
        Handler.__init__(self)

    @property
    def initialized(self):
        return self.stream is not None

    async def _init_writer(self):
        """
        Open the current base file with the (original) mode and encoding.
        Return the resulting stream.
        """
        async with self._intialization_lock:
            if not self.initialized:
                self.stream = await aiofiles.open(
                    file=self.absolute_file_path,
                    mode=self.mode,
                    encoding=self.encoding,
                )

    async def close(self):
        if not self.stream:
            return
        if hasattr(self.stream, "flush"):
            await self.stream.flush()
        await self.stream.close()

    async def emit(self, record: LogRecord):  # type: ignore
        if not self.initialized:
            await self._init_writer()

        try:
            msg = self.format(record) + self.terminator
            await self.stream.write(msg)
            await self.stream.flush()
        except Exception as e:
            await self.handleError(record)


Namer = Callable[[str], str]
Rotator = Callable[[str, str], None]


class BaseAsyncRotatingFileHandler(AsyncFileHandler, metaclass=abc.ABCMeta):
    def __init__(
        self,
        filename: str,
        mode: str = "a",
        encoding: str = None,
        namer: Namer = None,
        rotator: Rotator = None,
    ) -> None:
        super().__init__(filename, mode, encoding)
        self.mode = mode
        self.encoding = encoding
        self.namer = namer
        self.rotator = rotator

    def should_rollover(self, record: LogRecord) -> bool:
        raise NotImplementedError

    async def do_rollover(self):
        raise NotImplementedError

    async def emit(self, record: LogRecord):  # type: ignore
        """
        Emit a record.

        Output the record to the file, catering for rollover as described
        in doRollover().
        """
        try:
            if self.should_rollover(record):
                await self.do_rollover()
            await super().emit(record)
        except Exception as e:
            await self.handleError(record)

    def rotation_filename(self, default_name: str) -> str:
        """
        Modify the filename of a log file when rotating.

        This is provided so that a custom filename can be provided.

        :param default_name: The default name for the log file.
        """
        if self.namer is None:
            return default_name

        return self.namer(default_name)

    def rotate(self, source: str, dest: str):
        """
        When rotating, rotate the current log.

        The default implementation calls the 'rotator' attribute of the
        handler, if it's callable, passing the source and dest arguments to
        it. If the attribute isn't callable (the default is None), the source
        is simply renamed to the destination.

        :param source: The source filename. This is normally the base
                       filename, e.g. 'test.log'
        :param dest:   The destination filename. This is normally
                       what the source is rotated to, e.g. 'test.log.1'.
        """
        if self.rotator is None:
            # logging issue 18940: A file may not have been created if delay is True.
            if os.path.exists(source):
                os.rename(source, dest)
        else:
            self.rotator(source, dest)

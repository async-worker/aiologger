import asyncio
import os
from logging import Handler, LogRecord

import aiofiles

from aiologger.handlers.streams import AsyncStreamHandler


class AsyncFileHandler(AsyncStreamHandler):
    def __init__(self, filename: str, mode: str = "a", encoding: str = None):
        filename = os.fspath(filename)
        self.absolute_file_path = os.path.abspath(filename)
        self.mode = mode
        self.encoding = encoding
        self.stream = None
        self._intialization_lock = asyncio.Lock()
        Handler.__init__(self)

    @property
    def initialized(self):
        return self.stream is not None

    async def _init_writer(self):
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

    async def emit(self, record: LogRecord):
        if not self.initialized:
            await self._init_writer()

        try:
            msg = self.format(record) + self.terminator
            await self.stream.write(msg)
            await self.stream.flush()
        except Exception as e:
            await self.handleError(record)
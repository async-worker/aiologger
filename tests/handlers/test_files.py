import asyncio
import datetime
import logging
import os
import sys
import time
from logging import LogRecord
from tempfile import NamedTemporaryFile
from unittest.mock import patch

import asynctest
from aiofiles.threadpool import AsyncTextIOWrapper
from asynctest import CoroutineMock, Mock
from freezegun import freeze_time

from aiologger.handlers.files import (
    AsyncFileHandler,
    BaseAsyncRotatingFileHandler,
    AsyncTimedRotatingFileHandler,
    RotationInverval,
    ONE_WEEK_IN_SECONDS,
    ONE_DAY_IN_SECONDS,
)
from aiologger.handlers.streams import AsyncStreamHandler


class AsyncFileHandlerTests(asynctest.TestCase):
    async def setUp(self):
        self.record = LogRecord(
            name="aiologger",
            level=20,
            pathname="/aiologger/tests/test_logger.py",
            lineno=17,
            msg="Xablau!",
            exc_info=None,
            args=None,
        )
        self.temp_file = NamedTemporaryFile()

    async def tearDown(self):
        patch.stopall()
        self.temp_file.close()

    async def test_initialization(self):
        encoding = "utf-8"
        mode = "x"
        handler = AsyncFileHandler(
            filename=self.temp_file.name, mode=mode, encoding=encoding
        )

        self.assertIsInstance(handler, AsyncStreamHandler)

        self.assertEqual(handler.absolute_file_path, self.temp_file.name)
        self.assertEqual(handler.mode, mode)
        self.assertEqual(handler.encoding, encoding)

        self.assertIsNone(handler.stream)

    async def test_close_closes_the_file(self):
        handler = AsyncFileHandler(filename=self.temp_file.name)

        await handler._init_writer()
        self.assertFalse(handler.stream.closed)

        await handler.close()
        self.assertTrue(handler.stream.closed)

    async def test_emit_writes_log_records_into_the_file(self):
        handler = AsyncFileHandler(filename=self.temp_file.name)

        await handler.emit(self.record)
        await handler.emit(self.record)

        with open(self.temp_file.name) as fp:
            content = fp.read()

        self.assertEqual(content, "Xablau!\nXablau!\n")

    async def test_init_stream_initializes_a_nonblocking_file_writer(self):
        handler = AsyncFileHandler(filename=self.temp_file.name)

        await handler._init_writer()

        self.assertIsInstance(handler.stream, AsyncTextIOWrapper)
        self.assertFalse(handler.stream.closed)
        self.assertEqual(handler.stream._file.name, self.temp_file.name)

    async def test_writer_is_initialized_only_once(self):
        handler = AsyncFileHandler(filename=self.temp_file.name)

        with patch(
            "aiologger.handlers.files.aiofiles.open", CoroutineMock()
        ) as open:
            await asyncio.gather(
                *(handler.emit(self.record) for _ in range(42))
            )
            open.assert_awaited_once()


class BaseAsyncRotatingFileHandlerTests(asynctest.TestCase):
    async def test_rotate_renames_the_source_file_if_a_rotator_isnt_available(
        self
    ):
        temp_file = NamedTemporaryFile()
        handler = BaseAsyncRotatingFileHandler(filename=temp_file.name)
        destination = temp_file.name + "1"

        self.assertTrue(os.path.exists(temp_file.name))
        self.assertFalse(os.path.exists(destination))

        handler.rotate(temp_file.name, destination)

        self.assertFalse(os.path.exists(temp_file.name))
        self.assertTrue(os.path.exists(destination))

    async def test_rotate_calls_the_rotator_if_one_is_avaialble(self):
        temp_file = NamedTemporaryFile()
        handler = BaseAsyncRotatingFileHandler(filename=temp_file.name)
        handler.rotator = Mock()
        destination = temp_file.name + "1"

        handler.rotate(temp_file.name, destination)

        handler.rotator.assert_called_once_with(temp_file.name, destination)

import asyncio
import fcntl
import os
from logging import LogRecord
from tempfile import NamedTemporaryFile
from unittest.mock import Mock, patch

import asynctest
from aiofiles.threadpool import AsyncTextIOWrapper
from asynctest import CoroutineMock

from aiologger.handlers import AsyncStreamHandler, AsyncFileHandler
from aiologger.protocols import AiologgerProtocol


class AsyncStreamHandlerTests(asynctest.TestCase):
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

        r_fileno, w_fileno = os.pipe()
        self.read_pipe = os.fdopen(r_fileno, "r")
        self.write_pipe = os.fdopen(w_fileno, "w")

    def tearDown(self):
        self.read_pipe.close()
        self.write_pipe.close()
        patch.stopall()

    def test_initialization(self):
        level = 666
        stream = Mock()
        formatter = Mock()
        filter = Mock()
        handler = AsyncStreamHandler(stream, level, formatter, filter)

        self.assertIsInstance(handler, AsyncStreamHandler)

        self.assertEqual(handler.level, level)
        self.assertEqual(handler.formatter, formatter)
        self.assertEqual(handler.stream, stream)
        self.assertIn(filter, handler.filters)

    async def test_init_writer_makes_pipe_nonblocking(self):
        flags = fcntl.fcntl(self.write_pipe.fileno(), fcntl.F_GETFL)
        self.assertEqual(flags, 1)
        handler = AsyncStreamHandler(
            stream=self.write_pipe, level=10, formatter=Mock()
        )
        await handler._init_writer()

        flags = fcntl.fcntl(self.write_pipe.fileno(), fcntl.F_GETFL)
        self.assertEqual(flags, 1 | os.O_NONBLOCK)

    async def test_init_writer_initializes_a_nonblocking_pipe_streamwriter(
        self
    ):

        handler = AsyncStreamHandler(
            stream=self.write_pipe, level=10, formatter=Mock()
        )

        self.assertFalse(handler.initialized)

        await handler._init_writer()

        self.assertIsInstance(handler.writer, asyncio.StreamWriter)
        self.assertIsInstance(handler.writer._protocol, AiologgerProtocol)
        self.assertEqual(handler.writer.transport._pipe, self.write_pipe)
        self.assertTrue(handler.initialized)

    async def test_init_writer_gets_the_running_event_loop(self):
        handler = AsyncStreamHandler(
            stream=self.write_pipe, level=10, formatter=Mock()
        )

        self.assertIsNone(handler.loop)

        await handler._init_writer()

        self.assertIsInstance(handler.loop, asyncio.AbstractEventLoop)

    async def test_emit_writes_records_into_the_stream(self):
        msg = self.record.msg
        formatter = Mock(format=Mock(return_value=msg))
        writer = Mock(write=CoroutineMock(), drain=CoroutineMock())

        with patch("aiologger.handlers.StreamWriter", return_value=writer):
            handler = AsyncStreamHandler(
                level=666, stream=self.write_pipe, formatter=formatter
            )

            await handler.emit(self.record)

            writer.write.assert_called_once_with(
                (msg + handler.terminator).encode()
            )
            writer.drain.assert_awaited_once()

    async def test_emit_calls_handleError_if_an_erro_occurs(self):
        writer = Mock(write=CoroutineMock(), drain=CoroutineMock())
        with patch("aiologger.handlers.StreamWriter", return_value=writer):
            handler = AsyncStreamHandler(
                level=666,
                stream=self.write_pipe,
                formatter=Mock(side_effect=Exception),
            )
            with asynctest.patch.object(handler, "handleError") as handleError:
                await handler.emit(self.record)

                handleError.assert_awaited_once_with(self.record)
                writer.write.assert_not_awaited()
                writer.drain.assert_not_awaited()

    async def test_handle_calls_emit_if_a_record_is_loggable(self):
        handler = AsyncStreamHandler(
            level=666, stream=Mock(), formatter=Mock(side_effect=Exception)
        )
        with asynctest.patch.object(handler, "emit") as emit, patch.object(
            handler, "filter", return_value=True
        ) as filter:
            self.assertTrue(await handler.handle(self.record))
            filter.assert_called_once_with(self.record)
            emit.assert_awaited_once_with(self.record)

    async def test_handle_doesnt_calls_emit_if_a_record_isnt_loggable(self):
        handler = AsyncStreamHandler(
            level=666, stream=Mock(), formatter=Mock(side_effect=Exception)
        )
        with asynctest.patch.object(handler, "emit") as emit, patch.object(
            handler, "filter", return_value=False
        ) as filter:
            self.assertFalse(await handler.handle(self.record))
            filter.assert_called_once_with(self.record)
            emit.assert_not_awaited()

    async def test_close_closes_the_underlying_transport(self):
        handler = AsyncStreamHandler(stream=self.write_pipe, level=10)
        await handler._init_writer()
        self.assertFalse(handler.writer.transport.is_closing())
        await handler.close()
        self.assertTrue(handler.writer.transport.is_closing())

    async def test_initialized_returns_true_if_writer_is_initialized(self):
        handler = AsyncStreamHandler(stream=self.write_pipe, level=10)
        self.assertFalse(handler.initialized)
        await handler._init_writer()
        self.assertTrue(handler.initialized)


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

        with patch("aiologger.handlers.aiofiles.open", CoroutineMock()) as open:
            await asyncio.gather(
                *(handler.emit(self.record) for _ in range(42))
            )
            open.assert_awaited_once()

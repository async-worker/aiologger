import asyncio
import inspect
import os
from logging import LogRecord
from typing import Tuple

import asynctest
from unittest.mock import Mock, patch

from asynctest import CoroutineMock

from aiologger.handlers import AsyncStreamHandler
from aiologger.logger import Logger


class LoggerTests(asynctest.TestCase):
    async def setUp(self):
        r_fileno, w_fileno = os.pipe()
        self.read_pipe = os.fdopen(r_fileno, 'r')
        self.write_pipe = os.fdopen(w_fileno, 'w')

        patch('aiologger.logger.sys.stdout', self.write_pipe).start()
        patch('aiologger.logger.sys.stderr', self.write_pipe).start()

        self.stream_reader, self.reader_transport = await self._make_read_pipe_stream_reader()

    def tearDown(self):
        self.read_pipe.close()
        self.write_pipe.close()
        self.reader_transport.close()
        patch.stopall()

    async def _make_read_pipe_stream_reader(self) -> Tuple[asyncio.StreamReader,
                                                           asyncio.ReadTransport]:
        reader = asyncio.StreamReader(loop=self.loop)
        protocol = asyncio.StreamReaderProtocol(reader)

        transport, protocol = await self.loop.connect_read_pipe(lambda: protocol,
                                                                self.read_pipe)
        return reader, transport

    async def test_init_with_default_handlers_initializes_handlers_for_stdout_and_stderr(self):
        handlers = [Mock(), Mock()]
        with asynctest.patch('aiologger.logger.AsyncStreamHandler.init_from_pipe',
                             CoroutineMock(side_effect=handlers)):

            logger = await Logger.with_default_handlers()
            self.assertCountEqual(logger.handlers, handlers)

    async def test_callhandlers_calls_handlers_for_loglevel(self):
        level10_handler = Mock(level=10, handle=CoroutineMock())
        level30_handler = Mock(level=30, handle=CoroutineMock())

        logger = await Logger.with_default_handlers()
        logger.handlers = [level10_handler, level30_handler]

        record = LogRecord(
            level=20,
            name='aiologger',
            pathname="/aiologger/tests/test_logger.py",
            lineno=17,
            msg="Xablau!",
            exc_info=None,
            args=None
        )
        await logger.callHandlers(record)

        level10_handler.handle.assert_awaited_once_with(record)
        level30_handler.handle.assert_not_awaited()

    async def test_it_raises_an_error_if_no_handlers_are_found_for_record(self):
        logger = await Logger.with_default_handlers()
        logger.handlers = []

        record = LogRecord(
            level=10,
            name='aiologger',
            pathname="/aiologger/tests/test_logger.py",
            lineno=17,
            msg="Xablau!",
            exc_info=None,
            args=None
        )
        with self.assertRaises(Exception):
            await logger.callHandlers(record)

    async def test_it_calls_multiple_handlers_if_multiple_handle_matches_are_found_for_record(self):
        level10_handler = Mock(level=10, handle=CoroutineMock())
        level20_handler = Mock(level=20, handle=CoroutineMock())

        logger = await Logger.with_default_handlers()
        logger.handlers = [level10_handler, level20_handler]

        record = LogRecord(
            level=30,
            name='aiologger',
            pathname="/aiologger/tests/test_logger.py",
            lineno=17,
            msg="Xablau!",
            exc_info=None,
            args=None
        )

        await logger.callHandlers(record)

        level10_handler.handle.assert_awaited_once_with(record)
        level20_handler.handle.assert_awaited_once_with(record)

    async def test_it_calls_handlers_if_logger_is_enabled_and_record_is_loggable(self):
        logger = await Logger.with_default_handlers()
        with patch.object(logger, 'filter', return_value=True) as filter, \
             asynctest.patch.object(logger, 'callHandlers') as callHandlers:
            record = Mock()
            await logger.handle(record)

            filter.assert_called_once_with(record)
            callHandlers.assert_awaited_once_with(record)

    async def test_it_doesnt_calls_handlers_if_logger_is_disabled(self):
        logger = await Logger.with_default_handlers()
        with asynctest.patch.object(logger, 'callHandlers') as callHandlers:
            record = Mock()
            logger.disabled = True
            await logger.handle(record)

            callHandlers.assert_not_awaited()

    async def test_it_doesnt_calls_handlers_if_record_isnt_loggable(self):
        logger = await Logger.with_default_handlers()
        with patch.object(logger, 'filter', return_value=False) as filter, \
             asynctest.patch.object(logger, 'callHandlers') as callHandlers:
            record = Mock()
            await logger.handle(record)

            filter.assert_called_once_with(record)
            callHandlers.assert_not_awaited()

    async def test_make_log_record_returns_a_log_record(self):
        logger = await Logger.with_default_handlers()
        record = logger.make_log_record(level=10, msg='Xablau', args=None)

        self.assertIsInstance(record, LogRecord)
        self.assertEqual(record.msg, 'Xablau')
        self.assertEqual(record.levelno, 10)
        self.assertEqual(record.levelname, 'DEBUG')

    async def test_make_log_record_build_exc_info_from_exception(self):
        logger = await Logger.with_default_handlers()
        try:
            raise ValueError("41 isn't the answer")
        except Exception as e:
            record = logger.make_log_record(level=10,
                                            msg='Xablau',
                                            args=None,
                                            exc_info=e)
            exc_class, exc, exc_traceback = record.exc_info
            self.assertEqual(exc_class, ValueError)
            self.assertEqual(exc, e)

    async def test_log_makes_and_handles_a_record(self):
        logger = await Logger.with_default_handlers()
        with asynctest.patch.object(logger, 'handle') as handle, \
             patch.object(logger, 'make_log_record') as make_log_record:

            await logger._log(level=10, msg='Xablau', args=None)
            handle.assert_awaited_once_with(make_log_record.return_value)

    async def test_it_logs_debug_messages(self):
        logger = await Logger.with_default_handlers()
        await logger.debug("Xablau")

        logged_content = await self.stream_reader.readline()
        self.assertEqual(logged_content, b"Xablau\n")

    async def test_it_logs_info_messages(self):
        logger = await Logger.with_default_handlers()
        await logger.info("Xablau")

        logged_content = await self.stream_reader.readline()
        self.assertEqual(logged_content, b"Xablau\n")

    async def test_it_logs_warning_messages(self):
        logger = await Logger.with_default_handlers()
        await logger.warning("Xablau")

        logged_content = await self.stream_reader.readline()
        self.assertEqual(logged_content, b"Xablau\n")

    async def test_it_logs_error_messages(self):
        logger = await Logger.with_default_handlers()
        await logger.error("Xablau")

        logged_content = await self.stream_reader.readline()
        self.assertEqual(logged_content, b"Xablau\n")

    async def test_it_logs_critical_messages(self):
        logger = await Logger.with_default_handlers()
        await logger.critical("Xablau")

        logged_content = await self.stream_reader.readline()
        self.assertEqual(logged_content, b"Xablau\n")

    async def test_it_logs_exception_messages(self):
        logger = await Logger.with_default_handlers()

        try:
            raise Exception('Xablau')
        except Exception:
            await logger.exception("Batemos tambores, eles panela.")

        logged_content = await self.stream_reader.readline()
        self.assertEqual(logged_content, b"Batemos tambores, eles panela.\n")

        while self.stream_reader._buffer:
            logged_content += await self.stream_reader.readline()

        current_func_name = inspect.currentframe().f_code.co_name

        self.assertIn(current_func_name.encode(), logged_content)
        self.assertIn(b"raise Exception('Xablau')", logged_content)

    async def test_shutdown_closes_all_handlers(self):
        logger = Logger()
        logger.handlers = [
            Mock(flush=CoroutineMock()),
            Mock(flush=CoroutineMock())
        ]
        await logger.shutdown()

        for handler in logger.handlers:
            handler.flush.assert_awaited_once()
            handler.close.assert_called_once()

    async def test_shutdown_ignores_erros(self):
        logger = Logger()
        logger.handlers = [
            Mock(flush=CoroutineMock(side_effect=ValueError)),
            Mock(flush=CoroutineMock())
        ]

        await logger.shutdown()

        logger.handlers[0].close.assert_not_called()
        logger.handlers[1].close.assert_called_once()

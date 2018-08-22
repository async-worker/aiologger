import asyncio
import inspect
import logging
import os
from logging import LogRecord
from typing import Tuple
from unittest.mock import Mock, patch

import asynctest
from asynctest import CoroutineMock

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
                             CoroutineMock(side_effect=handlers)) as init_from_pipe:
            logger = Logger.with_default_handlers(loop=self.loop)
            await logger._initialize()
            self.assertCountEqual(logger.handlers, handlers)

            self.assertCountEqual(
                [logging.DEBUG, logging.WARNING],
                [call[1]['level'] for call in init_from_pipe.await_args_list]
            )

    async def test_init_with_default_handlers_initializes_handlers_with_proper_log_levels(
            self):
        handlers = [Mock(), Mock()]
        with asynctest.patch(
                'aiologger.logger.AsyncStreamHandler.init_from_pipe',
                CoroutineMock(side_effect=handlers)) as init_from_pipe:
            logger = Logger.with_default_handlers()
            await logger._initialize()
            self.assertCountEqual(logger.handlers, handlers)

    async def test_callhandlers_calls_handlers_for_loglevel(self):
        level10_handler = Mock(level=10, handle=CoroutineMock())
        level30_handler = Mock(level=30, handle=CoroutineMock())

        logger = Logger.with_default_handlers()
        await logger._initialize()
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
        logger = Logger.with_default_handlers()
        await logger._initialize()
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

        logger = Logger.with_default_handlers()
        await logger._initialize()
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
        logger = Logger.with_default_handlers()
        with patch.object(logger, 'filter', return_value=True) as filter, \
                asynctest.patch.object(logger, 'callHandlers') as callHandlers:
            record = Mock()
            await logger.handle(record)

            filter.assert_called_once_with(record)
            callHandlers.assert_awaited_once_with(record)

    async def test_it_doesnt_calls_handlers_if_logger_is_disabled(self):
        logger = Logger.with_default_handlers()
        with asynctest.patch.object(logger, 'callHandlers') as callHandlers:
            record = Mock()
            logger.disabled = True
            await logger.handle(record)

            callHandlers.assert_not_awaited()

    async def test_it_doesnt_calls_handlers_if_record_isnt_loggable(self):
        logger = Logger.with_default_handlers()
        with patch.object(logger, 'filter', return_value=False) as filter, \
                asynctest.patch.object(logger, 'callHandlers') as callHandlers:
            record = Mock()
            await logger.handle(record)

            filter.assert_called_once_with(record)
            callHandlers.assert_not_awaited()

    async def test_make_log_record_returns_a_log_record(self):
        logger = Logger.with_default_handlers()
        await logger._initialize()
        record = logger.make_log_record(level=10, msg='Xablau', args=None)

        self.assertIsInstance(record, LogRecord)
        self.assertEqual(record.msg, 'Xablau')
        self.assertEqual(record.levelno, 10)
        self.assertEqual(record.levelname, 'DEBUG')

    async def test_log_makes_a_record_with_build_exc_info_from_exception(self):
        logger = Logger.with_default_handlers()
        try:
            raise ValueError("41 isn't the answer")
        except Exception as e:
            with patch.object(logger, 'handle', CoroutineMock()) as handle:
                await logger._log(level=10,
                                  msg='Xablau',
                                  args=None,
                                  exc_info=e)
                call = handle.await_args_list.pop()
                record: LogRecord = call[0][0]
                exc_class, exc, exc_traceback = record.exc_info
                self.assertEqual(exc_class, ValueError)
                self.assertEqual(exc, e)

    async def test_it_logs_debug_messages(self):
        logger = Logger.with_default_handlers()
        await logger.debug("Xablau")

        logged_content = await self.stream_reader.readline()
        self.assertEqual(logged_content, b"Xablau\n")

    async def test_it_logs_info_messages(self):
        logger = Logger.with_default_handlers()
        await logger.info("Xablau")

        logged_content = await self.stream_reader.readline()
        self.assertEqual(logged_content, b"Xablau\n")

    async def test_it_logs_warning_messages(self):
        logger = Logger.with_default_handlers()
        await logger.warning("Xablau")

        logged_content = await self.stream_reader.readline()
        self.assertEqual(logged_content, b"Xablau\n")

    async def test_it_logs_error_messages(self):
        logger = Logger.with_default_handlers()
        await logger.error("Xablau")

        logged_content = await self.stream_reader.readline()
        self.assertEqual(logged_content, b"Xablau\n")

    async def test_it_logs_critical_messages(self):
        logger = Logger.with_default_handlers()
        await logger.critical("Xablau")

        logged_content = await self.stream_reader.readline()
        self.assertEqual(logged_content, b"Xablau\n")

    async def test_it_logs_exception_messages(self):
        logger = Logger.with_default_handlers()

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

    async def test_shutdown_doest_not_closes_handlers_if_not_initialized(self):
        handler_factory = CoroutineMock(return_value=[
            Mock(flush=CoroutineMock()),
            Mock(flush=CoroutineMock())
        ])
        logger = Logger(handler_factory=handler_factory)
        await logger.shutdown()
        handler_factory.assert_not_awaited()
        self.assertCountEqual([], logger.handlers)

    async def test_shutdown_closes_all_handlers_if_initialized(self):
        handlers = [
            Mock(flush=CoroutineMock()),
            Mock(flush=CoroutineMock())
        ]
        logger = Logger(handler_factory=CoroutineMock(return_value=handlers))
        await logger._initialize()

        await logger.shutdown()

        self.assertCountEqual(handlers, logger.handlers)

        for handler in logger.handlers:
            handler.flush.assert_awaited_once()
            handler.close.assert_called_once()

    async def test_shutdown_doest_not_closes_handlers_twice(self):
        handlers = [
            Mock(flush=CoroutineMock()),
            Mock(flush=CoroutineMock())
        ]
        logger = Logger(handler_factory=CoroutineMock(return_value=handlers))
        await logger._initialize()

        await asyncio.gather(logger.shutdown(),
                             logger.shutdown(),
                             logger.shutdown())

        self.assertCountEqual(handlers, logger.handlers)

        for handler in logger.handlers:
            handler.flush.assert_awaited_once()
            handler.close.assert_called_once()

    async def test_shutdown_ignores_erros(self):
        logger = Logger()
        await logger._initialize()
        logger.handlers = [
            Mock(flush=CoroutineMock(side_effect=ValueError)),
            Mock(flush=CoroutineMock())
        ]

        await logger.shutdown()

        logger.handlers[0].close.assert_not_called()
        logger.handlers[1].close.assert_called_once()

    async def test_logger_handlers_are_not_initialized_twice(self):
        condition = asyncio.Condition()
        initialize_meta = {'count': 0}

        async def create_handlers():
            async with condition:
                await condition.wait_for(predicate=lambda: initialize_meta['count'] == 4)

            return await Logger._create_default_handlers()

        handlers_factory = CoroutineMock(side_effect=create_handlers)

        logger = Logger(handler_factory=CoroutineMock(side_effect=handlers_factory))

        original_initialize = logger._initialize

        async def initialize():
            async with condition:
                initialize_meta['count'] += 1
                condition.notify_all()
            await original_initialize()

        patch.object(logger, '_initialize', initialize).start()

        await asyncio.gather(
            logger.info('sardinha'),
            logger.info('tilápia'),
            logger.info('xerelete'),
            logger.error('fraldinha'),
        )

        handlers_factory.assert_called_once()
        await logger.shutdown()

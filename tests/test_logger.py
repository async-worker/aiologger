import asyncio
import fcntl
import os
from logging import LogRecord

import asynctest
from unittest.mock import Mock, patch

from asynctest import CoroutineMock

from aiologger.logger import AsyncStreamHandler, Logger
from aiologger.protocols import AiologgerProtocol


class AsyncStreamHandlerTests(asynctest.TestCase):
    def setUp(self):
        self.record = LogRecord(
            name='aiologger',
            level=20,
            pathname="/aiologger/tests/test_logger.py",
            lineno=17,
            msg="Xablau!",
            exc_info=None,
            args=None
        )

    def test_make_initalizes_a_new_AsyncStreamHandler(self):
        level = 666
        stream = Mock()
        formatter = Mock()
        filter = Mock()
        handler = AsyncStreamHandler.make(level, stream, formatter, filter)

        self.assertIsInstance(handler, AsyncStreamHandler)

        self.assertEqual(handler.level, level)
        self.assertEqual(handler.formatter, formatter)
        self.assertEqual(handler.stream, stream)
        self.assertIn(filter, handler.filters)

    async def test_emit_writes_records_into_the_stream(self):
        msg = self.record.msg
        formatter = Mock(format=Mock(return_value=msg))
        stream = Mock(write=CoroutineMock(), drain=CoroutineMock())

        handler = AsyncStreamHandler.make(level=666,
                                          stream=stream,
                                          formatter=formatter)

        await handler.emit(self.record)

        stream.write.assert_awaited_once_with((msg+handler.terminator).encode())
        stream.drain.assert_awaited_once()

    async def test_emit_calls_handleError_if_an_erro_occurs(self):
        stream = Mock(write=CoroutineMock(), drain=CoroutineMock())
        handler = AsyncStreamHandler.make(level=666,
                                          stream=stream,
                                          formatter=Mock(side_effect=Exception))
        with asynctest.patch.object(handler, 'handleError') as handleError:
            await handler.emit(self.record)

            handleError.assert_awaited_once_with(self.record)
            stream.write.assert_not_awaited()
            stream.drain.assert_not_awaited()

    async def test_handle_calls_emit_if_a_record_is_loggable(self):
        handler = AsyncStreamHandler.make(level=666,
                                          stream=Mock(),
                                          formatter=Mock(side_effect=Exception))
        with asynctest.patch.object(handler, 'emit') as emit, \
             patch.object(handler, 'filter', return_value=True) as filter:

            self.assertTrue(await handler.handle(self.record))
            filter.assert_called_once_with(self.record)
            emit.assert_awaited_once_with(self.record)

    async def test_handle_doesnt_calls_emit_if_a_record_isnt_loggable(self):
        handler = AsyncStreamHandler.make(level=666,
                                          stream=Mock(),
                                          formatter=Mock(side_effect=Exception))
        with asynctest.patch.object(handler, 'emit') as emit, \
                patch.object(handler, 'filter', return_value=False) as filter:
            self.assertFalse(await handler.handle(self.record))
            filter.assert_called_once_with(self.record)
            emit.assert_not_awaited()


class LoggerTests(asynctest.TestCase):
    def setUp(self):
        r_fileno, w_fileno = os.pipe()
        self.read_pipe = os.fdopen(r_fileno, 'r')
        self.write_pipe = os.fdopen(w_fileno, 'w')

        patch('aiologger.logger.sys.stdout', self.write_pipe).start()
        patch('aiologger.logger.sys.stderr', self.write_pipe).start()

    def tearDown(self):
        self.read_pipe.close()
        self.write_pipe.close()
        patch.stopall()

    async def test_init_async_initializes_stream_writers(self):
        with patch.object(Logger, 'make_stream_writer',
                          CoroutineMock()) as make_stream_writer:
            logger = await Logger.init_async()

            self.assertEqual(logger.stdout_writer, make_stream_writer.return_value)
            self.assertEqual(logger.stderr_writer, make_stream_writer.return_value)

    async def test_make_stream_writer_makes_pipe_nonblocking(self):
        flags = fcntl.fcntl(self.write_pipe.fileno(), fcntl.F_GETFL)
        self.assertEqual(flags, 1)

        await Logger.make_stream_writer(
            protocol_factory=AiologgerProtocol,
            pipe=self.write_pipe,
            loop=self.loop
        )

        flags = fcntl.fcntl(self.write_pipe.fileno(), fcntl.F_GETFL)
        self.assertEqual(flags, 1 | os.O_NONBLOCK)

    async def test_make_stream_writer_initializes_a_nonblocking_pipe_streamwriter(self):
        writer = await Logger.make_stream_writer(
            protocol_factory=AiologgerProtocol,
            pipe=self.write_pipe,
            loop=self.loop
        )

        self.assertIsInstance(writer, asyncio.StreamWriter)
        self.assertIsInstance(writer._protocol, AiologgerProtocol)
        self.assertEqual(writer.transport._pipe, self.write_pipe)

    async def test_callhandlers_calls_handlers_for_loglevel(self):
        level10_handler = Mock(level=10, handle=CoroutineMock())
        level30_handler = Mock(level=30, handle=CoroutineMock())

        logger = await Logger.init_async()
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
        logger = await Logger.init_async()
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

        logger = await Logger.init_async()
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
        logger = await Logger.init_async()
        with patch.object(logger, 'filter', return_value=True) as filter, \
             asynctest.patch.object(logger, 'callHandlers') as callHandlers:
            record = Mock()
            await logger.handle(record)

            filter.assert_called_once_with(record)
            callHandlers.assert_awaited_once_with(record)

    async def test_it_doesnt_calls_handlers_if_logger_is_disabled(self):
        logger = await Logger.init_async()
        with asynctest.patch.object(logger, 'callHandlers') as callHandlers:
            record = Mock()
            logger.disabled = True
            await logger.handle(record)

            callHandlers.assert_not_awaited()

    async def test_it_doesnt_calls_handlers_if_record_isnt_loggable(self):
        logger = await Logger.init_async()
        with patch.object(logger, 'filter', return_value=False) as filter, \
                asynctest.patch.object(logger, 'callHandlers') as callHandlers:
            record = Mock()
            await logger.handle(record)

            filter.assert_called_once_with(record)
            callHandlers.assert_not_awaited()

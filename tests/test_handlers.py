import asyncio
import fcntl
import os
from logging import LogRecord
from unittest.mock import Mock, patch

import asynctest
from asynctest import CoroutineMock

from aiologger.handlers import AsyncStreamHandler
from aiologger.protocols import AiologgerProtocol


class AsyncStreamHandlerTests(asynctest.TestCase):
    async def setUp(self):
        self.record = LogRecord(
            name='aiologger',
            level=20,
            pathname="/aiologger/tests/test_logger.py",
            lineno=17,
            msg="Xablau!",
            exc_info=None,
            args=None
        )

        r_fileno, w_fileno = os.pipe()
        self.read_pipe = os.fdopen(r_fileno, 'r')
        self.write_pipe = os.fdopen(w_fileno, 'w')

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

    async def test_init_from_pipe_makes_pipe_nonblocking(self):
        flags = fcntl.fcntl(self.write_pipe.fileno(), fcntl.F_GETFL)
        self.assertEqual(flags, 1)

        await AsyncStreamHandler.init_from_pipe(
            pipe=self.write_pipe,
            level=10,
            formatter=Mock()
        )

        flags = fcntl.fcntl(self.write_pipe.fileno(), fcntl.F_GETFL)
        self.assertEqual(flags, 1 | os.O_NONBLOCK)

    async def test_init_from_pipe_initializes_a_nonblocking_pipe_streamwriter(self):
        handler = await AsyncStreamHandler.init_from_pipe(
            pipe=self.write_pipe,
            level=10,
            formatter=Mock()
        )

        self.assertIsInstance(handler.stream, asyncio.StreamWriter)
        self.assertIsInstance(handler.stream._protocol, AiologgerProtocol)
        self.assertEqual(handler.stream.transport._pipe, self.write_pipe)

    async def test_emit_writes_records_into_the_stream(self):
        msg = self.record.msg
        formatter = Mock(format=Mock(return_value=msg))
        stream = Mock(write=CoroutineMock(), drain=CoroutineMock())

        handler = AsyncStreamHandler(level=666,
                                     stream=stream,
                                     formatter=formatter)

        await handler.emit(self.record)

        stream.write.assert_awaited_once_with((msg+handler.terminator).encode())
        stream.drain.assert_awaited_once()

    async def test_emit_calls_handleError_if_an_erro_occurs(self):
        stream = Mock(write=CoroutineMock(), drain=CoroutineMock())
        handler = AsyncStreamHandler(level=666,
                                     stream=stream,
                                     formatter=Mock(side_effect=Exception))
        with asynctest.patch.object(handler, 'handleError') as handleError:
            await handler.emit(self.record)

            handleError.assert_awaited_once_with(self.record)
            stream.write.assert_not_awaited()
            stream.drain.assert_not_awaited()

    async def test_handle_calls_emit_if_a_record_is_loggable(self):
        handler = AsyncStreamHandler(level=666,
                                     stream=Mock(),
                                     formatter=Mock(side_effect=Exception))
        with asynctest.patch.object(handler, 'emit') as emit, \
                patch.object(handler, 'filter', return_value=True) as filter:

            self.assertTrue(await handler.handle(self.record))
            filter.assert_called_once_with(self.record)
            emit.assert_awaited_once_with(self.record)

    async def test_handle_doesnt_calls_emit_if_a_record_isnt_loggable(self):
        handler = AsyncStreamHandler(level=666,
                                     stream=Mock(),
                                     formatter=Mock(side_effect=Exception))
        with asynctest.patch.object(handler, 'emit') as emit, \
                patch.object(handler, 'filter', return_value=False) as filter:
            self.assertFalse(await handler.handle(self.record))
            filter.assert_called_once_with(self.record)
            emit.assert_not_awaited()

    async def test_close_closes_the_underlying_transport(self):
        handler = await AsyncStreamHandler.init_from_pipe(pipe=self.write_pipe,
                                                          level=10,
                                                          formatter=Mock())
        self.assertFalse(handler.stream.transport.is_closing())
        handler.close()
        self.assertTrue(handler.stream.transport.is_closing())

from logging import LogRecord

import asynctest
from unittest.mock import Mock, patch

from asynctest import CoroutineMock

from aiologger.logger import AsyncStreamHandler


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

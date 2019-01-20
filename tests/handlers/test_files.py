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
    RolloverInterval,
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
    async def setUp(self):
        self.temp_file = NamedTemporaryFile()

    async def tearDown(self):
        self.temp_file.close()
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)

    async def test_rotate_renames_the_source_file_if_a_rotator_isnt_available(
        self
    ):
        handler = BaseAsyncRotatingFileHandler(filename=self.temp_file.name)
        destination = self.temp_file.name + "1"

        self.assertTrue(os.path.exists(self.temp_file.name))
        self.assertFalse(os.path.exists(destination))

        handler.rotate(self.temp_file.name, destination)

        self.assertFalse(os.path.exists(self.temp_file.name))
        self.assertTrue(os.path.exists(destination))

    async def test_rotate_calls_the_rotator_if_one_is_avaialble(self):
        handler = BaseAsyncRotatingFileHandler(filename=self.temp_file.name)
        handler.rotator = Mock()
        destination = self.temp_file.name + "1"

        handler.rotate(self.temp_file.name, destination)

        handler.rotator.assert_called_once_with(
            self.temp_file.name, destination
        )

    async def test_emit_does_rollover_if_should_rollover(self):
        handler = BaseAsyncRotatingFileHandler(filename=self.temp_file.name)
        handler.should_rollover = Mock(return_value=True)

        async def rollover_is_done():
            """
            sleep is needed so that the loop can schedule the other
            `do_rollover` coroutines, simulating a real `do_rollover` behaviour
            """
            await asyncio.sleep(0.1)
            handler.should_rollover.return_value = False

        handler.do_rollover = CoroutineMock(side_effect=rollover_is_done)

        await asyncio.gather(
            *(
                handler.emit(
                    LogRecord(
                        name=str(i),
                        level=20,
                        pathname="/aiologger/tests/test_logger.py",
                        lineno=17,
                        msg="Xablau!",
                        exc_info=None,
                        args=None,
                    )
                )
                for i in range(42)
            )
        )

        handler.do_rollover.assert_awaited_once()


class AsyncTimedRotatingFileHandlerTests(asynctest.TestCase):
    async def setUp(self):
        self.log_record = LogRecord(
            name="aiologger",
            level=20,
            pathname="/aiologger/tests/test_logger.py",
            lineno=17,
            msg="Xablau!",
            exc_info=None,
            args=None,
        )
        self.temp_file = NamedTemporaryFile()
        self.files_to_remove = [self.temp_file.name]

    async def tearDown(self):
        patch.stopall()
        for file_path in self.files_to_remove:
            if os.path.exists(file_path):
                os.unlink(file_path)

    async def test_rollover(self):
        handler = AsyncTimedRotatingFileHandler(
            filename=self.temp_file.name,
            when=RolloverInterval.SECONDS,
            backup_count=1,
        )
        formatter = logging.Formatter("%(asctime)s %(message)s")
        handler.formatter = formatter
        r1 = logging.makeLogRecord({"msg": "testing - initial"})
        await handler.emit(r1)
        self.assertTrue(os.path.exists(self.temp_file.name))

        await asyncio.sleep(1.1)

        r2 = logging.makeLogRecord({"msg": "testing - after delay"})
        await handler.emit(r2)
        await handler.close()
        # At this point, we should have a recent rotated file which we
        # can test for the existence of. However, in practice, on some
        # machines which run really slowly, we don't know how far back
        # in time to go to look for the log file. So, we go back a fair
        # bit, and stop as soon as we see a rotated file. In theory this
        # could of course still fail, but the chances are lower.
        found = False
        now = datetime.datetime.now()
        GO_BACK = 5 * 60  # seconds
        for secs in range(GO_BACK):
            prev = now - datetime.timedelta(seconds=secs)
            fn = self.temp_file.name + prev.strftime(".%Y-%m-%d_%H-%M-%S")
            found = os.path.exists(fn)
            if found:
                self.files_to_remove.append(fn)
                break

        if not found:
            # todo : remove
            # print additional diagnostics
            dn, fn = os.path.split(self.temp_file.name)
            files = [f for f in os.listdir(dn) if f.startswith(fn)]
            print(
                "Test time: %s" % now.strftime("%Y-%m-%d %H-%M-%S"),
                file=sys.stderr,
            )
            print("The only matching files are: %s" % files, file=sys.stderr)
            for f in files:
                print("Contents of %s:" % f)
                path = os.path.join(dn, f)
                with open(path, "r") as tf:
                    print(tf.read())
        self.assertTrue(
            found, msg=f"No rotated files found, went back {GO_BACK} seconds"
        )

    async def test_invalid_rotation_interval(self):
        for invalid_interval in ("X", "W", "W7", "Xablau"):
            with self.assertRaises(ValueError):
                AsyncTimedRotatingFileHandler(
                    filename=self.temp_file.name, when=invalid_interval
                )

    async def test_compute_rollover_daily_attime(self):
        current_time = 0
        at_time = datetime.time(12, 0, 0)
        handler = AsyncTimedRotatingFileHandler(
            self.temp_file.name,
            when=RolloverInterval.MIDNIGHT,
            interval=1,
            backup_count=0,
            utc=True,
            at_time=at_time,
        )
        try:
            actual = handler.compute_rollover(current_time)
            self.assertEqual(actual, current_time + 12 * 60 * 60)

            actual = handler.compute_rollover(current_time + 13 * 60 * 60)
            self.assertEqual(actual, current_time + 36 * 60 * 60)
        finally:
            await handler.close()

    async def test_compute_rollover_weekly_attime(self):
        current_time = int(time.time())
        today = current_time - current_time % 86400

        at_time = datetime.time(12, 0, 0)

        week_day = time.gmtime(today).tm_wday
        for day, interval in enumerate(RolloverInterval.WEEK_DAYS):
            handler = AsyncTimedRotatingFileHandler(
                filename=self.temp_file.name,
                when=interval,
                interval=1,
                backup_count=0,
                utc=True,
                at_time=at_time,
            )
            try:
                if week_day > day:
                    # The rollover day has already passed this week, so we
                    # go over into next week
                    expected = 7 - week_day + day
                else:
                    expected = day - week_day
                # At this point expected is in days from now, convert to seconds
                expected *= ONE_DAY_IN_SECONDS
                # Add in the rollover time
                expected += 12 * 60 * 60
                # Add in adjustment for today
                expected += today
                actual = handler.compute_rollover(today)
                self.assertEqual(
                    actual, expected, msg=f"failed in timezone: {time.timezone}"
                )

                if day == week_day:
                    # goes into following week
                    expected += ONE_WEEK_IN_SECONDS

                actual = handler.compute_rollover(today + 13 * 60 * 60)
                self.assertEqual(
                    actual, expected, msg=f"failed in timezone: {time.timezone}"
                )
            finally:
                await handler.close()

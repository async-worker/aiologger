import asyncio
import json
import inspect
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Tuple
from unittest.mock import Mock, patch
import time

import asynctest

from aiologger.loggers.json import JsonLogger
from aiologger.formatters.json import FUNCTION_NAME_FIELDNAME, \
    LOG_LEVEL_FIELDNAME, DATETIME_FORMAT
from freezegun import freeze_time

class JsonLoggerTests(asynctest.TestCase):
    async def setUp(self):
        r_fileno, w_fileno = os.pipe()
        self.read_pipe = os.fdopen(r_fileno, 'r')
        self.write_pipe = os.fdopen(w_fileno, 'w')

        patch('aiologger.logger.sys.stdout', self.write_pipe).start()
        patch('aiologger.logger.sys.stderr', self.write_pipe).start()

        self.stream_reader, self.reader_transport = await self._make_read_pipe_stream_reader()
        self.logger = await JsonLogger.with_default_handlers(level=logging.DEBUG)

    async def tearDown(self):
        # self.read_pipe.close()
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

    async def test_it_logs_valid_json_string_if_message_is_json_serializeable(self):
        message = {
            'info': 'Se tem permissao, tamo dando sarrada',
            'msg': {
                'foo': 'bar',
                'baz': 'blu'
            }
        }

        await self.logger.error(message)

        logged_content = await self.stream_reader.readline()
        json_log = json.loads(logged_content)

        self.assertDictEqual(json_log['msg'], message)

    async def test_it_logs_valid_json_string_if_message_isnt_json_serializeable(self):
        class FooJsonUnserializeable:
            pass

        obj = FooJsonUnserializeable()
        message = {'info': obj}
        await self.logger.error(message)

        logged_content = await self.stream_reader.readline()
        json_log = json.loads(logged_content)

        self.assertDictEqual(json_log['msg'], {'info': str(obj)})

    async def test_it_escapes_strings(self):
        message = """"Aaaalgma coisa"paando `bem por'/\t \\" \" \' \n "aaa """

        await self.logger.error(message)

        logged_content = await self.stream_reader.readline()
        json_log = json.loads(logged_content)

        self.assertEqual(json_log['msg'], message)

    @freeze_time("2017-03-31T04:20:00-06:00")
    async def test_it_logs_current_log_time(self):
        now = datetime.now(tz=timezone.utc).astimezone().isoformat()

        await self.logger.error("Batemos tambores, eles panela.")

        logged_content = await self.stream_reader.readline()
        json_log = json.loads(logged_content)

        self.assertEqual(json_log['logged_at'], now)

    @freeze_time("2017-03-31T04:20:00-05:00")
    async def test_it_logs_time_at_desired_tz(self):
        desired_tz = timezone(timedelta(hours=-1))
        now = datetime.now(tz=timezone.utc).astimezone(desired_tz).isoformat()


        logger = await JsonLogger.with_default_handlers(level=logging.DEBUG, tz=desired_tz)
        await logger.error("Batemos tambores, eles panela.")

        logged_content = await self.stream_reader.readline()
        json_log = json.loads(logged_content)

        self.assertEqual(json_log['logged_at'], now)

    async def test_it_logs_current_function_name(self):
        await self.logger.error("Batemos tambores, eles panela.")

        logged_content = await self.stream_reader.readline()
        json_log = json.loads(logged_content)
        self.assertEqual(json_log['function'],
                         'test_it_logs_current_function_name')

    async def test_it_logs_exceptions_tracebacks(self):
        exception_message = "Carros importados pra garantir os translados"

        try:
            raise Exception(exception_message)
        except Exception:
            await self.logger.exception("Aqui nao eh GTA, eh pior, eh Grajau")

        logged_content = await self.stream_reader.readline()
        json_log = json.loads(logged_content)

        exc_class, exc_message, exc_traceback = json_log['exc_info']
        self.assertEqual(f"Exception: Exception('{exception_message}',)", exc_message)

        current_func_name = inspect.currentframe().f_code.co_name
        self.assertIn(current_func_name, exc_traceback[0])
        self.assertIn('raise Exception(exception_message)', exc_traceback[1])

    async def test_it_logs_datetime_objects(self):
        message = {
            'date': datetime.now().date(),
            'time': datetime.now().time(),
            'datetime': datetime.now()
        }

        await self.logger.error(message)

        logged_content = await self.stream_reader.readline()
        json_log = json.loads(logged_content)

        expected_output = {
            'date': message['date'].isoformat(),
            'time': message['time'].isoformat(),
            'datetime': message['datetime'].strftime(DATETIME_FORMAT)
        }
        self.assertDictEqual(json_log['msg'], expected_output)

    async def test_extra_param_adds_content_to_document_root(self):
        extra = {
            'artist': "Joanne Shaw Taylor",
            'song': 'Wild is the wind'
        }

        await self.logger.info("Music", extra=extra)
        logged_content = json.loads(await self.stream_reader.readline())

        self.assertDictContainsSubset(extra, logged_content)

    async def test_flatten_param_adds_message_to_document_root(self):
        message = {
            'artist': 'Dave Meniketti',
            'song': 'Loan me a dime'
        }
        await self.logger.info(message, flatten=True)
        logged_content = json.loads(await self.stream_reader.readline())

        self.assertDictContainsSubset(message, logged_content)

    async def test_flatten_method_parameter_overwrites_default_attributes(self):
        message = {'logged_at': 'Yesterday'}

        await self.logger.info(message, flatten=True)
        logged_content = json.loads(await self.stream_reader.readline())

        self.assertEqual(message['logged_at'], logged_content['logged_at'])

    async def test_flatten_method_parameter_does_nothing_is_message_isnt_a_dict(self):
        message = "I'm not a dict :("

        await self.logger.info(message, flatten=True)
        logged_content = json.loads(await self.stream_reader.readline())

        self.assertEqual(message, logged_content['msg'])

    async def test_flatten_instance_attr_adds_messages_to_document_root(self):
        self.logger.flatten = True

        message = {'The Jeff Healey Band': 'Cruel Little Number'}
        await self.logger.info(message)
        logged_content = json.loads(await self.stream_reader.readline())

        self.assertDictContainsSubset(message, logged_content)

    async def test_flatten_instance_attr_overwrites_default_attributes(self):
        self.logger.flatten = True

        message = {'logged_at': 'Yesterday'}
        await self.logger.info(message)
        logged_content = json.loads(await self.stream_reader.readline())

        self.assertEqual(message['logged_at'], logged_content['logged_at'])

    @patch('logging.StreamHandler.terminator', '')
    async def test_it_forwards_serializer_kwargs_parameter_to_serializer(self):
        message = {
            'logged_at': 'Yesterday',
            'line_number': 1,
            'function': 'print',
            'level': 'easy',
            'file_path': 'Somewhere over the rainbow'
        }
        options = {'indent': 2, 'sort_keys': True}
        await self.logger.info(message, flatten=True, serializer_kwargs=options)

        logged_content = bytes()
        while True:
            chunk = await self.stream_reader.readline()
            logged_content += chunk
            if not self.stream_reader._buffer:
                break

        expected_content = json.dumps(message, **options)

        self.assertEqual(logged_content.decode(), expected_content + '\n')

    @patch('logging.StreamHandler.terminator', '')
    async def test_it_forwards_serializer_kwargs_instance_attr_to_serializer(self):
        self.logger.serializer_kwargs = {'indent': 2, 'sort_keys': True}

        message = {
            'logged_at': 'Yesterday',
            'line_number': 1,
            'function': 'print',
            'level': 'easy',
            'file_path': 'Somewhere over the rainbow'
        }
        await self.logger.info(message, flatten=True)

        logged_content = bytes()
        while True:
            chunk = await self.stream_reader.readline()
            logged_content += chunk
            if not self.stream_reader._buffer:
                break

        expected_content = json.dumps(message, **self.logger.serializer_kwargs)

        self.assertEqual(logged_content.decode(), expected_content + '\n')

    async def test_extra_parameter_adds_content_to_root_of_all_messages(self):
        logger = await JsonLogger.with_default_handlers(level=10,
                                                        extra={'dog': 'Xablau'})
        message = {'log_message': 'Xena'}
        await logger.info(message)

        logged_content = json.loads(await self.stream_reader.readline())

        self.assertEqual(logged_content['msg']['log_message'], 'Xena')
        self.assertEqual(logged_content['dog'], 'Xablau')

    async def test_extra_parameter_on_log_method_function_call_updates_extra_parameter_on_init(self):
        logger = await JsonLogger.with_default_handlers(level=10,
                                                        extra={'dog': 'Xablau'})
        message = {'log_message': 'Xena'}
        await logger.info(message, extra={"ham": "eggs"})

        logged_content = json.loads(await self.stream_reader.readline())

        self.assertEqual(logged_content['msg']['log_message'], 'Xena')
        self.assertEqual(logged_content['dog'], 'Xablau')
        self.assertEqual(logged_content['ham'], 'eggs')

    async def test_callable_values_are_called_before_serialization(self):
        a_callable = Mock(return_value="I'm a callable that returns a string!")

        await self.logger.info(a_callable)
        logged_content = json.loads(await self.stream_reader.readline())
        self.assertEqual(logged_content['msg'], a_callable.return_value)

    async def test_default_fields_are_excludeable(self):
        logger = await JsonLogger.with_default_handlers(
            level=10,
            exclude_fields=[
                FUNCTION_NAME_FIELDNAME,
                LOG_LEVEL_FIELDNAME
            ]
        )

        await logger.info("Xablau")
        logged_content = json.loads(await self.stream_reader.readline())

        self.assertNotIn(FUNCTION_NAME_FIELDNAME, logged_content)
        self.assertNotIn(LOG_LEVEL_FIELDNAME, logged_content)

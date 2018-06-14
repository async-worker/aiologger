import json
import unittest
from unittest.mock import patch
from aiologger.formatters.json import ExtendedJsonFormatter, \
    LOG_LEVEL_FIELDNAME, LINE_NUMBER_FIELDNAME
from aiologger.loggers.json import LogRecord

from freezegun import freeze_time


@freeze_time('2006-06-06T06:06:06.666666')
class ExtendedJsonFormatterTests(unittest.TestCase):
    def setUp(self):
        self.formatter = ExtendedJsonFormatter()
        self.record = LogRecord(
            level=30,
            name='aiologger',
            pathname="/aiologger/tests/formatters/test_json_formatter.py",
            func='xablaufunc',
            lineno=42,
            msg={"dog": "Xablau", "action": "bark"},
            exc_info=None,
            args=None,
            extra=None,
            flatten=False,
            serializer_kwargs={}
        )

    def test_it_uses_default_log_fields_if_none_are_excluded_on_initialization(self):
        formatter = ExtendedJsonFormatter()
        self.assertEqual(
            ExtendedJsonFormatter.default_fields,
            formatter.log_fields
        )

    def test_default_log_fields_can_be_excluded_with_exclude_fields_initialization_argument(self):
        formatter = ExtendedJsonFormatter(exclude_fields=(LOG_LEVEL_FIELDNAME,))
        self.assertNotIn(LOG_LEVEL_FIELDNAME, formatter.log_fields)

    @freeze_time('2006-06-06T06:06:06.666666')
    def test_formatter_fields_for_record_with_default_fields(self):
        result = dict(self.formatter.formatter_fields_for_record(self.record))
        self.assertEqual(
            result,
            {
                'logged_at': '2006-06-06T06:06:06.666666',
                'line_number': 42,
                'function': 'xablaufunc',
                'level': 'WARNING',
                'file_path': '/aiologger/tests/formatters/test_json_formatter.py'
            }
        )

    def test_formatter_fields_for_record_with_excluded_fields(self):
        log_fields = {LOG_LEVEL_FIELDNAME, LINE_NUMBER_FIELDNAME}

        with patch.object(self.formatter, 'log_fields', log_fields):
            result = dict(self.formatter.formatter_fields_for_record(self.record))
            self.assertEqual(result, {'line_number': 42, 'level': 'WARNING'})

    def test_default_format(self):
        serialized_result = self.formatter.format(self.record)
        content = json.loads(serialized_result)
        self.assertEqual(
            content,
            {
                'logged_at': '2006-06-06T06:06:06.666666',
                'line_number': 42,
                'function': 'xablaufunc',
                'level': 'WARNING',
                'file_path': '/aiologger/tests/formatters/test_json_formatter.py',
                'msg': {
                    "dog": "Xablau",
                    "action": "bark"
                }
            }
        )

    def test_flatten_record_attr_adds_msg_to_root(self):
        self.record.flatten = True
        serialized_result = self.formatter.format(self.record)

        content = json.loads(serialized_result)
        self.assertEqual(
            content,
            {
                'logged_at': '2006-06-06T06:06:06.666666',
                'line_number': 42,
                'function': 'xablaufunc',
                'level': 'WARNING',
                'file_path': '/aiologger/tests/formatters/test_json_formatter.py',
                'dog': 'Xablau',
                'action': 'bark'
            }
        )

    def test_flatten_record_attr_does_nothing_if_msg_isnt_a_dict_instance(self):
        self.record.flatten = True
        self.record.msg = "Xablau, the dog"
        serialized_result = self.formatter.format(self.record)

        content = json.loads(serialized_result)
        self.assertEqual(
            content,
            {
                'logged_at': '2006-06-06T06:06:06.666666',
                'line_number': 42,
                'function': 'xablaufunc',
                'level': 'WARNING',
                'file_path': '/aiologger/tests/formatters/test_json_formatter.py',
                'msg': 'Xablau, the dog'
            }
        )

    def test_serialized_kwargs_record_attr_is_passed_to_instance_serialized_function(self):
        self.record.serializer_kwargs = {'indent': 2, 'sort_keys': True}
        expected_msg = {
            'logged_at': '2006-06-06T06:06:06.666666',
            'line_number': 42,
            'function': 'xablaufunc',
            'level': 'WARNING',
            'file_path': '/aiologger/tests/formatters/test_json_formatter.py',
            'msg': {
                'dog': 'Xablau',
                'action': 'bark'
            }
        }

        with patch.object(self.formatter, 'serializer') as serializer:
            self.formatter.format(self.record)
            serializer.assert_called_once_with(
                expected_msg,
                indent=2,
                sort_keys=True,
                default=self.formatter._default_handler
            )

    def test_extra_record_attr_adds_content_to_root_of_msg(self):
        self.record.extra = {'female_dog': 'Xena'}
        serialized_result = self.formatter.format(self.record)

        content = json.loads(serialized_result)
        self.assertEqual(
            content,
            {
                'logged_at': '2006-06-06T06:06:06.666666',
                'line_number': 42,
                'function': 'xablaufunc',
                'level': 'WARNING',
                'file_path': '/aiologger/tests/formatters/test_json_formatter.py',
                'msg': {
                    "dog": "Xablau",
                    "action": "bark"
                },
                'female_dog': 'Xena'
            }
        )


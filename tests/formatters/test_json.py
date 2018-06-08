import unittest
from logging import LogRecord

from aiologger.formatters.json import JsonFormatter


class JsonFormatterTests(unittest.TestCase):
    def setUp(self):
        self.record = LogRecord(
            level=30,
            name='aiologger',
            pathname="/aiologger/tests/formatters/test_json.py",
            lineno=42,
            msg="Xablau",
            exc_info=None,
            args=None
        )
        self.formatter = JsonFormatter()

    def test_default_fieldname_is_overwriteable(self):
        formatter = JsonFormatter(default_msg_fieldname='dog')

        self.assertEqual(formatter.default_msg_fieldname, 'dog')
        msg = formatter.format(self.record)
        self.assertEqual(msg, formatter.serializer({'dog': 'Xablau'}))

    def test_format_adds_exceptions_infos(self):
        self.record.exc_info = "Xena"
        self.record.exc_text = 'Xablito'

        self.assertEqual(
            self.formatter.format(self.record),
            self.formatter.serializer({
                'msg': 'Xablau',
                'exc_info': 'Xena',
                'exc_text': 'Xablito'
            })
        )

    def test_format_logs_msg_as_is_if_msg_is_a_dict(self):
        self.record.msg = {'dog': 'Xablau'}

        msg = self.formatter.format(self.record)
        self.assertEqual(
            msg,
            self.formatter.serializer({
                'dog': 'Xablau'
            })
        )

import logging
import unittest
from unittest.mock import Mock

from aiologger.filters import StdoutFilter


class StdoutFilterTests(unittest.TestCase):
    def setUp(self):
        self.stdout_filter = StdoutFilter()

    def test_it_filters_records_with_warning_log_level(self):
        record = Mock(levelno=logging.WARNING)
        self.assertFalse(self.stdout_filter.filter(record))

    def test_it_filters_records_with_error_log_level(self):
        record = Mock(levelno=logging.ERROR)
        self.assertFalse(self.stdout_filter.filter(record))

    def test_it_filters_records_with_critical_log_level(self):
        record = Mock(levelno=logging.CRITICAL)
        self.assertFalse(self.stdout_filter.filter(record))

    def test_it_doesnt_filters_records_with_debug_log_level(self):
        record = Mock(levelno=logging.DEBUG)
        self.assertTrue(self.stdout_filter.filter(record))

    def test_it_doesnt_filters_records_with_info_log_level(self):
        record = Mock(levelno=logging.INFO)
        self.assertTrue(self.stdout_filter.filter(record))

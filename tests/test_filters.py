import unittest
from unittest.mock import Mock

from aiologger.filters import StdoutFilter, Filter
from aiologger.levels import LogLevel
from tests.utils import make_log_record


class FilterTests(unittest.TestCase):
    def test_filter_allows_records_with_name_equal_to_filter_name(self):
        filter = Filter("A.B.C")
        log_record = make_log_record(name="A.B.C")
        self.assertTrue(filter.filter(log_record))

    def test_filter_allows_any_records_if_filter_name_isnt_provided(self):
        filter = Filter()

        log_record = make_log_record(name="name doesn't matter")
        self.assertTrue(filter.filter(log_record))

        log_record = make_log_record(name="A.B")
        self.assertTrue(filter.filter(log_record))

        log_record = make_log_record(name="A.B.C.D")
        self.assertTrue(filter.filter(log_record))

    def test_filter_allows_records_with_name_starting_with_filter_name(self):
        filter = Filter("A.B")
        log_record = make_log_record(name="A.B.C")
        self.assertTrue(filter.filter(log_record))

    def test_filter_disallows_records_with_name_starting_with_filter_name_that_isnt_a_prefix(
        self
    ):
        filter = Filter("A.B")
        log_record = make_log_record(name="A.BC")
        self.assertFalse(filter.filter(log_record))

    def test_it_disallows_records_with_name_not_starting_with_filter_name(self):
        filter = Filter("A.B")
        log_record = make_log_record(name="B.A")
        self.assertFalse(filter.filter(log_record))


class StdoutFilterTests(unittest.TestCase):
    def setUp(self):
        self.stdout_filter = StdoutFilter()

    def test_it_filters_records_with_warning_log_level(self):
        record = Mock(levelno=LogLevel.WARNING)
        self.assertFalse(self.stdout_filter.filter(record))

    def test_it_filters_records_with_error_log_level(self):
        record = Mock(levelno=LogLevel.ERROR)
        self.assertFalse(self.stdout_filter.filter(record))

    def test_it_filters_records_with_critical_log_level(self):
        record = Mock(levelno=LogLevel.CRITICAL)
        self.assertFalse(self.stdout_filter.filter(record))

    def test_it_doesnt_filters_records_with_debug_log_level(self):
        record = Mock(levelno=LogLevel.DEBUG)
        self.assertTrue(self.stdout_filter.filter(record))

    def test_it_doesnt_filters_records_with_info_log_level(self):
        record = Mock(levelno=LogLevel.INFO)
        self.assertTrue(self.stdout_filter.filter(record))

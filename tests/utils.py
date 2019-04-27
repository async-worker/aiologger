from aiologger.levels import LogLevel
from aiologger.records import LogRecord


def make_log_record(**kwargs) -> LogRecord:
    """
    Make a LogRecord whose attributes are defined by the specified kwargs
    """
    record = LogRecord(  # type: ignore
        name=None,
        level=LogLevel.NOTSET,
        pathname="",
        lineno=0,
        msg="",
        args=(),
        exc_info=None,
    )
    record.__dict__.update(kwargs)
    return record

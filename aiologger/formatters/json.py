import json
import traceback
from datetime import datetime
from inspect import istraceback
from typing import Callable, Iterable, Union, Dict, Optional, List
from datetime import timezone

from aiologger.formatters.base import Formatter
from aiologger.levels import LEVEL_TO_NAME
from aiologger.records import LogRecord, ExtendedLogRecord
from aiologger.utils import CallableWrapper




class JsonFormatter(Formatter):

    LOGGED_AT_FIELDNAME = "logged_at"
    LINE_NUMBER_FIELDNAME = "line_number"
    FUNCTION_NAME_FIELDNAME = "function"
    LOG_LEVEL_FIELDNAME = "level"
    MSG_FIELDNAME = "msg"
    FILE_PATH_FIELDNAME = "file_path"

    def __init__(
        self,
        serializer: Callable[..., str] = json.dumps,
        default_msg_fieldname: str = None,
    ) -> None:
        super(JsonFormatter, self).__init__()
        self.serializer = serializer
        self.default_msg_fieldname = (
            default_msg_fieldname
            or self.MSG_FIELDNAME
        )

    def _default_handler(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif istraceback(obj):
            tb = "".join(traceback.format_tb(obj))
            return tb.strip().split("\n")
        elif isinstance(obj, Exception):
            return "Exception: %s" % repr(obj)
        elif type(obj) is type:
            return str(obj)
        elif isinstance(obj, CallableWrapper):
            return obj()
        return str(obj)

    def format(self, record: LogRecord) -> str:
        """
        Formats a record and serializes it as a JSON str. If record message isnt
        already a dict, initializes a new dict and uses `default_msg_fieldname`
        as a key as the record msg as the value.
        If the serialized result is of type bytes (if orjson is used), then it is converted to utf-8.
        """
        msg: Union[str, dict] = record.msg
        if not isinstance(msg, dict):
            msg = {self.default_msg_fieldname: msg}

        if record.exc_info:
            msg["exc_info"] = record.exc_info
        if record.exc_text:
            msg["exc_text"] = record.exc_text

        return self._serializer_ensure_str(msg=msg)

    @classmethod
    def format_error_msg(cls, record: LogRecord, exception: Exception) -> Dict:
        traceback_info: Optional[List[str]]
        if exception.__traceback__:
            traceback_info = cls.format_traceback(exception.__traceback__)
        else:
            traceback_info = None
        return {
            "record": {
                cls.LINE_NUMBER_FIELDNAME: record.lineno,
                cls.LOG_LEVEL_FIELDNAME: record.levelname,
                cls.FILE_PATH_FIELDNAME: record.filename,
                cls.FUNCTION_NAME_FIELDNAME: record.funcName,
                cls.MSG_FIELDNAME: str(record.msg),
            },
            cls.LOGGED_AT_FIELDNAME: datetime.utcnow().isoformat(),
            "logger_exception": {
                "type": str(type(exception)),
                "exc": str(exception),
                "traceback": traceback_info,
            },
        }

    def _serializer_ensure_str(
        self,
        msg: dict,
        record: Optional[Union[LogRecord, ExtendedLogRecord]] = None,
    ) -> str:
        """
        This ensures that the formatter will return a str object when the serializer
        may return a bytes object.
        """
        if hasattr(record, "serializer_kwargs"):
            result: Union[str, bytes] = self.serializer(
                msg,
                default=self._default_handler,
                **record.serializer_kwargs,  # type: ignore
            )
        else:
            result: Union[str, bytes] = self.serializer(  # type: ignore
                msg, default=self._default_handler
            )

        if isinstance(result, str):
            return result
        elif isinstance(result, bytes):
            return result.decode()
        else:
            resType = type(result)
            raise TypeError(
                f"ERROR: serialized object must be of str or bytes type, given {result} with type {resType}"
            )


class ExtendedJsonFormatter(JsonFormatter):
    level_to_name_mapping = LEVEL_TO_NAME

    def __init__(
        self,
        serializer: Callable[..., str] = json.dumps,
        default_msg_fieldname: str = None,
        exclude_fields: Iterable[str] = None,
        tz: timezone = None,
    ) -> None:

        super(ExtendedJsonFormatter, self).__init__(
            serializer=serializer, default_msg_fieldname=default_msg_fieldname
        )
        default_fields = frozenset(
            [
                self.LOG_LEVEL_FIELDNAME,
                self.LOGGED_AT_FIELDNAME,
                self.LINE_NUMBER_FIELDNAME,
                self.FUNCTION_NAME_FIELDNAME,
                self.FILE_PATH_FIELDNAME,
            ]
        )
        self.tz = tz
        if exclude_fields is None:
            self.log_fields = default_fields
        else:
            self.log_fields = default_fields - set(exclude_fields)

    def formatter_fields_for_record(self, record: LogRecord):
        """
        :type record: aiologger.records.ExtendedLogRecord
        """
        datetime_serialized = (
            datetime.now(timezone.utc).astimezone(self.tz).isoformat()
        )

        default_fields = (
            (self.LOGGED_AT_FIELDNAME, datetime_serialized),
            (self.LINE_NUMBER_FIELDNAME, record.lineno),
            (self.FUNCTION_NAME_FIELDNAME, record.funcName),
            (self.LOG_LEVEL_FIELDNAME, self.level_to_name_mapping[record.levelno]),
            (self.FILE_PATH_FIELDNAME, record.pathname),
        )

        for field, value in default_fields:
            if field in self.log_fields:
                yield field, value

    def format(self, record: ExtendedLogRecord) -> str:  # type: ignore
        """
        :type record: aiologger.records.ExtendedLogRecord
        """
        msg = dict(self.formatter_fields_for_record(record))
        if record.flatten and isinstance(record.msg, dict):
            msg.update(record.msg)
        else:
            msg[self.default_msg_fieldname] = record.msg

        if record.extra:
            msg.update(record.extra)
        if record.exc_info:
            msg["exc_info"] = record.exc_info
        if record.exc_text:
            msg["exc_text"] = record.exc_text

        return self._serializer_ensure_str(msg=msg, record=record)


class ECSExtendedJsonFormatter(ExtendedJsonFormatter):
    """JSON formatter compliant with Elastic Common Schema"""

    LOGGED_AT_FIELDNAME = "@timestamp"
    LINE_NUMBER_FIELDNAME = "log.origin.file.line"
    FUNCTION_NAME_FIELDNAME = "log.origin.function"
    LOG_LEVEL_FIELDNAME = "log.level"
    MSG_FIELDNAME = "message"
    FILE_PATH_FIELDNAME = "log.origin.file.name"

import os
import time
from collections import Mapping

from aiologger.levels import LogLevel, get_level_name


class LogRecord:
    """
    A ExtendedLogRecord instance represents an event being logged.

    ExtendedLogRecord instances are created every time something is logged. They
    contain all the information pertinent to the event being logged. The
    main information passed in is in msg and args, which are combined
    using str(msg) % args to create the message field of the record. The
    record also includes information such as when the record was created,
    the source line where the logging call was made, and any exception
    information to be logged.
    """

    def __init__(
        self,
        name: str,
        level: LogLevel,
        pathname: str,
        lineno: int,
        msg,
        args,
        exc_info,
        func=None,
        sinfo=None,
        **kwargs,
    ):
        """
        Initialize a logging record with interesting information.
        """
        ct = time.time()
        self.name = name
        self.msg = msg
        #
        # The following statement allows passing of a dictionary as a sole
        # argument, so that you can do something like
        #  logging.debug("a %(a)d b %(b)s", {'a':1, 'b':2})
        # Suggested by Stefan Behnel.
        # Note that without the test for args[0], we get a problem because
        # during formatting, we test to see if the arg is present using
        # 'if self.args:'. If the event being logged is e.g. 'Value is %d'
        # and if the passed arg fails 'if self.args:' then no formatting
        # is done. For example, logger.warning('Value is %d', 0) would log
        # 'Value is %d' instead of 'Value is 0'.
        # For the use case of passing a dictionary, this should not be a
        # problem.
        # Issue #21172: a request was made to relax the isinstance check
        # to hasattr(args[0], '__getitem__'). However, the docs on string
        # formatting still seem to suggest a mapping object is required.
        # Thus, while not removing the isinstance check, it does now look
        # for collections.abc.Mapping rather than, as before, dict.
        if args and len(args) == 1 and isinstance(args[0], Mapping) and args[0]:
            args = args[0]
        self.args = args
        self.levelname = get_level_name(level)
        self.levelno = level
        self.pathname = pathname
        try:
            self.filename = os.path.basename(pathname)
            self.module = os.path.splitext(self.filename)[0]
        except (TypeError, ValueError, AttributeError):
            self.filename = pathname
            self.module = "Unknown module"
        self.exc_info = exc_info
        self.exc_text = None  # used to cache the traceback text
        self.stack_info = sinfo
        self.lineno = lineno
        self.funcName = func
        self.created = ct
        self.msecs = (ct - int(ct)) * 1000

        if hasattr(os, "getpid"):
            self.process = os.getpid()
        else:
            self.process = None

    def __str__(self):
        return '<ExtendedLogRecord: %s, %s, %s, %s, "%s">' % (
            self.name,
            self.levelno,
            self.pathname,
            self.lineno,
            self.msg,
        )

    __repr__ = __str__

    def get_message(self):
        """
        Return the message for this ExtendedLogRecord.

        Return the message for this ExtendedLogRecord after merging any user-supplied
        arguments with the message.
        """
        msg = str(self.msg)
        if self.args:
            msg = msg % self.args
        return msg


class ExtendedLogRecord(LogRecord):
    def __init__(
        self,
        name,
        level,
        pathname,
        lineno,
        msg,
        args,
        exc_info,
        func=None,
        sinfo=None,
        **kwargs,
    ):
        super().__init__(
            name, level, pathname, lineno, msg, args, exc_info, func, sinfo
        )
        self.extra = kwargs["extra"]
        self.flatten = kwargs["flatten"]
        self.serializer_kwargs = kwargs["serializer_kwargs"]

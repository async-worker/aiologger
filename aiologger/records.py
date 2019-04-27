# The following code and documentation was inspired, and in some cases
# copied and modified, from the work of Vinay Sajip and contributors
# on cpython's logging package
import os
import time
from collections import Mapping
from typing import Optional

from aiologger.levels import LogLevel, get_level_name


class LogRecord:
    """
    A LogRecord instance represents an event being logged.

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
    ) -> None:
        """
        :param name: The name of the logger used to log the event represented
        by this LogRecord. Note that this name will always have this value,
        even though it may be emitted by a handler attached to a
        different (ancestor) logger.
        :param level: The numeric level of the logging event (one of DEBUG,
        INFO etc.) Note that this is converted to two attributes of the
        LogRecord: levelno for the numeric value and levelname for the
        corresponding level name.
        :param pathname: The full pathname of the source file where the
        logging call was made.
        :param lineno: The line number in the source file where the logging
        call was made.
        :param msg: The event description message, possibly a format string
        with placeholders for variable data.
        :param args: Variable data to merge into the msg argument to obtain
        the event description.
        :param exc_info: An exception tuple with the current exception
        information, or None if no exception information is available.
        :param func: The name of the function or method from which the
        logging call was invoked.
        :param sinfo: A text string representing stack information from the
        base of the stack in the current thread, up to the logging call.
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
        # Issue logging#21172: a request was made to relax the isinstance check
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
        self.exc_text: Optional[str] = None  # used to cache the traceback text
        self.stack_info = sinfo
        self.lineno = lineno
        self.funcName = func
        self.created = ct
        self.msecs = (ct - int(ct)) * 1000
        self.process = os.getpid()
        self.asctime: Optional[str] = None
        self.message: Optional[str] = None

    def __str__(self):
        return (
            f"<{self.__class__.__name__}: {self.name}, {self.levelno}, "
            f'{self.pathname}, {self.lineno}, "{self.msg}">'
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

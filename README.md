# aiologger

[![PYPI](https://img.shields.io/pypi/v/aiologger.svg)](http://pypi.python.org/pypi/aiologger)
[![PYPI Python Versions](https://img.shields.io/pypi/pyversions/aiologger.svg)](http://pypi.python.org/pypi/aiologger)
[![Build Status](https://travis-ci.org/diogommartins/aiologger.svg?branch=master)](https://travis-ci.org/diogommartins/aiologger)
[![codecov](https://codecov.io/gh/diogommartins/aiologger/branch/master/graph/badge.svg)](https://codecov.io/gh/diogommartins/aiologger)


The builtin python logger is IO blocking. This means that using the builting 
`logging` module will interfere with your asynchronouns application performance. `aiologger` aims to be the standard Asynchronous non blocking logging for python and asyncio. 

# Installation

```
pip install aiologger
``` 

# Testing 

```
pip install -r requirements-dev.txt
py.test
```

# Usage

The most basic use case is to log the output into `stdout` and `stderr`. 
Using `Logger.with_default_handlers` you're able to effortlessly create a new
`Logger` instance with handlers for handling `debug` and `info` as `stdout` and
 `warning`, `critical`, `exception` and `error` as `stderr`.


```python
import asyncio
from aiologger import Logger


async def main():
    logger = await Logger.with_default_handlers(name='my-logger')
    
    await logger.debug("Hello stdout !")
    await logger.info("Hello stdout !")

    await logger.warning("Hello stderr !")
    await logger.error("Hello stderr !")
    await logger.critical("Hello stderr !")

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()

```

# Loggers

## JsonLogger

A simple, featureful, drop-in replacement to the default `aiologger.Logger` 
that grants to always log valid, single line, JSON output.

### It logs everything

``` python
import asyncio
from datetime import datetime

from aiologger.loggers.json import JsonLogger


async def main():
    logger = await JsonLogger.with_default_handlers()
    await logger.info({
        'date_objects': datetime.now(),
        'exceptions': KeyError("Boooom"),
        'types': JsonLogger
    })

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()

>>> {"msg": {"date_objects": "2017-03-31T03:17:33.898880", "exceptions": "Exception: 'Boooom'", "types": "<class 'simple_json_logger.logger.JsonLogger'>"}, "logged_at": "2017-03-31T03:17:33.900136", "line_number": 8, "function": "<module>", "level": "INFO", "file_path": "/Users/diogo/PycharmProjects/aiologger/bla.py"}
```

`Callable[[], str]` log values may also be used to generate dynamic content that
are evaluated at serialization time:

```python
import asyncio
from random import randint

from aiologger.loggers.json import JsonLogger


async def main():
    logger = await JsonLogger.with_default_handlers(level=10, extra={"random_number": lambda: randint(1, 100)})
    
    await logger.info("First log line")
    # {"logged_at": "2018-02-06T13:55:35.439355", "line_number": 1, "function": "<module>", "level": "INFO", "file_path": "<input>", "msg": "First log line", "random_number": 6}
    
    await logger.info("Second log line")
    # {"logged_at": "2018-02-06T13:55:35.439590", "line_number": 2, "function": "<module>", "level": "INFO", "file_path": "<input>", "msg": "Second log line", "random_number": 48}

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()

``` 

###  Adding content to root

By default, everything passed to the log methods is inserted inside
the `msg` root attribute, but sometimes we want to add content to the root level.
For this, we may use the `extra` or `flatten` parameters.

#### Extra

The `extra` parameter also allow you to override the default root content:

```python
import asyncio
from aiologger.loggers.json import JsonLogger


async def main():
    a = 69
    b = 666
    c = [a, b]
    logger = await JsonLogger.with_default_handlers(level=10)

    await logger.info("I'm a simple log")
    >>> {"msg": "I'm a simple log", "logged_at": "2017-08-11T12:21:05.722216", "line_number": 5, "function": "<module>", "level": "INFO", "path": "/Users/diogo/PycharmProjects/aiologger/bla.py"}
    
    await logger.info("I'm a simple log", extra=locals())
    >>> {"msg": "I'm a simple log", "logged_at": "Yesterday", "line_number": 6, "function": "<module>", "level": "DEBUG", "path": "/Users/diogo/PycharmProjects/aiologger/bla.py", "logger": "<JsonLogger aiologger-json (INFO)>", "c": [69, 666], "b": 666, "a": 69}

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

The `extra` parameter also allow you to override the default root content:

```python
import asyncio
from aiologger.loggers.json import JsonLogger


async def main():
    logger = await JsonLogger.with_default_handlers(level=10)

    await logger.info("I'm a simple log")
    >>> {"msg": "I'm a simple log", "logged_at": "2017-08-11T12:21:05.722216", "line_number": 6, "function": "<module>", "level": "INFO", "path": "/Users/diogo/PycharmProjects/aiologger/bla.py"}
    
    await logger.info("I'm a simple log", extra={'logged_at': 'Yesterday'})
    >>> {"msg": "I'm a simple log", "logged_at": "Yesterday", "line_number": 6, "function": "<module>", "level": "INFO", "path": "/Users/diogo/PycharmProjects/aiologger/bla.py"}

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

and it may also be used as an instance attribute:

```python
import asyncio
from aiologger.loggers.json import JsonLogger


async def main():
    logger = await JsonLogger.with_default_handlers(level=10, extra={'logged_at': 'Yesterday'})

    await logger.info("I'm a simple log")
    >>> {"msg": "I'm a simple log", "logged_at": "Yesterday", "line_number": 6, "function": "<module>", "level": "INFO", "path": "/Users/diogo/PycharmProjects/aiologger/bla.py"}
    
    await logger.info("I'm a simple log")
    >>> {"msg": "I'm a simple log", "logged_at": "Yesterday", "line_number": 6, "function": "<module>", "level": "INFO", "path": "/Users/diogo/PycharmProjects/aiologger/bla.py"}

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

#### Flatten

Alternatively, this behavior may be achieved using `flatten`. Which is
available both as a method parameter and instance attribute.

As an instance attribute, every call to a log method would "flat" the dict attributes.

```python
import asyncio
from aiologger.loggers.json import JsonLogger


async def main():
    logger = await JsonLogger.with_default_handlers(level=10, flatten=True)

    await logger.info({"status_code": 200, "response_time": 0.00534534})
    >>> {"status_code": 200, "response_time": 0.534534, "logged_at": "2017-08-11T16:18:58.446985", "line_number": 6, "function": "<module>", "level": "INFO", "path": "/Users/diogo/PycharmProjects/simple_json_logger/bla.py"}
    
    await logger.error({"status_code": 404, "response_time": 0.00134534})
    >>> {"status_code": 200, "response_time": 0.534534, "logged_at": "2017-08-11T16:18:58.446986", "line_number": 6, "function": "<module>", "level": "INFO", "path": "/Users/diogo/PycharmProjects/simple_json_logger/bla.py"}

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

As a method parameter, only the specific call would add the content to the root.

```python
import asyncio
from aiologger.loggers.json import JsonLogger


async def main():
    logger = await JsonLogger.with_default_handlers(level=10)

    await logger.info({"status_code": 200, "response_time": 0.00534534}, flatten=True)
    >>> {"logged_at": "2017-08-11T16:23:16.312441", "line_number": 6, "function": "<module>", "level": "INFO", "path": "/Users/diogo/PycharmProjects/simple_json_logger/bla.py", "status_code": 200, "response_time": 0.00534534}
    
    await logger.error({"status_code": 404, "response_time": 0.00134534})
    >>> {"logged_at": "2017-08-11T16:23:16.312618", "line_number": 8, "function": "<module>", "level": "ERROR", "path": "/Users/diogo/PycharmProjects/simple_json_logger/bla.py", "msg": {"status_code": 404, "response_time": 0.00134534}}

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

**Warning**: It is possible to overwrite keys that are already present at root level.

```python
import asyncio
from aiologger.loggers.json import JsonLogger


async def main():
    logger = await JsonLogger.with_default_handlers(level=10)

    await logger.info({'logged_at': 'Yesterday'}, flatten=True)
    >>> {"logged_at": "Yesterday", "line_number": 6, "function": "<module>", "level": "INFO", "path": "/Users/diogo/PycharmProjects/simple_json_logger/bla.py"}

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

## Formatters

A set of sweet `logging.Formatter` subclasses! 

## JsonFormatter

Contribute to documentation ! =)

## ExtendedJsonFormatter

Contribute to documentation ! =)


## Compatibility

Currently tested only on python 3.6

## Depencencies

Has none.

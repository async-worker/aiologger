# aiologger

[![PYPI](https://img.shields.io/pypi/v/aiologger.svg)](http://pypi.python.org/pypi/aiologger)
[![PYPI Python Versions](https://img.shields.io/pypi/pyversions/aiologger.svg)](http://pypi.python.org/pypi/aiologger)
[![Build Status](https://travis-ci.org/diogommartins/aiologger.svg?branch=master)](https://travis-ci.org/diogommartins/aiologger)
[![codecov](https://codecov.io/gh/diogommartins/aiologger/branch/master/graph/badge.svg)](https://codecov.io/gh/diogommartins/aiologger)


The builtin python logger is IO blocking. This means that using the builting 
`logging` module will interfere with your asynchronouns application performance. `aiologger` aims to be the standard Asynchronous non blocking logging for python and asyncio. 

## Installation

```
pip install aiologger
``` 

## Testing 

```
pip install -r requirements-dev.txt
py.test
```

## Usage

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

## Loggers

### JsonLogger

A simple, featureful, drop-in replacement to the default `aiologger.Logger` 
that grants to always log valid, single line, JSON output.

#### It logs everything

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

>>> {"msg": {"date_objects": "2017-03-31T03:17:33.898880", "exceptions": "Exception: 'Boooom'", "types": "<class 'simple_json_logger.logger.JsonLogger'>"}, "logged_at": "2017-03-31T03:17:33.900136", "line_number": 8, "function": "<module>", "level": "INFO", "file_path": "/Volumes/partition2/Users/diogo/PycharmProjects/simple_json_logger/bla.py"}
```

`Callable[[], str]` log values may also be used to generate dynamic content that
are evaluated at serialization time:

```python
import asyncio
from random import randint

from aiologger.loggers.json import JsonLogger


async def main():
    logger = await JsonLogger.with_default_handlers(extra={"random_number": lambda: randint(1, 100)})
    
    await logger.info("First log line")
    # {"logged_at": "2018-02-06T13:55:35.439355", "line_number": 1, "function": "<module>", "level": "INFO", "file_path": "<input>", "msg": "First log line", "random_number": 6}
    
    await logger.info("Second log line")
    # {"logged_at": "2018-02-06T13:55:35.439590", "line_number": 2, "function": "<module>", "level": "INFO", "file_path": "<input>", "msg": "Second log line", "random_number": 48}

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

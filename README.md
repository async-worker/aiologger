# aiologger

[![PYPI](https://img.shields.io/pypi/v/aiologger.svg)](http://pypi.python.org/pypi/aiologger)
[![PYPI Python Versions](https://img.shields.io/pypi/pyversions/aiologger.svg)](http://pypi.python.org/pypi/aiologger)
[![Build Status](https://travis-ci.org/B2W-BIT/aiologger.svg?branch=master)](https://travis-ci.org/B2W-BIT/aiologger)
[![codecov](https://codecov.io/gh/B2W-BIT/aiologger/branch/master/graph/badge.svg)](https://codecov.io/gh/B2W-BIT/aiologger)


The builtin python logger is IO blocking. This means that using the builtin 
`logging` module will interfere with your asynchronouns application performance. 
`aiologger` aims to be the standard Asynchronous non blocking logging for 
python and asyncio. 

# Installation

```
pip install aiologger
``` 

# Testing 

```
pipenv install --dev
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
    logger = Logger.with_default_handlers(name='my-logger')
    
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
    await logger.info("Im a string")
    # {"logged_at": "2018-06-14T09:34:56.482817", "line_number": 9, "function": "main", "level": "INFO", "file_path": "/Users/diogo.mmartins/Library/Preferences/PyCharm2018.1/scratches/scratch_47.py", "msg": "Im a string"}
    
    await logger.info({
        'date_objects': datetime.now(),
        'exceptions': KeyError("Boooom"),
        'types': JsonLogger
    })
    # {"logged_at": "2018-06-14T09:34:56.483000", "line_number": 13, "function": "main", "level": "INFO", "file_path": "/Users/diogo.mmartins/Library/Preferences/PyCharm2018.1/scratches/scratch_47.py", "msg": {"date_objects": "2018-06-14T09:34:56.482953", "exceptions": "Exception: KeyError('Boooom',)", "types": "<JsonLogger aiologger-json (DEBUG)>"}}


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()

```

### JsonLogger Options

`Callable[[], str]` log values may also be used to generate dynamic content that
are evaluated at serialization time:

```python
import asyncio
import logging
from random import randint

from aiologger.loggers.json import JsonLogger


def rand():
    return randint(1, 100)


async def main():
    logger = await JsonLogger.with_default_handlers(level=logging.DEBUG)

    await logger.info(rand)
    # {"logged_at": "2018-06-14T09:37:52.624123", "line_number": 15, "function": "main", "level": "INFO", "file_path": "/Users/diogo.mmartins/Library/Preferences/PyCharm2018.1/scratches/scratch_47.py", "msg": 70}

    await logger.info({"Xablau": rand})
    # {"logged_at": "2018-06-14T09:37:52.624305", "line_number": 18, "function": "main", "level": "INFO", "file_path": "/Users/diogo.mmartins/Library/Preferences/PyCharm2018.1/scratches/scratch_47.py", "msg": {"Xablau": 29}}

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
``` 

###  Adding content to root

By default, everything passed to the log methods is inserted inside
the `msg` root attribute, but sometimes we want to add content to the root level.

#### Flatten

This behavior may be achieved using `flatten`. Which is
available both as a method parameter and instance attribute.

As an instance attribute, every call to a log method would "flat" the dict attributes.

```python
import asyncio
import logging
from aiologger.loggers.json import JsonLogger


async def main():
    logger = await JsonLogger.with_default_handlers(level=logging.DEBUG, flatten=True)

    await logger.info({"status_code": 200, "response_time": 0.00534534})
    # {"status_code": 200, "response_time": 0.534534, "logged_at": "2017-08-11T16:18:58.446985", "line_number": 6, "function": "<module>", "level": "INFO", "path": "/Users/diogo/PycharmProjects/aiologger/bla.py"}
    
    await logger.error({"status_code": 404, "response_time": 0.00134534})
    # {"status_code": 200, "response_time": 0.534534, "logged_at": "2017-08-11T16:18:58.446986", "line_number": 6, "function": "<module>", "level": "INFO", "path": "/Users/diogo/PycharmProjects/aiologger/bla.py"}

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

As a method parameter, only the specific call would add the content to the root.

``` python
import asyncio
import logging
from aiologger.loggers.json import JsonLogger


async def main():
    logger = await JsonLogger.with_default_handlers(level=logging.DEBUG)

    await logger.info({"status_code": 200, "response_time": 0.00534534}, flatten=True)
    # {"logged_at": "2017-08-11T16:23:16.312441", "line_number": 6, "function": "<module>", "level": "INFO", "path": "/Users/diogo/PycharmProjects/aiologger/bla.py", "status_code": 200, "response_time": 0.00534534}
    
    await logger.error({"status_code": 404, "response_time": 0.00134534})
    # {"logged_at": "2017-08-11T16:23:16.312618", "line_number": 8, "function": "<module>", "level": "ERROR", "path": "/Users/diogo/PycharmProjects/aiologger/bla.py", "msg": {"status_code": 404, "response_time": 0.00134534}}

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

**Warning**: It is possible to overwrite keys that are already present at root level.

```python
import asyncio
import logging
from aiologger.loggers.json import JsonLogger


async def main():
    logger = await JsonLogger.with_default_handlers(level=logging.DEBUG)

    await logger.info({'logged_at': 'Yesterday'}, flatten=True)
    # {"logged_at": "Yesterday", "line_number": 6, "function": "<module>", "level": "INFO", "path": "/Users/diogo/PycharmProjects/aiologger/bla.py"}

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

#### Extra

The `extra` parameter allow you to add specific content to root:


```python
import asyncio
import logging
from aiologger.loggers.json import JsonLogger


async def main():
    a = 69
    b = 666
    c = [a, b]
    logger = await JsonLogger.with_default_handlers(level=logging.DEBUG)

    await logger.info("I'm a simple log")
    # {"msg": "I'm a simple log", "logged_at": "2017-08-11T12:21:05.722216", "line_number": 5, "function": "<module>", "level": "INFO", "path": "/Users/diogo/PycharmProjects/aiologger/bla.py"}
    
    await logger.info({"dog": "Xablau"}, extra=locals())
    # {"logged_at": "2018-06-14T09:47:29.477705", "line_number": 14, "function": "main", "level": "INFO", "file_path": "/Users/diogo.mmartins/Library/Preferences/PyCharm2018.1/scratches/scratch_47.py", "msg": {"dog": "Xablau"}, "logger": "<JsonLogger aiologger-json (DEBUG)>", "c": [69, 666], "b": 666, "a": 69}


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

It also allows you to override the default root content:

```python
import asyncio
import logging
from aiologger.loggers.json import JsonLogger


async def main():
    logger = await JsonLogger.with_default_handlers(level=logging.DEBUG)

    await logger.info("I'm a simple log")
    # {"msg": "I'm a simple log", "logged_at": "2017-08-11T12:21:05.722216", "line_number": 6, "function": "<module>", "level": "INFO", "path": "/Users/diogo/PycharmProjects/aiologger/bla.py"}
    
    await logger.info("I'm a simple log", extra={'logged_at': 'Yesterday'})
    # {"msg": "I'm a simple log", "logged_at": "Yesterday", "line_number": 6, "function": "<module>", "level": "INFO", "path": "/Users/diogo/PycharmProjects/aiologger/bla.py"}

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

and it may also be used as an instance attribute:

```python
import asyncio
import logging
from aiologger.loggers.json import JsonLogger


async def main():
    logger = await JsonLogger.with_default_handlers(level=logging.DEBUG, extra={'logged_at': 'Yesterday'})

    await logger.info("I'm a simple log")
    # {"msg": "I'm a simple log", "logged_at": "Yesterday", "line_number": 6, "function": "<module>", "level": "INFO", "path": "/Users/diogo/PycharmProjects/aiologger/bla.py"}
    
    await logger.info("I'm a simple log")
    # {"msg": "I'm a simple log", "logged_at": "Yesterday", "line_number": 6, "function": "<module>", "level": "INFO", "path": "/Users/diogo/PycharmProjects/aiologger/bla.py"}

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```


#### Exclude default logger fields

If you think that the default fields are too much, it's also possible to 
exclude fields from the output message. 

```python
import asyncio
import logging
from aiologger.loggers.json import JsonLogger
from aiologger.formatters.json import FUNCTION_NAME_FIELDNAME, LOGGED_AT_FIELDNAME


async def main():
    logger = await JsonLogger.with_default_handlers(
        level=logging.DEBUG,
        exclude_fields=[FUNCTION_NAME_FIELDNAME,
                        LOGGED_AT_FIELDNAME,
                        'file_path',
                        'line_number']
    )

    await logger.info("Function, file path and line number wont be printed")
    # {"level": "INFO", "msg": "Function, file path and line number wont be printed"}

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

### Serializer options

`serializer_kwargs` is available both as instance attribute and as
a log method parameter and may be used to pass keyword arguments to the
`serializer` function. (See more: https://docs.python.org/3/library/json.html)

For pretty printing the output, you may use the `indent` kwarg. Ex.:

```python
import asyncio
import logging
from aiologger.loggers.json import JsonLogger


async def main():
    logger = await JsonLogger.with_default_handlers(
        level=logging.DEBUG,
        serializer_kwargs={'indent': 4}
    )

    await logger.info({
        "artist": "Black Country Communion",
        "song": "Cold"
    })

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
```

Would result in a pretty indented output:

```javascript
{
    "logged_at": "2017-08-11T21:04:21.559070",
    "line_number": 5,
    "function": "<module>",
    "level": "INFO",
    "file_path": "/Users/diogo/Library/Preferences/PyCharm2017.1/scratches/scratch_32.py",
    "msg": {
        "artist": "Black Country Communion",
        "song": "Cold"
    }
}
```

The same result can be achieved making a log call with `serializer_kwargs`
as a parameter.


```python
await logger.warning({'artist': 'Black Country Communion', 'song': 'Cold'}, serializer_kwargs={'indent': 4})
```

## Compatibility

Currently tested only on python 3.6

## Depencencies

Has none.

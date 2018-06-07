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

.. aiologger documentation master file, created by
   sphinx-quickstart on Thu Jan 31 17:38:35 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to aiologger docs!
=====================================

|PYPI| |PYPI Python Versions| |Build Status| |codecov| |black|

.. |PYPI| image:: https://img.shields.io/pypi/v/aiologger.svg
   :target: http://pypi.python.org/pypi/aiologger
.. |PYPI Python Versions| image:: https://img.shields.io/pypi/pyversions/aiologger.svg
   :target: http://pypi.python.org/pypi/aiologger
.. |Build Status| image:: https://travis-ci.org/B2W-BIT/aiologger.svg?branch=master
   :target: https://travis-ci.org/B2W-BIT/aiologger
.. |codecov| image:: https://codecov.io/gh/B2W-BIT/aiologger/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/B2W-BIT/aiologger
.. |black| image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :target: https://github.com/ambv/black

The builtin python logger is IO blocking. This means that using the
builtin ``logging`` module will interfere with your asynchronouns
application performance. ``aiologger`` aims to be the standard
Asynchronous non blocking logging for python and asyncio.

.. _GitHub: https://github.com/B2W-BIT/aiologger
.. _diogommartins: https://github.com/diogommartins
.. _daltonmatos: https://github.com/daltonmatos
.. _aiofiles: https://github.com/Tinche/aiofiles/tree/master/aiofiles



Installation
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   pip install aiologger

Testing
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   pipenv install --dev
   py.test


Dependencies
============

- Python 3.6+
- *Optional*: aiofiles_ is required for file handlers

Authors and License
===================

The ``aiologger`` package is written mostly by diogommartins_ and daltonmatos_.

It's *MIT* licensed and freely available.

Feel free to improve this package and send a pull request to GitHub_.


Table of Contents
=================

.. toctree::
   :maxdepth: 3

   usage
   loggers
   handlers
   contributing

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


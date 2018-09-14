.. _advanced:

Advanced topics
===============

.. _custom-auth:

Custom authentication
---------------------

The contents of :func:`~quiz.execution.execute`\'s ``auth`` parameter as passed to :func:`snug.execute <snug.query.execute>`.
This means that aside from basic authentication, a callable is accepted.

In most cases, you're just going to be adding a header, for which a convenient shortcut exists:

.. code-block:: python3

   >>> import snug
   >>> my_auth = snug.header_adder({'Authorization': 'My auth header!'})
   >>> execute(query, auth=my_auth)
   ...

See `here <https://snug.readthedocs.io/en/latest/advanced.html#authentication-methods>`_
for more detailed information.

.. _http-clients:

HTTP Clients
------------

The ``client`` parameter of :func:`~quiz.execution.execute` allows the use
of different HTTP clients. By default, `requests <https://python-requests.org>`_
and `aiohttp <https://aiohttp.readthedocs.io>`_ are supported.

Example usage:

.. code-block:: python3

   >>> import requests
   >>> quiz.execute(query, client=requests.Session())
   ...

To register another HTTP client, see `docs here <https://snug.readthedocs.io/en/latest/advanced.html#registering-http-clients>`_.

.. _executors:

Executors
---------

To make it easier to call :func:`~quiz.execution.execute()`
repeatedly with specific arguments, the :func:`~quiz.execution.executor()` shortcut can be used.

.. code-block:: python3

   >>> import requests
   >>> exec = snug.executor(auth=('me', 'password'),
   ...                      client=requests.Session())
   >>> exec(some_query)
   >>> exec(other_query)
   ...
   >>> # we can still override arguments on each call
   >>> exec(another_query, auth=('bob', 'hunter2'))

.. _async:

Async
-----

:func:`~quiz.execution.execute_async` is the asynchronous counterpart of
:func:`~quiz.execution.execute`.
It has a similar API, but works with the whole async/await pattern.

Here is a simple example:

.. code-block:: python3

   >>> import asyncio
   >>> future = quiz.execute_async(
   ...     query,
   ...     url='https://api.github.com/graphql',
   ...     auth=('me', 'password'),
   ... )
   >>> loop = asyncio.get_event_loop()
   >>> loop.run_until_complete(future)
   ...

The async HTTP client used by default is very rudimentary.
Using `aiohttp <https://aiohttp.readthedocs.io>`_ is highly recommended.
Here is an example usage:

.. code-block:: python3

  >>> import aiohttp
  >>> async def mycode():
  ...     async with aiohttp.ClientSession() as s:
  ...         return await quiz.execute_async(
  ...             query,
  ...             url='https://api.github.com/graphql',
  ...             auth=('me', 'password'),
  ...             client=s,
  ...          )
  >>> loop = asyncio.get_event_loop()
  >>> loop.run_until_complete(mycode())
  ...

.. note::

   :func:`~quiz.execution.async_executor()` is also available.

.. _schemas:

Caching schemas
---------------

Retrieving a schema every time with :meth:`~quiz.schema.Schema.from_url`
is not efficient.
A better way is to store the schema locally, and load it once.

A schema can be downloaded with :func:`quiz.download_schema_to_path`:

.. code-block:: python3

   >>> schema_path = '/path/to/schema.Jason'
   >>> quiz.download_schema_to_path('https://api.github.com/graphql',
   ...                              path=schema_path,
   ...                              auth=('me', 'password'),)

Such a schema can be loaded with :func:`quiz.Schema.from_path <quiz.schema.Schema.from_path>`:

.. code-block:: python3

   >>> schema = quiz.Schema.from_path(schema_path)

Making modules

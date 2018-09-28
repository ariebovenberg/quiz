.. _advanced:

Advanced topics
===============

.. _custom-auth:

Custom authentication
---------------------

The contents of :func:`~quiz.execution.execute`\'s ``auth`` parameter as passed to :func:`snug.execute() <snug.query.execute>`.
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

   :func:`~quiz.execution.async_executor` is also available
   with a similar API as :func:`~quiz.execution.executor`.

.. _caching_schemas:

Caching schemas
---------------

We've seen that :meth:`Schema.from_url() <quiz.schema.Schema.from_url>`
allows us to retrieve a schema directly from the API.
It is also possible to store a retrieved schema on the filesystem,
to avoid the need for downloading it every time.

This can be done with :meth:`~quiz.schema.Schema.to_path`.

.. code-block:: python3

   >>> schema = quiz.Schema.from_url(...)
   >>> schema.to_path('/path/to/schema.json')

Such a schema can be loaded with :func:`Schema.from_path() <quiz.schema.Schema.from_path>`:

.. code-block:: python3

   >>> schema = quiz.Schema.from_path('/path/to/schema.json')

.. _modules:

Populating modules
------------------

As we've seen, a :class:`~quiz.schema.Schema` contains generated classes.
It can be useful to add these classes to a python module:

* It allows pickling of instances
* A python module is the idiomatic format for exposing classes.

In order to do this, provide the ``module`` argument
in any of the schema constructors.
Then, use :meth:`~quiz.schema.Schema.populate_module` to add the classes
to this module.

.. code-block:: python3

   # my_module.py
   import quiz
   schema = quiz.Schema.from_url(..., module=__name__)
   schema.populate_module()


.. code-block:: python3

   # my_code.py
   import my_module
   my_module.MyObject


.. seealso::

   The :ref:`examples <examples>` show some practical applications of this feature.

.. _scalars:

Custom scalars
--------------

.. warning::

   Custom scalars are not yet implemented. They will be, soon.

.. _selectionset:

The selection API
-----------------

.. warning::

   This section is work in progress.
   See the :class:`~quiz.build.SelectionSet` API docs and :ref:`examples` for now.

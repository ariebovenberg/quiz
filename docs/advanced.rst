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

GraphQL APIs often use custom scalars to represent data such as dates or URLs.
By default, custom scalars in the schema
are defined as :class:`~quiz.types.GenericScalar`,
which accepts any of the base scalar types
(``str``, ``bool``, ``float``, ``int``, ``ID``).

It is recommended to define scalars explicitly.
This can be done by implementing a :class:`~quiz.types.Scalar` subclass
and specifying the :meth:`~quiz.types.Scalar.__gql_dump__` method
and/or the :meth:`~quiz.types.Scalar.__gql_load__` classmethod.

Below shows an example of a ``URI`` scalar for GitHub's v4 API:

.. code-block:: python3

   import urllib

   class URI(quiz.Scalar):
       """A URI string"""
       def __init__(self, url: str):
           self.components = urllib.parse.urlparse(url)

       # needed if converting TO GraphQL
       def __gql_dump__(self) -> str:
           return self.components.geturl()

       # needed if loading FROM GraphQL responses
       @classmethod
       def __gql_load__(cls, data: str) -> URI:
           return cls(data)


To make sure this scalar is used in the schema,
pass it to the schema constructor:

.. code-block:: python3

   # this also works with Schema.from_url()
   schema = quiz.Schema.from_path(..., scalars=[URI, MyOtherScalar, ...])
   schema.URI is URI  # True


.. _selectionset:

The ``SELECTOR`` API
--------------------

The :class:`quiz.SELECTOR <quiz.build.SELECTOR>`
object allows writing GraphQL in python syntax.

It is recommended to import this object as an easy-to-type variable name,
such as ``_``.

.. code-block:: python3

   import quiz.SELECTOR as _

Fields
~~~~~~

A selection with simple fields can be constructed by chaining attribute lookups.
Below shows an example of a selection with 3 fields:

.. code-block:: python3

   selection = _.field1.field2.foo

Note that we can write the same across multiple lines, using brackets.

.. code-block:: python3

   selection = (
       _
       .field1
       .field2
       .foo
   )

This makes the selection more readable. We will be using this style from now on.

How does this look in GraphQL? Let's have a look:

   >>> str(selection)
   {
     field1
     field2
     foo
   }

.. note::

   Newlines between brackets are valid python syntax.
   When chaining fields, **do not** add commas:

   .. code-block:: python3

      # THIS IS WRONG:
      selection = (
          _,
          .field1,
          .field2,
          .foo,
      )


Arguments
~~~~~~~~~

To add arguments to a field, simply use python's function call syntax
with keyword arguments:

.. code-block:: python3

   selection = (
       _
       .field1
       .field2(my_arg=4, qux='my value')
       .foo(bar=None)
   )

This converts to the following GraphQL:

.. code-block:: python3

   >>> str(selection)
   {
     field1
     field2(my_arg: 4, qux: "my value")
     foo(bar: null)
   }


Selections
~~~~~~~~~~

To add a selection to a field, use python's slicing syntax.
Within the ``[]`` brackets, a new selection can be defined.

.. code-block:: python3

   selection = (
       _
       .field1
       .field2[
           _
           .subfieldA
           .subfieldB
           .more[
               _
               .nested
               .data
           ]
           .another_field
       ]
       .foo
   )


This converts to the following GraphQL:

.. code-block:: python3

   >>> str(selection)
   {
     field1
     field2 {
       subfieldA
       subfieldB
       more {
         nested
         data
       }
       another_field
     }
     foo
   }

Aliases
~~~~~~~

To add an alias to a field, add a function call before the field,
specifying the field name:

.. code-block:: python3

   selection = (
       _
       .field1
       ('my_alias').field2
       .foo
   )

This converts to the following GraphQL:

.. code-block:: python3

   >>> str(selection)
   {
     field1
     my_alias: field2
     foo
   }

Fragments & Directives
~~~~~~~~~~~~~~~~~~~~~~

Fragments and directives are not yet supported.
See the roadmap.

Combinations
~~~~~~~~~~~~

The above features can be combined without restriction.
Here is an example of a complex query to GitHub's v4 API:

.. code-block:: python3

   selection = (
       _
       .rateLimit[
           _
           .remaining
           .resetAt
       ]
       ('hello_repo').repository(owner='octocat', name='hello-world')[
           _
           .createdAt
       ]
       .organization(login='github')[
           _
           .location
           .members(first=10)[
               _.edges[
                   _.node[
                       _.id
                   ]
               ]
               ('count').totalCount
           ]
       ]
   )

This translates in to the following GraphQL:

.. code-block:: python3

   >>> str(selection)
   {
     rateLimit {
       remaining
       resetAt
     }
     hello_repo: repository(owner: "octocat", name: "hello-world") {
       createdAt
     }
     organization(login: "github") {
       location
       members(first: 10) {
         edges {
           node {
             id
           }
         }
         count: totalCount
       }
     }
   }

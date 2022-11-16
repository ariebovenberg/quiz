🎱 Quiz
=======

.. image:: https://img.shields.io/pypi/v/quiz.svg?style=flat-square
   :target: https://pypi.python.org/pypi/quiz

.. image:: https://img.shields.io/pypi/l/quiz.svg?style=flat-square
   :target: https://pypi.python.org/pypi/quiz

.. image:: https://img.shields.io/pypi/pyversions/quiz.svg?style=flat-square
   :target: https://pypi.python.org/pypi/quiz

.. image:: https://img.shields.io/readthedocs/quiz.svg?style=flat-square
   :target: http://quiz.readthedocs.io/

.. image:: https://img.shields.io/codecov/c/github/ariebovenberg/quiz.svg?style=flat-square&logo=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABgAAAAaCAMAAACaYWzBAAABX1BMVEUAAAD///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8P/Ub/AAAAdHRSTlMAAQIDBAUGBw0PERIVFhcZGhsgISQmKSorLS8zODk6PUFDR0lLTE1YXF5fYGRlaHB1dnd4eXt/g4eKjJKVlpeYmZqcnqOkpaanqqusrq+xsrW3ubu8vb7Hzc7Q1dfZ3N3e3+Dh4ujp6uzt7/Hz9fb3+Pv9/mHMvTIAAAFPSURBVHgBbdDXcxJRGIbx55zvnI1ijJI1YuxiEkWNsRjsKPYiFuxFsRdREH3//5Hd2YvMLL/bZ76L9yMTYe74o95g+L57qgaRQiC9qbF+X2N35zBHxmj80bC9mFYqs/sv/NLfZXxWAiekq5soTLekJgaRw9IyxOCd8yHCIekoEbaMdITEKFhCQ/9qwB1dIWGNhIu6D9s0qDJlnoIPU8z0tZ1VXSITDMACmfNq8liL0/X6jnXgIcCGXUsLmxf0jA96q7Fv7RQz5m/kI9/pI1+lTw/vvZC0F1YkPb/V6Uk/0Ot6ANJrn2c4KbVmAbfvlTgNmDmosidf6s2AVYpnmoenOlssjUBw5Iyt+lnByLkAhchB3SZQEjmmM8RJYUXnJoXAkp5glHg2/laNZNLJZXUh8a588l3XHWWB3SO9aVTXW7nMv5TUwblS4cCDLzsx4D/omEB2BXPuawAAAABJRU5ErkJggg==
   :target: https://codecov.io/gh/ariebovenberg/quiz

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg?style=flat-square
   :target: https://github.com/psf/black

Capable GraphQL client for Python.

Features:

* Sync/async compatible, pluggable HTTP clients.
* Auto-generate typed and documented python APIs
* ORM-like syntax to write GraphQL.

Note that this project is in an early alpha stage.
Some features are not yet implemented (see the roadmap below),
and it may be a little rough around the edges.
If you encounter a problem or have a feature request,
don't hesitate to open an issue in the `issue tracker <https://github.com/ariebovenberg/quiz/issues>`_.


Quickstart
----------

A quick 'n dirty request to GitHub's new V4 API:

.. code-block:: python3

   >>> import quiz
   >>> query = '''
   ...   {
   ...     repository(owner: "octocat", name: "Hello-World") {
   ...       createdAt
   ...       description
   ...     }
   ...   }
   ... '''
   >>> quiz.execute(query, url='https://api.github.com/graphql',
   ...              auth=('me', 'password'))
   {"repository": ...}


Features
--------

1. **Adaptability**. Built on top of `snug <http://snug.readthedocs.io/>`_,
   quiz supports different HTTP clients

   .. code-block:: python3

      import requests
      result = quiz.execute(query, ..., client=requests.Session())

   as well as async execution
   (optionally with `aiohttp <http:aiohttp.readthedocs.io/>`_):

   .. code-block:: python3

      result = await quiz.execute_async(query, ...)

2. **Typing**.
   Convert a GraphQL schema into documented python classes:

   .. code-block:: python3

      >>> schema = quiz.Schema.from_url('https://api.github.com/graphql',
      ...                               auth=('me', 'password'))
      >>> help(schema.Repository)
      class Repository(Node, ProjectOwner, Subscribable, Starrable,
       UniformResourceLocatable, RepositoryInfo, quiz.types.Object)
       |  A repository contains the content for a project.
       |
       |  Method resolution order:
       |      ...
       |
       |  Data descriptors defined here:
       |
       |  assignableUsers
       |      : UserConnection
       |      A list of users that can be assigned to issues in this repo
       |
       |  codeOfConduct
       |      : CodeOfConduct or None
       |      Returns the code of conduct for this repository
       ...


3. **GraphQL "ORM"**. Write queries as you would with an ORM:

   .. code-block:: python3

      >>> _ = quiz.SELECTOR
      >>> query = schema.query[
      ...     _
      ...     .repository(owner='octocat', name='Hello-World')[
      ...         _
      ...         .createdAt
      ...         .description
      ...     ]
      ... ]
      >>> str(query)
      query {
        repository(owner: "octocat", name: "Hello-World") {
          createdAt
          description
        }
      }

4. **Offline query validation**. Use the schema to catch errors quickly:

   .. code-block:: python3

      >>> schema.query[
      ...     _
      ...     .repository(owner='octocat', name='Hello-World')[
      ...         _
      ...         .createdAt
      ...         .foo
      ...         .description
      ...     ]
      ... ]
      SelectionError: SelectionError on "Query" at path "repository":

          SelectionError: SelectionError on "Repository" at path "foo":

              NoSuchField: field does not exist

5. **Deserialization into python objects**. Responses are loaded into the schema's types.
   Use ``.`` to access fields:

   .. code-block:: python3

      >>> r = quiz.execute(query, ...)
      >>> r.repository.description
      "My first repository on GitHub!"
      >>> isinstance(r.repository, schema.Repository)
      True

   If you prefer the raw JSON response, you can always do:

   .. code-block:: python3

      >>> quiz.execute(str(query), ...)
      {"repository": ...}


Installation
------------

``quiz`` and its dependencies are pure python. Installation is easy as:

.. code-block:: bash

   pip install quiz


Contributing
------------

After you've cloned the repo locally, set up the development environment
with:

.. code-block:: bash

   make init

For quick test runs, run:

.. code-block:: bash

   pytest

To run all tests and checks on various python versions, run:

.. code-block:: bash

   make test

Generate the docs with:

.. code-block:: bash

   make docs


Pull requests welcome!


Preliminary roadmap
-------------------

================================================================== ===========
Feature                                                            status
================================================================== ===========
Input objects                                                      planned
better query validation errors                                     planned
more examples in docs                                              planned
executing selection sets directly                                  planned
introspection fields (i.e. ``__typename``)                         planned
custom scalars for existing types (e.g. ``datetime``)              planned
improve Object/Interface API                                       planned
value object docs                                                  planned
Mutations & subscriptions                                          planned
Inline fragments                                                   planned
Fragments and fragment spreads                                     planned
py2 unicode robustness                                             planned
Mixing in raw GraphQL                                              planned
Module autogeneration                                              planned
Type inference (e.g. enum values)                                  planned
Variables                                                          planned
Directives                                                         planned
Integer 32-bit limit                                               planned
converting names from camelcase to snake-case                      idea
Autogenerate module .rst from schema                               idea
Autogenerate module .py from schema                                idea
Escaping python keywords                                           idea
Handling markdown in descriptions                                  idea
Warnings when using deprecated fields                              idea
Handle optional types descriptions in schema                       idea
Returning multiple validation errors at the same time              idea
Explicit ordering                                                  idea
================================================================== ===========

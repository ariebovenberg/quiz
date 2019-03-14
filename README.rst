
.. raw:: html

   <p align="center">

   <img src="https://raw.githubusercontent.com/ariebovenberg/quiz/master/docs/_static/quiz-logo.png" height="150">

   <br/>

   <a href="https://travis-ci.org/ariebovenberg/quiz" class="reference external image-reference">
         <img src="https://img.shields.io/travis/ariebovenberg/quiz.svg?style=flat-square&logo=travis" alt="Build status">
   </a>

   <a href="https://codecov.io/gh/ariebovenberg/quiz" class="reference external image-reference">
         <img src="https://img.shields.io/codecov/c/github/ariebovenberg/quiz.svg?style=flat-square&logo=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABgAAAAaCAMAAACaYWzBAAABX1BMVEUAAAD///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////8P/Ub/AAAAdHRSTlMAAQIDBAUGBw0PERIVFhcZGhsgISQmKSorLS8zODk6PUFDR0lLTE1YXF5fYGRlaHB1dnd4eXt/g4eKjJKVlpeYmZqcnqOkpaanqqusrq+xsrW3ubu8vb7Hzc7Q1dfZ3N3e3+Dh4ujp6uzt7/Hz9fb3+Pv9/mHMvTIAAAFPSURBVHgBbdDXcxJRGIbx55zvnI1ijJI1YuxiEkWNsRjsKPYiFuxFsRdREH3//5Hd2YvMLL/bZ76L9yMTYe74o95g+L57qgaRQiC9qbF+X2N35zBHxmj80bC9mFYqs/sv/NLfZXxWAiekq5soTLekJgaRw9IyxOCd8yHCIekoEbaMdITEKFhCQ/9qwB1dIWGNhIu6D9s0qDJlnoIPU8z0tZ1VXSITDMACmfNq8liL0/X6jnXgIcCGXUsLmxf0jA96q7Fv7RQz5m/kI9/pI1+lTw/vvZC0F1YkPb/V6Uk/0Ot6ANJrn2c4KbVmAbfvlTgNmDmosidf6s2AVYpnmoenOlssjUBw5Iyt+lnByLkAhchB3SZQEjmmM8RJYUXnJoXAkp5glHg2/laNZNLJZXUh8a588l3XHWWB3SO9aVTXW7nMv5TUwblS4cCDLzsx4D/omEB2BXPuawAAAABJRU5ErkJggg==" alt="Test coverage">
   </a>

   <img src="https://img.shields.io/badge/dependabot-enabled-brightgreen.svg?longCache=true&logo=dependabot&style=flat-square" alt="Dependabot">

   <a href="http://quiz.readthedocs.io/" class="reference external image-reference">
         <img src="https://img.shields.io/readthedocs/quiz.svg?style=flat-square&logo=read-the-docs&logoColor=white" alt="Documentation status">
   </a>

   <br/>

   <a href="https://pypi.python.org/pypi/quiz" class="reference external image-reference">
         <img src="https://img.shields.io/pypi/status/quiz.svg?style=flat-square&colorB=orange&logo=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABgAAAAYCAMAAADXqc3KAAABIFBMVEUAAAAAAAD///+AgID///+qqqr////////////V1dX///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////9biOZSAAAAX3RSTlMAAQECAgMDBAUGBggJCg4QERITFBceICQpLC0uMDM0QUJFRkdISktPUlNUXF5hbW5vcHZ7fYCBgoSGjI+Ql5iam6Cio6SlsLW5u73CxcjK1Nvd3+3z9Pb3+Pn6+/z9/ugrIWMAAAEFSURBVHgBZc7nUupgGEXhRQ4niVHArtgFFcTeiwKigtg7BkT2/d+FI6Lmmzwz+ZHsyZqXEMt8sadz2Uwmu5juNhaXCXXM4xl/9CxcaHtNt9kEUYJsNjWIikQwuexrfEBl3NCwq9G4znAwOex8DaehwWNPY706x8MQJf5c6488aRgHs3SiFUipyj/LCM3oiohLSUt4wdD/B41gWyReX/qwjVu3iNl2jGWVcP6+J3VNR1kpvJ8QN7o8KuYLhXzxuKLHrk7MY12+fr3pEBfAZqimZtOvt/nvH9IUTrtUUV0BDd2BhUtOjVaQfG3g4lBVvWVo6B5wWFXIwfddyblZQ3oSLNpPiMUn8+xFVjc7sxcAAAAASUVORK5CYII=&logoColor=white" alt="Development status">
   </a>

   <a href="https://pypi.python.org/pypi/quiz" class="reference external image-reference">
         <img src="https://img.shields.io/pypi/v/quiz.svg?style=flat-square&logo=python&logoColor=white" alt="Latest version">
   </a>

   <a href="https://pypi.python.org/pypi/quiz" class="reference external image-reference">
         <img src="https://img.shields.io/pypi/l/quiz.svg?style=flat-square&logo=github&logoColor=white&colorB=blue" alt="License">
   </a>

   <a href="https://pypi.python.org/pypi/quiz" class="reference external image-reference">
         <img src="https://img.shields.io/pypi/pyversions/quiz.svg?style=flat-square&logo=python&logoColor=white" alt="Supported python versions">
   </a>

   </p>


Quiz
====

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
Input objects                                                      v0.2.0
better query validation errors                                     v0.2.0
more examples in docs                                              v0.2.0
executing selection sets directly                                  v0.2.0
introspection fields (i.e. ``__typename``)                         v0.2.0
custom scalars for existing types (e.g. ``datetime``)              v0.2.0
improve Object/Interface API                                       v0.2.0
value object docs                                                  v0.2.0
Mutations & subscriptions                                          v0.2.0
Inline fragments                                                   v0.2.0
Fragments and fragment spreads                                     v0.3.0
py2 unicode robustness                                             v0.3.0
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

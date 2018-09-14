
.. raw:: html

   <p align="center">

   <img src="https://raw.githubusercontent.com/ariebovenberg/quiz/develop/docs/_static/quiz-logo.png" height="150">

   <br/>

   <a href="https://travis-ci.org/ariebovenberg/quiz" class="reference external image-reference">
         <img src="https://img.shields.io/travis/ariebovenberg/quiz.svg?style=flat-square" alt="Build status">
   </a>

   <a href="https://codecov.io/gh/ariebovenberg/quiz" class="reference external image-reference">
         <img src="https://img.shields.io/codecov/c/github/ariebovenberg/quiz.svg?style=flat-square" alt="Test coverage">
   </a>

   <a href="http://quiz.readthedocs.io/" class="reference external image-reference">
         <img src="https://img.shields.io/readthedocs/quiz.svg?style=flat-square" alt="Documentation status">
   </a>

   <br/>

   <a href="https://pypi.python.org/pypi/quiz" class="reference external image-reference">
         <img src="https://img.shields.io/badge/status-Alpha-orange.svg?style=flat-square" alt="Development status">
   </a>

   <a href="https://pypi.python.org/pypi/quiz" class="reference external image-reference">
         <img src="https://img.shields.io/pypi/v/quiz.svg?style=flat-square" alt="Latest version">
   </a>

   <a href="https://pypi.python.org/pypi/quiz" class="reference external image-reference">
         <img src="https://img.shields.io/pypi/l/quiz.svg?style=flat-square" alt="License">
   </a>

   <a href="https://pypi.python.org/pypi/quiz" class="reference external image-reference">
         <img src="https://img.shields.io/pypi/pyversions/quiz.svg?style=flat-square" alt="Supported python versions">
   </a>

   </p>


Quiz
====

Capable GraphQL client.
**Work in progress: many features are not available/stable/documented**.

Features:

* Sync/async compatible, pluggable HTTP clients.
* Auto-generate typed and documented python APIs
* ORM-like syntax to write GraphQL.

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
   >>> quiz.execute(query, url='https://api.github.com/graphl',
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

      >>> schema = quiz.schema.get(url='https://api.github.com/graphql',
      ...                          auth=('me', 'password'))
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
      >>> q = schema.query[
      ...     _
      ...     .repository(owner='octocat', name='Hello-World')[
      ...         _
      ...         .createdAt
      ...         .description
      ...     ]
      ... ]
      >>> print(q)
      query {
        repository(owner: "octocat", name: "Hello-World") {
          createdAt
          description
        }
      }

   Catch errors:

   .. code-block:: python3

      >>> schema.query(
      ...     _
      ...     .repository(owner='octocat', name='Hello-World')[
      ...         _
      ...         .createdAt
      ...         .foo
      ...         .description
      ...     ]
      ... )
      quiz.NoSuchField: "Repository" has no field "foo"


Installation
------------

.. code-block:: bash

   pip install quiz


Preliminary roadmap
-------------------

================================================================== ===========
Feature                                                            status
================================================================== ===========
Adaptable Execution                                                done
Class autogeneration                                               done
Python 2.7-3.7 support                                             done
CI                                                                 done
Test for help()                                                    done
Text escaping                                                      done
Floats                                                             done
Field aliases                                                      done
Improve schema API (consistent with docs)                          done
Examples working                                                   v0.0.3
Up-to-date documentation                                           v0.0.3
scalars                                                            v0.0.3
download_schema                                                    v0.0.3
validation error messages                                          v0.0.3
Deserialization                                                    v0.0.3
SelectionSet.__str__                                               v0.0.3

Object/Interface as metaclass                                      v0.0.4
value object docs                                                  v0.0.4
Mutations                                                          v0.0.4
Input objects                                                      v0.0.4
Inline fragments                                                   v0.0.4
Fragments and fragment spreads                                     v0.0.5
py2 unicode robustness                                             v0.0.5
Mixing in raw GraphQL                                              planned
Module autogeneration                                              planned
Type inference (e.g. enum values)                                  planned
Variables                                                          planned
Directives                                                         planned
Integer 32-bit limit                                               planned
Parsing raw GraphQL                                                idea
Pickling                                                           idea
converting variables from camelcase to snake-case                  idea
Autogenerate module .rst from schema                               idea
Autogenerate module .py from schema                                idea
Escaping python keywords                                           idea
Handling markdown in descriptions                                  idea
Warnings when using deprecated fields                              idea
Handle optional types descriptions in schema                       idea
Returning multiple validation errors at the same time              idea
================================================================== ===========

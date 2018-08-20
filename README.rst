Quiz 🎱
=======

.. image:: https://img.shields.io/badge/status-alpha-orange.svg?style=flat-square
    :target: https://pypi.python.org/pypi/quiz

.. image:: https://img.shields.io/pypi/v/quiz.svg?style=flat-square
    :target: https://pypi.python.org/pypi/quiz

.. image:: https://img.shields.io/pypi/l/quiz.svg?style=flat-square
    :target: https://pypi.python.org/pypi/quiz

.. image:: https://img.shields.io/pypi/pyversions/quiz.svg?style=flat-square
    :target: https://pypi.python.org/pypi/quiz

.. image:: https://img.shields.io/travis/ariebovenberg/quiz.svg?style=flat-square
    :target: https://travis-ci.org/ariebovenberg/quiz

.. image:: https://img.shields.io/codecov/c/github/ariebovenberg/quiz.svg?style=flat-square
    :target: https://codecov.io/gh/ariebovenberg/quiz

.. image:: https://img.shields.io/readthedocs/quiz.svg?style=flat-square
    :target: http://quiz.readthedocs.io/

Capable GraphQL client. **Work in progress**.

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
   ...     my_repo: repository(owner: "octocat", name: "Hello-World") {
   ...       createdAt
   ...       description
   ...     }
   ...     organization(login: "github") {
   ...       location
   ...       email
   ...       avatarUrl(size: 50)
   ...       project(number: 1) {
   ...         name
   ...         state
   ...       }
   ...     }
   ...   }
   ... '''
   >>> quiz.execute(query, url='https://api.github.com/graphl',
   ...              auth=('me', 'password'))
   {"my_repo": ..., "organization": ...}


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


3. **GraphQL ORM**. Write queries as you would with an ORM:

   .. code-block:: python3

      >>> _ = quiz.SELECTOR
      >>> q = schema.query(
      ...     _
      ...     ('my_repo').repository(owner='octocat', name='Hello-World')[
      ...         _
      ...         .createdAt
      ...         .description
      ...     ]
      ...     .organization(login='github')[
      ...         _
      ...         .location
      ...         .email
      ...         .avatarUrl(size=50)
      ...         .project(number=1)[
      ...             _
      ...             .name
      ...             .state
      ...         ]
      ...     ]
      ... )
      >>> print(q)
      query {
        my_repo: repository(owner: "octocat", name: "Hello-World") {
          createdAt
          description
        }
        organization(login: "github") {
          location
          email
          avatarUrl(size: 50)
          project(number: 1) {
            name
            state
          }
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


Tentative roadmap

================================================================== ===========
Feature                                                            status
================================================================== ===========
Adaptable Execution                                                done
Class autogeneration                                               done
Python 2.7-3.7 support                                             done
CI                                                                 done
Test for help()                                                    done
Text escaping                                                      done
Up-to-date documentation                                           v0.0.2
Floats                                                             v0.0.2
Input objects                                                      v0.0.2
Mutations                                                          v0.0.2
Inline fragments                                                   v0.0.3
Aliases                                                            v0.0.3
Fragments and fragment spreads                                     v0.0.4
Custom primitives                                                  v0.0.4
Mixing in raw GraphQL                                              planned
Deserialization                                                    planned
Module autogeneration                                              planned
Type inference (e.g. enum values)                                  planned
Variables                                                          planned
Directives                                                         planned
Integer 32-bit limit                                               planned
Parsing raw GraphQL
Pickling
converting variables from camelcase to snake-case
Autogenerate module .rst
Autogenerate module .py
Escaping python keywords
Handling markdown in descriptions
Warnings when using deprecated fields
Handle optional types descriptions in schema
Returning multiple validation errors at the same time
================================================================== ===========

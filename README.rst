Quiz 🎱
=======

Capable GraphQL client. **Work in progress**.

Features:

* Sync/async compatible, pluggable HTTP clients.
* Auto-generate typed and documented python APIs
* ORM-like syntax to write GraphQL.

Quickstart
----------

A quick 'n dirty request to GitHub's new V4 API:

.. code-block:: python

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

   .. code-block:: python

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
      >>> q = ghub.query(
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
      >>> str(ghub)

   Catch errors:

   .. code-block:: python3

      >>> ghub.query(
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
Inline fragments                                                   planned
Text escaping                                                      planned
Non-ascii characters                                               planned
Module autogeneration                                              planned
Aliases                                                            planned
Input objects                                                      planned
Fragments and fragment spreads                                     planned
Custom primitives                                                  planned
Deserialization                                                    planned
Mutations                                                          planned
Python 2.7-3.7 support                                             planned
CI                                                                 planned
Variables
Directives
Parsing raw GraphQL
Type inference (e.g. enum values)
Pickling
converting variables from camelcase to snake-case
Autogenerate module .rst
Autogenerate module .py
Escaping python keywords
Handling markdown in descriptions
Warnings when using deprecated fields
================================================================== ===========

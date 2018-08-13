Quiz 🎱
=======

Capable GraphQL client. Currently in experimental state.

Features:

* Typed, documented interfaces to GraphQL APIs
* Use python to write and validate GraphQL queries
* sync/async compatibility

Quickstart
----------

Making a simple query:

.. code-block:: python

   >>> import quiz
   >>> query = '''
   ...   {
   ...     repository(owner: "octocat", name: "Hello-World") {
   ...       createdAt
   ...       description
   ...     }
   ...     organization(login: "github") {
   ...       location
   ...       email
   ...     }
   ...   }
   ... '''
   >>> quiz.execute(query, url='http://api.github.com/graphl',
   ...              auth=('me', 'password'))
   {"repository": {"createdAt": ..., ...}, "organization": ...}


Features
--------

1. **Flexibility**. Built on top of `snug <http://snug.readthedocs.io/>`_,
   quiz supports different HTTP clients...

   .. code-block:: python

      import requests
      result = quiz.execute(query, client=requests.Session(), ...)

   ...as well as async:

   .. code-block:: python3

      result = await quiz.execute_async(query, ...)


2. **Build GraphQL in python**.

   
   .. code-block:: python
   
      >>> from quiz import execute, selector as _, query
   
      >>> q = query(
      ...     _
      ...     .repository(owner='octocat', name='Hello-World')[
      ...         _
      ...         .createdAt
      ...         .description
      ...     ]
      ...     .organization(login='github')[
      ...         _
      ...         .location
      ...         .email
      ...         .project(number=1)[
      ...             _
      ...             .name
      ...             .state
      ...         ]
      ...     ]
      ... )


Todos
-----

* better custom primitives handling
* deserialization
* mutations
* type inference for enum values
* improved introspection
* python2.7, 3.4, 3.5, 3.6 support
* more examples
* proper CI
* docs
* warnings on using deprecated objects
* pickling
* schema to .rst
* schema to .py
* escape python keywords present in GraphQL
* handling markdown (CommonMark) in descriptions

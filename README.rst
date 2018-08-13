Quiz 🎱
=======

(Under construction) A capable GraphQL client. Currently in experimental state.

Features:

* Typed, documented interfaces to GraphQL APIs
* Use python to write and validate GraphQL queries
* sync/async compatibility

Features
--------

Write GraphQL queries in python-syntax

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

   >>> str(q)
   query {
     repository(owner: "octocat", name: "Hello-World") {
       createdAt
       description
     }
     organization(login: "github") {
       location
       email
       project(number: 1) {
         name
         state
       }
     }
   }
   >>> result = execute(q)


Todo
----

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

Quiz 🎱
=======

(Under construction) A GraphQL client. Currently in experimental state.

Aims:

* Create typed, documented interfaces to GraphQL APIs
* Write GraphQL queries in python-syntax
* sync/async compatibility

Features
--------

Write GraphQL queries in python-syntax

.. code-block:: python

   from quiz import query, field_chain as _, execute

   my_query = query [_
     .repository(owner='octocat', name='Hello-World') [_
       .createdAt
     ]
   ]

   response = execute(my_query)

Todo
----

* deserialization
* introspection
* mutations
* better custom primitives handling
* python2.7, 3.4, 3.5, 3.6 support
* more examples
* proper CI
* docs
* warnings on using deprecated objects
* pickling
* handling markdown (CommonMark) in descriptions
* schema to .rst
* schema to .py

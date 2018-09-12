User guide
==========

This page gives an introduction on the features of Quiz.

Executing a simple query
------------------------

Making a simple GraphQL query is easy. We'll use github's API v4 as an example.

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


:func:`~quiz.execution.execute` allows us to specify the query as text,
along with the target ``url`` and authentication credentials.

Executing a raw query (i.e. :class:`str`) returns the result as JSON.

.. note::

   For executing queries asynchronously,
   use :func:`~quiz.execution.execute_async`.
   For more information about executing queries, see :ref:`here <executors>`.


Retrieving a schema
-------------------

When performing multiple requests to a GraphQL API,
it is useful to retrieve its :class:`~quiz.schema.Schema`.
The schema will allow us to:

* validate queries
* convert responses into python objects
* introspect types and fields

The fastest way to retrieve a :class:`~quiz.schema.Schema`
is to grab it right from the API with :meth:`~quiz.schema.Schema.from_url`.
Let's retrieve GitHub's GraphQL schema:

.. code-block:: python3

   >>> schema = quiz.Schema.from_url('https://api.github.com/graphql',
   ...                               auth=('me', 'password'))


The schema contains python classes for GraphQL types.
These can be inspected with python's own :func:`help`:


.. code-block:: python3

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
    (truncated)


In the next section, we will see how this will allow us
to easily write and validate queries.

.. note::

   For more information about creating and inspecting schemas,
   see :ref:`here <schemas>`.


Constructing GraphQL
--------------------
   
As we've seen in the first section,
we can execute queries in text form.
Using the :class:`~quiz.schema.Schema`, however,
we can write GraphQL using python syntax.
To do this, we use the :data:`~quiz.build.SELECTOR` object
combined with python's :term:`slice` syntax.

The example below shows how we can recreate our original query in this syntax:

.. code-block:: python3

   >>> from quiz import SELECTOR as _
   >>> query = schema.query[
   ...     _
   ...     .repository(owner='octocat', name='hello-world')[
   ...         _
   ...         .createdAt
   ...         .description
   ...     ]
   ... ]

We can easily convert this to a GraphQL string:

.. code-block:: python3

   >>> print(query)
   query {
     repository(owner: "octocat", name: "Hello-World") {
       createdAt
       description
     }
   }

The main advantage of using python syntax is to catch mistakes
before sending anything to the API.

For example, what would happen if we added a non-existent field?

.. code-block:: python3

   >>> schema.query[
   ...     _
   ...     .repository(owner='octocat', name='hello-world')[
   ...         _
   ...         .createdAt
   ...         .description
   ...         .foo
   ...     ]
   ... ]
   NoSuchField: Object "Repository" has no field "foo"

Now we are confident with our query, we can use :func:`~quiz.execution.execute`
to evaluate the result.

.. code-block:: python3

   >>> result = quiz.execute(query)


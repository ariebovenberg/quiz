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


:func:`~quiz.execution.execute` allows us to specify the query as text,
along with the ``url`` of the API and authentication.

Executing a query returns the result as JSON.

For more information about executing queries, see :ref:`here <executors>`.

.. note::

   For executing queries asynchronously,
   use :func:`~quiz.execution.execute_async`.


Retrieving a schema
-------------------

When performing multiple requests to a GraphQL API,
it is useful to retrieve its schema.
The schema will allow us to:

* validate queries
* convert responses into python objects
* introspect types and fields

.. code-block:: python3

   >>> schema = quiz.Schema.get('https://api.github.com/graphql',
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


As we can see, :func:`schema.get() <quiz.schema.get>` retrieves the schema.


Constructing GraphQL
--------------------
   
hello

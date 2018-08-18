User guide
==========

This page gives an introduction on the features of Quiz.

Making a simple request
-----------------------

Making a simple GraphQL request is easy. We'll use github's API v4 as an example.

.. code-block:: python3

   >>> import quiz
   >>> # our GraphQL query as text
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



The ``SelectionSet`` API
------------------------
   
hello


Schemas
-------

foo

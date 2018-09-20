"""Components for executing GraphQL operations"""
import json
import typing as t
from functools import partial

import snug
from gentools import py2_compatible, return_

from .build import Query, gql
from .utils import JSON, ValueObject

__all__ = [
    'execute',
    'execute_async',
    'executor',
    'async_executor',
    'ErrorResponse',
    'Executable',
]

Executable = t.Union[str, Query]
"""Anything which can be executed as a GraphQL operation"""


def as_gql(obj):
    # type: Executable -> str
    if isinstance(obj, str):
        return obj
    assert isinstance(obj, Query)
    return gql(obj)


@py2_compatible
def as_http(doc, url):
    # type: (str, str) -> snug.Query[Dict[str, JSON]]
    response = yield snug.Request('POST', url, json.dumps({
        'query': doc,
    }).encode('ascii'), headers={'Content-Type': 'application/json'})
    content = json.loads(response.content.decode())
    if 'errors' in content:
        raise ErrorResponse(**content)
    return_(content['data'])


def execute(obj, url, **kwargs):
    """Execute a GraphQL executable

    Parameters
    ----------
    obj: :data:`~quiz.execution.Executable`
        The object to execute.
        This may be raw GraphQL, a document, single operation,
        or a query shorthand
    url: str
        The URL of the target endpoint
    **kwargs
         ``auth`` and/or ``client``, passed to :func:`snug.query.execute`.

    Returns
    -------
    JSON
        The response data

    Raises
    ------
    ErrorResponse
        If errors are present in the response
    """
    return snug.execute(as_http(as_gql(obj), url), **kwargs)


def executor(**kwargs):
    """Create a version of :func:`execute` with bound arguments.
    Equivalent to ``partial(execute, **kwargs)``.

    Parameters
    ----------
    **kwargs
       ``url``, ``auth``, and/or ``client``, passed to :func:`execute`

    Returns
    -------
    ~typing.Callable[[Executable], JSON]
        A callable to execute GraphQL executables

    Example
    -------

    >>> execute = executor(url='https://api.github.com/graphql',
    ...                    auth=('me', 'password'))
    >>> result = execute('''
    ...   {
    ...     repository(owner: "octocat" name: "Hello-World") {
    ...       description
    ...     }
    ...   }
    ... ''', client=requests.Session())
    """
    return partial(execute, **kwargs)


def execute_async(obj, url, **kwargs):
    """Execute a GraphQL executable asynchronously

    Parameters
    ----------
    obj: Executable
        The object to execute.
        This may be raw GraphQL, a document, single operation,
        or a query shorthand
    url: str
        The URL of the target endpoint
    **kwargs
         ``auth`` and/or ``client``,
         passed to :func:`snug.query.execute_async`.

    Returns
    -------
    JSON
        The response data

    Raises
    ------
    ErrorResponse
        If errors are present in the response
    """
    return snug.execute_async(as_http(as_gql(obj), url), **kwargs)


def async_executor(**kwargs):
    """Create a version of :func:`execute_async` with bound arguments.
    Equivalent to ``partial(execute_async, **kwargs)``.

    Parameters
    ----------
    **kwargs
       ``url``, ``auth``, and/or ``client``, passed to :func:`execute_async`

    Returns
    -------
    ~typing.Callable[[Executable], ~typing.Awaitable[JSON]]
        A callable to asynchronously execute GraphQL executables

    Example
    -------

    >>> execute = async_executor(url='https://api.github.com/graphql',
    ...                          auth=('me', 'password'))
    >>> result = await execute('''
    ...   {
    ...     repository(owner: "octocat" name: "Hello-World") {
    ...       description
    ...     }
    ...   }
    ... ''')
    """
    return partial(execute_async, **kwargs)


class ErrorResponse(ValueObject, Exception):
    __fields__ = [
        ('data', t.Dict[str, JSON], 'Data returned in the response'),
        ('errors', t.List[t.Dict[str, JSON]],
         'Errors returned in the response'),
    ]

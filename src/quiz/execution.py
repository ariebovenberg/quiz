"""Components for executing GraphQL operations"""
import json
import typing as t
from functools import partial

import snug
from gentools import irelay

from .build import Query
from .types import load
from .utils import JSON, ValueObject

__all__ = [
    "execute",
    "execute_async",
    "executor",
    "async_executor",
    "Executable",
    "ErrorResponse",
    "HTTPError",
    "RawResult",
    "QueryMetadata",
]

Executable = t.Union[str, Query]
"""Anything which can be executed as a GraphQL operation"""


def _exec(executable):
    # type: (Executable) -> t.Generator
    if isinstance(executable, str):
        return (yield executable)
    elif isinstance(executable, Query):
        return load(
            executable.cls, executable.selections, (yield str(executable))
        )
    else:
        raise NotImplementedError("not executable: " + repr(executable))


def middleware(url, query_str):
    # type: (str, str) -> snug.Query[t.Dict[str, JSON]]
    request = snug.POST(
        url,
        content=json.dumps({"query": query_str}).encode("ascii"),
        headers={"Content-Type": "application/json"},
    )
    response = yield request
    if response.status_code >= 400:
        raise HTTPError(response, request)
    content = json.loads(response.content.decode("utf-8"))
    if "errors" in content:
        content.setdefault("data", {})
        raise ErrorResponse(**content)
    return RawResult(
        content["data"], QueryMetadata(request=request, response=response)
    )


def execute(obj, url, **kwargs):
    """Execute a GraphQL executable

    Parameters
    ----------
    obj: :data:`~quiz.execution.Executable`
        The object to execute.
        This may be a raw string or a query
    url: str
        The URL of the target endpoint
    **kwargs
         ``auth`` and/or ``client``, passed to :func:`snug.query.execute`.

    Returns
    -------
    RawResult (a dict) or the schema's return type
        In case of a raw string, a raw result.
        Otherwise, an instance of the schema's type queried for.

    Raises
    ------
    ErrorResponse
        If errors are present in the response
    HTTPError
        If the response has a non 2xx response code
    """
    snug_query = irelay(_exec(obj), partial(middleware, url))
    return snug.execute(snug_query, **kwargs)


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
        This may be a raw string or a query
    url: str
        The URL of the target endpoint
    **kwargs
         ``auth`` and/or ``client``,
         passed to :func:`snug.query.execute_async`.

    Returns
    -------
    RawResult (a dict) or the schema's return type
        In case of a raw string, a raw result.
        Otherwise, an instance of the schema's type queried for.


    Raises
    ------
    ErrorResponse
        If errors are present in the response
    HTTPError
        If the response has a non 2xx response code
    """
    snug_query = irelay(_exec(obj), partial(middleware, url))
    return snug.execute_async(snug_query, **kwargs)


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
    """A response containing errors"""

    __fields__ = [
        ("data", t.Dict[str, JSON], "Data returned in the response"),
        (
            "errors",
            t.List[t.Dict[str, JSON]],
            "Errors returned in the response",
        ),
    ]


class RawResult(dict):
    """Dictionary as result of a raw query.

    Contains HTTP :class:`metadata <QueryMetadata>`
    in its ``__metadata__`` attribute.
    """

    __slots__ = "__metadata__"

    def __init__(self, items, meta):
        super(RawResult, self).__init__(items)
        self.__metadata__ = meta


class QueryMetadata(ValueObject):
    """HTTP metadata for query"""

    __fields__ = [
        ("response", snug.Response, "The response object"),
        ("request", snug.Request, "The original request"),
    ]


class HTTPError(ValueObject, Exception):
    """Indicates a response with a non 2xx status code"""

    __fields__ = [
        ("response", snug.Response, "The response object"),
        ("request", snug.Request, "The original request"),
    ]

    def __str__(self):
        return (
            "Response with status {0.status_code}, content: {0.content!r} "
            'for URL "{1.url}". View this exception\'s `request` and '
            "`response` attributes for detailed info.".format(
                self.response, self.request
            )
        )

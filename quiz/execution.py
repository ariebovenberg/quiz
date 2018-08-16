"""Components for executing GraphQL"""
import json
import typing as t
from functools import partial

import snug

from .types import Document, ErrorResponse, Operation, SelectionSet, gql

__all__ = [
    'execute',
]

Executable = t.Union[str, Document, Operation, SelectionSet]


def as_gql(obj: Executable) -> str:
    if isinstance(obj, str):
        return obj
    # TODO: typecheck?
    return gql(obj)


def as_http(doc: str, url: str) -> snug.Query[t.Dict[str, t.Any]]:
    response = yield snug.Request('POST', url, json.dumps({
        'query': doc,
    }).encode('ascii'), headers={'Content-Type': 'application/json'})
    content = json.loads(response.content)
    if 'errors' in content:
        raise ErrorResponse(**content)
    return content['data']


def execute(obj, url, **kwargs):
    """Execute a GraphQL executable

    Parameters
    ----------
    obj: str or Document or Operation or SelectionSet
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


def executor(url: str, **kwargs) -> t.Callable[[Operation], 'JSON']:
    return partial(execute, url=url, **kwargs)


# TODO: async counterparts

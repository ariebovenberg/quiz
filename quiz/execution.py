"""Components for executing GraphQL"""
import json
import typing as t
from functools import partial

import snug

from .types import Document, Operation, SelectionSet, gql

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
        # TODO: special exception class
        raise Exception(content['errors'])
    return content['data']


def execute(obj: Executable, url: str, **kwargs) -> 'JSON':
    return snug.execute(as_http(as_gql(obj), url), **kwargs)


def executor(url: str, **kwargs) -> t.Callable[[Operation], 'JSON']:
    return partial(execute, url=url, **kwargs)


# TODO: async counterparts

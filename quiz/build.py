import json
import typing as t
from dataclasses import dataclass, replace
from functools import singledispatch
from operator import methodcaller
from textwrap import indent

import snug

INDENT = '  '
NEWLINE = ''
URL = 'https://api.github.com/graphql'


gql = methodcaller('__gql__')


@singledispatch
def to_gql(obj):
    raise TypeError('cannot serialize to GraphQL: {}'.format(type(obj)))


@to_gql.register(str)
def _str_to_gql(obj):
    return f'"{obj}"'


@dataclass
class Attribute:
    name: str
    kwargs: t.Dict[str, t.Any]

    def __gql__(self):
        if self.kwargs:
            joined = ', '.join('{}: {}'.format(k, to_gql(v))
                               for k, v in self.kwargs.items())
            return f'{self.name}({joined})'
        else:
            return self.name

    def __repr__(self):
        return f'.{self.name}'


@dataclass
class NestedObject:
    attr: Attribute
    fields: 'FieldChain'

    def __repr__(self):
        return 'Nested({}, {})'.format(self.name, list(self.fields))

    def __gql__(self):
        return '{} {{\n{}\n}}'.format(gql(self.attr),
                                      indent(gql(self.fields), INDENT))


@dataclass
class FieldChain:
    __fields__: t.List[t.Union[Attribute, NestedObject]]

    def __getattr__(self, name):
        return FieldChain(self.__fields__ + [Attribute(name, {})])

    def __getitem__(self, key):
        assert isinstance(key, FieldChain)
        assert len(key.__fields__) >= 1
        *rest, target = self.__fields__
        return FieldChain(
            rest + [NestedObject(target, key)]
        )

    def __repr__(self):
        return 'FieldChain({!r})'.format(list(self.__fields__))

    def __call__(self, **kwargs):
        *rest, target = self.__fields__
        return FieldChain(rest + [replace(target, kwargs=kwargs)])

    def __gql__(self):
        return '\n'.join(map(gql, self.__fields__))


@dataclass
class Query(snug.Query):
    fields: FieldChain

    def __gql__(self):
        return '{{\n{}\n}}'.format(indent(gql(self.fields), INDENT))

    __str__ = __gql__

    def __iter__(self):
        response = yield snug.Request('POST', URL, content=json.dumps({
            'query': gql(self)
        }))
        return json.loads(response.content)


field_chain = FieldChain([])


class Namespace:

    def __init__(self, classes):
        for c in classes:
            setattr(self, c.__name__, c)

    def __getitem__(self, key):
        return Query(key)

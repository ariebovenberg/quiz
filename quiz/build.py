import enum
import json
import typing as t
from dataclasses import dataclass, replace
from functools import singledispatch
from operator import methodcaller, attrgetter
from textwrap import indent

import snug

from . import types

# TODO: __slots__

INDENT = "  "
NEWLINE = ""

gql = methodcaller("__gql__")


FieldName = str
"""a valid GraphQL fieldname"""


@singledispatch
def argument_as_gql(obj):
    raise TypeError("cannot serialize to GraphQL: {}".format(type(obj)))


argument_as_gql.register(str, '"{}"'.format)
argument_as_gql.register(int, str)


# TODO: make specific enum subclass to ensure
# only graphql compatible enums are set?
@argument_as_gql.register(enum.Enum)
def _enum_to_gql(obj):
    return obj.value


class _FrozenDict(t.Mapping):
    __slots__ = '_inner'

    def __init__(self, inner=()):
        self._inner = dict(inner)

    __len__ = property(attrgetter('_inner.__len__'))
    __iter__ = property(attrgetter('_inner.__iter__'))
    __getitem__ = property(attrgetter('_inner.__getitem__'))
    __repr__ = property(attrgetter('_inner.__repr__'))

    def __hash__(self):
        return hash(frozenset(self._inner.items()))


@dataclass(frozen=True, init=False)
class Field:
    name: FieldName
    kwargs: _FrozenDict = _FrozenDict()

    def __init__(self, name, kwargs=()):
        self.__dict__.update({
            'name': name,
            'kwargs': _FrozenDict(kwargs)
        })

    def __gql__(self):
        if self.kwargs:
            joined = ", ".join(
                "{}: {}".format(k, argument_as_gql(v))
                for k, v in self.kwargs.items()
            )
            return f"{self.name}({joined})"
        else:
            return self.name

    def __repr__(self):
        return f".{self.name}"


@dataclass(frozen=True)
class NestedObject:
    attr:   Field
    fields: t.Tuple['Fieldlike']

    def __repr__(self):
        return "Nested({}, {})".format(self.attr.name, list(self.fields))

    def __gql__(self):
        return "{} {{\n{}\n}}".format(
            gql(self.attr), indent('\n'.join(map(gql, self.fields)),
                                   INDENT)
        )


Fieldlike = t.Union[Field, NestedObject]


class Error(Exception):
    """an error relating to building a query"""


@dataclass(repr=False, frozen=True, init=False)
class FieldChain:
    """A "magic" field sequence builder"""
    # the attribute needs to have a dunder name to prevent
    # comflicts with GraphQL field names
    __fields__: t.Tuple[Fieldlike]
    # TODO: should this be unordered? (i.e. frozenset)

    def __init__(self, *fields):
        self.__dict__['__fields__'] = fields

    @classmethod
    def _make(cls, fields):
        return cls(*fields)

    def __getattr__(self, name):
        return FieldChain._make(self.__fields__ + (Field(name, {}), ))

    def __getitem__(self, selection):
        # TODO: check duplicate fieldnames
        try:
            *rest, target = self.__fields__
        except ValueError:
            raise Error('cannot select fields form empty field list')
        if isinstance(selection, str):
            # parse the string?
            # selection = RawGraphQL(dedent(selection).strip())
            raise NotImplementedError('raw GraphQL not yet implemented')
        elif isinstance(selection, FieldChain):
            assert len(selection.__fields__) >= 1
        return FieldChain._make(tuple(rest) +
                                (NestedObject(target, selection.__fields__), ))

    def __repr__(self):
        return "FieldChain({!r})".format(list(self.__fields__))

    # TODO: prevent `self` from conflicting with kwargs
    def __call__(self, **kwargs):
        try:
            *rest, target = self.__fields__
        except ValueError:
            raise Error('cannot call empty field list')
        return FieldChain._make(tuple(rest) +
                                (replace(target, kwargs=kwargs), ))

    def __iter__(self):
        return iter(self.__fields__)

    def __len__(self):
        return len(self.__fields__)


@dataclass
class Query(snug.Query):
    url:    str
    fields: FieldChain

    def __gql__(self):
        return "{{\n{}\n}}".format(indent(gql(self.fields), INDENT))

    __str__ = __gql__

    def __iter__(self):
        response = yield snug.Request(
            "POST", self.url, content=json.dumps({"query": gql(self)}),
            headers={'Content-Type': 'application/json'}
        )
        return json.loads(response.content)


field_chain = FieldChain()


class Namespace:

    def __init__(self, url: str, classes: types.ClassDict):
        self._url = url
        for name, cls in classes.items():
            setattr(self, name, cls)

    def __getitem__(self, key):
        # TODO: determine query type dynamically
        return self.Query[key]
        # breakpoint()
        # return Query(self._url, key)

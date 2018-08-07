import enum
import json
import typing as t
from dataclasses import dataclass, replace
from functools import singledispatch
from operator import methodcaller
from textwrap import indent

from .utils import FrozenDict, Error

import snug

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

# TODO: float, with exponent form


# TODO: make specific enum subclass to ensure
# only graphql compatible enums are set?
@argument_as_gql.register(enum.Enum)
def _enum_to_gql(obj):
    return obj.value


Selection = t.Union['Field', 'FragmentSpread', 'InlineFragment']


class SelectionSet(t.Tuple[Selection]):
    __slots__ = ()


@dataclass(frozen=True, init=False)
class Field:
    name: FieldName
    kwargs: FrozenDict = FrozenDict()
    selection_set: SelectionSet = SelectionSet()
    # - alias
    # - directives

    def __init__(self, name, kwargs=(), selection_set=()):
        self.__dict__.update({
            'name': name,
            'kwargs': FrozenDict(kwargs),
            'selection_set': SelectionSet(selection_set)
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


# TODO: ** operator for specifying fragments
@dataclass(repr=False, frozen=True, init=False)
class Selector(t.Iterable[Selection], t.Sized):
    """A "magic" selection set builder"""
    # the attribute needs to have a dunder name to prevent
    # comflicts with GraphQL field names
    __selections__: t.Tuple[Field]
    # according to the GQL spec: this is ordered

    def __init__(self, *selections):
        self.__dict__['__selections__'] = selections

    # TODO: optimize
    @classmethod
    def _make(cls, selections):
        return cls(*selections)

    def __getattr__(self, name):
        return Selector._make(self.__selections__ + (Field(name, {}), ))

    # TODO: support raw graphql strings
    def __getitem__(self, selection):
        # TODO: check duplicate fieldnames
        try:
            *rest, target = self.__selections__
        except ValueError:
            raise Error('cannot select fields from empty field list')

        assert isinstance(selection, Selector)
        assert len(selection.__selections__) >= 1

        return Selector._make(
            tuple(rest)
            + (replace(target, selection_set=selection.__selections__), ))

    def __repr__(self):
        return "Selector({!r})".format(list(self.__selections__))

    # TODO: prevent `self` from conflicting with kwargs
    def __call__(self, **kwargs):
        try:
            *rest, target = self.__selections__
        except ValueError:
            raise Error('cannot call empty field list')
        return Selector._make(
            tuple(rest) + (replace(target, kwargs=kwargs), ))

    def __iter__(self):
        return iter(self.__selections__)

    def __len__(self):
        return len(self.__selections__)


@dataclass
class Query(snug.Query):
    url:    str
    fields: Selector

    def __gql__(self):
        return "{{\n{}\n}}".format(indent(gql(self.fields), INDENT))

    __str__ = __gql__

    def __iter__(self):
        response = yield snug.Request(
            "POST", self.url, content=json.dumps({"query": gql(self)}),
            headers={'Content-Type': 'application/json'}
        )
        return json.loads(response.content)


field_chain = Selector()


class Namespace:

    def __init__(self, url: str, classes: t.Dict[str, type]):
        self._url = url
        for name, cls in classes.items():
            setattr(self, name, cls)

    def __getitem__(self, key):
        # TODO: determine query type dynamically
        return self.Query[key]
        # breakpoint()
        # return Query(self._url, key)


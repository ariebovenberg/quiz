import json
import typing as t
from dataclasses import dataclass, replace
from functools import singledispatch
from operator import methodcaller
from textwrap import indent, dedent

import snug
from . import types

INDENT = "  "
NEWLINE = ""

gql = methodcaller("__gql__")


@singledispatch
def primitive_to_gql(obj):
    raise TypeError("cannot serialize to GraphQL: {}".format(type(obj)))


@primitive_to_gql.register(str)
def _str_to_gql(obj):
    return f'"{obj}"'


@dataclass
class RawGraphQL:
    text: str

    def __gql__(self):
        return self.text


@dataclass
class Field:
    name: str
    kwargs: t.Dict[str, t.Any]

    def __gql__(self):
        if self.kwargs:
            joined = ", ".join(
                "{}: {}".format(k, primitive_to_gql(v))
                for k, v in self.kwargs.items()
            )
            return f"{self.name}({joined})"
        else:
            return self.name

    def __repr__(self):
        return f".{self.name}"


@dataclass
class NestedObject:
    attr: Field
    fields: t.Union["FieldChain", RawGraphQL]

    def __repr__(self):
        return "Nested({}, {})".format(self.name, list(self.fields))

    def __gql__(self):
        return "{} {{\n{}\n}}".format(
            gql(self.attr), indent(gql(self.fields), INDENT)
        )


@dataclass
class FieldChain:
    __fields__: t.List[t.Union[Field, NestedObject]]

    def __getattr__(self, name):
        return FieldChain(self.__fields__ + [Field(name, {})])

    def __getitem__(self, selection):
        # TODO: check duplicate fieldnames
        *rest, target = self.__fields__
        if isinstance(selection, str):
            # parse the string?
            selection = RawGraphQL(dedent(selection).strip())
        elif isinstance(selection, FieldChain):
            assert len(selection.__fields__) >= 1
        return FieldChain(rest + [NestedObject(target, selection)])

    def __repr__(self):
        return "FieldChain({!r})".format(list(self.__fields__))

    def __call__(self, **kwargs):
        *rest, target = self.__fields__
        return FieldChain(rest + [replace(target, kwargs=kwargs)])

    def __gql__(self):
        return "\n".join(map(gql, self.__fields__))


@dataclass
class Query(snug.Query):
    url:    str
    fields: FieldChain

    def __gql__(self):
        return "{{\n{}\n}}".format(indent(gql(self.fields), INDENT))

    __str__ = __gql__

    def __iter__(self):
        response = yield snug.Request(
            "POST", self.url, content=json.dumps({"query": gql(self)})
        )
        return json.loads(response.content)


field_chain = FieldChain([])


class Namespace:
    def __init__(self, url: str, classes: types.ClassDict):
        self._url = url
        for name, cls in classes.items():
            setattr(self, name, cls)

    def __getitem__(self, key):
        return Query(self._url, key)

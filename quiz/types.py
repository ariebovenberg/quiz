"""main module for constructing graphQL queries"""
# TODO: __slots__
import abc
import enum
import json
import typing as t
from collections import ChainMap, defaultdict
from dataclasses import dataclass, replace
from functools import partial, singledispatch
from itertools import chain
from operator import methodcaller
from textwrap import indent

import snug

from . import schema
from .utils import Error, FrozenDict

ClassDict = t.Dict[str, type]
NoneType = type(None)
INDENT = "  "

gql = methodcaller("__gql__")

FieldName = str
"""a valid GraphQL fieldname"""


@singledispatch
def argument_as_gql(obj):
    raise TypeError("cannot serialize to GraphQL: {}".format(type(obj)))


argument_as_gql.register(str, '"{}"'.format)
# TODO: string escape
argument_as_gql.register(int, str)

# TODO: float, with exponent form


@argument_as_gql.register(enum.Enum)
def _enum_to_gql(obj):
    return obj.value


Selection = t.Union['Field', 'FragmentSpread', 'InlineFragment']
SelectionSet = t.Tuple[Selection]


def selection_set_gql(selections: SelectionSet) -> str:
    return '{{\n{}\n}}'.format(
        '\n'.join(
            indent(f.graphql(), INDENT) for f in selections
        )
    ) if selections else ''


@dataclass(frozen=True, init=False)
class Field:
    name: FieldName
    kwargs: FrozenDict = FrozenDict()
    selection_set: SelectionSet = ()
    # TODO:
    # - alias
    # - directives

    def __init__(self, name, kwargs=(), selection_set=()):
        self.__dict__.update({
            'name': name,
            'kwargs': FrozenDict(kwargs),
            'selection_set': selection_set,
        })

    def graphql(self):
        arguments = '({})'.format(
            ', '.join(
                "{}: {}".format(k, argument_as_gql(v))
                for k, v in self.kwargs.items()
            )
        ) if self.kwargs else ''
        selection_set = (
            ' ' + selection_set_gql(self.selection_set)
            if self.selection_set else '')
        return self.name + arguments + selection_set

    __gql__ = graphql


# TODO: ** operator for specifying fragments
@dataclass(repr=False, frozen=True, init=False)
class Selector(t.Iterable[Selection], t.Sized):
    """A "magic" selection set builder"""
    # the attribute needs to have a dunder name to prevent
    # comflicts with GraphQL field names
    __selections__: t.Tuple[Field]
    # according to the GQL spec: this is ordered

    # why can't this subclass tuple?
    # Then we would have unwanted methods like index()

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


# @dataclass
# class Query(snug.Query):
#     url:    str
#     fields: Selector

#     def __gql__(self):
#         return "{{\n{}\n}}".format(indent(gql(self.fields), INDENT))

#     __str__ = __gql__

#     def __iter__(self):
#         response = yield snug.Request(
#             "POST", self.url, content=json.dumps({"query": gql(self)}),
#             headers={'Content-Type': 'application/json'}
#         )
#         return json.loads(response.content)


selector = Selector()


class ID(str):
    """represents a unique identifier, often used to refetch an object
    or as the key for a cache. The ID type is serialized in the same way
    as a String; however, defining it as an ID signifies that it is not
    intended to be human‐readable"""


BUILTIN_SCALARS = {
    "Boolean": bool,
    "String":  str,
    "ID":      ID,
    "Float":   float,
    "Int":     int,
}


@dataclass(frozen=True)
class NoSuchField(Error):
    on: type
    name: str


@dataclass(frozen=True)
class NoSuchArgument(Error):
    on: type
    field: 'FieldSchema'
    name: str


@dataclass(frozen=True)
class InvalidArgumentType(Error):
    on: type
    field: 'FieldSchema'
    name: str
    value: object


@dataclass(frozen=True)
class MissingArgument(Error):
    on: type
    field: 'FieldSchema'
    name: str


@dataclass(frozen=True)
class InvalidSelection(Error):
    on: type
    field: 'FieldSchema'


class Representable(abc.ABC):
    """Interface for GraphQL-representable objects"""

    # TODO: allow specifying custom/none indent
    @abc.abstractmethod
    def graphql(self):
        pass


@dataclass(frozen=True)
class InlineFragment(Representable):
    on: type
    selection_set: SelectionSet
    # TODO: add directives

    def graphql(self):
        return '... on {} {}'.format(
            self.on.__name__,
            selection_set_gql(self.selection_set)
        )


class OperationType(enum.Enum):
    QUERY = 'query'
    MUTATION = 'mutation'
    SUBSCRIPTION = 'subscription'


@dataclass(frozen=True)
class Operation:
    type: OperationType
    selection_set: SelectionSet = ()
    # TODO:
    # - name (optional)
    # - variable_defs (optional)
    # - directives (optional)


def _is_optional(typ):
    """check whether a type is a typing.Optional"""
    try:
        return typ.__origin__ is t.Union and NoneType in typ.__args__
    except AttributeError:
        return False


def _check_args(cls, field, kwargs) -> t.NoReturn:
    invalid_args = kwargs.keys() - field.args.keys()
    if invalid_args:
        raise NoSuchArgument(cls, field, invalid_args.pop())

    for param in field.args.values():
        try:
            value = kwargs[param.name]
        except KeyError:
            if not _is_optional(param.type):
                raise MissingArgument(cls, field, param.name)
        else:
            if not isinstance(value, param.type):
                raise InvalidArgumentType(
                    cls, field, param.name, value
                )


def _check_field(parent, field) -> t.NoReturn:
    assert isinstance(field, Field)
    try:
        schema = getattr(parent, field.name)
    except AttributeError:
        raise NoSuchField(parent, field.name)

    _check_args(parent, schema, field.kwargs)

    for f in field.selection_set:
        _check_field(schema.type, f)


# inherit from ABCMeta to allow mixing with other ABCs
class ObjectMeta(abc.ABCMeta):

    def __getitem__(self, selection_set: SelectionSet) -> InlineFragment:
        for field in selection_set:
            _check_field(self, field)
        return InlineFragment(self, selection_set)

    # TODO: prevent direct instantiation


class Object(metaclass=ObjectMeta):
    """a graphQL object"""


# - InputObject: calling instantiates an instance,
#   results must be instances of the class
class InputObject:
    pass


# separate class to distinguish graphql enums from normal Enums
# TODO: include deprecation attributes in instances?
# TODO: a __repr__ which includes the description, deprecation, etc?
class Enum(enum.Enum):
    pass


# separate class to distinguish graphql interfaces from normal ABCs
class Interface(abc.ABC):
    pass


class InputValue(t.NamedTuple):
    name: str
    desc: str
    type: type


class FieldSchema(t.NamedTuple):
    name: str
    desc: str
    type: type
    args: FrozenDict  # TODO: use type parameters
    is_deprecated: bool
    deprecation_reason: t.Optional[str]


def _namedict(classes):
    return {c.__name__: c for c in classes}


def object_as_type(typ: schema.Object,
                   interfaces: t.Mapping[str, type(Interface)]) -> type:
    return type(
        typ.name,
        (Object, ) + tuple(interfaces[i.name] for i in typ.interfaces),
        {"__doc__": typ.desc, "__schema__": typ},
    )


# NOTE: fields are not added yet. These must be added later with _add_fields
# why is this? Circular references may exist, which can only be added
# after all classes have been defined
def interface_as_type(typ: schema.Interface):
    return type(typ.name, (Interface, ),
                {"__doc__": typ.desc, "__schema__": typ})


def enum_as_type(typ: schema.Enum) -> t.Type[enum.Enum]:
    # TODO: convert camelcase to snake-case?
    cls = Enum(typ.name, {v.name: v.name for v in typ.values})
    cls.__doc__ = typ.desc
    cls.__schema__ = typ
    for member, conf in zip(cls.__members__.values(), typ.values):
        member.__doc__ = conf.desc
        member.__schema__ = conf
    return cls


# TODO: better error handling:
# - empty list of types
# - types not found
# python flattens unions, this is OK because GQL does not allow nested unions
def union_as_type(typ: schema.Union, objs: ClassDict):
    union = t.Union[tuple(objs[o.name] for o in typ.types)]
    union.__name__ = typ.name
    union.__doc__ = typ.desc
    union.__schema__ = typ
    return union


def inputobject_as_type(typ: schema.InputObject):
    return type(typ.name, (), {"__doc__": typ.desc, "__schema__": typ})


def _add_fields(obj, classes) -> None:
    for f in obj.__schema__.fields:
        setattr(
            obj,
            f.name,
            FieldSchema(
                name=f.name,
                desc=f.name,
                args=FrozenDict({
                    i.name: InputValue(
                        name=i.name,
                        desc=i.desc,
                        type=resolve_typeref(i.type, classes),
                    )
                    for i in f.args
                }),
                is_deprecated=f.is_deprecated,
                deprecation_reason=f.deprecation_reason,
                type=resolve_typeref(f.type, classes),
            ),
        )
    return obj


def resolve_typeref(ref: schema.TypeRef, classes: ClassDict) -> type:
    if ref.kind is schema.Kind.NON_NULL:
        return _resolve_typeref_required(ref.of_type, classes)
    else:
        return t.Optional[_resolve_typeref_required(ref, classes)]


# TODO: exception handling
def _resolve_typeref_required(ref, classes) -> type:
    assert ref.kind is not schema.Kind.NON_NULL
    if ref.kind is schema.Kind.LIST:
        return t.List[resolve_typeref(ref.of_type, classes)]
    return classes[ref.name]


def gen(types: t.Iterable[schema.Typelike], scalars: ClassDict) -> ClassDict:

    by_kind = defaultdict(list)
    for tp in types:
        by_kind[tp.__class__].append(tp)

    scalars_ = ChainMap(scalars, BUILTIN_SCALARS)
    assert not {tp.name for tp in by_kind[schema.Scalar]} - scalars_.keys()

    interfaces = _namedict(map(interface_as_type, by_kind[schema.Interface]))
    enums = _namedict(map(enum_as_type, by_kind[schema.Enum]))
    objs = _namedict(
        list(
            map(
                partial(object_as_type, interfaces=interfaces),
                by_kind[schema.Object],
            )
        )
    )
    unions = _namedict(
        map(partial(union_as_type, objs=objs), by_kind[schema.Union])
    )
    input_objects = _namedict(
        map(inputobject_as_type, by_kind[schema.InputObject])
    )

    classes = ChainMap(
        scalars_, interfaces, enums, objs, unions, input_objects
    )

    # we can only add fields after all classes have been created.
    for obj in chain(objs.values(), interfaces.values()):
        _add_fields(obj, classes)

    return classes


class Namespace:

    def __init__(self, url: str, classes: t.Dict[str, type]):
        # TODO: support schema's where "Query" is not the query type
        assert 'Query' in classes
        # TODO: check in the spec whether this is always the case
        assert all(c[0].isupper() for c in classes)

        self.url = url
        self.classes = classes
        # TODO: maybe do __getattr__ delegating to self.classes
        # instead of setting attributes
        self.__dict__.update(classes)

    def query(self, selection_set: SelectionSet) -> Operation:
        for field in selection_set:
            _check_field(self.Query, field)
        return Operation(OperationType.QUERY, selection_set)

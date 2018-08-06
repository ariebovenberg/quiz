import abc
import enum
import typing as t
from collections import ChainMap, defaultdict
from dataclasses import dataclass
from functools import partial
from itertools import chain

from . import schema, build
from .utils import FrozenDict

ClassDict = t.Dict[str, type]
NoneType = type(None)


class ID(str):
    """represents a unique identifier, often used to refetch an object
    or as the key for a cache. The ID type is serialized in the same way
    as a String; however, defining it as an ID signifies that it is not
    intended to be human‐readable"""


BUILTIN_SCALARS = {
    "Boolean": bool,
    "String": str,
    "ID": ID,
    "Float": float,
    "Int": int,
}


class Error(Exception):
    """base for all graphQL errors"""


@dataclass(frozen=True)
class NoSuchField(Error):
    on: type
    name: str


@dataclass(frozen=True)
class NoSuchArgument(Error):
    on: type
    field: 'Field'
    name: str


@dataclass(frozen=True)
class InvalidArgumentType(Error):
    on: type
    field: 'Field'
    name: str
    value: object


@dataclass(frozen=True)
class MissingArgument(Error):
    on: type
    field: 'Field'
    name: str


# TODO: besides Field, allow InlineFragment, FragmentSpread
SelectionSet = t.Tuple['Field']


@dataclass(frozen=True)
class InlineFragment:
    on: type
    selection_set: SelectionSet
    # TODO: add:
    # - directives
    # - selection_set


def _is_optional(typ):
    """check whether type type is a typing.Optional"""
    try:
        return typ.__origin__ is t.Union and NoneType in typ.__args__
    except AttributeError:
        return False


def _check_args(cls, field, kwargs) -> t.NoReturn:
    invalid_args = kwargs.keys() - field.args.keys()
    if invalid_args:
        raise NoSuchArgument(cls, field, invalid_args.pop())

    # TODO: refactor with map/filter
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


# inherit from ABCMeta to allow mixing with other ABCs
class ObjectMeta(abc.ABCMeta):

    def __getitem__(self, selection_set: SelectionSet) -> InlineFragment:
        for field in selection_set:
            assert isinstance(field, build.Field)
            try:
                schema = getattr(self, field.name)
            except AttributeError:
                raise NoSuchField(self, field.name)

            _check_args(self, schema, field.kwargs)
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


class Field(t.NamedTuple):
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
# when all classes have been built
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
            Field(
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

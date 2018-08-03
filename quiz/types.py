import abc
import enum
import typing as t
from collections import ChainMap, defaultdict
from dataclasses import dataclass
from functools import partial
from itertools import chain

from . import schema, build

ClassDict = t.Dict[str, type]


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


@dataclass(frozen=True)
class NoSuchField(Exception):
    on: type
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


class ObjectMeta(abc.ABCMeta):

    # TODO: creates query
    def __getitem__(self, selection_set: SelectionSet) -> InlineFragment:
        for selection in selection_set:
            assert isinstance(selection, build.Field)
            if not hasattr(self, selection.name):
                raise NoSuchField(self, selection.name)
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
    args: t.Tuple[InputValue]
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
                args=[
                    InputValue(
                        name=i.name,
                        desc=i.desc,
                        type=resolve_typeref(i.type, classes),
                    )
                    for i in f.args
                ],
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

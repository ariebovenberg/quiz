import abc
import enum
import typing as t
from collections import ChainMap, defaultdict
from functools import partial
from itertools import chain
from operator import attrgetter

from toolz import compose

from . import schema

ClassDict = t.Dict[str, type]


class InputValue(t.NamedTuple):
    name: str
    desc: str
    type: type


class Field(t.NamedTuple):
    name: str
    desc: str
    type: type
    args: InputValue
    deprecated: bool
    deprecation_reason = t.Optional[str]


def _namedict(classes):
    return {c.__name__: c for c in classes}


def object_as_type(
    typ: schema.Object, interfaces: t.Mapping[str, abc.ABCMeta]
) -> type:
    return type(
        typ.name,
        tuple(interfaces[i.name] for i in typ.interfaces),
        {"__doc__": typ.desc, "__schema__": typ},
    )


def interface_as_type(typ: schema.Interface):
    return type(typ.name, (abc.ABC,), {"__doc__": typ.desc, "__schema__": typ})


def enum_as_type(typ: schema.Enum) -> t.Type[enum.Enum]:
    cls = enum.Enum(typ.name, {v.name: v.name for v in typ.values})
    cls.__doc__ = typ.desc
    cls.__schema__ = typ
    return cls


def union_as_type(typ: schema.Union, objs: ClassDict):
    union = t.Union[tuple(objs[o.name] for o in typ.types)]
    union.__name__ = typ.name
    union.__doc__ = typ.desc
    return union


def _add_fields(obj, classes) -> None:
    obj.__fields__ = {
        f.name: resolve_typeref(f.type, classes) for f in obj.__schema__.fields
    }
    return obj


def resolve_typeref(ref: schema.TypeRef, classes: ClassDict) -> type:
    if ref.kind is schema.Kind.NON_NULL:
        return _resolve_typeref_required(ref.of_type, classes)
    else:
        return t.Optional[_resolve_typeref_required(ref, classes)]


def _resolve_typeref_required(ref, classes) -> type:
    assert ref.kind is not schema.Kind.NON_NULL
    if ref.kind is schema.Kind.LIST:
        return t.List[resolve_typeref(ref.of_type, classes)]
    elif ref.kind in (
        schema.Kind.OBJECT,
        schema.Kind.INTERFACE,
        schema.Kind.SCALAR,
        schema.Kind.UNION,
        schema.Kind.ENUM,
    ):
        return classes[ref.name]
    else:
        breakpoint()


ID = type("ID", (str,), {})
BUILTIN_SCALARS = {
    "Boolean": bool,
    "String": str,
    "ID": ID,
    "Float": float,
    "Int": int,
}


def build(types: t.Iterable[schema.Typelike], scalars: ClassDict) -> ClassDict:

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

    classes = ChainMap(scalars_, interfaces, enums, objs, unions)

    # we can only add fields after all classes have been created.
    for obj in chain(objs.values(), interfaces.values()):
        _add_fields(obj, classes)

    return classes


def make_module(name: str, classes: t.Iterable[type]) -> ModuleType:

    my_module = ModuleType(name)
    for cls in classes:
        try:
            cls.__module__ = my_module.__name__
        except (AttributeError, TypeError):
            pass
        setattr(my_module, cls.__name__, cls)

    return my_module

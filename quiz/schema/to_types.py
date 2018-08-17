import typing as t
from collections import defaultdict
from functools import partial
from itertools import chain

import six

from . import raw
from .. import types
from ..utils import FrozenDict, merge

ClassDict = t.Dict[str, type]


def _namedict(classes):
    return {c.__name__: c for c in classes}


def object_as_type(typ, interfaces, module_name):
    # type: (raw.Object, Mapping[str, Type[types.Interface]], str) -> type
    return type(
        str(typ.name),
        tuple(interfaces[i.name] for i in typ.interfaces) + (types.Object, ),
        {"__doc__": typ.desc, "__raw__": typ, '__module__': module_name},
    )


# NOTE: fields are not added yet. These must be added later with _add_fields
# why is this? Circular references may exist, which can only be added
# after all classes have been defined
def interface_as_type(typ, module_name):
    # type: (raw.Interface, str) -> type
    return type(str(typ.name), (types.Interface, ),
                {"__doc__": typ.desc, '__raw__': typ,
                 '__module__': module_name})


def enum_as_type(typ, module_name):
    # type: (raw.Enum, str) -> Type[types.Enum]
    # TODO: convert camelcase to snake-case?
    assert len(typ.values) > 0
    cls = types.Enum(typ.name, [(v.name, v.name) for v in typ.values],
                     module=module_name)
    cls.__doc__ = typ.desc
    for member, conf in zip(cls.__members__.values(), typ.values):
        member.__doc__ = conf.desc
    return cls


# TODO: better error handling:
# - empty list of types
# - types not found
def union_as_type(typ, objs):
    # type (raw.Union, ClassDict) -> type
    return type(
        str(typ.name),
        (types.Union, ),
        {
            '__doc__': typ.desc,
            '__args__': tuple(objs[o.name] for o in typ.types)
        }
    )


def inputobject_as_type(typ):
    # type raw.InputObject -> type
    return type(str(typ.name), (types.InputObject, ), {"__doc__": typ.desc})


def _add_fields(obj, classes):
    for f in obj.__raw__.fields:
        setattr(
            obj,
            f.name,
            types.FieldSchema(
                name=f.name,
                desc=f.desc,
                args=FrozenDict({
                    i.name: types.InputValue(
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
    del obj.__raw__
    return obj


def resolve_typeref(ref, classes):
    # type: (raw.TypeRef, ClassDict) -> type
    if ref.kind is raw.Kind.NON_NULL:
        return _resolve_typeref_required(ref.of_type, classes)
    else:
        return type('Nullable', (types.Nullable, ), {
            '__arg__': _resolve_typeref_required(ref, classes)
        })


# TODO: exception handling?
def _resolve_typeref_required(ref, classes):
    assert ref.kind is not raw.Kind.NON_NULL
    if ref.kind is raw.Kind.LIST:
        return type('List', (types.List, ), {
            '__arg__': resolve_typeref(ref.of_type, classes)
        })
    return classes[ref.name]


def build(type_schemas, module_name, scalars=FrozenDict.EMPTY):
    # type: (Iterable[raw.TypeSchema], str, ClassDict) -> ClassDict

    by_kind = defaultdict(list)
    for tp in type_schemas:
        by_kind[tp.__class__].append(tp)

    scalars_ = merge(scalars, types.BUILTIN_SCALARS)
    undefined_scalars = {
        tp.name for tp in by_kind[raw.Scalar]} - six.viewkeys(scalars_)
    if undefined_scalars:
        # TODO: special exception class
        raise Exception('Undefined scalars: {}'.format(', '.join(
            undefined_scalars)))

    interfaces = _namedict(map(
        partial(interface_as_type, module_name=module_name),
        by_kind[raw.Interface]
    ))
    enums = _namedict(map(
        partial(enum_as_type, module_name=module_name),
        by_kind[raw.Enum]
    ))
    objs = _namedict(map(
        partial(object_as_type, interfaces=interfaces,
                module_name=module_name),
        by_kind[raw.Object],
    ))
    unions = _namedict(map(
        partial(union_as_type, objs=objs),
        by_kind[raw.Union]
    ))
    input_objects = _namedict(map(
        inputobject_as_type,
        by_kind[raw.InputObject]
    ))

    classes = merge(
        scalars_, interfaces, enums, objs, unions, input_objects
    )

    # we can only add fields after all classes have been created.
    for obj in chain(objs.values(), interfaces.values()):
        _add_fields(obj, classes)

    return classes

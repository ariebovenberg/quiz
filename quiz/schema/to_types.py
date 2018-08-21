import typing as t
from collections import defaultdict
from functools import partial
from itertools import chain

import six

from . import raw
from .. import core
from ..compat import map
from ..execution import execute
from ..utils import FrozenDict, merge

ClassDict = t.Dict[str, type]


def _namedict(classes):
    return {c.__name__: c for c in classes}


def object_as_type(typ, interfaces, module_name):
    # type: (raw.Object, Mapping[str, Type[types.Interface]], str) -> type
    # we don't add the fields yet -- these types may not exist yet.
    return type(
        str(typ.name),
        tuple(interfaces[i.name] for i in typ.interfaces) + (core.Object, ),
        {"__doc__": typ.desc, "__raw__": typ, '__module__': module_name},
    )


def interface_as_type(typ, module_name):
    # type: (raw.Interface, str) -> type
    # we don't add the fields yet -- these types may not exist yet.
    return type(str(typ.name), (core.Interface, ),
                {"__doc__": typ.desc, '__raw__': typ,
                 '__module__': module_name})


def enum_as_type(typ, module_name):
    # type: (raw.Enum, str) -> Type[types.Enum]
    assert len(typ.values) > 0
    cls = core.Enum(typ.name, [(v.name, v.name) for v in typ.values],
                    module=module_name)
    cls.__doc__ = typ.desc
    for member, conf in zip(cls.__members__.values(), typ.values):
        member.__doc__ = conf.desc
    return cls


def union_as_type(typ, objs):
    # type (raw.Union, ClassDict) -> type
    assert len(typ.types) > 1
    return type(
        str(typ.name),
        (core.Union, ),
        {
            '__doc__': typ.desc,
            '__args__': tuple(objs[o.name] for o in typ.types)
        }
    )


def inputobject_as_type(typ):
    # type raw.InputObject -> type
    return type(str(typ.name), (core.InputObject, ), {"__doc__": typ.desc})


def _add_fields(obj, classes):
    for f in obj.__raw__.fields:
        setattr(
            obj,
            f.name,
            core.FieldSchema(
                name=f.name,
                desc=f.desc,
                args=FrozenDict({
                    i.name: core.InputValue(
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
        return core.Nullable[_resolve_typeref_required(ref, classes)]


def _resolve_typeref_required(ref, classes):
    assert ref.kind is not raw.Kind.NON_NULL
    if ref.kind is raw.Kind.LIST:
        return core.List[resolve_typeref(ref.of_type, classes)]
    return classes[ref.name]


def build(type_schemas, module_name, scalars=FrozenDict.EMPTY):
    # type: (Iterable[raw.TypeSchema], str, ClassDict) -> ClassDict

    by_kind = defaultdict(list)
    for tp in type_schemas:
        by_kind[tp.__class__].append(tp)

    scalars_ = merge(scalars, core.BUILTIN_SCALARS)
    undefined_scalars = {
        tp.name for tp in by_kind[raw.Scalar]} - six.viewkeys(scalars_)
    if undefined_scalars:
        raise core.Error('Undefined scalars: {}'.format(', '.join(
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


def get(url, scalars=FrozenDict.EMPTY, module='__main__', **kwargs):
    """Build a GraphQL schema by introspecting an API

    Parameters
    ----------
    url: str
        URL of the target GraphQL API
    scalars: ~typing.Mapping[str, object]
        Custom scalars to use

        Warning
        -------

        Scalars are not yet properly implemented
    module: str
        The module name to set on the generated classes
    **kwargs
        ``auth`` or ``client``, passed to :func:`~quiz.execution.execute`.

    Returns
    -------
    Mapping[str, type]
        A mapping of names to classes
    """
    result = execute(raw.INTROSPECTION_QUERY, url=url, **kwargs)
    return build(raw.load(result), scalars=scalars, module_name=module)

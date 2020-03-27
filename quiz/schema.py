"""Functionality relating to the raw GraphQL schema"""
import enum
import json
import sys
import typing as t
from collections import defaultdict
from dataclasses import dataclass, fields
from functools import partial
from itertools import chain
from operator import methodcaller
from os import fspath
from types import new_class
from typing import Type

from . import types
from .build import Query
from .execution import execute
from .utils import JSON, FrozenDict, add_slots, merge

__all__ = ["Schema", "INTROSPECTION_QUERY"]

RawSchema = t.Dict[str, JSON]
ClassDict = t.Dict[str, type]


def _namedict(classes):
    return {c.__name__: c for c in classes}


def object_as_type(typ, interfaces, module):
    # type: (Object, t.Mapping[str, types.Interface], str) -> type
    # we don't add the fields yet -- these types may not exist yet.
    return type(
        str(typ.name),
        tuple(interfaces[i.name] for i in typ.interfaces) + (types.Object,),
        {"__doc__": typ.desc, "__raw__": typ, "__module__": module},
    )


def interface_as_type(typ, module):
    # type: (Interface, str) -> type
    # we don't add the fields yet -- these types may not exist yet.
    return new_class(
        str(typ.name),
        (types.Namespace,),
        kwds={"metaclass": types.Interface},
        exec_body=methodcaller(
            "update",
            {"__doc__": typ.desc, "__raw__": typ, "__module__": module},
        ),
    )


def enum_as_type(typ, module):
    # type: (Enum, str) -> Type[types.Enum]
    assert len(typ.values) > 0
    cls = types.Enum(
        typ.name, [(v.name, v.name) for v in typ.values], module=module
    )
    cls.__doc__ = typ.desc
    for member, conf in zip(cls.__members__.values(), typ.values):
        member.__doc__ = conf.desc
    return cls


def union_as_type(typ, objs):
    # type (Union, ClassDict) -> type
    assert len(typ.types) >= 1, "Encountered a Union with zero types"
    return type(
        str(typ.name),
        (types.Union,),
        {
            "__doc__": typ.desc,
            "__args__": tuple(objs[o.name] for o in typ.types),
        },
    )


def inputobject_as_type(typ, module):
    # type (InputObject, str) -> Type[types.InputObject]
    return type(
        str(typ.name),
        (types.InputObject,),
        {"__doc__": typ.desc, "__raw__": typ, "__module__": module},
    )


def _add_fields(obj, classes):
    for f in obj.__raw__.fields:
        setattr(
            obj,
            f.name,
            types.FieldDefinition(
                name=f.name,
                desc=f.desc,
                args=FrozenDict(
                    {
                        i.name: types.InputValueDefinition(
                            name=i.name,
                            desc=i.desc,
                            type=resolve_typeref(i.type, classes),
                        )
                        for i in f.args
                    }
                ),
                is_deprecated=f.is_deprecated,
                deprecation_reason=f.deprecation_reason,
                type=resolve_typeref(f.type, classes),
            ),
        )
    del obj.__raw__
    return obj


def _add_input_fields(obj: Type[types.InputObject], classes):
    # TODO: fix this duplication of data
    obj.__input_fields__ = {
        f.name: types.InputValueDefinition(
            f.name, f.desc, type=resolve_typeref(f.type, classes)
        )
        for f in obj.__raw__.input_fields
    }
    for f in obj.__raw__.input_fields:
        setattr(
            obj,
            f.name,
            types.InputObjectFieldDescriptor(obj.__input_fields__[f.name]),
        )
    del obj.__raw__


def resolve_typeref(ref, classes):
    # type: (TypeRef, ClassDict) -> type
    if ref.kind is Kind.NON_NULL:
        return _resolve_typeref_required(ref.of_type, classes)
    else:
        return types.Nullable[_resolve_typeref_required(ref, classes)]


def _resolve_typeref_required(ref, classes):
    assert ref.kind is not Kind.NON_NULL
    if ref.kind is Kind.LIST:
        return types.List[resolve_typeref(ref.of_type, classes)]
    return classes[ref.name]


class _QueryCreator(object):
    def __init__(self, schema):
        self.schema = schema

    def __getitem__(self, selection_set):
        cls = self.schema.query_type
        return Query(
            cls, selections=types.validate_selection_set(cls, selection_set)
        )


@add_slots
@dataclass(frozen=True, repr=False)
class Schema:
    """A GraphQL schema.

    Use :meth:`~Schema.from_path`, :meth:`~Schema.from_url`,
    or :meth:`~Schema.from_raw` to instantiate.
    """

    classes: ClassDict
    query_type: type
    mutation_type: t.Optional[type]
    subscription_type: t.Optional[type]
    module: t.Optional[str]
    raw: RawSchema

    def __getattr__(self, name):
        try:
            return self.classes[name]
        except KeyError:
            raise AttributeError(name)

    def __dir__(self):
        return list(
            chain(
                self.classes,
                (f.name for f in fields(self.__class__)),
                dir(super(Schema, self)),
            )
        )

    def __repr__(self):
        return "quiz.Schema(module={})".format(self.module)

    def populate_module(self):
        """Populate the schema's module with the schema's classes

        Note
        ----
        The schema's ``module`` must be set (i.e. not ``None``)

        Raises
        ------
        RuntimeError
            If the schema module is not set
        """
        # TODO: this is a bit ugly
        if self.module is None:
            raise RuntimeError("schema.module is not set")
        module_obj = sys.modules[self.module]
        for name, cls in self.classes.items():
            setattr(module_obj, name, cls)

    # interim object to allow slice syntax: Schema.query[...]
    @property
    def query(self):
        """Creator for a query operation

        Example
        -------

        >>> from quiz import _
        >>> str(schema.query[
        ...     _
        ...     .field1
        ...     .foo
        ... ])
        query {
          field1
          foo
        }
        """
        return _QueryCreator(self)

    @classmethod
    def from_path(cls, path, module=None, scalars=()):
        """Create a :class:`Schema` from a JSON at a path

        Parameters
        ----------
        path: str or ~os.PathLike
            The path to the raw schema JSON file.
        module: ~typing.Optional[str], optional
            The name of the module to use when creating the schema's classes.
        scalars: ~typing.Iterable[~typing.Type[Scalar]]
            :class:`~quiz.types.Scalar` classes to use in the schema.
            Scalars in the schema, but not in this collection, will be defined
            as :class:`~quiz.types.AnyScalar` subclasses.

        Returns
        -------
        Schema
            The generated schema

        Raises
        ------
        IOError
            If the file at given path cannot be read
        """
        with open(fspath(path)) as rfile:
            return cls.from_raw(
                json.load(rfile), module=module, scalars=scalars
            )

    def to_path(self, path):
        """Dump the schema as JSON to a path

        Parameters
        ----------
        path: str or ~os.PathLike
            The path to write the raw schema to
        """
        with open(fspath(path), "w") as wfile:
            json.dump(self.raw, wfile)

    @classmethod
    def from_raw(cls, raw_schema, module=None, scalars=()):
        """Create a :class:`Schema` from a raw JSON schema

        Parameters
        ----------
        raw_schema: ~typing.List[~typing.Dict[str, JSON]]
            The raw GraphQL schema.
            I.e. the result of the :data:`INTROSPECTION_QUERY`
        module: ~typing.Optional[str], optional
            The name of the module to use when creating classes
        scalars: ~typing.Iterable[~typing.Type[Scalar]]
            :class:`~quiz.types.Scalar` classes to use in the schema.
            Scalars in the schema, but not in this collection, will be defined
            as :class:`~quiz.types.AnyScalar` subclasses.

        Returns
        -------
        Schema
            The schema constructed from raw data
        """
        by_kind = defaultdict(list)
        for tp in _load_types(raw_schema):
            by_kind[tp.__class__].append(tp)

        scalars_by_name = _namedict(scalars)
        scalars_by_name.update(types.BUILTIN_SCALARS)
        scalars_by_name.update(
            (
                tp.name,
                type(str(tp.name), (types.AnyScalar,), {"__doc__": tp.desc}),
            )
            for tp in by_kind[Scalar]
            if tp.name not in scalars_by_name
        )

        interfaces = _namedict(
            map(partial(interface_as_type, module=module), by_kind[Interface])
        )
        enums = _namedict(
            map(partial(enum_as_type, module=module), by_kind[Enum])
        )
        objs = _namedict(
            map(
                partial(object_as_type, interfaces=interfaces, module=module),
                by_kind[Object],
            )
        )
        unions = _namedict(
            map(partial(union_as_type, objs=objs), by_kind[Union])
        )
        input_objects = _namedict(
            map(
                partial(inputobject_as_type, module=module),
                by_kind[InputObject],
            )
        )

        classes = merge(
            scalars_by_name, interfaces, enums, objs, unions, input_objects
        )

        # we can only add these after all classes have been created.
        for obj in chain(objs.values(), interfaces.values()):
            _add_fields(obj, classes)
        for obj in input_objects.values():
            _add_input_fields(obj, classes)

        return cls(
            classes,
            query_type=classes[raw_schema["queryType"]["name"]],
            mutation_type=(
                raw_schema["mutationType"]
                and classes[raw_schema["mutationType"]["name"]]
            ),
            subscription_type=(
                raw_schema["subscriptionType"]
                and classes[raw_schema["subscriptionType"]["name"]]
            ),
            module=module,
            raw=raw_schema,
        )

    @classmethod
    def from_url(cls, url, scalars=(), module=None, **kwargs):
        """Build a GraphQL schema by introspecting an API

        Parameters
        ----------
        url: str
            URL of the target GraphQL API
        scalars: ~typing.Iterable[~typing.Type[Scalar]]
            :class:`~quiz.types.Scalar` classes to use in the schema.
            Scalars in the schema, but not in this sequence, will be defined as
            :class:`~quiz.types.AnyScalar` subclasses.

        module: ~typing.Optional[str], optional
            The module name to set on the generated classes
        **kwargs
            ``auth`` or ``client``, passed to :func:`~quiz.execution.execute`.

        Returns
        -------
        Schema
            The generated schema

        Raises
        ------
        ~quiz.types.ErrorResponse
            If there are errors in the response data
        """
        result = execute(INTROSPECTION_QUERY, url=url, **kwargs)
        return cls.from_raw(result["__schema"], scalars=scalars, module=module)

    # TODO: from_url_async


def _load_types(raw_schema):
    # type RawSchema -> Iterable[TypeSchema]
    return map(
        lambda typ: KIND_CAST[typ.kind](typ),
        map(_deserialize_type, raw_schema["types"]),
    )


INTROSPECTION_QUERY = """
{
  __schema {
    queryType { name }
    mutationType { name }
    subscriptionType { name }
    types {
      ...FullType
    }
  }
}

fragment FullType on __Type {
  kind
  name
  description
  fields(includeDeprecated: true) {
    name
    description
    args {
      ...InputValue
    }
    type {
      ...TypeRef
    }
    isDeprecated
    deprecationReason
  }
  inputFields {
    ...InputValue
  }
  interfaces {
    ...TypeRef
  }
  enumValues(includeDeprecated: true) {
    name
    description
    isDeprecated
    deprecationReason
  }
  possibleTypes {
    ...TypeRef
  }
}

fragment InputValue on __InputValue {
  name
  description
  type { ...TypeRef }
  defaultValue
}

fragment TypeRef on __Type {
  kind
  name
  ofType {
    kind
    name
    ofType {
      kind
      name
      ofType {
        kind
        name
      }
    }
  }
}
"""
"""Query to retrieve the raw schema"""


class Kind(enum.Enum):
    OBJECT = "OBJECT"
    SCALAR = "SCALAR"
    NON_NULL = "NON_NULL"
    LIST = "LIST"
    INTERFACE = "INTERFACE"
    ENUM = "ENUM"
    INPUT_OBJECT = "INPUT_OBJECT"
    UNION = "UNION"


@add_slots
@dataclass(frozen=True)
class TypeRef:
    name: t.Optional[str]
    kind: Kind
    of_type: t.Optional["TypeRef"]


@add_slots
@dataclass(frozen=True)
class InputValue:
    name: str
    desc: str
    type: TypeRef
    default: object


@add_slots
@dataclass(frozen=True)
class Field:
    name: str
    type: TypeRef
    args: t.List[InputValue]
    desc: str
    is_deprecated: bool
    deprecation_reason: t.Optional[str]


@add_slots
@dataclass(frozen=True)
class Type:
    name: t.Optional[str]
    kind: Kind
    desc: str
    fields: t.Optional[t.List[Field]]
    input_fields: t.Optional[t.List["InputValue"]]
    interfaces: t.Optional[t.List[TypeRef]]
    possible_types: t.Optional[t.List[TypeRef]]
    enum_values: t.Optional[t.List["EnumValue"]]


@add_slots
@dataclass(frozen=True)
class EnumValue:
    name: str
    desc: str
    is_deprecated: bool
    deprecation_reason: t.Optional[str]


KIND_CAST = {
    Kind.SCALAR: lambda typ: Scalar(name=typ.name, desc=typ.desc),
    Kind.OBJECT: lambda typ: Object(
        name=typ.name,
        desc=typ.desc,
        interfaces=typ.interfaces,
        input_fields=typ.input_fields,
        fields=typ.fields,
    ),
    Kind.INTERFACE: lambda typ: Interface(
        name=typ.name, desc=typ.desc, fields=typ.fields
    ),
    Kind.ENUM: lambda typ: Enum(
        name=typ.name, desc=typ.desc, values=typ.enum_values
    ),
    Kind.UNION: lambda typ: Union(
        name=typ.name, desc=typ.desc, types=typ.possible_types
    ),
    Kind.INPUT_OBJECT: lambda typ: InputObject(
        name=typ.name, desc=typ.desc, input_fields=typ.input_fields
    ),
}


def make_inputvalue(conf):
    return InputValue(
        name=conf["name"],
        desc=conf["description"],
        type=make_typeref(conf["type"]),
        default=conf["defaultValue"],
    )


def make_typeref(conf):
    return TypeRef(
        name=conf["name"],
        kind=Kind(conf["kind"]),
        of_type=conf.get("ofType") and make_typeref(conf["ofType"]),
    )


def make_field(conf):
    return Field(
        name=conf["name"],
        type=make_typeref(conf["type"]),
        args=list(map(make_inputvalue, conf["args"])),
        desc=conf["description"],
        is_deprecated=conf["isDeprecated"],
        deprecation_reason=conf["deprecationReason"],
    )


def make_enumval(conf):
    return EnumValue(
        name=conf["name"],
        desc=conf["description"],
        is_deprecated=conf["isDeprecated"],
        deprecation_reason=conf["deprecationReason"],
    )


def _deserialize_type(conf):
    # type: (t.Dict[str, JSON]) -> Type
    return Type(
        name=conf["name"],
        kind=Kind(conf["kind"]),
        desc=conf["description"],
        fields=conf["fields"] and list(map(make_field, conf["fields"])),
        input_fields=conf["inputFields"]
        and list(map(make_inputvalue, conf["inputFields"])),
        interfaces=conf["interfaces"]
        and list(map(make_typeref, conf["interfaces"])),
        possible_types=conf["possibleTypes"]
        and list(map(make_typeref, conf["possibleTypes"])),
        enum_values=conf["enumValues"]
        and list(map(make_enumval, conf["enumValues"])),
    )


@add_slots
@dataclass(frozen=True)
class Interface:
    name: str
    desc: str
    fields: t.List[Field]


@add_slots
@dataclass(frozen=True)
class Object:
    name: str
    desc: str
    interfaces: t.List[TypeRef]
    fields: t.List[Field]


@add_slots
@dataclass(frozen=True)
class Scalar:
    name: str
    desc: str


@add_slots
@dataclass(frozen=True)
class Enum:
    name: str
    desc: str
    values: t.List[EnumValue]


@add_slots
@dataclass(frozen=True)
class Union:
    name: str
    desc: str
    types: t.List[TypeRef]


@add_slots
@dataclass(frozen=True)
class InputObject:
    name: str
    desc: str
    input_fields: t.List[InputValue]


TypeSchema = t.Union[Interface, Object, Scalar, Enum, Union, InputObject]

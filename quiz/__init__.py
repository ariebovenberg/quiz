import abc
import enum
import json
import typing as t
from collections import defaultdict
from dataclasses import dataclass
from functools import partial
from itertools import chain
from operator import attrgetter, methodcaller
from textwrap import indent
from types import ModuleType, SimpleNamespace

import snug
from toolz import compose

INDENT = '  '
NEWLINE = ''
URL = 'https://api.github.com/graphql'

INTROSPECTION_QUERY = '''\
query IntrospectionQuery {
  __schema {
    queryType {
      name
    }
    mutationType {
      name
    }
    subscriptionType {
      name
    }
    types {
      ...FullType
    }
    directives {
      name
      description
      args {
        ...InputValue
      }
      onOperation
      onFragment
      onField
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
}'''

gql = methodcaller('__gql__')


@dataclass
class Attribute:
    name: str

    def __gql__(self):
        return self.name

    def __repr__(self):
        return f'.{self.name}'


@dataclass
class FieldSequence:
    __fields__: t.Tuple[Attribute]

    def __getattr__(self, name):
        return FieldSequence(self.__fields__ + (Attribute(name), ))

    def __getitem__(self, key):
        name = self.__fields__[-1].name
        return FieldSequence(
            self.__fields__[:-1]
            + (NestedObject(name, key.__fields__), )
        )

    def __repr__(self):
        return 'FieldSequence({!r})'.format(list(self.__fields__))

    def __gql__(self):
        return '\n'.join(map(gql, self.__fields__))


@dataclass
class NestedObject:
    name: str
    fields: FieldSequence

    def __repr__(self):
        return 'Nested({}, {})'.format(self.name, list(self.fields))

    def __gql__(self):
        inner = '\n'.join(map(gql, self.fields))
        return '{} {{\n{}\n}}'.format(self.name, indent(inner, INDENT))


class WithAttributes:

    def __getitem__(self, key):
        return SlicedObject(self, key)


@dataclass
class SlicedObject(snug.Query):
    obj: object
    fields: FieldSequence

    def __gql__(self):
        return '{{\n{}\n}}'.format(indent(gql(self.fields), INDENT))

    def __iter__(self):
        response = yield snug.Request('POST', URL, content=json.dumps({
            'query': gql(self)
        }))
        return json.loads(response.content)


F = FieldSequence(())


class Kind(enum.Enum):
    OBJECT = 'OBJECT'
    SCALAR = 'SCALAR'
    NON_NULL = 'NON_NULL'
    LIST = 'LIST'
    INTERFACE = 'INTERFACE'
    ENUM = 'ENUM'
    INPUT_OBJECT = 'INPUT_OBJECT'
    UNION = 'UNION'


class TypeRef(t.NamedTuple):
    name:    t.Optional[str]
    kind:    Kind
    of_type: t.Optional['TypeRef']


class InputValue(t.NamedTuple):
    name:    str
    desc:    str
    type:    TypeRef
    default: object


class Field(t.NamedTuple):
    name:               str
    type:               TypeRef
    args:               t.List[InputValue]
    desc:               str
    is_deprecated:      bool
    deprecation_reason: t.Optional[str]


class GeneralType(t.NamedTuple):
    name:           t.Optional[str]
    kind:           Kind
    desc:           str
    fields:         t.Optional[t.List[Field]]
    input_fields:   t.Optional[t.List['InputValue']]
    interfaces:     t.Optional[t.List[TypeRef]]
    possible_types: t.Optional[t.List[TypeRef]]
    enum_values:    t.Optional[t.List]


class EnumValue(t.NamedTuple):
    name: str
    desc: str
    is_deprecated: bool
    deprecation_reason: t.Optional[str]


def make_inputvalue(conf):
    return InputValue(
        name=conf['name'],
        desc=conf['description'],
        type=make_typeref(conf['type']),
        default=conf['defaultValue'],
    )


def make_typeref(conf):
    return TypeRef(
        name=conf['name'],
        kind=Kind(conf['kind']),
        of_type=conf.get('ofType') and make_typeref(conf['ofType'])
    )


def make_field(conf):
    return Field(
        name=conf['name'],
        type=make_typeref(conf['type']),
        args=list(map(make_inputvalue, conf['args'])),
        desc=conf['description'],
        is_deprecated=conf['isDeprecated'],
        deprecation_reason=conf['deprecationReason'],

    )


def make_enumval(conf):
    return EnumValue(
        name=conf['name'],
        desc=conf['description'],
        is_deprecated=conf['isDeprecated'],
        deprecation_reason=conf['deprecationReason'],
    )


def deserialize_type(conf) -> GeneralType:
    return GeneralType(
        name=conf['name'],
        kind=Kind(conf['kind']),
        desc=conf['description'],
        fields=conf['fields'] and list(map(make_field, conf['fields'])),
        input_fields=conf['inputFields'] and list(
            map(make_inputvalue, conf['inputFields'])),
        interfaces=conf['interfaces'] and list(
            map(make_typeref, conf['interfaces'])),
        possible_types=conf['possibleTypes'] and list(
            map(make_typeref, conf['possibleTypes'])),
        enum_values=conf['enumValues'] and list(
            map(make_enumval, conf['enumValues']))
    )


class Interface(t.NamedTuple):
    name:   str
    desc:   str
    fields: t.List[Field]


class Object(t.NamedTuple):
    name:         str
    desc:         str
    interfaces:   TypeRef
    input_fields: t.Optional[t.List[InputValue]]
    fields:       t.List[Field]


class Scalar(t.NamedTuple):
    name: str
    desc: str


class Enum(t.NamedTuple):
    name: str
    desc: str
    values: t.List[EnumValue]


class Union(t.NamedTuple):
    name: str
    desc: str
    types: t.List[TypeRef]


class InputObject(t.NamedTuple):
    name: str
    desc: str
    input_fields: t.List[InputValue]


Typelike = t.Union[
    Interface,
    Object,
    Scalar,
    Enum,
    Union,
    InputObject,
]


def cast_type(typ: GeneralType) -> Typelike:
    if typ.kind is Kind.SCALAR:
        assert typ.interfaces is None
        assert typ.input_fields is None
        assert typ.fields is None
        assert typ.possible_types is None
        assert typ.enum_values is None
        return Scalar(name=typ.name, desc=typ.desc)
    elif typ.kind is Kind.OBJECT:
        assert typ.enum_values is None
        assert typ.possible_types is None
        return Object(
            name=typ.name,
            desc=typ.desc,
            interfaces=typ.interfaces,
            input_fields=typ.input_fields,
            fields=typ.fields,
        )
    elif typ.kind is Kind.INTERFACE:
        assert typ.input_fields is None
        assert typ.interfaces is None
        assert typ.enum_values is None
        assert typ.possible_types is not None
        return Interface(
            name=typ.name,
            desc=typ.desc,
            fields=typ.fields,
        )
    elif typ.kind is Kind.ENUM:
        assert typ.interfaces is None
        assert typ.input_fields is None
        assert typ.fields is None
        assert typ.possible_types is None
        return Enum(
            name=typ.name,
            desc=typ.desc,
            values=typ.enum_values,
        )
    elif typ.kind is Kind.UNION:
        assert typ.interfaces is None
        assert typ.input_fields is None
        assert typ.fields is None
        return Union(
            name=typ.name,
            desc=typ.desc,
            types=typ.possible_types,
        )
    elif typ.kind is Kind.INPUT_OBJECT:
        assert typ.fields is None
        assert typ.interfaces is None
        assert typ.possible_types is None
        assert typ.enum_values is None
        return InputObject(
            name=typ.name,
            desc=typ.desc,
            input_fields=typ.input_fields,
        )
    else:
        raise NotImplementedError(type.kind)


def object_as_type(typ: Object,
                   interfaces: t.Mapping[str, abc.ABCMeta],
                   scalars: t.Mapping[str, type]) -> type:
    f = type(typ.name,
             tuple(interfaces[i.name] for i in typ.interfaces)
             + (WithAttributes, ),
             {**{field.name: make_stub(field, scalars=scalars)
                 for field in typ.fields},
              **{'__doc__': typ.desc}})
    return f


def make_typename(t: TypeRef, maybe_null: bool, scalars) -> str:
    if t.kind is Kind.NON_NULL:
        return make_typename(t.of_type, maybe_null=False, scalars=scalars)
    elif t.kind is Kind.LIST:
        return f'~typing.List[{make_typename(t.of_type, True, scalars)}]'
    elif maybe_null:
        return f'~typing.Optional[{make_typename(t, False, scalars)}]'
    else:
        return t.name


def make_stub(field: Field,
              scalars: t.Mapping[str, type]) -> abc.abstractproperty:

    def stub(*args, **kwargs):
        raise NotImplementedError()

    stub.__name__ = field.name
    stub.__doc__ = f'''\
    {field.desc}

    Returns
    -------
    {make_typename(field.type, True, scalars)}
    '''
    return abc.abstractproperty(stub)


def interface_as_type(typ: Interface, scalars):
    f = type(typ.name, (abc.ABC, ), {**{
        field.name: make_stub(field, scalars)
        for field in typ.fields
    }, **{
        '__doc__': typ.desc
    }})
    return f


def enum_as_type(typ: Enum):
    f = enum.Enum(typ.name, {v.name: v.name for v in typ.values})
    members_desc = '\n\n    '.join(map('``{0.name}`` - {0.desc}'.format,
                                       typ.values))
    f.__doc__ = f'''
    {typ.desc}

    **Members**:

    {members_desc} '''
    return f


def union_as_type(typ: Union, objs: t.Mapping[str, type]):
    union = type(typ.name, (abc.ABC, ), {})
    for o in typ.types:
        union.register(objs[o.name])
    union.__doc__ = '''\
    union of: {}
    '''.format(', '.join(o.name for o in typ.types))

    # union = t.Union[tuple(objs[o.name] for o in typ.types)]
    return union


def make_module(name: str, classes: t.Iterable[type]) -> ModuleType:

    my_module = ModuleType(name)
    for cls in classes:
        try:
            cls.__module__ = my_module.__name__
        except (AttributeError, TypeError):
            pass
        setattr(my_module, cls.__name__, cls)

    return my_module


def make_classes(schema: list,
                 scalars: t.Mapping[str, type]) -> t.Iterator[type]:
    loaded = map(compose(cast_type, deserialize_type), schema['types'])

    by_kind = defaultdict(list)
    for c in loaded:
        by_kind[c.__class__].append(c)

    interfaces = list(map(partial(interface_as_type, scalars=scalars),
                          by_kind[Interface]))
    scalars_ = map(compose(scalars.__getitem__, attrgetter('name')),
                   by_kind[Scalar])
    enums = map(enum_as_type, by_kind[Enum])
    objs = list(map(partial(object_as_type,
                            scalars=scalars,
                            interfaces={i.__name__: i for i in interfaces}),
                    by_kind[Object]))
    unions = map(partial(union_as_type,
                         objs={o.__name__: o for o in objs}),
                 by_kind[Union])

    return chain(interfaces, scalars_, enums, objs, unions)


def make_namespace(classes):
    by_name = {c.__name__: c for c in classes}
    # The query object is special
    return SimpleNamespace(**by_name, **{'query': by_name['Query']()})

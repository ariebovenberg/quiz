"""Functionality relating to the raw GraphQL schema"""
import enum
import typing as t

from ..compat import map

RawSchema = t.List[dict]

INTROSPECTION_QUERY = """
{
  __schema {
    queryType { name }
    mutationType { name }
    subscriptionType { name }
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
}
"""


class Kind(enum.Enum):
    OBJECT = "OBJECT"
    SCALAR = "SCALAR"
    NON_NULL = "NON_NULL"
    LIST = "LIST"
    INTERFACE = "INTERFACE"
    ENUM = "ENUM"
    INPUT_OBJECT = "INPUT_OBJECT"
    UNION = "UNION"


TypeRef = t.NamedTuple('TypeRef', [
    ('name', t.Optional[str]),
    ('kind', Kind),
    ('of_type', t.Optional['TypeRef']),
])
InputValue = t.NamedTuple('InputValue', [
    ('name', str),
    ('desc', str),
    ('type', TypeRef),
    ('default', object),
])
Field = t.NamedTuple('Field', [
    ('name', str),
    ('type', TypeRef),
    ('args', t.List[InputValue]),
    ('desc', str),
    ('is_deprecated', bool),
    ('deprecation_reason', t.Optional[str]),
])
Type = t.NamedTuple('Type', [
    ('name', t.Optional[str]),
    ('kind', Kind),
    ('desc', str),
    ('fields', t.Optional[t.List[Field]]),
    ('input_fields', t.Optional[t.List["InputValue"]]),
    ('interfaces', t.Optional[t.List[TypeRef]]),
    ('possible_types', t.Optional[t.List[TypeRef]]),
    ('enum_values', t.Optional[t.List]),
])
EnumValue = t.NamedTuple('EnumValue', [
    ('name', str),
    ('desc', str),
    ('is_deprecated', bool),
    ('deprecation_reason', t.Optional[str]),
])


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
    # type: Dict[str, JSON] -> Type
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


Interface = t.NamedTuple('Interface', [
    ('name', str),
    ('desc', str),
    ('fields', t.List[Field]),
])
Object = t.NamedTuple('Object', [
    ('name', str),
    ('desc', str),
    ('interfaces', t.List[TypeRef]),
    ('input_fields', t.Optional[t.List[InputValue]]),
    ('fields', t.List[Field]),
])
Scalar = t.NamedTuple('Scalar', [
    ('name', str),
    ('desc', str),
])
Enum = t.NamedTuple('Enum', [
    ('name', str),
    ('desc', str),
    ('values', t.List[EnumValue]),
])
Union = t.NamedTuple('Union', [
    ('name', str),
    ('desc', str),
    ('types', t.List[TypeRef]),
])
InputObject = t.NamedTuple('InputObject', [
    ('name', str),
    ('desc', str),
    ('input_fields', t.List[InputValue]),
])
TypeSchema = t.Union[Interface, Object, Scalar, Enum, Union, InputObject]


def _cast_type(typ):
    # type: Type -> TypeSchema
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
        return Interface(name=typ.name, desc=typ.desc, fields=typ.fields)
    elif typ.kind is Kind.ENUM:
        assert typ.interfaces is None
        assert typ.input_fields is None
        assert typ.fields is None
        assert typ.possible_types is None
        return Enum(name=typ.name, desc=typ.desc, values=typ.enum_values)
    elif typ.kind is Kind.UNION:
        assert typ.interfaces is None
        assert typ.input_fields is None
        assert typ.fields is None
        return Union(name=typ.name, desc=typ.desc, types=typ.possible_types)
    elif typ.kind is Kind.INPUT_OBJECT:
        assert typ.fields is None
        assert typ.interfaces is None
        assert typ.possible_types is None
        assert typ.enum_values is None
        return InputObject(
            name=typ.name, desc=typ.desc, input_fields=typ.input_fields
        )
    else:
        raise NotImplementedError(type.kind)


def load(raw_schema):
    # type RawSchema -> Iterable[TypeSchema]
    return (_cast_type(_deserialize_type(t)) for t in raw_schema['types'])

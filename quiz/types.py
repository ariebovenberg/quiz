"""Components for typed GraphQL interactions"""
import enum
import math
import typing as t
from dataclasses import dataclass
from itertools import chain, starmap
from operator import methodcaller

from .build import Field, InlineFragment, SelectionSet, dump_inputvalue, escape
from .utils import JSON, FrozenDict, add_slots

__all__ = [
    # types
    "AnyScalar",
    "Boolean",
    "Enum",
    "FieldDefinition",
    "Float",
    "ID",
    "InputObject",
    "InputObjectFieldDescriptor",
    "InputValue",
    "InputValueDefinition",
    "Int",
    "Interface",
    "List",
    "Nullable",
    "Object",
    "ResponseType",
    "Scalar",
    "String",
    "StringLike",
    "Union",
    # TODO: mutation
    # TODO: subscription
    # validation
    "validate",
    "ValidationError",
    "SelectionError",
    "NoSuchField",
    "NoSuchArgument",
    "SelectionsNotSupported",
    "InvalidArgumentType",
    "InvalidArgumentValue",
    "MissingArgument",
    "CouldNotCoerce",
    "NoValueForField",
    "load",
]

MIN_INT = -2 << 30
MAX_INT = (2 << 30) - 1


@add_slots
@dataclass(frozen=True)
class InputValueDefinition:
    name: str
    desc: str
    type: type


_PRIMITIVE_TYPES = (int, float, bool, str)


# TODO: make ABCMeta or generic?
class InputValue(object):
    """Base class for input value classes.
    These values may be used in GraphQL queries (requests)"""

    # TODO: make abstract
    def __gql_dump__(self):
        # type: () -> str
        """Serialize the object to a GraphQL primitive value"""
        raise NotImplementedError(
            "GraphQL serialization is not defined for this type"
        )

    # TODO: a sensible default implementation
    @classmethod
    def coerce(cls, value):
        raise NotImplementedError()


class InputWrapper(InputValue):
    """Base class for input values containing one value"""

    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        if type(self) == type(other):
            return self.value == other.value
        return NotImplemented

    def __repr__(self):
        return "{}({})".format(self.__class__.__name__, self.value)


# TODO: make ABCMeta/generic?
# TODO: rename to indicate it can be the parser, not the value itself?
class ResponseType(object):
    """Base class for response value classes.
    These classes are used to load GraphQL responses into (python) types"""

    # TODO: make abstract?
    @classmethod
    def __gql_load__(cls, data):
        """Load an instance from GraphQL"""
        raise NotImplementedError(
            "GraphQL deserialization is not defined for this type"
        )


class HasFields(type):
    """metaclass for classes with GraphQL field definitions"""

    def __getitem__(self, selection_set):
        # type: (SelectionSet) -> InlineFragment
        return InlineFragment(self, validate(self, selection_set))


class Namespace(object):
    def __init__(__self, **kwargs):
        __self.__dict__.update(kwargs)

    def __fields__(self):
        return {k: v for k, v in self.__dict__.items() if k != "__metadata__"}

    def __eq__(self, other):
        if type(self) == type(other):
            return self.__fields__() == other.__fields__()
        return NotImplemented

    def __repr__(self):
        return "{}({})".format(
            self.__class__.__qualname__,
            ", ".join(starmap("{}={!r}".format, self.__dict__.items())),
        )


class Object(Namespace, metaclass=HasFields):
    """a graphQL object"""


@add_slots
@dataclass(frozen=True)
class InputObjectFieldDescriptor:
    value: InputValueDefinition

    def __get__(self, obj, objtype=None):
        if obj is None:  # accessing on class
            return self
        try:
            return obj.__dict__[self.value.name]
        except KeyError:
            raise NoValueForField()

    # full descriptor interface is necessary to be displayed nicely in help()
    def __set__(self, obj, value):
        raise AttributeError("Can't set field value")

    # TODO: instead of type.__name__, use something different, explicit
    # __doc__ allows descriptor to be displayed nicely in help()
    @property
    def __doc__(self):
        return ": {.__name__}\n    {}".format(self.value.type, self.value.desc)


# TODO: slots?
# TODO: coercing from dict?
class InputObject(object):
    """Base class for input objects"""

    __input_fields__ = FrozenDict.EMPTY

    def __init__(__self__, **kwargs):
        self = __self__  # prevents `self` from potentially clobbering kwargs
        argnames_defined = self.__input_fields__.keys()
        argnames_required = {
            name
            for name, obj in self.__input_fields__.items()
            if not issubclass(obj.type, Nullable)
        }
        argnames_given = kwargs.keys()

        invalid_argnames = argnames_given - argnames_defined
        if invalid_argnames:
            raise NoSuchArgument(
                "invalid arguments: {}".format(", ".join(invalid_argnames))
            )

        missing_argnames = argnames_required - argnames_given
        if missing_argnames:
            raise MissingArgument(
                "invalid arguments: {}".format(", ".join(missing_argnames))
            )

        self.__dict__.update(kwargs)

    def __eq__(self, other):
        if type(self) == type(other):
            return self.__dict__ == other.__dict__
        return NotImplemented

    def __gql_dump__(self):
        return "{{{}}}".format(
            " ".join(
                "{}: {}".format(name, dump_inputvalue(value))
                for name, value in self.__dict__.items()
            )
        )

    def __repr__(self):
        return "{}({})".format(
            self.__class__.__qualname__,
            ", ".join(starmap("{}={!r}".format, self.__dict__.items())),
        )


class Enum(InputValue, ResponseType, enum.Enum):
    """A GraphQL enum value. Accepts strings as inputs"""

    @classmethod
    def coerce(cls, value):
        # type: (object) -> Enum
        try:
            return cls(value)
        except ValueError:
            raise CouldNotCoerce(
                "{!r} is not a valid {.__name__}".format(value, cls)
            )

    def __gql_dump__(self):
        # type: () -> str
        return self.value

    def __repr__(self):
        return ".".join([self.__class__.__qualname__, self.value])

    @classmethod
    def __gql_load__(cls, data):
        return cls(data)


class Interface(HasFields):
    """metaclass for interfaces"""


class NoValueForField(AttributeError):
    """Indicates a value cannot be retrieved for the field"""


@add_slots
@dataclass(frozen=True)
class CouldNotCoerce(ValueError):
    """Could not coerce a value"""

    reason: str


@add_slots
@dataclass(frozen=True)
class FieldDefinition:
    name: str
    desc: str
    type: type
    args: FrozenDict[str, InputValueDefinition]
    is_deprecated: bool
    deprecation_reason: t.Optional[str]

    def __get__(self, obj, objtype=None):
        if obj is None:  # accessing on class
            return self
        try:
            return obj.__dict__[self.name]
        except KeyError:
            raise NoValueForField()

    # full descriptor interface is necessary to be displayed nicely in help()
    def __set__(self, obj, value):
        raise AttributeError("Can't set field value")

    # __doc__ allows descriptor to be displayed nicely in help()
    @property
    def __doc__(self):
        return ": {.__name__}\n    {}".format(self.type, self.desc)


class _Generic(type):
    def __eq__(self, other):
        if isinstance(other, type(self)):
            return self.__arg__ == other.__arg__
        return NotImplemented


class _ListMeta(_Generic):

    # TODO: a better autogenerated name
    def __getitem__(self, arg):
        return type("List[{.__name__}]".format(arg), (List,), {"__arg__": arg})

    def __instancecheck__(self, instance):
        return isinstance(instance, list) and all(
            isinstance(i, self.__arg__) for i in instance
        )


# Q: why not typing.List?
# A: it doesn't support __doc__, __name__, or isinstance()
# TODO: a separate class for input value lists?
class List(InputWrapper, ResponseType, metaclass=_ListMeta):
    __arg__ = object

    @classmethod
    def coerce(cls, data):
        # type: (object) -> List
        if isinstance(data, list):
            return cls(list(map(cls.__arg__.coerce, data)))
        else:
            raise CouldNotCoerce("Invalid type, must be a list")

    def __gql_dump__(self):
        # type: () -> str
        return "[{}]".format(
            " ".join(map(methodcaller("__gql_dump__"), self.value))
        )

    @classmethod
    def __gql_load__(cls, data):
        return list(map(cls.__arg__.__gql_load__, data))


class _NullableMeta(_Generic):

    # TODO: a better autogenerated name
    def __getitem__(self, arg):
        return type(
            "Nullable[{.__name__}]".format(arg), (Nullable,), {"__arg__": arg}
        )

    def __instancecheck__(self, instance):
        return instance is None or isinstance(instance, self.__arg__)


# Q: why not typing.Optional?
# A: it is not easily distinguished from Union,
#    and doesn't support __doc__, __name__, or isinstance()
class Nullable(InputWrapper, ResponseType, metaclass=_NullableMeta):
    __arg__ = object

    @classmethod
    def coerce(cls, data):
        # type: (object) -> Nullable
        return cls(data if data is None else cls.__arg__.coerce(data))

    def __gql_dump__(self):
        # type: () -> str
        return "null" if self.value is None else self.value.__gql_dump__()

    @classmethod
    def __gql_load__(cls, data):
        return data if data is None else cls.__arg__.__gql_load__(data)


# TODO: add __getitem__, similar to list and nullable
class UnionMeta(type):
    pass


# Q: why not typing.Union?
# A: it isn't consistent across python versions,
#    and doesn't support __doc__, __name__, or isinstance()
class Union(object, metaclass=UnionMeta):
    __args__ = ()


class Scalar(InputWrapper, ResponseType):
    """Base class for scalars"""


class _AnyScalarMeta(type):
    def __instancecheck__(self, instance):
        return isinstance(instance, _PRIMITIVE_TYPES)


class AnyScalar(Scalar, metaclass=_AnyScalarMeta):
    """A generic scalar, accepting any primitive type"""

    def __init__(self, value):
        self.value = value

    @classmethod
    def coerce(cls, data):
        if data is None or isinstance(data, Scalar):
            return cls(data)
        try:
            gql_type = PY_TYPE_TO_GQL_TYPE[type(data)]
        except KeyError:
            raise CouldNotCoerce("Invalid type, must be a scalar")
        return cls(gql_type.coerce(data))

    def __gql_dump__(self):
        # type: () -> str
        if self.value is None:
            return "null"
        else:
            return self.value.__gql_dump__()

    @classmethod
    def __gql_load__(cls, data):
        # type: (T) -> T
        return data


class Float(InputWrapper, ResponseType):
    """A GraphQL float object. The main difference with :class:`float`
    is that it may not be infinite or NaN"""

    # TODO: consistent types of exceptions to raise
    @classmethod
    def coerce(cls, value):
        # type: (object) -> Float
        if not isinstance(value, (float, int)):
            raise CouldNotCoerce("Invalid type, must be float or int")
        if math.isnan(value) or math.isinf(value):
            raise CouldNotCoerce("Float value cannot be infinite or NaN")
        return cls(float(value))

    def __gql_dump__(self):
        return str(self.value)

    @classmethod
    def __gql_load__(cls, data):
        # type: (Union[float, int]) -> float
        return float(data)


class Int(InputWrapper, ResponseType):
    """A GraphQL integer object. The main difference with :class:`int`
    is that it may only represent integers up to 32 bits in size"""

    @classmethod
    def coerce(cls, value):
        # type: (object) -> Int
        if not isinstance(value, int):
            raise CouldNotCoerce("Invalid type, must be int")
        if not MIN_INT < value < MAX_INT:
            raise CouldNotCoerce(
                "{} is not representable by a 32-bit integer".format(value)
            )
        return cls(int(value))

    def __gql_dump__(self):
        return str(self.value)

    @classmethod
    def __gql_load__(cls, data):
        # type: (int) -> int
        return data


class Boolean(InputWrapper, ResponseType):
    """A GraphQL boolean object"""

    @classmethod
    def coerce(cls, value):
        # type: (object) -> Boolean
        if isinstance(value, bool):
            return cls(value)
        else:
            raise CouldNotCoerce("A boolean type is required")

    def __gql_dump__(self):
        return "true" if self.value else "false"

    @classmethod
    def __gql_load__(cls, data):
        # type: (bool) -> bool
        return data


class StringLike(InputWrapper, ResponseType):
    """Base for string-like types"""

    @classmethod
    def coerce(cls, value):
        # type: (object) -> StringLike
        if isinstance(value, str):
            return cls(value)
        else:
            raise CouldNotCoerce("A string type is required")

    def __gql_dump__(self):
        return '"{}"'.format(escape(self.value))

    @classmethod
    def __gql_load__(cls, data):
        # type: (str) -> str
        return data


class String(StringLike):
    """GraphQL text type"""


class ID(StringLike):
    """A GraphQL ID. Serialized the same way as a string"""


def _unwrap_list_or_nullable(type_):
    # type: t.Type[Nullable, List, Scalar, Enum, InputObject]
    # -> Type[Scalar | Enum | InputObject]
    if issubclass(type_, (Nullable, List)):
        return _unwrap_list_or_nullable(type_.__arg__)
    return type_


def validate_value(
    name: str, typ: t.Type[InputValue], value: object,
) -> t.Union[InputValue, "InvalidArgumentValue"]:
    # TODO: proper isinstance
    if type(value) == typ:
        return value
    else:
        try:
            return typ.coerce(value)
        except CouldNotCoerce as e:
            return InvalidArgumentValue(name, value, e.reason)


# TODO: make generic
class ValidationResult:
    pass


@add_slots
@dataclass(frozen=True)
class Errors(ValidationResult):
    items: t.Set["ValidationError"]


# TODO: typing
@add_slots
@dataclass(frozen=True)
class Valid(ValidationResult):
    value: object


def validate_args(schema, actual):
    # type: (t.Mapping[str, InputValueDefinition], t.Mapping[str, object])
    # -> ValidationResult[t.Mapping[str, object]]
    # TODO: cleanup this logic
    required_args = {
        name
        for name, defin in schema.items()
        if not issubclass(defin.type, Nullable)
    }
    errors = set(
        chain(
            map(NoSuchArgument, actual.keys() - schema.keys()),
            map(MissingArgument, required_args - actual.keys()),
        )
    )
    coerced = {
        name: validate_value(name, schema[name].type, value)
        for name, value in actual.items()
        if name in schema
    }
    errors.update(
        v for v in coerced.values() if isinstance(v, InvalidArgumentValue)
    )
    return Errors(errors) if errors else Valid(coerced)


def _validate_args(schema, actual):
    # type: (t.Mapping[str, InputValueDefinition], t.Mapping[str, object])
    # -> t.Mapping[str, object]
    invalid_args = actual.keys() - schema.keys()
    if invalid_args:
        raise NoSuchArgument(invalid_args.pop())
    required_args = {
        name
        for name, defin in schema.items()
        if not issubclass(defin.type, Nullable)
    }
    missing_args = required_args - actual.keys()
    if missing_args:
        # TODO: return all missing args
        raise MissingArgument(missing_args.pop())

    for input_value in schema.values():
        try:
            value = actual[input_value.name]
        except KeyError:
            continue  # arguments of nullable type may be omitted

        if not isinstance(value, input_value.type):
            raise InvalidArgumentType(input_value.name, value)

    return actual


def _validate_field(schema, actual):
    # type (Optional[FieldDefinition], Field) -> Field
    # raises:
    # - NoSuchField
    # - SelectionsNotSupported
    # - NoSuchArgument
    # - RequredArgument
    # - InvalidArgumentType
    if schema is None:
        raise NoSuchField()
    _validate_args(schema.args, actual.kwargs)
    if actual.selection_set:
        type_ = _unwrap_list_or_nullable(schema.type)
        if not isinstance(type_, HasFields):
            raise SelectionsNotSupported()
        validate(type_, actual.selection_set)
    return actual


def validate(cls, selection_set):
    """Validate a selection set against a type

    Parameters
    ----------
    cls: type
        The class to validate against, an ``Object`` or ``Interface``
    selection_set: SelectionSet
        The selection set to validate

    Returns
    -------
    SelectionSet
        The validated selection set

    Raises
    ------
    SelectionError
        If the selection set is not valid
    """
    for _field in selection_set:
        try:
            _validate_field(getattr(cls, _field.name, None), _field)
        except ValidationError as e:
            raise SelectionError(cls, _field.name, e)
    return selection_set


T = t.TypeVar("T")


# TODO: refactor using singledispatch
# TODO: cleanup this API: ``field`` is often unneeded. unify with ``load``?
def load_field(type_, field, value):
    # type: (t.Type[T], Field, JSON) -> T
    if issubclass(type_, Namespace):
        assert isinstance(value, dict)
        return load(type_, field.selection_set, value)
    elif issubclass(type_, Nullable):
        return (
            None if value is None else load_field(type_.__arg__, field, value)
        )
    elif issubclass(type_, List):
        assert isinstance(value, list)
        return [load_field(type_.__arg__, field, v) for v in value]
    elif issubclass(type_, _PRIMITIVE_TYPES):
        assert isinstance(value, type_)
        return value
    elif issubclass(type_, AnyScalar):
        assert isinstance(value, type_)
        return value
    elif issubclass(type_, Scalar):
        return type_.__gql_load__(value)
    elif issubclass(type_, Enum):
        assert value, type_._members_names_
        return type_(value)
    else:
        raise NotImplementedError()


def load(cls, selection_set, response):
    """Load a response for a selection set

    Parameters
    ----------
    cls: Type[T]
        The class to load against, an ``Object`` or ``Interface``
    selection_set: SelectionSet
        The selection set to validate
    response: t.Mapping[str, JSON]
        The JSON response data

    Returns
    -------
    T
        An instance of ``cls``
    """
    instance = cls(
        **{
            field.alias
            or field.name: load_field(
                getattr(cls, field.name).type,
                field,
                response[field.alias or field.name],
            )
            for field in selection_set
        }
    )
    # TODO: do this in a cleaner way
    if hasattr(response, "__metadata__"):
        instance.__metadata__ = response.__metadata__
    return instance


class ValidationError(Exception):
    """base class for validation errors"""


@add_slots
@dataclass(frozen=True)
class SelectionError(ValidationError):
    on: type
    path: str
    error: ValidationError

    def __str__(self):
        return '{} on "{}" at path "{}":\n\n    {}: {}'.format(
            self.__class__.__name__,
            self.on.__name__,
            self.path,
            self.error.__class__.__name__,
            self.error,
        )


@add_slots
@dataclass(frozen=True)
class NoSuchField(ValidationError):
    def __str__(self):
        return "field does not exist"


@add_slots
@dataclass(frozen=True)
class NoSuchArgument(ValidationError):
    name: str

    def __str__(self):
        return 'argument "{}" does not exist'.format(self.name)


@add_slots
@dataclass(frozen=True)
class InvalidArgumentValue(ValidationError):
    name: str
    value: object
    message: str


@add_slots
@dataclass(frozen=True)
class InvalidArgumentType(ValidationError):
    name: str
    value: object

    def __str__(self):
        return 'invalid value "{}" of type {} for argument "{}"'.format(
            self.value, type(self.value), self.name
        )


@add_slots
@dataclass(frozen=True)
class MissingArgument(ValidationError):
    name: str

    def __str__(self):
        return 'argument "{}" missing (required)'.format(self.name)


@add_slots
@dataclass(frozen=True)
class SelectionsNotSupported(ValidationError):
    def __str__(self):
        return "selections not supported on this object"


BUILTIN_SCALARS = {
    "Boolean": bool,
    "String": str,
    "Float": float,
    "Int": int,
}


PY_TYPE_TO_GQL_TYPE = {
    float: Float,
    int: Int,
    bool: Boolean,
    str: String,
}

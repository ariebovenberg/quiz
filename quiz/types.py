"""Components for typed GraphQL interactions"""
import abc
import enum
import math
import typing as t
from dataclasses import dataclass
from functools import partial
from itertools import chain, starmap
from operator import methodcaller
from textwrap import indent
from typing import Any, Callable, Generic, Iterable
from typing import List as List_
from typing import Mapping, Optional, Sequence, Set, Tuple, Type, TypeVar
from typing import Union as Union_

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

T = TypeVar("T")
U = TypeVar("U")
V = TypeVar("V")
E = TypeVar("E")
MIN_INT = -2 << 30
MAX_INT = (2 << 30) - 1
INDENT = "  "
_indent = partial(indent, prefix=INDENT)


# Ok/Err container, similar to Result in Rust, or Either.
class Result(Generic[T, E]):
    @abc.abstractmethod
    def map(self, f: Callable[[T], U]) -> "Result[U, E]":
        "Apply a function to the successful result, leaving errors untouched"

    @abc.abstractmethod
    def map_err(self, f: Callable[[E], V]) -> "Result[U, V]":
        "Apply a function to the error result, leaving the OK value untouched"

    @abc.abstractmethod
    def map_or_else(
        self, f: Callable[[T], U], fallback: Callable[[E], V]
    ) -> "Result[U, V]":
        """Apply a function to the successful result,
        or apply a fallback to the error result"""

    @abc.abstractmethod
    def is_ok(self) -> bool:
        "True if the result is Ok"

    @abc.abstractmethod
    def is_err(self) -> bool:
        "True if the result is Err"

    @abc.abstractmethod
    def ok(self) -> Optional[T]:
        "Return the Ok result if present"

    @abc.abstractmethod
    def err(self) -> Optional[E]:
        "Return the Err result if present"

    @staticmethod
    def sequence(
        results: Iterable["Result[T, E]"],
    ) -> "Result[Sequence[T], Sequence[Tuple[int, E]]]":
        oks: List[T] = []
        errs: List[Tuple[int, E]] = []
        for i, r in enumerate(results):
            if r.is_ok():
                oks.append(r.ok())
            else:
                errs.append((i, r.err()))
                break
        else:
            return Ok(oks)

        for i, r in enumerate(results, start=i + 1):
            if r.is_err():
                errs.append((i, r.err()))

        return Err(errs)


@add_slots
@dataclass(frozen=True)
class Ok(Result[T, E]):
    value: T

    def map(self, f: Callable[[T], U]) -> "Result[U, E]":
        return Ok(f(self.value))

    def map_err(self, f: Callable[[E], V]) -> Result[U, V]:
        return self

    def map_or_else(
        self, f: Callable[[T], U], fallback: Callable[[E], V]
    ) -> "Result[U, V]":
        return Ok(f(self.value))

    def is_ok(self) -> bool:
        return True

    def is_err(self) -> bool:
        return False

    def ok(self) -> Optional[T]:
        return self.value

    def err(self) -> Optional[E]:
        return None

    def __repr__(self) -> str:
        return f"Ok({self.value!r})"


@add_slots
@dataclass(frozen=True)
class Err(Result[T, E]):
    value: E

    def map(self, f: Callable[[T], U]) -> Result[U, E]:
        return self

    def map_err(self, f: Callable[[E], V]) -> Result[U, V]:
        return Err(f(self.value))

    def map_or_else(
        self, f: Callable[[T], U], fallback: Callable[[E], V]
    ) -> "Result[U, V]":
        return Err(fallback(self.value))

    def is_ok(self) -> bool:
        return False

    def is_err(self) -> bool:
        return True

    def ok(self) -> Optional[T]:
        return None

    def err(self) -> Optional[E]:
        return self.value

    def __repr__(self) -> str:
        return f"Err({self.value!r})"


@add_slots
@dataclass(frozen=True)
class InputValueDefinition:
    name: str
    desc: str
    type: type


_PRIMITIVE_TYPES = (int, float, bool, str)


class InputValue:
    """Base class for input value classes.
    These values may be used in GraphQL queries (requests)"""

    # TODO: make abstract
    def __gql_dump__(self) -> str:
        """Serialize the object to a GraphQL primitive value"""
        raise NotImplementedError(
            "GraphQL serialization is not defined for this type"
        )

    @classmethod
    def coerce(cls: Type[T], value: object) -> Result[T, str]:
        return Err(f"No coercion defined to type {cls!r}")


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


# TODO: rename to indicate it can be the parser, not the value itself?
class ResponseType:
    """Base class for response value classes.
    These classes are used to load GraphQL responses into (python) types"""

    # TODO: T can also be another type
    @classmethod
    def __gql_load__(cls: Type[T], data: str) -> T:
        """Load an instance from GraphQL"""
        raise NotImplementedError(
            "GraphQL deserialization is not defined for this type"
        )


class HasFields(type):
    """Metaclass for classes with GraphQL field definitions"""

    def __getitem__(self, selection_set: SelectionSet) -> InlineFragment:
        return InlineFragment(self, validate(self, selection_set))


class Namespace:
    def __init__(__self, **kwargs) -> None:
        __self.__dict__.update(kwargs)

    def __fields__(self) -> Mapping[str, object]:
        return {k: v for k, v in self.__dict__.items() if k != "__metadata__"}

    def __eq__(self, other: object) -> bool:
        if type(self) == type(other):
            return self.__fields__() == other.__fields__()
        return NotImplemented

    def __repr__(self) -> str:
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


class InputObject:
    """Base class for input objects"""

    __input_fields__ = FrozenDict.EMPTY

    @classmethod
    def coerce(cls: Type[T], value: object) -> Result[T, str]:
        if isinstance(value, dict):
            if all(isinstance(k, str) for k in value):
                result = validate_args(cls.__input_fields__, value)
                if isinstance(result, Err):
                    raise NotImplementedError()
                else:
                    return Ok(cls(**result.value))
            else:
                return Err("Dict with non-string key")
        else:
            return Err(f"Invalid type {type(value)!r}")

    def __init__(__self__, **kwargs) -> None:
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

    def __eq__(self, other: object) -> bool:
        if type(self) == type(other):
            return self.__dict__ == other.__dict__
        return NotImplemented

    def __gql_dump__(self) -> str:
        return "{{{}}}".format(
            " ".join(
                "{}: {}".format(name, dump_inputvalue(value))
                for name, value in self.__dict__.items()
            )
        )

    def __repr__(self) -> str:
        return "{}({})".format(
            self.__class__.__qualname__,
            ", ".join(starmap("{}={!r}".format, self.__dict__.items())),
        )


class Enum(InputValue, ResponseType, enum.Enum):
    """A GraphQL enum value. Accepts strings as inputs"""

    @classmethod
    def coerce(cls: Type[T], value: object) -> Result[T, str]:
        if isinstance(value, str):
            try:
                return Ok(cls(value))
            except ValueError:
                return Err(f"'{value}' is not a valid enum option.")
        else:
            return Err(f"Invalid type {type(value)}.")

    def __gql_dump__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return ".".join([self.__class__.__qualname__, self.value])

    @classmethod
    def __gql_load__(cls: Type[T], data: str) -> T:
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


# Q: why not typing.List?
# A: it doesn't support __doc__, __name__, or isinstance()
# TODO: a separate class for input value lists?
class List(InputWrapper, ResponseType, metaclass=_ListMeta):
    __arg__ = object

    @classmethod
    def coerce(cls: Type[T], data: object) -> Result[T, str]:
        if isinstance(data, list):
            subresults = map(partial(validate_value2, cls.__arg__), data)
            traversed = Result.sequence(subresults)
            return traversed.map_or_else(
                cls,
                fallback=lambda errs: "Invalid items in list:\n"
                + _indent(
                    "\n".join(
                        [f"at index {i}:\n{_indent(m)}" for i, m in errs]
                    )
                ),
            )
        else:
            return Err(f"Invalid type {type(data)}.")

    def __gql_dump__(self) -> str:
        return "[{}]".format(
            " ".join(map(methodcaller("__gql_dump__"), self.value))
        )

    @classmethod
    def __gql_load__(cls, data: str) -> list:
        return list(map(cls.__arg__.__gql_load__, data))


class _NullableMeta(_Generic):

    # TODO: a better autogenerated name
    def __getitem__(self, arg):
        return type(
            "Nullable[{.__name__}]".format(arg), (Nullable,), {"__arg__": arg}
        )


# Q: why not typing.Optional?
# A: it is not easily distinguished from Union,
#    and doesn't support __doc__, __name__, or isinstance()
class Nullable(InputWrapper, ResponseType, metaclass=_NullableMeta):
    __arg__ = object

    @classmethod
    def coerce(cls: Type[T], data: object) -> Result[T, str]:
        if data is None:
            return Ok(cls(None))
        else:
            return cls.__arg__.coerce(data).map(cls)
        return Ok(cls(data if data is None else cls.__arg__.coerce(data)))

    def __gql_dump__(self) -> str:
        return "null" if self.value is None else self.value.__gql_dump__()

    @classmethod
    def __gql_load__(cls, data: Any) -> Any:
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

    def __gql_dump__(self) -> str:
        if self.value is None:
            return "null"
        else:
            return self.value.__gql_dump__()

    @classmethod
    def __gql_load__(cls, data: T) -> T:
        return data


class Float(InputWrapper, ResponseType):
    """A GraphQL float object. The main difference with :class:`float`
    is that it may not be infinite or NaN"""

    @classmethod
    def coerce(cls: Type[T], value: object) -> Result[T, str]:
        if not isinstance(value, (float, int)):
            return Err(
                f"Can only coerce float or int, not {class_name(type(value))}."
            )
        elif math.isnan(value) or math.isinf(value):
            return Err("Value cannot be infinite or NaN.")
        return Ok(cls(float(value)))

    def __gql_dump__(self) -> str:
        return str(self.value)

    @classmethod
    def __gql_load__(cls, data: Union_[float, int]) -> float:
        return float(data)


class Int(InputWrapper, ResponseType):
    """A GraphQL integer object. The main difference with :class:`int`
    is that it may only represent integers up to 32 bits in size"""

    @classmethod
    def coerce(cls: Type[T], value: object) -> Result[T, str]:
        if not isinstance(value, int):
            return Err("Invalid type, must be int.")
        elif not MIN_INT < value < MAX_INT:
            return Err("Integer beyond 32-bit limit.")
        return Ok(cls(int(value)))

    def __gql_dump__(self) -> str:
        return str(self.value)

    @classmethod
    def __gql_load__(cls, data: int) -> int:
        return data


class Boolean(InputWrapper, ResponseType):
    """A GraphQL boolean object"""

    @classmethod
    def coerce(cls: Type[T], value: object) -> Result[T, str]:
        if isinstance(value, bool):
            return Ok(cls(value))
        else:
            return Err("Invalid type, must be bool.")

    def __gql_dump__(self) -> str:
        return "true" if self.value else "false"

    @classmethod
    def __gql_load__(cls, data: bool) -> bool:
        return data


class StringLike(InputWrapper, ResponseType):
    """Base for string-like types"""

    @classmethod
    def coerce(cls: Type[T], value: object) -> Result[T, str]:
        if isinstance(value, str):
            return Ok(cls(value))
        else:
            return Err("Invalid type, must be str.")

    def __gql_dump__(self) -> str:
        return '"{}"'.format(escape(self.value))

    @classmethod
    def __gql_load__(cls, data: str) -> str:
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


T_inputvalue = TypeVar("T", bound=InputValue)


def class_name(cls: Type) -> str:
    try:
        return cls.__name__
    except AttributeError:
        return str(cls)


def validate_value2(
    typ: t.Type[T_inputvalue], value: object
) -> Result[T_inputvalue, str]:
    if isinstance(value, typ):
        return Ok(value)
    else:
        return typ.coerce(value).map_err(
            lambda msg: f"Could not coerce to {class_name(typ)}:\n"
            + _indent(msg)
        )
        coerced = typ.coerce(value)
        if not isinstance(coerced, Ok):
            raise NotImplementedError()
        else:
            return Ok(coerced.value)


def validate_value(
    name: str, typ: t.Type[InputValue], value: object
) -> t.Union[InputValue, "InvalidArgumentValue"]:
    # TODO: proper isinstance
    if type(value) == typ:
        return value
    else:
        try:
            return typ.coerce(value)
        except CouldNotCoerce as e:
            return InvalidArgumentValue(name, value, e.reason)


def validate_args(
    schema: Mapping[str, InputValueDefinition], actual: Mapping[str, object]
) -> Result[Mapping[str, object], Set["ValidationError"]]:
    # -> Result[t.Mapping[str, object]]
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
    return Err(errors) if errors else Ok(coerced)


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


BUILTIN_SCALARS = {"Boolean": bool, "String": str, "Float": float, "Int": int}


PY_TYPE_TO_GQL_TYPE = {float: Float, int: Int, bool: Boolean, str: String}

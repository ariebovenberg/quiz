"""Components for typed GraphQL interactions"""
import enum
import typing as t
from itertools import starmap

from .build import Field, InlineFragment, SelectionSet
from .utils import JSON, FrozenDict, ValueObject

__all__ = [
    # types
    "Enum",
    "Union",
    "GenericScalar",
    "Scalar",
    "List",
    "Interface",
    "Object",
    "Nullable",
    "FieldDefinition",
    "InputValue",
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
    "MissingArgument",
    "NoValueForField",
    "load",
]


InputValue = t.NamedTuple(
    "InputValue", [("name", str), ("desc", str), ("type", type)]
)

_PRIMITIVE_TYPES = (int, float, bool, str)


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


class InputObject(object):
    """not yet implemented"""


# separate class to distinguish graphql enums from normal Enums
class Enum(enum.Enum):
    pass


class Interface(HasFields):
    """metaclass for interfaces"""


class NoValueForField(AttributeError):
    """Indicates a value cannot be retrieved for the field"""


class FieldDefinition(ValueObject):
    __fields__ = [
        ("name", str, "Field name"),
        ("desc", str, "Field description"),
        ("type", type, "Field data type"),
        ("args", FrozenDict[str, InputValue], "Accepted field arguments"),
        ("is_deprecated", bool, "Whether the field is deprecated"),
        ("deprecation_reason", t.Optional[str], "Reason for deprecation"),
    ]

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


class ListMeta(type):
    def __getitem__(self, arg):
        return type("[{.__name__}]".format(arg), (List,), {"__arg__": arg})

    def __instancecheck__(self, instance):
        return isinstance(instance, list) and all(
            isinstance(i, self.__arg__) for i in instance
        )


# Q: why not typing.List?
# A: it doesn't support __doc__, __name__, or isinstance()
class List(object, metaclass=ListMeta):
    __arg__ = object


class NullableMeta(type):
    def __getitem__(self, arg):
        return type(
            "{.__name__} or None".format(arg), (Nullable,), {"__arg__": arg}
        )

    def __instancecheck__(self, instance):
        return instance is None or isinstance(instance, self.__arg__)


# Q: why not typing.Optional?
# A: it is not easily distinguished from Union,
#    and doesn't support __doc__, __name__, or isinstance()
class Nullable(object, metaclass=NullableMeta):
    __arg__ = object


class UnionMeta(type):
    def __instancecheck__(self, instance):
        return isinstance(instance, self.__args__)


# Q: why not typing.Union?
# A: it isn't consistent across python versions,
#    and doesn't support __doc__, __name__, or isinstance()
class Union(object, metaclass=UnionMeta):
    __args__ = ()


class Scalar(object):
    """Base class for scalars"""

    def __gql_dump__(self):
        """Serialize the scalar to a GraphQL primitive value"""
        raise NotImplementedError(
            "GraphQL serialization is not defined for this scalar"
        )

    @classmethod
    def __gql_load__(cls, data):
        """Load a scalar instance from GraphQL"""
        raise NotImplementedError(
            "GraphQL deserialization is not defined for this scalar"
        )


class GenericScalarMeta(type):
    def __instancecheck__(self, instance):
        return isinstance(instance, _PRIMITIVE_TYPES)


class GenericScalar(Scalar, metaclass=GenericScalarMeta):
    """A generic scalar, accepting any primitive type"""


def _unwrap_list_or_nullable(type_):
    # type: t.Type[Nullable, List, Scalar, Enum, InputObject]
    # -> Type[Scalar | Enum | InputObject]
    if issubclass(type_, (Nullable, List)):
        return _unwrap_list_or_nullable(type_.__arg__)
    return type_


def _validate_args(schema, actual):
    # type: (t.Mapping[str, InputValue], t.Mapping[str, object])
    # -> Mapping[str, object]
    invalid_args = actual.keys() - schema.keys()
    if invalid_args:
        raise NoSuchArgument(invalid_args.pop())

    for input_value in schema.values():
        try:
            value = actual[input_value.name]
        except KeyError:
            if issubclass(input_value.type, Nullable):
                continue  # arguments of nullable type may be omitted
            else:
                raise MissingArgument(input_value.name)

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
    for field in selection_set:
        try:
            _validate_field(getattr(cls, field.name, None), field)
        except ValidationError as e:
            raise SelectionError(cls, field.name, e)
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
    elif issubclass(type_, GenericScalar):
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


class SelectionError(ValueObject, ValidationError):
    __fields__ = [
        ("on", type, "Type on which the error occurred"),
        ("path", str, "Path at which the error occurred"),
        ("error", ValidationError, "Original error"),
    ]

    def __str__(self):
        return '{} on "{}" at path "{}":\n\n    {}: {}'.format(
            self.__class__.__name__,
            self.on.__name__,
            self.path,
            self.error.__class__.__name__,
            self.error,
        )


class NoSuchField(ValueObject, ValidationError):
    __fields__ = []

    def __str__(self):
        return "field does not exist"


class NoSuchArgument(ValueObject, ValidationError):
    __fields__ = [("name", str, "(Invalid) argument name")]

    def __str__(self):
        return 'argument "{}" does not exist'.format(self.name)


class InvalidArgumentType(ValueObject, ValidationError):
    __fields__ = [
        ("name", str, "Argument name"),
        ("value", object, "(Invalid) value"),
    ]

    def __str__(self):
        return 'invalid value "{}" of type {} for argument "{}"'.format(
            self.value, type(self.value), self.name
        )


class MissingArgument(ValueObject, ValidationError):
    __fields__ = [("name", str, "Missing argument name")]

    def __str__(self):
        return 'argument "{}" missing (required)'.format(self.name)


class SelectionsNotSupported(ValueObject, ValidationError):
    __fields__ = []

    def __str__(self):
        return "selections not supported on this object"


BUILTIN_SCALARS = {"Boolean": bool, "String": str, "Float": float, "Int": int}

"""Components for typed GraphQL interactions"""
import enum
import typing as t
from itertools import starmap

import six

from .build import InlineFragment
from .utils import FrozenDict, ValueObject

__all__ = [
    # types
    'Enum',
    'Union',
    'GenericScalar',
    'List',
    'Interface',
    'Object',
    'Nullable',
    'FieldDefinition',
    'InputValue',
    # TODO: mutation
    # TODO: subscription

    # validation
    'validate',
    'ValidationError',
    'SelectionError',
    'NoSuchField',
    'NoSuchArgument',
    'SelectionsNotSupported',
    'InvalidArgumentType',
    'MissingArgument',

    'NoValueForField',
    'load',
]


InputValue = t.NamedTuple('InputValue', [
    ('name', str),
    ('desc', str),
    ('type', type),
])

_PRIMITIVE_TYPES = (int, float, bool, six.text_type)


class HasFields(type):
    """metaclass for classes with GraphQL field definitions"""

    def __getitem__(self, selection_set):
        # type: SelectionSet -> InlineFragment
        return InlineFragment(self, validate(self, selection_set))


class Namespace(object):

    def __init__(__self__, **kwargs):
        __self__.__dict__.update(kwargs)

    def __eq__(self, other):
        if type(self) == type(other):
            return self.__dict__ == other.__dict__
        return NotImplemented

    if six.PY2:  # pragma: no cover
        def __ne__(self, other):
            equal = self.__eq__(other)
            return NotImplemented if equal is NotImplemented else not equal

    def __repr__(self):
        return '{}({})'.format(
            getattr(self.__class__, '__qualname__' if six.PY3 else '__name__'),
            ', '.join(starmap('{}={!r}'.format, self.__dict__.items()))
        )


@six.add_metaclass(HasFields)
class Object(Namespace):
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
        ('name', str, 'Field name'),
        ('desc', str, 'Field description'),
        ('type', type, 'Field data type'),
        ('args', FrozenDict[str, InputValue], 'Accepted field arguments'),
        ('is_deprecated', bool, 'Whether the field is deprecated'),
        ('deprecation_reason', t.Optional[str], 'Reason for deprecation'),
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
        return ': {.__name__}\n    {}'.format(self.type, self.desc)


class ListMeta(type):

    def __getitem__(self, arg):
        return type('[{.__name__}]'.format(arg), (List, ), {
            '__arg__': arg
        })

    def __instancecheck__(self, instance):
        return (isinstance(instance, list)
                and all(isinstance(i, self.__arg__) for i in instance))


# Q: why not typing.List?
# A: it doesn't support __doc__, __name__, or isinstance()
@six.add_metaclass(ListMeta)
class List(object):
    __arg__ = object


class NullableMeta(type):

    def __getitem__(self, arg):
        return type('{.__name__} or None'.format(arg), (Nullable, ), {
            '__arg__': arg
        })

    def __instancecheck__(self, instance):
        return instance is None or isinstance(instance, self.__arg__)


# Q: why not typing.Optional?
# A: it is not easily distinguished from Union,
#    and doesn't support __doc__, __name__, or isinstance()
@six.add_metaclass(NullableMeta)
class Nullable(object):
    __arg__ = object


class UnionMeta(type):

    def __instancecheck__(self, instance):
        return isinstance(instance, self.__args__)


# Q: why not typing.Union?
# A: it isn't consistent across python versions,
#    and doesn't support __doc__, __name__, or isinstance()
@six.add_metaclass(UnionMeta)
class Union(object):
    __args__ = ()


class GenericScalarMeta(type):

    def __instancecheck__(self, instance):
        return isinstance(instance, _PRIMITIVE_TYPES)


@six.add_metaclass(GenericScalarMeta)
class GenericScalar(object):
    pass


def _unwrap_list_or_nullable(type_):
    # type: Type[Nullable, List, Scalar, Enum, InputObject]
    # -> Type[Scalar | Enum | InputObject]
    if issubclass(type_, (Nullable, List)):
        return _unwrap_list_or_nullable(type_.__arg__)
    return type_


def _validate_args(schema, actual):
    # type: (Mapping[str, InputValue], Mapping[str, object])
    # -> Mapping[str, object]
    invalid_args = six.viewkeys(actual) - six.viewkeys(schema)
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


# TODO: refactor using singledispatch
def _load(type_, field, value):
    # type: (Type[T], Field, JSON) -> T
    if issubclass(type_, Namespace):
        assert isinstance(value, dict)
        return load(type_, field.selection_set, value)
    elif issubclass(type_, Nullable):
        return None if value is None else _load(type_.__arg__, field, value)
    elif issubclass(type_, List):
        assert isinstance(value, list)
        return [_load(type_.__arg__, field, v) for v in value]
    elif issubclass(type_, _PRIMITIVE_TYPES):
        assert isinstance(value, type_)
        return value
    elif issubclass(type_, GenericScalar):
        assert isinstance(value, type_)
        return value
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
    response: t.Dict[str, JSON]
        The JSON response data

    Returns
    -------
    T
        An instance of ``cls``
    """
    return cls(**{
        field.alias or field.name: _load(
            getattr(cls, field.name).type,
            field,
            response[field.alias or field.name],
        )
        for field in selection_set
    })


class ValidationError(Exception):
    """base class for validation errors"""


class SelectionError(ValueObject, ValidationError):
    __fields__ = [
        ('on', type, 'Type on which the error occurred'),
        ('path', str, 'Path at which the error occurred'),
        ('error', ValidationError, 'Original error'),
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
        return 'field does not exist'


class NoSuchArgument(ValueObject, ValidationError):
    __fields__ = [
        ('name', str, '(Invalid) argument name'),
    ]

    def __str__(self):
        return 'argument "{}" does not exist'.format(self.name)


class InvalidArgumentType(ValueObject, ValidationError):
    __fields__ = [
        ('name', str, 'Argument name'),
        ('value', object, '(Invalid) value'),
    ]

    def __str__(self):
        return 'invalid value "{}" of type {} for argument "foo"'.format(
            self.value,
            type(self.value),
            self.name,
        )


class MissingArgument(ValueObject, ValidationError):
    __fields__ = [
        ('name', str, 'Missing argument name'),
    ]

    def __str__(self):
        return 'argument "{}" missing (required)'.format(self.name)


class SelectionsNotSupported(ValueObject, ValidationError):
    __fields__ = []

    def __str__(self):
        return 'selections not supported on this object'


BUILTIN_SCALARS = {
    "Boolean": bool,
    "String":  str,
    "Float":   float,
    "Int":     int,
}

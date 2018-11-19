"""Components for typed GraphQL interactions"""
import enum
import math
import typing as t
from itertools import starmap

import six

from .build import InlineFragment, dump_inputvalue, escape
from .compat import default_ne
from .utils import FrozenDict, ValueObject

__all__ = [
    # types
    'AnyScalar',
    'Boolean',
    'Enum',
    'FieldDefinition',
    'Float',
    'ID',
    'InputObject',
    'InputObjectFieldDescriptor',
    'InputValue',
    'InputValueDefinition',
    'Int',
    'Interface',
    'List',
    'Nullable',
    'Object',
    'ResponseType',
    'Scalar',
    'String',
    'StringLike',
    'Union',
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

MIN_INT = -2 << 30
MAX_INT = (2 << 30) - 1


InputValueDefinition = t.NamedTuple('InputValueDefinition', [
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

    # prevent `self` from potentially clobbering kwargs
    def __init__(__self__, **kwargs):
        __self__.__dict__.update(kwargs)

    def __eq__(self, other):
        if type(self) == type(other):
            return self.__dict__ == other.__dict__
        return NotImplemented

    if six.PY2:  # pragma: no cover
        __ne__ = default_ne

    def __repr__(self):
        return '{}({})'.format(
            getattr(self.__class__, '__qualname__' if six.PY3 else '__name__'),
            ', '.join(starmap('{}={!r}'.format, self.__dict__.items()))
        )


@six.add_metaclass(HasFields)
class Object(Namespace):
    """a graphQL object"""


class InputObjectFieldDescriptor(ValueObject):
    __fields__ = [
        ('value', InputValueDefinition, 'The input value'),
    ]

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
        return ': {.__name__}\n    {}'.format(self.value.type, self.value.desc)


# TODO: slots?
# TODO: validation?
# TODO: coercing from dict?
# TODO: prevent setting invalid attributes?
class InputObject(object):
    """Base class for input objects"""
    __input_fields__ = {}

    def __init__(__self__, **kwargs):
        self = __self__  # prevents `self` from potentially clobbering kwargs
        argnames_defined = six.viewkeys(self.__input_fields__)
        argnames_required = {
            name for name, obj in six.iteritems(self.__input_fields__)
            if not issubclass(obj.type, Nullable)
        }
        argnames_given = six.viewkeys(kwargs)

        invalid_argnames = argnames_given - argnames_defined
        if invalid_argnames:
            raise NoSuchArgument(
                'invalid arguments: {}'.format(', '.join(invalid_argnames)))

        missing_argnames = argnames_required - argnames_given
        if missing_argnames:
            raise MissingArgument(
                'invalid arguments: {}'.format(', '.join(missing_argnames)))

        self.__dict__.update(kwargs)

    def __eq__(self, other):
        if type(self) == type(other):
            return self.__dict__ == other.__dict__
        return NotImplemented

    if six.PY2:  # pragma: no cover
        __ne__ = default_ne

    def __gql_dump__(self):
        return '{{{}}}'.format(' '.join(
            '{}: {}'.format(name, dump_inputvalue(value))
            for name, value in self.__dict__.items()
        ))

    def __repr__(self):
        return '{}({})'.format(
            getattr(self.__class__, '__qualname__' if six.PY3 else '__name__'),
            ', '.join(starmap('{}={!r}'.format, self.__dict__.items()))
        )


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
        ('args', FrozenDict[str, InputValueDefinition],
         'Accepted field arguments'),
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

    # TODO: a better autogenerated name
    def __getitem__(self, arg):
        return type('[{.__name__}]'.format(arg), (List, ), {
            '__arg__': arg
        })

    def __instancecheck__(self, instance):
        return (isinstance(instance, list)
                and all(isinstance(i, self.__arg__) for i in instance))

    def __eq__(self, other):
        if isinstance(other, ListMeta):
            return self.__arg__ == other.__arg__
        return NotImplemented

    if six.PY2:  # pragma: no cover
        __ne__ = default_ne


# Q: why not typing.List?
# A: it doesn't support __doc__, __name__, or isinstance()
@six.add_metaclass(ListMeta)
class List(object):
    __arg__ = object


class NullableMeta(type):

    # TODO: a better autogenerated name
    def __getitem__(self, arg):
        return type('{.__name__} or None'.format(arg), (Nullable, ), {
            '__arg__': arg
        })

    def __instancecheck__(self, instance):
        return instance is None or isinstance(instance, self.__arg__)

    def __eq__(self, other):
        if isinstance(other, NullableMeta):
            return self.__arg__ == other.__arg__
        return NotImplemented

    if six.PY2:  # pragma: no cover
        __ne__ = default_ne


# Q: why not typing.Optional?
# A: it is not easily distinguished from Union,
#    and doesn't support __doc__, __name__, or isinstance()
@six.add_metaclass(NullableMeta)
class Nullable(object):
    __arg__ = object


# TODO: add __getitem__, similar to list and nullable
class UnionMeta(type):

    def __instancecheck__(self, instance):
        return isinstance(instance, self.__args__)


# Q: why not typing.Union?
# A: it isn't consistent across python versions,
#    and doesn't support __doc__, __name__, or isinstance()
@six.add_metaclass(UnionMeta)
class Union(object):
    __args__ = ()


# TODO: make ABCMeta
# TODO: make generic
class InputValue(object):
    """Base class for input value classes.
    These values may be used in GraphQL queries (requests)"""
    def __init__(self, value):
        self.value = value

    # TODO: make abstract
    def __gql_dump__(self):
        # type: () -> str
        """Serialize the object to a GraphQL primitive value"""
        raise NotImplementedError(
            'GraphQL serialization is not defined for this type')

    # TODO: a sensible default implementation
    @classmethod
    def coerce(cls, value):
        raise NotImplementedError()


# TODO: make ABCMeta
# TODO: make generic
# TODO: rename to indicate it can be the parser, not the value itself?
class ResponseType(object):
    """Base class for response value classes.
    These classes are used to load GraphQL responses into (python) types"""

    # TODO: make abstract?
    @classmethod
    def __gql_load__(cls, data):
        """Load an instance from GraphQL"""
        raise NotImplementedError(
            'GraphQL deserialization is not defined for this type')


class Scalar(InputValue, ResponseType):
    """Base class for scalars"""

class _AnyScalarMeta(type):

    def __instancecheck__(self, instance):
        return isinstance(instance, _PRIMITIVE_TYPES)


# TODO: test, add dump/load implementations
# TODO: rename to AnyScalar?
@six.add_metaclass(_AnyScalarMeta)
class AnyScalar(Scalar):
    """A generic scalar, accepting any primitive type"""
    @classmethod
    def coerce(cls, data):
        return cls(Float.coerce(data))


class Float(InputValue, ResponseType):
    """A GraphQL float object. The main difference with :class:`float`
    is that it may not be infinite or NaN"""
    # TODO: consistent types of exceptions to raise
    @classmethod
    def coerce(cls, value):
        # type: Any -> Float
        if not isinstance(value, (float, int)):
            raise ValueError('Invalid type, must be float or int')
        if math.isnan(value) or math.isinf(value):
            raise ValueError('Float value cannot be infinite or NaN')
        return cls(float(value))

    def __gql_dump__(self):
        return str(self.value)

    @classmethod
    def __gql_load__(cls, data):
        # type: Union[float, int] -> float
        return float(data)


class Int(InputValue, ResponseType):
    """A GraphQL integer object. The main difference with :class:`int`
    is that it may only represent integers up to 32 bits in size"""
    @classmethod
    def coerce(cls, value):
        if not isinstance(value, six.integer_types):
            raise ValueError('Invalid type, must be int')
        if not MIN_INT < value < MAX_INT:
            raise ValueError('{} is not representable by a 32-bit integer'
                             .format(value))
        return cls(int(value))

    def __gql_dump__(self):
        return str(self.value)

    @classmethod
    def __gql_load__(cls, data):
        return data


class Boolean(InputValue, ResponseType):
    """A GraphQL boolean object"""
    @classmethod
    def coerce(cls, value):
        if isinstance(value, bool):
            return cls(value)
        else:
            raise ValueError('A boolean type is required')

    def __gql_dump__(self):
        return 'true' if self.value else 'false'

    # TODO: remove duplication
    @classmethod
    def __gql_load__(cls, data):
        return data


class StringLike(InputValue, ResponseType):
    """Base for string-like types"""
    @classmethod
    def coerce(cls, value):
        if isinstance(value, six.text_type):
            return cls(value)
        elif six.PY2 and isinstance(value, bytes):
            return cls(six.text_type(value))
        else:
            raise ValueError('A string type is required')

    def __gql_dump__(self):
        return '"{}"'.format(escape(self.value))

    # TODO: remove duplication
    @classmethod
    def __gql_load__(cls, data):
        return data


class String(StringLike):
    """GraphQL text type"""


class ID(StringLike):
    """A GraphQL ID. Serialized the same way as a string"""


def _unwrap_list_or_nullable(type_):
    # type: Type[Nullable, List, Scalar, Enum, InputObject]
    # -> Type[Scalar | Enum | InputObject]
    if issubclass(type_, (Nullable, List)):
        return _unwrap_list_or_nullable(type_.__arg__)
    return type_


def _validate_args(schema, actual):
    # type: (Mapping[str, InputValueDefinition], Mapping[str, object])
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
# TODO: cleanup this API: ``field`` is often unneeded. unify with ``load``?
def load_field(type_, field, value):
    # type: (Type[T], Field, JSON) -> T
    if issubclass(type_, Namespace):
        assert isinstance(value, dict)
        return load(type_, field.selection_set, value)
    elif issubclass(type_, Nullable):
        return None if value is None else load_field(
            type_.__arg__, field, value)
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
    response: t.Dict[str, JSON]
        The JSON response data

    Returns
    -------
    T
        An instance of ``cls``
    """
    return cls(**{
        field.alias or field.name: load_field(
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
        return 'invalid value "{}" of type {} for argument "{}"'.format(
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

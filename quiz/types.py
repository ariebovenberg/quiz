"""main module for constructing graphQL queries"""
import enum
import typing as t
from functools import partial
from operator import attrgetter, methodcaller

import six

from .compat import indent, singledispatch
from .utils import Error, FrozenDict, init_last, value_object

NoneType = type(None)
INDENT = "  "

gql = methodcaller("__gql__")

FieldName = str
"""a valid GraphQL fieldname"""

JSON = t.Any
JsonObject = t.Dict[str, JSON]


@singledispatch
def argument_as_gql(obj):
    # type: object -> str
    raise TypeError("cannot serialize to GraphQL: {}".format(type(obj)))


# TODO: IMPORTANT! implement string escape
argument_as_gql.register(str, '"{}"'.format)

# TODO: limit to 32 bit integers!
argument_as_gql.register(int, str)
argument_as_gql.register(NoneType, 'null'.format)
argument_as_gql.register(bool, {True: 'true', False: 'false'}.__getitem__)

# TODO: float, with exponent form


@argument_as_gql.register(enum.Enum)
def _enum_to_gql(obj):
    return obj.value


@value_object
class FieldSchema(object):
    __slots__ = '_values'
    __fields__ = [
        ('name', str),
        ('desc', str),
        ('type', type),
        ('args', FrozenDict),  # TODO: FrozenDict[str, InputValue]
        ('is_deprecated', bool),
        ('deprecation_reason', t.Optional[str]),
    ]

    # TODO: actual descriptor implementation
    def __get__(self, obj, objtype=None):  # pragma: no cover
        return self

    # TODO: actual descriptor implementation
    def __set__(self, obj, value):
        raise NotImplementedError

    # __doc__ allows descriptor to be displayed nicely in help()
    @property
    def __doc__(self):
        return '{.__name__}\n    {}'.format(self.type, self.desc)


# TODO: add fragmentspread
Selection = t.Union['Field', 'InlineFragment']


# TODO: ** operator for specifying fragments
class SelectionSet(t.Iterable[Selection], t.Sized):
    """A "magic" selection set builder"""
    # the attribute needs to have a dunder name to prevent
    # conflicts with GraphQL field names
    __slots__ = '__selections__'

    # Q: why can't this subclass tuple?
    # A: Then we would have unwanted methods like index()

    def __init__(self, *selections):
        self.__selections__ = selections

    # TODO: optimize
    @classmethod
    def _make(cls, selections):
        return cls(*selections)

    def __getattr__(self, name):
        return SelectionSet._make(self.__selections__ + (Field(name), ))

    # TODO: support raw graphql strings
    def __getitem__(self, selection_set):
        # TODO: check duplicate fieldnames
        if not self.__selections__:
            raise Error('cannot select fields from empty field list')

        rest, target = init_last(self.__selections__)

        assert isinstance(selection_set, SelectionSet)
        assert len(selection_set.__selections__) >= 1

        return SelectionSet._make(
            tuple(rest)
            + (target.replace(selection_set=selection_set), ))

    def __repr__(self):
        return "<SelectionSet> {}".format(gql(self))

    # `__self` allows `self` as an argument name
    def __call__(__self, **kwargs):
        if not __self.__selections__:
            raise Error('cannot call empty field list')

        rest, target = init_last(__self.__selections__)

        return SelectionSet._make(
            tuple(rest) + (target.replace(kwargs=FrozenDict(kwargs)), ))

    def __iter__(self):
        return iter(self.__selections__)

    def __len__(self):
        return len(self.__selections__)

    def __gql__(self):
        return '{{\n{}\n}}'.format(
            '\n'.join(
                indent(gql(f), INDENT) for f in self.__selections__
            )
        ) if self.__selections__ else ''

    def __eq__(self, other):
        if isinstance(other, type(self)):
            return other.__selections__ == self.__selections__
        return NotImplemented

    def __ne__(self, other):
        equality = self.__eq__(other)
        return NotImplemented if equality is NotImplemented else not equality

    __hash__ = property(attrgetter('__selections__.__hash__'))


@value_object
class Raw(object):
    __slots__ = '_values'
    __fields__ = [
        ('content', str)
    ]

    def __gql__(self):
        return self.content


@value_object
class Field(object):
    __slots__ = '_values'
    __fields__ = [
        ('name', FieldName),
        ('kwargs', FrozenDict),
        ('selection_set', SelectionSet),
        # in the future:
        # - alias
        # - directives
    ]
    __defaults__ = (FrozenDict.EMPTY, SelectionSet())

    def __gql__(self):
        arguments = '({})'.format(
            ', '.join(
                "{}: {}".format(k, argument_as_gql(v))
                for k, v in self.kwargs.items()
            )
        ) if self.kwargs else ''
        selection_set = (
            ' ' + gql(self.selection_set)
            if self.selection_set else '')
        return self.name + arguments + selection_set


selector = SelectionSet()


class ID(str):
    """represents a unique identifier, often used to refetch an object
    or as the key for a cache. The ID type is serialized in the same way
    as a String; however, defining it as an ID signifies that it is not
    intended to be human-readable"""


BUILTIN_SCALARS = {
    "Boolean": bool,
    "String":  str,
    "ID":      ID,
    "Float":   float,
    "Int":     int,
}


@value_object
class ErrorSet(Error):
    __fields__ = [
        ('errors', t.FrozenSet[Error])
    ]


@value_object
class SelectionError(Error):
    __fields__ = [
        ('on', type),
        ('path', t.Tuple[str, ...]),
        ('error', Error),
    ]


@value_object
class InvalidField(Error):
    __fields__ = []


@value_object
class InvalidArguments(Error):
    __fields__ = [
        ('names', t.Tuple[str, ...]),
    ]


@value_object
class RequiredArgument(Error):
    __fields__ = [
        ('field_name', str),
        ('name', str),
    ]


@value_object
class NoSuchField(Error):
    __fields__ = [
        ('on', str),
        ('name', str),
        ('path', t.Tuple[str, ...]),
    ]
    __defaults__ = ((), )


@value_object
class NoSuchArgument(Error):
    __fields__ = [
        ('on', type),
        ('field', FieldSchema),
        ('name', str),
    ]


@value_object
class InvalidArgumentType(Error):
    __fields__ = [
        ('on', type),
        ('field', FieldSchema),
        ('name', str),
        ('value', object),
    ]


@value_object
class MissingArguments(Error):
    __fields__ = [
        ('names', t.Tuple[str, ...]),
    ]


@value_object
class MissingArgument(Error):
    __fields__ = [
        ('on', type),
        ('field', FieldSchema),
        ('name', str),
    ]


@value_object
class InvalidSelection(Error):
    __fields__ = [
        ('on', type),
        ('field', FieldSchema),
    ]


@value_object
class ErrorResponse(Error):
    __fields__ = [
        ('data', t.Dict[str, JSON]),
        ('errors', t.List[t.Dict[str, JSON]]),
    ]


@value_object
class InlineFragment(object):
    __fields__ = [
        ('on', type),
        ('selection_set', SelectionSet),
    ]
    # in the future: directives

    def __gql__(self):
        return '... on {} {}'.format(
            self.on.__name__,
            gql(self.selection_set)
        )


class OperationType(enum.Enum):
    QUERY = 'query'
    MUTATION = 'mutation'
    SUBSCRIPTION = 'subscription'


@value_object
class Operation(object):
    __slots__ = '_values'
    __fields__ = [
        ('type', OperationType),
        ('selection_set', SelectionSet)
    ]
    __defaults__ = (SelectionSet(), )
    # in the future:
    # - name (optional)
    # - variable_defs (optional)
    # - directives (optional)

    def __gql__(self):
        return '{} {}'.format(self.type.value,
                              gql(self.selection_set))


def _unwrap_list_or_nullable(type_):
    # type: type -> type
    if issubclass(type_, (Nullable, List)):
        return _unwrap_list_or_nullable(type_.__arg__)
    return type_


def _check_args(cls, field, kwargs):
    invalid_args = six.viewkeys(kwargs) - six.viewkeys(field.args)
    if invalid_args:
        raise NoSuchArgument(cls, field, invalid_args.pop())

    for param in field.args.values():
        try:
            value = kwargs[param.name]
        except KeyError:
            if not issubclass(param.type, Nullable):
                raise MissingArgument(cls, field, param.name)
        else:
            if not isinstance(value, param.type):
                raise InvalidArgumentType(
                    cls, field, param.name, value
                )


def _check_field(parent, field):
    assert isinstance(field, Field)
    try:
        schema = getattr(parent, field.name)
    except AttributeError:
        raise NoSuchField(parent, field.name)

    _check_args(parent, schema, field.kwargs)

    for f in field.selection_set:
        _check_field(_unwrap_list_or_nullable(schema.type), f)


def _validate_args(schema, actual):
    # type: (Mapping[str, InputValue], Mapping[str, Any]) -> Mapping[str, Any]
    invalid_args = six.viewkeys(actual) - six.viewkeys(schema)
    if invalid_args:
        raise InvalidArguments(tuple(invalid_args))

    missing_args = {
        name for name, field in schema.items()
        if not issubclass(field.type, Nullable)
    } - six.viewkeys(actual)
    if missing_args:
        raise MissingArguments(tuple(missing_args))

    return actual


def _validate_field(schema, actual):
    # type (FieldSchema, Field) -> FieldCheck
    validated_kwargs = _validate_args(schema.args, actual.kwargs)
    return actual


def validate(cls, selection_set):
    """Validate a selection set against a type

    Parameters
    ----------
    cls: type
        The class to validate against
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
            schema = getattr(cls, field.name)
        except AttributeError:
            raise SelectionError(cls, (field.name, ), InvalidField())

        assert isinstance(schema, FieldSchema)

        try:
            _validate_field(schema, field)
        except Error as e:
            raise SelectionError(cls, (field.name, ), e)

    return selection_set


class CanMakeFragmentMeta(type):

    # TODO: also interfaces, unions can be made into fragments
    def __getitem__(self, selection_set):
        # type: SelectionSet -> InlineFragment
        for field in selection_set:
            _check_field(self, field)
        return InlineFragment(self, selection_set)


# TODO: prevent instantiation?
# assumption: all items in Object.__dict__ are fields
@six.add_metaclass(CanMakeFragmentMeta)
class Object(object):
    """a graphQL object"""


# - InputObject: calling instantiates an instance,
#   results must be instances of the class
class InputObject(object):
    pass


# separate class to distinguish graphql enums from normal Enums
# TODO: include deprecation attributes in instances?
# TODO: a __repr__ which includes the description, deprecation, etc?
class Enum(enum.Enum):
    pass


# TODO: this should be a metaclass
class Interface(object):
    pass


class ListMeta(type):

    def __getitem__(self, arg):
        return type('List[{.__name__}]'.format(arg), (List, ), {
            '__arg__': arg
        })

    def __instancecheck__(self, instance):
        return (isinstance(instance, list)
                and all(isinstance(i, self.__arg__) for i in instance))


@six.add_metaclass(ListMeta)
class List(object):
    __arg__ = object


class NullableMeta(type):

    def __getitem__(self, arg):
        return type('Nullable[{.__name__}]'.format(arg), (Nullable, ), {
            '__arg__': arg
        })

    def __instancecheck__(self, instance):
        return instance is None or isinstance(instance, self.__arg__)


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


@value_object
class Document(object):
    __slots__ = '_values'
    __fields__ = [
        ('operations', t.List[Operation])
        # TODO: fragments
    ]


InputValue = t.NamedTuple('InputValue', [
    ('name', str),
    ('desc', str),
    ('type', type),
])


def query(selection_set, cls):
    """Create a query operation

    Parameters
    ----------
    selection_set: selectionSet
        The selection set
    cls: type
        The query type

    Returns
    -------
    Operation
        The query operation
    """
    for field in selection_set:
        _check_field(cls, field)
    return Operation(OperationType.QUERY, selection_set)


# introspection_query = Operation(
#     OperationType.QUERY,
#     Raw(schema.raw.INTROSPECTION_QUERY)
# )

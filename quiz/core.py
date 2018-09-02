"""Main module for constructing graphQL queries"""
import enum
import re
import typing as t
from operator import attrgetter, methodcaller

import six

from .compat import indent, singledispatch
from .utils import Empty, FrozenDict, compose, init_last, value_object

__all__ = [
    # building graphQL documents
    'SelectionSet',
    'Selection',
    'Field',
    'InlineFragment',
    'Raw',
    'Operation',
    'query',
    'OperationType',
    'validate',

    'FieldDefinition',
    'InputValue',

    # types
    'Enum',
    'Union',
    'List',
    'Interface',
    'Object',
    'Nullable',

    'selector',
    'gql',

    # typing
    'FieldName',
    'JsonObject',
    'JSON',

    # exceptions
    'Error',
    'ErrorResponse',

    'SelectionError',
    'NoSuchField',
    'NoSuchArgument',
    'SelectionsNotSupported',
    'InvalidArgumentType',
    'MissingArgument',

    # utils (low-level)
    'escape',
    'argument_as_gql',
]

INDENT = "  "

gql = methodcaller("__gql__")


@value_object
class FieldDefinition(object):
    __slots__ = '_values'
    __fields__ = [
        ('name', str, 'Field name'),
        ('desc', str, 'Field description'),
        ('type', type, 'Field data type'),
        ('args', FrozenDict[str, 'InputValue'], 'Accepted field arguments'),
        ('is_deprecated', bool, 'Whether the field is deprecated'),
        ('deprecation_reason', t.Optional[str], 'Reason for deprecation'),
    ]

    def __get__(self, obj, objtype=None):  # pragma: no cover
        if obj is None:  # accessing on class
            return self
        raise NotImplementedError()

    def __set__(self, obj, value):
        raise NotImplementedError()

    # __doc__ allows descriptor to be displayed nicely in help()
    @property
    def __doc__(self):
        return ': {.__name__}\n    {}'.format(self.type, self.desc)


class SelectionSet(t.Iterable['Selection'], t.Sized):
    """Sequence of selections

    Parameters
    ----------
    *selections: Selection
        Items in the selection set.

    Notes
    -----
    * Instances are immutable.
    * Extending selection sets is possible through special methods
      (``__getattr__``, ``__call__``, ``__getitem__``)
    """
    # The attribute needs to have a dunder name to prevent
    # conflicts with GraphQL field names.
    # This is also why we can't just subclass `tuple`.
    __slots__ = '__selections__'

    def __init__(self, *selections):
        self.__selections__ = selections

    # TODO: check if actually faster
    # faster, internal, alternative to __init__
    @classmethod
    def _make(cls, selections):
        instance = cls.__new__(cls)
        instance.__selections__ = tuple(selections)
        return instance

    def __getattr__(self, fieldname):
        """Add a new field to the selection set.

        Parameters
        ----------
        fieldname: str
            The name of the field to add.

        Returns
        -------
        SelectionSet
            A selection set with the new field added to the end.

        Example
        -------

        This functionality can be used to quickly create a sequence of fields:

        >>> _ = SelectionSet()
        >>> (
        ...     _
        ...     .foo
        ...     .bar
        ...     .bing
        ... )
        <SelectionSet> {
          foo
          bar
          bing
        }
        """
        return SelectionSet._make(self.__selections__ + (Field(fieldname), ))

    def __getitem__(self, selections):
        """Add a sub-selection to the last field in the selection set

        Parameters
        ----------
        selections: SelectionSet
            The selection set to nest

        Example
        -------

        >>> _ = SelectionSet()
        >>> (
        ...     _
        ...     .foo
        ...     .bar[
        ...         _
        ...         .qux
        ...         .bing
        ...     ]
        ...     .other_field
        ... )
        <SelectionSet> {
          foo
          bar {
            qux
            bing
          }
          other_field
        }

        Returns
        -------
        SelectionSet
            A selection set with selections added to the last field.

        Raises
        ------
        Error
            In case the selection set is empty
        """
        try:
            rest, target = init_last(self.__selections__)
        except Empty:
            raise Error('cannot select fields from empty field list')

        assert isinstance(selections, SelectionSet)
        assert len(selections.__selections__) >= 1

        return SelectionSet._make(
            tuple(rest)
            + (target.replace(selection_set=selections), ))

    def __repr__(self):
        return "<SelectionSet> {}".format(gql(self))

    # Positional arguments are retrieved manually from *args.
    # This ensures there can be no conflict with (named) **kwargs.
    # Otherwise, something like `self` could not be given as a keyword arg.
    def __call__(*args, **kwargs):
        """The selection set may be called in two distinct ways:

        1. With keyword arguments ``**kwargs``.
           These will be added as arguments to the last field
           in the selection set.
        2. With a single ``alias`` argument. This has the affect of adding
           an alias to the next field in the selection set.

        Parameters
        ----------
        alias: str, optional
            If given, the next field in the selection set will get this alias.

            Example
            -------

            >>> _ = SelectionSet()
            >>> selection = (
            ...     _
            ...     .foo
            ...     ('my_alias').bla
            ...     .other_field
            ... )
            <SelectionSet> {
               foo
               my_alias: bla
               other_field
            }

            Note
            ----
            The alias can only be specified as a :term:`positional argument`,
            and may not be combined with ``**kwargs``.

        **kwargs
            Adds arguments to the previous field in the chain

            Example
            -------

            >>> _ = SelectionSet()
            >>> (
            ...     _
            ...     .foo
            ...     .bla(a=4, b='qux')
            ...     .other_field
            ... )
            <SelectionSet> {
              foo
              bla(a: 4, b: "qux")
              other_field
            }

            Note
            ----
            Each field argument must be a :term:`keyword argument`.

        Returns
        -------
        SelectionSet
            The new selection set

        Raises
        ------
        Error
            In case field arguments are given, but the selection set is empty
        """
        # TODO: check alias validity
        try:
            self, alias = args
        except ValueError:
            # alias is *not* given --> case 1
            self, = args
            return self.__add_kwargs(kwargs)
        else:
            # alias is given --> case 2
            return _AliasForNextField(*args)

    def __add_kwargs(self, args):
        try:
            rest, target = init_last(self.__selections__)
        except Empty:
            raise Error('cannot call empty field list')

        return SelectionSet._make(
            tuple(rest) + (target.replace(kwargs=FrozenDict(args)), ))

    def __iter__(self):
        """Iterate over the selection set contents

        Returns
        -------
        Iterator[Selection]
            An iterator over selections
        """
        return iter(self.__selections__)

    def __len__(self):
        """Number of items in the selection set

        Returns
        -------
        int
            The number of items in the selection set
        """
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


class _AliasForNextField(object):
    __slots__ = '__selection_set', '__alias'

    def __init__(self, selection_set, alias):
        self.__selection_set = selection_set
        self.__alias = alias

    def __getattr__(self, fieldname):
        return SelectionSet._make(
            self.__selection_set.__selections__
            + (Field(fieldname, alias=self.__alias), )
        )


selector = SelectionSet()


@value_object
class Raw(object):
    __slots__ = '_values'
    __fields__ = [
        ('content', str, 'The raw GraphQL content')
    ]

    def __gql__(self):
        return self.content


@value_object
class Field(object):
    __slots__ = '_values'
    __fields__ = [
        ('name', 'FieldName', 'Field name'),
        ('kwargs', FrozenDict, 'Given arguments'),
        ('selection_set', SelectionSet, 'Selection of subfields'),
        ('alias', t.Optional[str], 'Field alias'),
        # in the future:
        # - directives
    ]
    __defaults__ = (FrozenDict.EMPTY, SelectionSet(), None)

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


class Error(Exception):
    """Base error class"""


@value_object
class SelectionError(Error):
    __fields__ = [
        ('on', type, 'Type on which the error occurred'),
        ('path', str, 'Path at which the error occurred'),
        ('error', Error, 'Original error'),
    ]


@value_object
class NoSuchField(Error):
    __fields__ = []


@value_object
class NoSuchArgument(Error):
    __fields__ = [
        ('name', str, '(Invalid) argument name'),
    ]


@value_object
class InvalidArgumentType(Error):
    __fields__ = [
        ('name', str, 'Argument name'),
        ('value', object, '(Invalid) value'),
    ]


@value_object
class MissingArgument(Error):
    __fields__ = [
        ('name', str, 'Missing argument name'),
    ]


@value_object
class SelectionsNotSupported(Error):
    __fields__ = []


@value_object
class ErrorResponse(Error):
    __fields__ = [
        ('data', t.Dict[str, 'JSON'], 'Data returned in the response'),
        ('errors', t.List[t.Dict[str, 'JSON']],
         'Errors returned in the response'),
    ]


@value_object
class InlineFragment(object):
    __fields__ = [
        ('on', type, 'Type of the fragment'),
        ('selection_set', SelectionSet, 'Subfields of the fragment'),
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
        ('type', OperationType, 'Type of the operation'),
        ('selection_set', SelectionSet, 'Fields selection')
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
        if not issubclass(type_, (Object, Interface)):
            raise SelectionsNotSupported()
        validate(type_, actual.selection_set)
    return actual


def validate(cls, selection_set):
    """Validate a selection set against a type

    Parameters
    ----------
    cls: Type[Object, Interface]
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
        except Error as e:
            raise SelectionError(cls, field.name, e)
    return selection_set


class CanMakeFragmentMeta(type):

    def __getitem__(self, selection_set):
        # type: SelectionSet -> InlineFragment
        return InlineFragment(self, validate(self, selection_set))


@six.add_metaclass(CanMakeFragmentMeta)
class Object(object):
    """a graphQL object"""


# - InputObject: calling instantiates an instance,
#   results must be instances of the class
class InputObject(object):
    pass


# separate class to distinguish graphql enums from normal Enums
class Enum(enum.Enum):
    pass


class Interface(object):
    pass


class ListMeta(type):

    def __getitem__(self, arg):
        return type('[{.__name__}]'.format(arg), (List, ), {
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
        return type('{.__name__} or None'.format(arg), (Nullable, ), {
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
        ('operations', t.List[Operation], 'List of operations')
        # future: fragments
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
    return Operation(OperationType.QUERY, validate(cls, selection_set))


_ESCAPE_PATTERNS = {
    '\b': r'\b',
    '\f': r'\f',
    '\n': r'\n',
    '\r': r'\r',
    '\t': r'\t',
    '\\': r'\\',
    '"':  r'\"',
}
_ESCAPE_RE = re.compile('|'.join(map(re.escape, _ESCAPE_PATTERNS)))


def _escape_match(match):
    return _ESCAPE_PATTERNS[match.group(0)]


def escape(txt):
    """Escape a string according to GraphQL specification

    Parameters
    ----------
    txt: str
        The string to escape

    Returns
    -------
    str
        the escaped string
    """
    return _ESCAPE_RE.sub(_escape_match, txt)


@singledispatch
def argument_as_gql(obj):
    # type: object -> str
    raise TypeError("cannot serialize to GraphQL: {}".format(type(obj)))


argument_as_gql.register(str, compose('"{}"'.format, escape))
argument_as_gql.register(int, str)
argument_as_gql.register(type(None), 'null'.format)
argument_as_gql.register(bool, {True: 'true', False: 'false'}.__getitem__)
argument_as_gql.register(float, str)


@argument_as_gql.register(Enum)
def _enum_to_gql(obj):
    return obj.value


Selection = t.Union[Field, InlineFragment]
"""Field or inline fragment"""
FieldName = str
"""Valid GraphQL fieldname"""
JSON = t.NewType('JSON', t.Any)
"""JSON serializable data"""
JsonObject = t.Dict[str, JSON]
"""Dictionary of strings to JSON serializable data"""


class ID(str):
    """Represents a unique identifier, often used to refetch an object
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

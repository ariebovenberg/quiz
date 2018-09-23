"""Main module for constructing graphQL queries"""
import enum
import re
import typing as t
from operator import attrgetter, methodcaller

from .compat import indent, singledispatch
from .utils import FrozenDict, ValueObject, compose, init_last

__all__ = [
    # building graphQL documents
    'SelectionSet',
    'Selection',
    'Field',
    'InlineFragment',
    'Raw',
    'Query',
    'SELECTOR',

    # render
    'gql',
    'escape',
    'argument_as_gql',
]

INDENT = "  "

gql = methodcaller("__gql__")


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
        >>> str(
        ...     _
        ...     .foo
        ...     .bar
        ...     .bing
        ... )
        {
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
        >>> str(
        ...     _
        ...     .foo
        ...     .bar[
        ...         _
        ...         .qux
        ...         .bing
        ...     ]
        ...     .other_field
        ... )
        {
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
        utils.Empty
            In case the selection set is empty
        """
        rest, target = init_last(self.__selections__)

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
            >>> str(
            ...     _
            ...     .foo
            ...     ('my_alias').bla
            ...     .other_field
            ... )
            {
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
            >>> str(
            ...     _
            ...     .foo
            ...     .bla(a=4, b='qux')
            ...     .other_field
            ... )
            {
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
        utils.Empty
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
        rest, target = init_last(self.__selections__)
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

    def __str__(self):
        """The selection set as raw graphQL"""
        return self.__gql__()

    def __gql__(self):
        return '{{\n{}\n}}'.format(
            '\n'.join(indent(gql(f), INDENT) for f in self)
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


SELECTOR = SelectionSet()
"""An empty, extendable :class:`SelectionSet`"""


class Raw(ValueObject):
    __fields__ = [
        ('content', str, 'The raw GraphQL content')
    ]

    def __gql__(self):
        return self.content


class Field(ValueObject):
    __fields__ = [
        ('name', str, 'Field name'),
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
        alias = self.alias + ': ' if self.alias else ''
        return alias + self.name + arguments + selection_set


class InlineFragment(ValueObject):
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


class Query(ValueObject):
    __fields__ = [
        ('cls', type, 'The query class'),
        ('selections', SelectionSet, 'Fields selection')
    ]
    # in the future:
    # - name (optional)
    # - variable_defs (optional)
    # - directives (optional)

    def __gql__(self):
        return 'query ' + gql(self.selections)

    def __str__(self):
        return self.__gql__()


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


@argument_as_gql.register(enum.Enum)
def _enum_to_gql(obj):
    return obj.value


Selection = t.Union[Field, InlineFragment]
"""Field or inline fragment"""

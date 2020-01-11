"""Main module for constructing graphQL queries"""
import enum
import re
import typing as t
from dataclasses import dataclass, replace
from functools import singledispatch
from operator import attrgetter, methodcaller
from textwrap import indent

from .utils import FrozenDict, compose, init_last, add_slots

__all__ = [
    "Field",
    "InlineFragment",
    "Query",
    "Raw",
    "_",
    "SELECTOR",
    "Selection",
    "SelectionSet",
    "dump_inputvalue",
    "escape",
    "gql",
]

INDENT = "  "

gql = methodcaller("__gql__")


class SelectionSet(t.Iterable["Selection"], t.Sized):
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
    __slots__ = "__selections__"

    def __init__(self, *selections):
        self.__selections__ = selections

    # TODO: check if actually faster
    # faster, internal, alternative to __init__
    @classmethod
    def __make__(cls, selections):
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
        return SelectionSet.__make__(self.__selections__ + (Field(fieldname),))

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

        return SelectionSet.__make__(
            tuple(rest) + (replace(target, selection_set=selections),)
        )

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
            (self,) = args
            return self.__add_kwargs(kwargs)
        else:
            # alias is given --> case 2
            return _AliasForNextField(*args)

    def __add_kwargs(self, args):
        rest, target = init_last(self.__selections__)
        return SelectionSet.__make__(
            tuple(rest) + (replace(target, kwargs=FrozenDict(args)),)
        )

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
        return (
            "{{\n{}\n}}".format(
                "\n".join(indent(gql(f), INDENT) for f in self)
            )
            if self.__selections__
            else ""
        )

    def __eq__(self, other):
        if isinstance(other, type(self)):
            return other.__selections__ == self.__selections__
        return NotImplemented

    __hash__ = property(attrgetter("__selections__.__hash__"))


@add_slots
@dataclass(frozen=True)
class _AliasForNextField:
    __selection_set: SelectionSet
    __alias: str

    def __getattr__(self, fieldname: str) -> SelectionSet:
        return SelectionSet.__make__(
            self.__selection_set.__selections__
            + (Field(fieldname, alias=self.__alias),)
        )


_ = SELECTOR = SelectionSet()
"""An empty, extendable :class:`SelectionSet`"""


@add_slots
@dataclass(frozen=True)
class Raw:
    content: str

    def __gql__(self):
        return self.content


@add_slots
@dataclass(frozen=True)
class Field:
    name: str
    kwargs: FrozenDict = FrozenDict.EMPTY
    selection_set: SelectionSet = SelectionSet()
    alias: t.Optional[str] = None
    # in the future:
    # - directives

    def __gql__(self):
        arguments = (
            "({})".format(
                ", ".join(
                    "{}: {}".format(k, dump_inputvalue(v))
                    for k, v in self.kwargs.items()
                )
            )
            if self.kwargs
            else ""
        )
        selection_set = (
            " " + gql(self.selection_set) if self.selection_set else ""
        )
        alias = self.alias + ": " if self.alias else ""
        return alias + self.name + arguments + selection_set


@add_slots
@dataclass(frozen=True)
class InlineFragment:
    on: type
    selection_set: SelectionSet
    # in the future: directives

    def __gql__(self):
        return "... on {} {}".format(self.on.__name__, gql(self.selection_set))


@add_slots
@dataclass(frozen=True)
class Query:
    cls: type
    selections: SelectionSet
    # in the future:
    # - name (optional)
    # - variable_defs (optional)
    # - directives (optional)

    def __gql__(self):
        return "query " + gql(self.selections)

    def __str__(self):
        return self.__gql__()


_ESCAPE_PATTERNS = {
    "\b": r"\b",
    "\f": r"\f",
    "\n": r"\n",
    "\r": r"\r",
    "\t": r"\t",
    "\\": r"\\",
    '"': r"\"",
}
_ESCAPE_RE = re.compile("|".join(map(re.escape, _ESCAPE_PATTERNS)))


def _escape_match(match):
    return _ESCAPE_PATTERNS[match.group(0)]


def escape(txt: str) -> str:
    "Escape a string according to GraphQL specification"
    return _ESCAPE_RE.sub(_escape_match, txt)


@singledispatch
def dump_inputvalue(obj) -> str:
    """Dumpy any input value to GraphQL"""
    try:
        # consistent with other dunder methods, we look it up on the class
        serializer = type(obj).__gql_dump__
    except AttributeError:
        raise TypeError("Cannot serialize to GraphQL: {}".format(type(obj)))
    else:
        return serializer(obj)


# see https://facebook.github.io/graphql/June2018/#sec-Input-Values
dump_inputvalue.register(str, compose('"{}"'.format, escape))
dump_inputvalue.register(int, str)  # TODO: catch > 32bit integers
dump_inputvalue.register(type(None), "null".format)
dump_inputvalue.register(bool, {True: "true", False: "false"}.__getitem__)
dump_inputvalue.register(float, str)  # TODO: catch NaN, inf


@dump_inputvalue.register(list)
def _list_to_gql(lst):
    return "[{}]".format(" ".join(map(dump_inputvalue, lst)))


@dump_inputvalue.register(enum.Enum)
def _enum_to_gql(obj):
    return obj.value


Selection = t.Union[Field, InlineFragment]
"""Field or inline fragment"""

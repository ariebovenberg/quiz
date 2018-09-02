"""Common utilities and boilerplate"""
import sys
import typing as t
from collections import namedtuple
from itertools import chain, starmap
from operator import attrgetter

import six

from .compat import PY2

__all__ = [
    'JSON',
    'Empty',
]

T1 = t.TypeVar('T1')
T2 = t.TypeVar('T2')


JSON = t.Union[str, int, float, bool, None,
               t.Dict[str, 'JSON'], t.List['JSON']]


def identity(obj):
    return obj


class FrozenDict(t.Mapping[T1, T2]):
    # see https://stackoverflow.com/questions/45864273
    if not (3, 7) > sys.version_info > (3, 4):  # pragma: no cover
        __slots__ = '_inner'

    def __init__(self, inner):
        self._inner = inner if isinstance(inner, dict) else dict(inner)

    __len__ = property(attrgetter('_inner.__len__'))
    __iter__ = property(attrgetter('_inner.__iter__'))
    __getitem__ = property(attrgetter('_inner.__getitem__'))
    __repr__ = property(attrgetter('_inner.__repr__'))

    def __hash__(self):
        return hash(frozenset(self._inner.items()))

    if PY2:  # pragma: no cover
        viewkeys = property(attrgetter('_inner.viewkeys'))


FrozenDict.EMPTY = FrozenDict({})


def merge(*dicts):
    """merge several mappings"""
    if dicts:
        return type(dicts[0])(
            chain.from_iterable(map(six.iteritems, dicts)))
    else:
        return {}


class Empty(Exception):
    """indicates a given list is unexpectedly empty"""


def init_last(items):
    # type: List[T] -> (List[T], T)
    """Return the first items and last item from a list

    Raises
    ------
    Empty
        if the given list is empty
    """
    try:
        return items[:-1], items[-1]
    except IndexError:
        raise Empty


class _ValueObjectMeta(type(t.Generic)):
    """Metaclass for ``ValueObject``"""

    def __new__(self, name, bases, dct):
        cls = super(_ValueObjectMeta, self).__new__(self, name, bases, dct)

        # skip the ``ValueObject`` class itself
        if bases == (object, ):
            return cls

        fieldnames = [n for n, _, _ in cls.__fields__]
        assert 'replace' not in fieldnames
        cls.__namedtuple_cls__ = namedtuple(
            '_' + name,
            [n for n, _, _ in cls.__fields__],
        )
        cls.__namedtuple_cls__.__new__.__defaults__ = getattr(
            cls, '__defaults__', ())
        for name, _, doc in cls.__fields__:
            setattr(cls, name, property(attrgetter('_values.' + name),
                                        doc=doc))

        return cls


@six.add_metaclass(_ValueObjectMeta)
class ValueObject(object):
    """Base class for "value object"-like classes,
    similar to frozen dataclasses in python 3.7+

    Example
    -------

    >>> class Foo(ValueObject, ...):
    ...     __slots__ = '_values'  # optional
    ...     __fields__ = [
    ...         ('foo', int, 'the foo'),
    ...         ('bla', str, 'description for bla'),
    ...     ]
    ...
    >>> f = Foo(4, bla='foo')
    >>> f
    Foo(foo=4, bla='foo')

    """
    __slots__ = ()

    def __init__(self, *args, **kwargs):
        self._values = self.__namedtuple_cls__(*args, **kwargs)

    def replace(self, **kwargs):
        """Create a new instance, with certain fields replaced with new values

        Parameters
        ----------
        **kwargs
            Updated field values

        Example
        -------
        >>> my_object
        MyObject(a=5, b="qux")
        >>> my_object.replace(b="new!")
        MyObject(a=5, b="new!")

        """
        new = type(self).__new__(type(self))
        new._values = self._values._replace(**kwargs)
        return new

    def __eq__(self, other):
        if type(self) is type(other):
            return self._values == other._values
        return NotImplemented

    def __ne__(self, other):
        if type(self) is type(other):
            return self._values != other._values
        return NotImplemented

    def __repr__(self):
        try:
            return '{}({})'.format(
                getattr(self.__class__, '__name__' if PY2 else '__qualname__'),
                ', '.join(starmap('{}={!r}'.format,
                                  zip(self._values._fields, self._values)))
            )
        except Exception:
            return object.__repr__(self)

    __hash__ = property(attrgetter('_values.__hash__'))


class compose(object):
    """compose a function from a chain of functions
    Parameters
    ----------
    *funcs
        callables to compose
    Note
    ----
    * if given no functions, acts as an identity function
    """
    def __init__(self, *funcs):
        self.funcs = funcs
        self.__wrapped__ = funcs[-1] if funcs else identity

    def __call__(self, *args, **kwargs):
        if not self.funcs:
            return identity(*args, **kwargs)
        tail, head = self.funcs[:-1], self.funcs[-1]
        value = head(*args, **kwargs)
        for func in reversed(tail):
            value = func(value)
        return value

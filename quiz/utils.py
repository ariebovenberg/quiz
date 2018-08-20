import sys
import typing as t
from collections import namedtuple
from itertools import chain, starmap
from operator import attrgetter

import six

from .compat import PY2

T1 = t.TypeVar('T1')
T2 = t.TypeVar('T2')


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


def replace(self, **kwargs):
    new = type(self).__new__(type(self))
    new._values = self._values._replace(**kwargs)
    return new


def __init__(self, *args, **kwargs):
    self._values = self.__namedtuple_cls__(*args, **kwargs)


def __eq__(self, other):
    if isinstance(other, type(self)):
        return self._values == other._values
    return NotImplemented


def __ne__(self, other):
    equality = self.__eq__(other)
    return NotImplemented if equality is NotImplemented else not equality


def __repr__(self):
    try:
        return '{}({})'.format(
            self.__class__.__name__ if PY2 else self.__class__.__qualname__,
            ', '.join(starmap('{}={!r}'.format,
                              zip(self._values._fields, self._values)))
        )
    except Exception:
        return object.__repr__(self)


def value_object(cls):
    """Decorate a class to make it a namedtuple-like class.

    Decorated classes get:
    * a ``replace()`` method
    * ``__repr__``, ``__eq__``, ``__ne__``, ``__init__``, ``__hash__``

    Example
    -------

    >>> @utils.value_object
    ... class Foo(...):
    ...     __slots__ = '_values'  # optional
    ...     __fields__ = [
    ...         ('foo', int),
    ...         ('bla', str),
    ...     ]
    ...
    >>> f = Foo(4, bla='foo')
    >>> f
    Foo(foo=4, bla='foo')

    """
    fieldnames = [n for n, _ in cls.__fields__]
    assert 'replace' not in fieldnames
    cls.__namedtuple_cls__ = namedtuple(
        '_' + cls.__name__,
        [n for n, _ in cls.__fields__],
    )
    cls.__namedtuple_cls__.__new__.__defaults__ = getattr(
        cls, '__defaults__', ())
    cls.__init__ = __init__
    cls.__eq__ = __eq__
    cls.__ne__ = __ne__
    cls.__repr__ = __repr__
    cls.__hash__ = property(attrgetter('_values.__hash__'))
    cls.replace = replace
    for name, _ in cls.__fields__:
        setattr(cls, name, property(attrgetter('_values.' + name)))

    return cls


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

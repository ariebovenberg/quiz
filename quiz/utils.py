"""Common utilities and boilerplate"""
import sys
import typing as t
from functools import partial
from itertools import chain
from operator import attrgetter

import attr
import six

from .compat import PY2

__all__ = [
    'JSON',
    'Empty',
]

T = t.TypeVar('T')
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
    # type: (t.List[T]) -> t.Tuple[t.List[T], T]
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


dataclass = partial(attr.s, frozen=True, slots=True)


def field(doc, **kwargs):
    return attr.ib(metadata={'doc': doc}, **kwargs)

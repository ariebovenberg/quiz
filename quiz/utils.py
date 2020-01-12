"""Common utilities and boilerplate"""
import sys
import typing as t
from dataclasses import fields
from itertools import chain
from operator import attrgetter, methodcaller

__all__ = ["JSON", "Empty"]

T = t.TypeVar("T")
T1 = t.TypeVar("T1")
T2 = t.TypeVar("T2")


JSON = t.Union[
    str, int, float, bool, None, t.Dict[str, "JSON"], t.List["JSON"]
]


def identity(obj):
    return obj


class FrozenDict(t.Mapping[T1, T2]):
    # see https://stackoverflow.com/questions/45864273
    if sys.version_info > (3, 7):  # pragma: no cover
        __slots__ = "_inner"

    def __init__(self, inner):
        self._inner = inner if isinstance(inner, dict) else dict(inner)

    __len__ = property(attrgetter("_inner.__len__"))
    __iter__ = property(attrgetter("_inner.__iter__"))
    __getitem__ = property(attrgetter("_inner.__getitem__"))
    __repr__ = property(attrgetter("_inner.__repr__"))

    def __hash__(self):
        return hash(frozenset(self._inner.items()))


FrozenDict.EMPTY = FrozenDict({})


def merge(*dicts):
    """merge several mappings"""
    if dicts:
        return type(dicts[0])(
            chain.from_iterable(map(methodcaller("items"), dicts))
        )
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


def _dataclass_getstate(self):
    return [getattr(self, f.name) for f in fields(self)]


def _dataclass_setstate(self, state):
    for field, value in zip(fields(self), state):
        # use setattr because dataclass may be frozen
        object.__setattr__(self, field.name, value)


# adapted from github.com/ericvsmith/dataclasses
def add_slots(cls):
    # Need to create a new class, since we can't set __slots__
    #  after a class has been created.

    # Make sure __slots__ isn't already set.
    if "__slots__" in cls.__dict__:  # pragma: no cover
        raise TypeError(f"{cls.__name__} already specifies __slots__")

    # Create a new dict for our new class.
    cls_dict = dict(cls.__dict__)
    field_names = tuple(f.name for f in fields(cls))
    cls_dict["__slots__"] = field_names
    for field_name in field_names:
        # Remove our attributes, if present. They'll still be
        #  available in _MARKER.
        cls_dict.pop(field_name, None)
    # Remove __dict__ itself.
    cls_dict.pop("__dict__", None)
    # And finally create the class.
    qualname = getattr(cls, "__qualname__", None)
    cls = type(cls)(cls.__name__, cls.__bases__, cls_dict)
    if qualname is not None:  # pragma: no cover
        cls.__qualname__ = qualname
    cls.__getstate__ = _dataclass_getstate
    cls.__setstate__ = _dataclass_setstate
    return cls

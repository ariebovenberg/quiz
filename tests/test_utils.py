import pytest

from quiz import utils
from quiz.compat import PY3

from .helpers import AlwaysEquals, NeverEquals


class TestNamedtupleData:

    def test_simple(self):

        @utils.value_object
        class Foo(object):
            __slots__ = '_values'
            __fields__ = [
                ('foo', int),
                ('bla', str),
            ]

        if PY3:
            Foo.__qualname__ = 'my_module.Foo'

        instance = Foo(4, bla='foo')

        assert instance == Foo(4, bla='foo')
        assert not instance == Foo(4, bla='blabla')
        assert instance == AlwaysEquals()
        assert not instance == NeverEquals()

        assert instance != Foo(4, bla='blabla')
        assert not instance != Foo(4, bla='foo')
        assert instance != NeverEquals()
        assert not instance != AlwaysEquals()

        assert instance.replace(foo=5) == Foo(5, bla='foo')
        assert instance.replace() == instance

        assert instance.foo == 4
        assert instance.bla == 'foo'

        with pytest.raises(AttributeError, match='blabla'):
            instance.blabla

        with pytest.raises(AttributeError, match="can't set"):
            instance.foo = 6

        if PY3:
            assert repr(instance) == 'my_module.Foo(foo=4, bla=\'foo\')'
        else:
            assert repr(instance) == 'Foo(foo=4, bla=\'foo\')'

    def test_defaults(self):

        @utils.value_object
        class Foo(object):
            __fields__ = [
                ('foo', int),
                ('bla', str),
                ('qux', float),
            ]
            __defaults__ = ('', 1.0)

        assert Foo(4) == Foo(4, '', 1.0)
        assert Foo(4, 'bla', 1.1) == Foo(4, 'bla', 1.1)

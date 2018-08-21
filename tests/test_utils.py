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

        assert hash(instance) == hash(instance.replace())
        assert hash(instance) != hash(instance.replace(foo=5))

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

        # repr should never fail, even if everything is wrong
        del instance._values
        repr(instance)

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


class TestMergeMappings:

    def test_empty(self):
        assert utils.merge() == {}

    def test_single(self):
        assert utils.merge({'foo': 4}) == {'foo': 4}

    def test_multiple(self):
        result = utils.merge(
            utils.FrozenDict({'foo': 5}),
            {'foo': 9, 'bla': 2},
            {'blabla': 1}
        )
        assert isinstance(result, utils.FrozenDict)
        assert result == {
            'foo': 9, 'bla': 2, 'blabla': 1
        }


class TestInitList:

    def test_simple(self):
        assert utils.init_last([1, 2, 3, 4, 5]) == ([1, 2, 3, 4], 5)

    def test_empty(self):
        with pytest.raises(utils.Empty):
            utils.init_last([])


class TestCompose:

    def test_empty(self):
        obj = object()
        func = utils.compose()
        assert func(obj) is obj
        assert isinstance(func.funcs, tuple)
        assert func.funcs == ()

    def test_one_func_with_multiple_args(self):
        func = utils.compose(int)
        assert func('10', base=5) == 5
        assert isinstance(func.funcs, tuple)
        assert func.funcs == (int, )

    def test_multiple_funcs(self):
        func = utils.compose(str, lambda x: x + 1, int)
        assert isinstance(func.funcs, tuple)
        assert func('30', base=5) == '16'
